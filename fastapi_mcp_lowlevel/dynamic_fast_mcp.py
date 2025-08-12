import asyncio
import inspect
from pydantic import BaseModel, ConfigDict, Field
from typing import Any, Awaitable, Callable, Protocol, get_origin, runtime_checkable
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.fastmcp.tools.base import Tool
from mcp.server.fastmcp.tools.tool_manager import ToolManager
from mcp.server.fastmcp.utilities.func_metadata import FuncMetadata, func_metadata
from mcp.types import Tool as MCPTool, AnyFunction, ToolAnnotations
from mcp.shared.context import LifespanContextT, RequestT
from mcp.server.session import ServerSessionT
from mcp.server.fastmcp.exceptions import ToolError


@runtime_checkable
class DynamicTool(Protocol):
    # TODO: name and structured_output seem like they could be part of a meta class
    def name(self) -> str:
        """Return the name of the tool."""

    def structured_output(self) -> bool | None:
        """Return whether the tool returns structured output."""

    def handle_description(self, ctx: Context) -> Awaitable[str]:
        """Return the description of the tool."""

    def handle_call(self, *args, **kwargs) -> Awaitable[Any]:
        """Handle the call to the tool."""


class DynamicToolWrapper(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    tool: DynamicTool = Field(exclude=True)
    fn: Callable[..., Any] = Field(exclude=True)
    name: str = Field(description="Name of the tool")
    title: str | None = Field(None, description="Human-readable title of the tool")
    parameters: dict[str, Any] = Field(description="JSON schema for tool parameters")
    fn_metadata: FuncMetadata = Field(
        description="Metadata about the function including a pydantic model for tool arguments"
    )
    is_async: bool = Field(description="Whether the tool is async")
    context_kwarg: str | None = Field(
        None, description="Name of the kwarg that should receive context"
    )
    annotations: ToolAnnotations | None = Field(
        None, description="Optional annotations for the tool"
    )

    async def run(
        self,
        arguments: dict[str, Any],
        context: Context[ServerSessionT, LifespanContextT, RequestT] | None = None,
        convert_result: bool = False,
    ) -> Awaitable[Any]:
        kwargs = arguments
        if self.context_kwarg:
            kwargs[self.context_kwarg] = context
        return await self.tool.handle_call(**kwargs)

    async def resolve_tool(self, context: Context) -> Tool:
        return Tool(
            fn=self.tool.handle_call,
            name=self.tool.name(),
            title=None,  # TODO: add title
            description=await self.tool.handle_description(context),
            parameters=self.parameters,
            fn_metadata=self.fn_metadata,
            is_async=True,  # TODO: add is_async
            context_kwarg=self.context_kwarg,
            annotations=None,  # TODO: add annotations
        )

    @classmethod
    def from_dynamic_tool(cls, tool: DynamicTool) -> "DynamicToolWrapper":
        context_kwarg = _find_context_kwarg(tool.handle_call)
        func_arg_metadata = func_metadata(
            tool.handle_call,
            skip_names=[context_kwarg] if context_kwarg is not None else [],
            structured_output=tool.structured_output(),
        )

        parameters = func_arg_metadata.arg_model.model_json_schema(by_alias=True)

        return cls(
            tool=tool,
            fn=tool.handle_call,
            name=tool.name(),
            title=None,  # TODO: add title
            parameters=parameters,
            fn_metadata=func_arg_metadata,
            is_async=True,  # TODO: add is_async
            context_kwarg=context_kwarg,
            annotations=None,  # TODO: add annotations
        )


class DynamicToolManager(ToolManager):
    _dynamic_tools: dict[str, DynamicToolWrapper]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dynamic_tools = {}

    # This method is not supported because it only returns Tool objects, not DynamicTool objects.
    def get_tool(self, name: str) -> Tool | None:
        raise NotImplementedError("DynamicToolManager does not support get_tool")

    def _get_tool(self, name: str) -> Tool | DynamicToolWrapper | None:
        return self._tools.get(name) or self._dynamic_tools.get(name)

    def add_dynamic_tool(self, tool: DynamicTool) -> None:
        self._dynamic_tools[tool.name()] = DynamicToolWrapper.from_dynamic_tool(tool)

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        context: Context[ServerSessionT, LifespanContextT, RequestT] | None = None,
        convert_result: bool = False,
    ) -> Any:
        tool = self._get_tool(name)
        if not tool:
            raise ToolError(f"Unknown tool: {name}")
        if isinstance(tool, DynamicToolWrapper):
            return await tool.run(arguments, context, convert_result)
        else:
            return await super().call_tool(name, arguments, context, convert_result)

    async def list_dynamic_tools(self, context: Context) -> list[Tool]:
        return await self._resolve_dynamic_tools(context)

    async def _resolve_dynamic_tools(self, context: Context) -> list[Tool]:
        return await asyncio.gather(
            *[tool.resolve_tool(context) for tool in self._dynamic_tools.values()]
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


def _find_context_kwarg(fn: Callable[..., Any]) -> str | None:
    sig = inspect.signature(fn)
    for param_name, param in sig.parameters.items():
        if get_origin(param.annotation) is not None:
            continue
        if issubclass(param.annotation, Context):
            return param_name
    return None
