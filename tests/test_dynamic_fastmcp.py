from unittest.mock import Mock
from mcp.server.fastmcp import Context
import pytest
from dynamic_fastmcp.dynamic_fastmcp import (
    DynamicFastMCP,
    DynamicTool,
    DynamicToolManager,
)
from starlette.authentication import SimpleUser


def test_init():
    mcp = DynamicFastMCP()
    assert mcp is not None
    assert mcp._tool_manager is not None
    assert isinstance(mcp._tool_manager, DynamicToolManager)


@pytest.mark.asyncio
async def test_list_tools():
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

        def structured_output(self) -> bool | None:
            return None

        async def handle_description(self, ctx: Context) -> str:
            assert ctx.request_context.request is not None
            return f"Dynamic Echo description for username: {ctx.request_context.request.user.username}"

        async def handle_call(self, text: str, ctx: Context) -> str:
            assert ctx.request_context.request is not None
            return f"Dynamic Echo call for username: {ctx.request_context.request.user.username}: {text}"

    @mcp.tool(description="Regular Echo")
    def echo(text: str, ctx: Context) -> str:
        return text

    resolved_tools = await mcp.list_tools()

    assert len(resolved_tools) == 2
    assert resolved_tools[0].name == "dynamic_echo"
    assert resolved_tools[0].title is None
    assert resolved_tools[0].description == "Dynamic Echo description for username: bob"
    assert resolved_tools[0].annotations is None
    assert resolved_tools[0].inputSchema == {
        "properties": {"text": {"title": "Text", "type": "string"}},
        "required": ["text"],
        "title": "handle_callArguments",
        "type": "object",
    }
    assert resolved_tools[0].outputSchema == {
        "properties": {"result": {"title": "Result", "type": "string"}},
        "required": ["result"],
        "title": "handle_callOutput",
        "type": "object",
    }

    assert resolved_tools[1].name == "echo"
    assert resolved_tools[1].title is None
    assert resolved_tools[1].description == "Regular Echo"
    assert resolved_tools[1].annotations is None
    assert resolved_tools[1].inputSchema == {
        "properties": {"text": {"title": "Text", "type": "string"}},
        "required": ["text"],
        "title": "echoArguments",
        "type": "object",
    }
    assert resolved_tools[1].outputSchema == {
        "properties": {"result": {"title": "Result", "type": "string"}},
        "required": ["result"],
        "title": "echoOutput",
        "type": "object",
    }

    mcp.get_context.assert_called_once()


@pytest.mark.asyncio
async def test_call_tool():
    mcp = DynamicFastMCP()

    context = Context(
        request_context=Mock(request=Mock(user=SimpleUser(username="bob")))
    )

    mcp.get_context = Mock(return_value=context)

    @mcp.tool()
    class DynamicEcho(DynamicTool):
        def name(self) -> str:
            return "dynamic_echo"

        def structured_output(self) -> bool | None:
            return None

        async def handle_description(self, ctx: Context) -> str:
            assert ctx.request_context.request is not None
            return f"Dynamic Echo description for username: {ctx.request_context.request.user.username}"

        async def handle_call(self, text: str, context: Context) -> str:
            assert context.request_context.request is not None
            return f"Dynamic Echo call for username: {context.request_context.request.user.username}: {text}"

    result = await mcp.call_tool("dynamic_echo", {"text": "Hello, world!"})
    assert result == "Dynamic Echo call for username: bob: Hello, world!"

    mcp.get_context.assert_called_once()
