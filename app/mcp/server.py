"""MCP transport shim for Vestra's data-access layer.

History: this module used to contain the persistence logic decorated as MCP
tools, but the FastAPI request path imported and awaited those functions
directly -- it never spoke the MCP protocol. The logic now lives in
``app/data/repository.py`` (the real DAL) and the client factory in
``app/data/mongo.py``.

This file keeps two contracts intact:

1. **Direct imports** -- ``from app.mcp.server import get_profile`` (and the
   other four functions) still work and return plain coroutines, because we
   re-export the repository callables unchanged. The agent nodes depend on this.
2. **MCP transport** -- the same functions are registered as MCP tools so the
   server can still be run as a standalone MCP endpoint via ``python -m
   app.mcp.server`` (``mcp.run()`` under ``__main__``).
"""

from mcp.server.fastmcp import FastMCP

# Client factory now lives in app.data.mongo; re-export for backward compat.
from app.data.mongo import get_client, get_db, set_client

# The real persistence logic. Re-exported under the same names so existing
# ``from app.mcp.server import <fn>`` imports keep returning plain coroutines.
from app.data.repository import (
    execute_trade,
    get_market_exposure,
    get_profile,
    log_reasoning,
    reject_trade,
)

mcp = FastMCP("vestra-mcp")

# Register the DAL functions as MCP tools for the optional transport. Decorating
# the imported callables (rather than redefining them) keeps a single source of
# truth -- the direct-import re-exports above and the MCP tools are the same code.
mcp.tool()(get_profile)
mcp.tool()(get_market_exposure)
mcp.tool()(execute_trade)
mcp.tool()(reject_trade)
mcp.tool()(log_reasoning)


__all__ = [
    "mcp",
    "get_client",
    "get_db",
    "set_client",
    "get_profile",
    "get_market_exposure",
    "execute_trade",
    "reject_trade",
    "log_reasoning",
]


if __name__ == "__main__":
    mcp.run()
