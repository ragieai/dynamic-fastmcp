from typing import Any
from mcp.server.fastmcp import Context
from fastapi_mcp_lowlevel.dynamic_fast_mcp import DynamicTool, DynamicToolManager


def test_add_tool_duplicate_warning(caplog):
    manager = DynamicToolManager(warn_on_duplicate_tools=True)
    manager.add_tool(lambda: {}, "test")
    manager.add_tool(lambda: {}, "test")
    assert "Tool already exists: test" in caplog.text


def test_add_tool_and_add_dynamic_tool_duplicate_warning(caplog):
    class TestTool(DynamicTool):
        def name(self) -> str:
            return "test"

        def structured_output(self) -> bool | None:
            return None

        async def handle_description(self, ctx: Context) -> str:
            return "Test tool"

        async def handle_call(self, *args, **kwargs) -> str:
            return "Test tool"

    manager = DynamicToolManager(warn_on_duplicate_tools=True)
    manager.add_tool(lambda: {}, "test")
    manager.add_dynamic_tool(TestTool())

    assert "Tool already exists: test" in caplog.text


def test_add_dynamic_tool_and_add_tool_duplicate_warning(caplog):
    class TestTool(DynamicTool):
        def name(self) -> str:
            return "test"

        def structured_output(self) -> bool | None:
            return None

        async def handle_description(self, ctx: Context) -> str:
            return "Test tool"

        async def handle_call(self, *args, **kwargs) -> str:
            return "Test tool"

    manager = DynamicToolManager(warn_on_duplicate_tools=True)
    manager.add_dynamic_tool(TestTool())
    manager.add_tool(lambda: {}, "test")

    assert "Tool already exists: test" in caplog.text
