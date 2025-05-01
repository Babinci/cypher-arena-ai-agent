from mcp.server.fastmcp import FastMCP
import httpx
from typing import List, Optional
from pydantic import BaseModel
from config import HEADERS, BASE_URL  # <-- import from config

# Create the MCP server instance

mcp = FastMCP("Cypher Arena MCP Server", log_level="INFO")


class TopicInsert(BaseModel):
    name: str
    source: Optional[str] = "agent"

class ContrastPairUpdate(BaseModel):
    id: int
    item1: Optional[str] = None
    item2: Optional[str] = None
    vector_embedding: Optional[str] = None

class TopicUpdate(BaseModel):
    id: int
    name: Optional[str] = None
    source: Optional[str] = None
    vector_embedding: Optional[str] = None

# ----------- Contrast Pairs Endpoints -----------

@mcp.tool()
def get_contrast_pairs(
    page: Optional[int] = 1,
    count: Optional[int] = 10,
    random: Optional[bool] = False,
    vector_embedding: Optional[bool] = False
) -> dict:
    """Retrieve a paginated list of contrast pairs, optionally randomized or with vector embeddings."""
    params = {"page": page, "count": count}
    if random:
        params["random"] = True
    if vector_embedding:
        params["vector_embedding"] = True
    resp = httpx.get(f"{BASE_URL}/contrast-pairs/", params=params, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()

@mcp.tool()
def batch_create_contrast_pairs(pairs: List[dict]) -> list:
    """Create multiple contrast pairs in a single request."""
    data = {"pairs": pairs}
    resp = httpx.post(f"{BASE_URL}/contrast-pairs/", json=data, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()

@mcp.tool()
def batch_rate_contrast_pairs(ratings: List[dict]) -> dict:
    """Rate multiple contrast pairs in a single request."""
    data = {"ratings": ratings}
    resp = httpx.post(f"{BASE_URL}/contrast-pairs/rate/", json=data, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()

@mcp.tool()
def batch_update_contrast_pairs(updates: List[ContrastPairUpdate]) -> dict:
    """Update multiple existing contrast pairs in a single request."""
    # Convert Pydantic models to dicts, excluding None values
    update_data = [u.dict(exclude_unset=True) for u in updates]
    data = {"updates": update_data}
    resp = httpx.patch(f"{BASE_URL}/contrast-pairs/update/", json=data, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()

# ----------- News Endpoints -----------

@mcp.tool()
def get_news(start_time: str, end_time: str, news_type: Optional[str] = None) -> list:
    """Retrieve news records filtered by a required date range and optional news type."""
    params = {"start_time": start_time, "end_time": end_time}
    if news_type:
        params["news_type"] = news_type
    resp = httpx.get(f"{BASE_URL}/news/", params=params, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()

@mcp.tool()
def batch_create_news(news_items: List[dict]) -> list:
    """Create multiple news records in a single request."""
    data = {"news_items": news_items}
    resp = httpx.post(f"{BASE_URL}/news/", json=data, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()

# ----------- Topics Endpoints -----------

@mcp.tool()
def get_topics(
    page: Optional[int] = 1,
    count: Optional[int] = 10,
    source: Optional[str] = None,
    random: Optional[bool] = False,
    vector_embedding: Optional[bool] = True
) -> dict:
    """Retrieve a paginated list of topics, with optional filtering, randomization, and vector embedding control."""
    params = {"page": page, "count": count}
    if source:
        params["source"] = source
    if random:
        params["random"] = True
    if not vector_embedding: # Only add if False, as True is the default in the API
        params["vector_embedding"] = False
    resp = httpx.get(f"{BASE_URL}/topics/", params=params, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()

@mcp.tool()
def batch_insert_topics(topics: List[TopicInsert]) -> list:
    """Insert multiple topics in a single request. Each topic must have a 'name' and can optionally have a 'source' (default: 'agent'). Uses get_or_create logic."""
    # Pydantic models need explicit conversion to dict for JSON serialization
    data = {"topics": [t.dict(exclude_unset=True) for t in topics]}
    resp = httpx.post(f"{BASE_URL}/topics/", json=data, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()

@mcp.tool()
def batch_update_topics(updates: List[TopicUpdate]) -> dict:
    """Update multiple existing topics in a single request."""
    # Convert Pydantic models to dicts, excluding None values
    update_data = [u.dict(exclude_unset=True) for u in updates]
    data = {"updates": update_data}
    resp = httpx.patch(f"{BASE_URL}/topics/", json=data, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


# ----------- Server Entrypoint -----------

if __name__ == "__main__":
    mcp.run()
