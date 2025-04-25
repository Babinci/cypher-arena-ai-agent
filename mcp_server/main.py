from mcp.server.fastmcp import FastMCP
import httpx
from typing import List, Optional

# Create the MCP server instance
mcp = FastMCP("Cypher Arena MCP Server", log_level="INFO")

BASE_URL = "https://backend.cypher-arena.com/words/agent"

# ----------- Contrast Pairs Endpoints -----------

@mcp.tool()
def get_contrast_pairs(page: Optional[int] = 1, count: Optional[int] = 10) -> dict:
    """Retrieve a paginated list of contrast pairs."""
    params = {"page": page, "count": count}
    resp = httpx.get(f"{BASE_URL}/contrast-pairs/", params=params)
    resp.raise_for_status()
    return resp.json()

@mcp.tool()
def batch_create_contrast_pairs(pairs: List[dict]) -> list:
    """Create multiple contrast pairs in a single request."""
    data = {"pairs": pairs}
    resp = httpx.post(f"{BASE_URL}/contrast-pairs/", json=data)
    resp.raise_for_status()
    return resp.json()

@mcp.tool()
def batch_rate_contrast_pairs(ratings: List[dict]) -> dict:
    """Rate multiple contrast pairs in a single request."""
    data = {"ratings": ratings}
    resp = httpx.post(f"{BASE_URL}/contrast-pairs/rate/", json=data)
    resp.raise_for_status()
    return resp.json()

# ----------- News Endpoints -----------

@mcp.tool()
def get_news(start_time: str, end_time: str, news_type: Optional[str] = None) -> list:
    """Retrieve news records filtered by a required date range and optional news type."""
    params = {"start_time": start_time, "end_time": end_time}
    if news_type:
        params["news_type"] = news_type
    resp = httpx.get(f"{BASE_URL}/news/", params=params)
    resp.raise_for_status()
    return resp.json()

# ----------- Topics Endpoints -----------

@mcp.tool()
def get_topics(page: Optional[int] = 1, count: Optional[int] = 10, source: Optional[str] = None) -> dict:
    """Retrieve a paginated list of topics, with optional filtering by source."""
    params = {"page": page, "count": count}
    if source:
        params["source"] = source
    resp = httpx.get(f"{BASE_URL}/topics/", params=params)
    resp.raise_for_status()
    return resp.json()

@mcp.tool()
def batch_insert_topics(topics: List[dict]) -> list:
    """Insert multiple topics in a single request."""
    data = {"topics": topics}
    resp = httpx.post(f"{BASE_URL}/topics/", json=data)
    resp.raise_for_status()
    return resp.json()

@mcp.tool()
def batch_update_topics(updates: List[dict]) -> dict:
    """Update multiple existing topics in a single request."""
    data = {"updates": updates}
    resp = httpx.patch(f"{BASE_URL}/topics/", json=data)
    resp.raise_for_status()
    return resp.json()

# ----------- Server Entrypoint -----------

if __name__ == "__main__":
    mcp.run()
