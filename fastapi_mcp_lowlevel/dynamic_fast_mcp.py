import asyncio
from typing import Any, Awaitable, Callable, Protocol, runtime_checkable
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.fastmcp.tools.base import Tool
from mcp.server.fastmcp.tools.tool_manager import ToolManager
from mcp.server.fastmcp.utilities.func_metadata import FuncMetadata, ArgModelBase
from mcp.types import Tool as MCPTool, AnyFunction


@runtime_checkable
class DynamicTool(Protocol):
    def name(self) -> str:
        """Return the name of the tool."""

    def handle_description(self, ctx: Context) -> Awaitable[str]:
        """Return the description of the tool."""

    def handle_call(self, *args, **kwargs) -> Awaitable[Any]:
        """Handle the call to the tool."""


class DynamicToolManager(ToolManager):
    _dynamic_tools: dict[str, DynamicTool]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dynamic_tools = {}

    def add_dynamic_tool(self, tool: DynamicTool) -> None:
        self._dynamic_tools[tool.name()] = tool

    async def list_dynamic_tools(self, context: Context) -> list[Tool]:
        return await self._resolve_dynamic_tools(context)

    async def _resolve_dynamic_tools(self, context: Context) -> list[Tool]:
        return await asyncio.gather(
            *[
                self._resolve_dynamic_tool(tool, context)
                for tool in self._dynamic_tools.values()
            ]
        )

    async def _resolve_dynamic_tool(self, tool: DynamicTool, context: Context) -> Tool:
        return Tool(
            fn=tool.handle_call,
            name=tool.name(),
            title=None,  # TODO: add title
            description=await tool.handle_description(context),
            parameters={},  # TODO: add parameters
            fn_metadata=FuncMetadata(
                arg_model=ArgModelBase,  # TODO: add arg_model
                output_schema=None,  # TODO: add output_schema
                output_model=None,  # TODO: add output_model
                wrap_output=False,  # TODO: add wrap_output
            ),
            is_async=True,
            context_kwarg=None,  # TODO: add context_kwarg
            annotations=None,  # TODO: add annotations
        )


class DynamicFastMCP(FastMCP):
    _tool_manager: DynamicToolManager

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tool_manager = DynamicToolManager()

    def tool(
        self,
        *args,
        **kwargs,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(clsOrFn: type[DynamicTool] | Callable[..., Any]) -> AnyFunction:
            if isinstance(clsOrFn, type) and issubclass(clsOrFn, DynamicTool):
                self.add_dynamic_tool(clsOrFn())
                return clsOrFn
            elif callable(clsOrFn):
                self.add_tool(clsOrFn, *args, **kwargs)
                return clsOrFn
            else:
                raise TypeError(
                    "The @tool decorator can only be applied to a class (subclass of DynamicTool) or a function"
                )

        return decorator

    def add_dynamic_tool(self, tool: DynamicTool) -> None:
        self._tool_manager.add_dynamic_tool(tool)

    async def list_tools(self) -> list[MCPTool]:
        context = self.get_context()
        tools = await super().list_tools()
        dynamic_tools = [
            MCPTool(
                name=tool.name,
                title=tool.title,
                description=tool.description,
                inputSchema=tool.parameters,
                outputSchema=tool.output_schema,
                annotations=tool.annotations,
            )
            for tool in await self._tool_manager.list_dynamic_tools(context=context)
        ]
        return sorted(tools + dynamic_tools, key=lambda x: x.name)
