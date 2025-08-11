from unittest.mock import Mock
from mcp.server.fastmcp import Context
import pytest
from fastapi_mcp_lowlevel.dynamic_fast_mcp import (
    DynamicFastMCP,
    DynamicTool,
    DynamicToolManager,
)
from mcp.shared.context import RequestContext
from starlette.authentication import SimpleUser


def test_init():
    mcp = DynamicFastMCP()
    assert mcp is not None
    assert mcp._tool_manager is not None
    assert isinstance(mcp._tool_manager, DynamicToolManager)


@pytest.mark.asyncio
async def test_dynamic_tool_registration():
    mcp = DynamicFastMCP()

    mcp.get_context = Mock(
        return_value=Context(
            request_context=Mock(request=Mock(user=SimpleUser(username="bob")))
        )
    )

    assert mcp is not None
    assert mcp._tool_manager is not None
    assert isinstance(mcp._tool_manager, DynamicToolManager)

    @mcp.tool()
    class DynamicEcho(DynamicTool):
        def name(self) -> str:
            return "dynamic_echo"

        async def handle_description(self, ctx: Context) -> str:
            assert ctx.request_context.request is not None
            return f"Dynamic Echo for username: {ctx.request_context.request.user.username}"

    @mcp.tool(description="Regular Echo")
    def echo(text: str, ctx: Context) -> str:
        return text

    resolved_tools = await mcp.list_tools()

    assert len(resolved_tools) == 2
    assert resolved_tools[0].name == "dynamic_echo"
    assert resolved_tools[0].description == "Dynamic Echo for username: bob"
    assert resolved_tools[1].name == "echo"
    assert resolved_tools[1].description == "Regular Echo"

    mcp.get_context.assert_called_once()
