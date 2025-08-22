# Dynamic FastMCP

Dynamic FastMCP is a Python library that extends the [Model Context Protocol (MCP)](https://github.com/modelcontextprotocol/python-sdk) FastMCP server with dynamic tool capabilities. It allows you to create MCP tools that can adapt their behavior and descriptions based on request context, user information, and path parameters.

## Features

- **Dynamic Tool Descriptions**: Tool descriptions that change based on context (user, request path, etc.)
- **Context-Aware Tool Execution**: Tools that can access request context during execution
- **Hybrid Tool Support**: Seamlessly combines regular MCP tools with dynamic tools
- **FastAPI Integration**: Easily mount on FastAPI applications with authentication
- **Multi-tenant Support**: Perfect for applications where tool behavior varies per user or tenant

## Installation

```bash
pip install dynamic-fastmcp
```

Or using Poetry:

```bash
poetry add dynamic-fastmcp
```

## Quick Start

### Basic Usage

```python
from dynamic_fastmcp import DynamicFastMCP, DynamicTool
from mcp.server.fastmcp import Context

# Create a Dynamic FastMCP instance
mcp = DynamicFastMCP()

# Regular tool - works just like standard FastMCP
@mcp.tool(description="Echoes the input text")
def echo(text: str, ctx: Context):
    return f"Echo: {text}"

# Dynamic tool - description and behavior adapt to context
@mcp.tool()
class PersonalizedEcho(DynamicTool):
    def name(self) -> str:
        return "personalized_echo"

    def structured_output(self) -> bool | None:
        return True

    async def handle_description(self, ctx: Context) -> str:
        user = ctx.request_context.request.user
        return f"Echoes text with personalization for {user.username}"

    async def handle_call(self, text: str, ctx: Context) -> str:
        user = ctx.request_context.request.user
        return f"Hello {user.username}, you said: {text}"
```

### FastAPI Integration

```python
from fastapi import FastAPI
from dynamic_fastmcp import DynamicFastMCP
from mcp.server.auth.provider import TokenVerifier, AccessToken

app = FastAPI()

class CustomTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        # Implement your token verification logic
        if token == "valid_token":
            return AccessToken(token=token, client_id="client_123", scopes=[])
        return None

# Create MCP instance with authentication
mcp = DynamicFastMCP(
    streamable_http_path="/",
    token_verifier=CustomTokenVerifier(),
)

# Mount MCP at different paths for multi-tenant support
app.mount("/mcp/{id}", app=mcp.streamable_http_app())
```

## Dynamic Tools

Dynamic tools implement the `DynamicTool` protocol and provide context-aware functionality:

### Required Methods

- `name()` → `str`: Return the tool name
- `structured_output()` → `bool | None`: Whether the tool returns structured output
- `handle_description(ctx: Context)` → `Awaitable[str]`: Return context-aware description
- `handle_call(*args, **kwargs)` → `Awaitable[Any]`: Handle the tool execution

### Example: Multi-tenant Tool

```python
@mcp.tool()
class TenantSpecificTool(DynamicTool):
    def name(self) -> str:
        return "tenant_tool"

    def structured_output(self) -> bool | None:
        return True

    async def handle_description(self, ctx: Context) -> str:
        tenant_id = ctx.request_context.request.path_params.get("id")
        return f"Performs tenant-specific operations for tenant {tenant_id}"

    async def handle_call(self, action: str, ctx: Context) -> str:
        tenant_id = ctx.request_context.request.path_params.get("id")
        user = ctx.request_context.request.user.username
        return f"Executing '{action}' for tenant {tenant_id} by user {user}"
```

### Example: User-aware Tool

```python
@mcp.tool()
class UserDashboard(DynamicTool):
    def name(self) -> str:
        return "dashboard"

    def structured_output(self) -> bool | None:
        return True

    async def handle_description(self, ctx: Context) -> str:
        username = ctx.request_context.request.user.username
        return f"Access dashboard data for {username}"

    async def handle_call(self, widget: str, ctx: Context) -> dict:
        username = ctx.request_context.request.user.username
        # Fetch user-specific data
        return {
            "user": username,
            "widget": widget,
            "data": f"User-specific {widget} data for {username}"
        }
```

## Architecture

### Core Components

- **`DynamicFastMCP`**: Enhanced FastMCP server that supports both regular and dynamic tools
- **`DynamicTool`**: Protocol defining the interface for dynamic tools
- **`DynamicToolWrapper`**: Internal wrapper that adapts dynamic tools to the MCP tool interface
- **`DynamicToolManager`**: Manages both regular and dynamic tools, handling tool resolution and execution

### Tool Resolution Flow

1. When tools are listed, dynamic tools resolve their descriptions using the current context
2. During execution, dynamic tools receive the full context including request information
3. The system automatically handles parameter validation and result conversion

## Authentication & Security

Dynamic FastMCP supports the standard MCP authentication patterns:

```python
from mcp.server.auth.provider import TokenVerifier, AccessToken
from mcp.server.auth.settings import AuthSettings
from pydantic import AnyHttpUrl

class MyTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        # Your verification logic here
        pass

mcp = DynamicFastMCP(
    token_verifier=MyTokenVerifier(),
    auth=AuthSettings(
        resource_server_url=AnyHttpUrl("https://your-auth-server.com"),
        issuer_url=AnyHttpUrl("https://your-auth-server.com"),
    ),
)
```

## Testing

Run the test suite:

```bash
poetry run pytest
```

The project includes comprehensive tests covering:
- Dynamic tool registration and execution
- Context handling
- Integration with FastAPI
- Multi-tenant scenarios

## Use Cases

### Multi-tenant SaaS Applications
Tools that behave differently based on tenant context:
```python
# Tool descriptions and behavior adapt per tenant
GET /mcp/tenant_123  # Tools show tenant_123 specific descriptions
GET /mcp/tenant_456  # Same tools, different descriptions for tenant_456
```

### User-specific Tools
Tools that provide personalized functionality:
```python
# User-aware tools that adapt to the authenticated user
@mcp.tool()
class MyFiles(DynamicTool):
    async def handle_description(self, ctx: Context) -> str:
        user = ctx.request_context.request.user.username
        return f"Manage files for {user}"
```

### Context-sensitive Operations
Tools that change behavior based on request path or parameters:
```python
# Same tool name, different behavior based on path
GET /mcp/development  # Development environment behavior
GET /mcp/production   # Production environment behavior
```

## Requirements

- Python 3.12+
- MCP SDK 1.13.0+
- FastAPI (for web integration)
- Pydantic (for data validation)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.

## Changelog

### v0.1.0
- Initial release
- Dynamic tool support
- FastAPI integration
- Authentication support
- Comprehensive test suite
