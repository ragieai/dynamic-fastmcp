import re
import multiprocessing
import socket
import time
from typing import Generator
from httpx import AsyncClient
import pytest
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.session import ClientSession
import uvicorn


def run_server(port: int) -> None:
    from dynamic_fastmcp.main import app

    server = uvicorn.Server(
        config=uvicorn.Config(app=app, host="127.0.0.1", port=port, log_level="debug")
    )
    print(f"Starting server on port {port}")
    server.run()


@pytest.fixture
def server_port() -> int:
    """Get a free port for testing."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# Credit: https://github.com/modelcontextprotocol/python-sdk
@pytest.fixture
def server_transport(server_port: int) -> Generator[str, None, None]:
    """Start server in a separate process with specified MCP instance and transport.

    Args:
        server_port: Port to run the server on

    Yields:
        str: The transport type ('sse' or 'streamable_http')
    """
    proc = multiprocessing.Process(
        target=run_server,
        args=(server_port,),
        daemon=True,
    )
    proc.start()

    # Wait for server to be running
    max_attempts = 20
    attempt = 0
    while attempt < max_attempts:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(("127.0.0.1", server_port))
                break
        except ConnectionRefusedError:
            time.sleep(0.1)
            attempt += 1
    else:
        raise RuntimeError(f"Server failed to start after {max_attempts} attempts")

    yield "streamable-http"

    proc.kill()
    proc.join(timeout=2)
    if proc.is_alive():
        print("Server process failed to terminate")


@pytest.mark.asyncio
async def test_mount(server_transport: str, server_port: int):
    async with AsyncClient(base_url=f"http://127.0.0.1:{server_port}") as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "Hello World"}

    async with streamablehttp_client(
        url=f"http://127.0.0.1:{server_port}/mcp/123",
        headers={"Authorization": "Bearer test"},
    ) as client:
        read_stream, write_stream, get_session_id = client

        async with ClientSession(read_stream, write_stream) as session:
            result = await session.initialize()
            tools_result = await session.list_tools()

            tools = tools_result.tools
            assert len(tools) == 2

            assert tools[0].name == "dynamic_echo"
            assert tools[0].description
            assert re.match(
                r"Echoes the input text: ([0-9a-fA-F-]{36}) \(path: 123\)",
                tools[0].description,
            )

            assert tools[1].name == "echo"
            assert tools[1].description == "Echoes the input text"
