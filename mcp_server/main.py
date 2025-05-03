from mcp.server.fastmcp import FastMCP
import httpx
from typing import List, Optional
from config import HEADERS, BASE_URL, logger  # <-- import from config
from datetime import datetime
from schemas import (
    TopicInsert,
    ContrastPairUpdate,
    TopicUpdate,
    ContrastPairRating,
    NewsItem,
    ISO_DATETIME_REGEX,
    PairStringInput,
)
from rag import get_similar_pairs
from utils_cache import init_cache
import asyncio
from rag import fetch_all_pairs_async
import time
from mcp.server.fastmcp import Context

# Create the MCP server instance

mcp = FastMCP("Cypher Arena MCP Server", log_level="INFO")

# ----------- Contrast Pairs Endpoints -----------


@mcp.tool()
def get_contrast_pairs(
    page: Optional[int] = 1,
    count: Optional[int] = 10,
    random: Optional[bool] = False,
    vector_embedding: Optional[bool] = False,
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
def batch_rate_contrast_pairs(ratings: List[ContrastPairRating]) -> dict:
    """Rate multiple contrast pairs in a single request."""
    data = {"ratings": [r.model_dump() for r in ratings]}
    resp = httpx.post(f"{BASE_URL}/contrast-pairs/rate/", json=data, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
def batch_update_contrast_pairs(updates: List[ContrastPairUpdate]) -> dict:
    """Update multiple existing contrast pairs in a single request."""
    # Convert Pydantic models to dicts, excluding None values
    update_data = [u.model_dump(exclude_unset=True) for u in updates]
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
def batch_create_news(news_items: List[NewsItem]) -> list:
    """Create multiple news records in a single request."""
    data = {"news_items": [item.model_dump(exclude_unset=True) for item in news_items]}
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
    vector_embedding: Optional[bool] = True,
) -> dict:
    """Retrieve a paginated list of topics, with optional filtering, randomization, and vector embedding control."""
    params = {"page": page, "count": count}
    if source:
        params["source"] = source
    if random:
        params["random"] = True
    if not vector_embedding:  # Only add if False, as True is the default in the API
        params["vector_embedding"] = False
    resp = httpx.get(f"{BASE_URL}/topics/", params=params, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
def batch_insert_topics(topics: List[TopicInsert]) -> list:
    """Insert multiple topics in a single request. Each topic must have a 'name' and can optionally have a 'source' (default: 'agent'). Uses get_or_create logic."""
    # Pydantic models need explicit conversion to dict for JSON serialization
    data = {"topics": [t.model_dump(exclude_unset=True) for t in topics]}
    resp = httpx.post(f"{BASE_URL}/topics/", json=data, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
def batch_update_topics(updates: List[TopicUpdate]) -> dict:
    """Update multiple existing topics in a single request."""
    # Convert Pydantic models to dicts, excluding None values
    update_data = [u.model_dump(exclude_unset=True) for u in updates]
    data = {"updates": update_data}
    resp = httpx.patch(f"{BASE_URL}/topics/", json=data, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
async def get_similar_pairs_tool(pair: PairStringInput, k: int = 10, ctx: Context = None) -> list:
    '''this tool gets k most similar contrasing pairs in format Item1 vs Item2'''
    # Check if context was provided (it should be by FastMCP)
    if ctx is None:
        logger.warning("Context object (ctx) not provided to get_similar_pairs_tool. Progress reporting disabled.")
        # Fallback or raise error? For now, just log and proceed without progress.

    logger.info(f"Entering get_similar_pairs_tool with pair='{pair.pair_string}', k={k}")
    start_time = time.time()
    try:
        result = await get_similar_pairs(pair, k, ctx)  # Await the async function directly
        end_time = time.time()
        logger.info(f"Exiting get_similar_pairs_tool. Duration: {end_time - start_time:.2f}s. Found {len(result) if result else 0} pairs.")
        return result
    except asyncio.TimeoutError:
        logger.error("Call to get_similar_pairs timed out within get_similar_pairs_tool.")
        raise
    except Exception as e:
        logger.exception(f"Error during get_similar_pairs execution in get_similar_pairs_tool: {e}")
        raise # Re-raise the exception to be handled by FastMCP


# ----------- Server Entrypoint -----------

if __name__ == "__main__":
    import time # Add time import for logging duration
    logger.info("Initializing cache before starting server...")
    start_cache_init = time.time()
    # Initialize cache before starting the server
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(init_cache(fetch_all_pairs_async))
    else:
        loop.run_until_complete(init_cache(fetch_all_pairs_async))
    mcp.run()
