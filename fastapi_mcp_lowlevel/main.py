import contextlib
import logging
from fastapi import FastAPI
from pydantic import AnyHttpUrl
from starlette.applications import Starlette
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.auth.provider import TokenVerifier, AccessToken
from mcp.server.auth.settings import AuthSettings


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

        return AccessToken(token=token, client_id="test", scopes=["test"])


mcp = FastMCP(
    streamable_http_path="/",
    token_verifier=TestTokenVerifier(),
    auth=AuthSettings(
        resource_server_url=AnyHttpUrl("https://example.com"),
        issuer_url=AnyHttpUrl("https://example.com"),
    ),
)


@mcp.tool()
def echo(self, text: str, ctx: Context):
    return text


app.mount("/mcp", app=mcp.streamable_http_app())
