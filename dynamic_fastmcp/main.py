import contextlib
import logging
from typing import Protocol
import uuid
from fastapi import FastAPI
from pydantic import AnyHttpUrl
from starlette.applications import Starlette
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.auth.provider import TokenVerifier, AccessToken
from mcp.server.auth.settings import AuthSettings

from dynamic_fastmcp.dynamic_fastmcp import DynamicFastMCP, DynamicTool


logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def lifespan(app: Starlette):
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(mcp.session_manager.run())
        yield


app = FastAPI(title="Test Server", lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "Hello World"}


class TestTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        if token != "test":
            return None

        return AccessToken(token=token, client_id=str(uuid.uuid4()), scopes=[])


mcp = DynamicFastMCP(
    streamable_http_path="/",
    token_verifier=TestTokenVerifier(),
    auth=AuthSettings(
        resource_server_url=AnyHttpUrl("https://example.com"),
        issuer_url=AnyHttpUrl("https://example.com"),
    ),
)


@mcp.tool(description="Echoes the input text")
def echo(text: str, ctx: Context):
    request = ctx.request_context.request
    assert request is not None, "Expected request to be set"
    return f"Echo to user ({request.user.username}): {text}"


@mcp.tool()
class DynamicEcho(DynamicTool):
    def name(self) -> str:
        return "dynamic_echo"

    async def handle_description(self, ctx: Context) -> str:
        request = ctx.request_context.request
        assert request is not None, "Expected request to be set"
        return f"Echoes the input text: {request.user.username}"

    async def handle_call(self, text: str, ctx: Context) -> str:
        request = ctx.request_context.request
        assert request is not None, "Expected request to be set"
        return f"Echo to user ({request.user.username}): {text}"


app.mount("/mcp", app=mcp.streamable_http_app())
