from unittest.mock import Mock
import pytest
from fastapi_mcp_lowlevel.dynamic_fast_mcp import DynamicTool, DynamicToolWrapper
from mcp.server.fastmcp import Context
from starlette.authentication import SimpleUser


class DynamicEcho(DynamicTool):
    def name(self) -> str:
        return "dynamic_echo"

    async def handle_description(self, ctx: Context) -> str:
        request = ctx.request_context.request
        assert request is not None, "Expected request to be set"
        return f"Echoes the input text: {request.user.username}"

    async def handle_call(self, text: str, custom_context_name: Context) -> str:
        request = custom_context_name.request_context.request
        assert request is not None, "Expected request to be set"
        return f"Echo to user ({request.user.username}): {text}"


@pytest.mark.asyncio
async def test_call_tool_with_custom_context_variable():
    context = Context(
        request_context=Mock(request=Mock(user=SimpleUser(username="bob")))
    )
    tool = DynamicEcho()
    wrapper = DynamicToolWrapper.from_dynamic_tool(tool)
    result = await wrapper.run({"text": "Hello, world!"}, context=context)
    assert result == "Echo to user (bob): Hello, world!"
