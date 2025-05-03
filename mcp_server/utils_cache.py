import asyncio
import time
import numpy as np
from sentence_transformers import SentenceTransformer
import torch
import pickle
import os
from config import logger
from base64 import b64decode # Need b64decode here for processing in init_cache

MODEL = None
LOCAL_CACHE_FILE = "mcp_server_cache.pkl"
CACHE_EXPIRY_SECONDS = 24 * 60 * 60  # 1 day

PAIRS_CACHE = {
    "data": None,
    "db_embeddings": None,
    "last_updated_timestamp": None  # Store timestamp directly
}

async def load_model_async():
    global MODEL
    start_time = time.time()
    logger.info("load_model_async: Attempting to load model...")
    if MODEL is None:
        logger.info(f"load_model_async: MODEL is None. Checking CUDA availability: {torch.cuda.is_available()}")
        try:
            loop = asyncio.get_event_loop()
            # Run SentenceTransformer loading in executor to avoid blocking event loop
            MODEL = await loop.run_in_executor(
                None,
                lambda: SentenceTransformer("Snowflake/snowflake-arctic-embed-l-v2.0", device="cuda")
            )
            logger.info(f"load_model_async: Model loaded successfully in {time.time() - start_time:.2f}s.")
        except Exception as e:
             logger.exception(f"load_model_async: Failed to load model after {time.time() - start_time:.2f}s. Error: {e}")
             # Decide if we should raise or just return None? For now, MODEL remains None.
    else:
        logger.info(f"load_model_async: Model already loaded. Took {time.time() - start_time:.2f}s.")
    return MODEL

def load_cache_from_file():
    """Attempts to load cache data from the local file."""
    start_time = time.time()
    logger.info(f"load_cache_from_file: Attempting to load cache from {LOCAL_CACHE_FILE}...")
    if os.path.exists(LOCAL_CACHE_FILE):
        try:
            with open(LOCAL_CACHE_FILE, "rb") as f:
                cached_data = pickle.load(f)
                # Basic validation
                if isinstance(cached_data, dict) and "last_updated_timestamp" in cached_data:
                    load_duration = time.time() - start_time
                    cache_age = time.time() - cached_data.get("last_updated_timestamp", 0)
                    logger.info(f"load_cache_from_file: Cache loaded successfully in {load_duration:.2f}s. Cache age: {cache_age:.0f}s.")
                    return cached_data
                else:
                    logger.error(f"load_cache_from_file: Invalid cache file format found in {LOCAL_CACHE_FILE}. Took {time.time() - start_time:.2f}s.")
        except (pickle.UnpicklingError, EOFError) as e:
            logger.error(f"load_cache_from_file: Could not unpickle cache from {LOCAL_CACHE_FILE}. Error: {e}. Took {time.time() - start_time:.2f}s.")
        except FileNotFoundError:
             # Should not happen due to os.path.exists check, but handle defensively
             logger.error(f"load_cache_from_file: File {LOCAL_CACHE_FILE} not found unexpectedly. Took {time.time() - start_time:.2f}s.")
        except Exception as e:
            logger.exception(f"load_cache_from_file: An unexpected error occurred while loading cache: {e}. Took {time.time() - start_time:.2f}s.")
    else:
        logger.info(f"load_cache_from_file: Cache file {LOCAL_CACHE_FILE} does not exist. Took {time.time() - start_time:.2f}s.")
    return None

def save_cache_to_file(cache_data):
    """Saves the current cache data to the local file."""
    start_time = time.time()
    logger.info(f"save_cache_to_file: Attempting to save cache to {LOCAL_CACHE_FILE}...")
    try:
        with open(LOCAL_CACHE_FILE, "wb") as f:
            pickle.dump(cache_data, f)
        logger.info(f"save_cache_to_file: Cache saved successfully in {time.time() - start_time:.2f}s.")
    except Exception as e:
        logger.exception(f"save_cache_to_file: Failed to save cache: {e}. Took {time.time() - start_time:.2f}s.")

async def init_cache(fetch_all_pairs_async):
    global PAIRS_CACHE
    overall_start_time = time.time()
    logger.info("init_cache: Starting cache initialization...")

    # Ensure model is loaded first
    await load_model_async()

    # 1. Try loading from local cache file
    loaded_cache = load_cache_from_file()
    if loaded_cache:
        cache_timestamp = loaded_cache.get("last_updated_timestamp", 0)
        current_time = time.time()
        if (current_time - cache_timestamp) < CACHE_EXPIRY_SECONDS:
            PAIRS_CACHE.update(loaded_cache)
            logger.info(f"init_cache: Cache loaded successfully from file (Timestamp: {time.ctime(cache_timestamp)}). Init duration: {time.time() - overall_start_time:.2f}s.")
            return PAIRS_CACHE
        else:
            logger.info(f"init_cache: Local cache file {LOCAL_CACHE_FILE} is expired (Timestamp: {time.ctime(cache_timestamp)}). Fetching fresh data.")

    # 2. If local cache is invalid, expired, or missing, fetch from backend
    logger.info("init_cache: Fetching fresh data for cache from backend...")
    fetch_start_time = time.time()
    try:
        all_pairs = await fetch_all_pairs_async()
        fetch_duration = time.time() - fetch_start_time
        logger.info(f"init_cache: Fetched {len(all_pairs)} total pairs from backend in {fetch_duration:.2f}s.")

        logger.info("init_cache: Processing fetched pairs and embeddings...")
        processing_start_time = time.time()
        pairs_with_embeddings = [p for p in all_pairs if p.get("vector_embedding")]
        db_embs = []
        decode_errors = 0
        for p in pairs_with_embeddings:
            try:
                emb_bytes = b64decode(p["vector_embedding"])
                emb = np.frombuffer(emb_bytes, dtype=np.float32)
                # Optional: Add dimension check here if needed
                db_embs.append(emb)
            except Exception as decode_err:
                decode_errors += 1
                logger.error(f"init_cache: Could not decode/process embedding for pair {p.get('id', 'N/A')}. Error: {decode_err}")

        processing_duration = time.time() - processing_start_time
        logger.info(f"init_cache: Processed embeddings in {processing_duration:.2f}s. Found {len(pairs_with_embeddings)} pairs with embeddings. {decode_errors} decode errors.")

        # Update PAIRS_CACHE only if fetch was successful
        PAIRS_CACHE["data"] = pairs_with_embeddings
        PAIRS_CACHE["last_updated_timestamp"] = time.time()
        if db_embs:
            logger.debug(f"init_cache: Stacking {len(db_embs)} embeddings into numpy array.")
            PAIRS_CACHE["db_embeddings"] = np.stack(db_embs)
        else:
             logger.warning("init_cache: No valid embeddings found after processing. Setting db_embeddings to None.")
             PAIRS_CACHE["db_embeddings"] = None

        # 3. Save the newly fetched data to local cache file
        save_cache_to_file(PAIRS_CACHE)
        logger.info(f"init_cache: Cache initialized successfully from backend. Total duration: {time.time() - overall_start_time:.2f}s.")

    except Exception as fetch_err:
        logger.exception(f"init_cache: ERROR Failed to fetch/process data from backend: {fetch_err}. Duration: {time.time() - fetch_start_time:.2f}s")
        # Decide how to handle failure
        if loaded_cache:
            logger.warning("init_cache: Using potentially stale cache due to backend fetch failure.")
            PAIRS_CACHE.update(loaded_cache) # Ensure stale cache is used if available
        else:
            logger.error("init_cache: Proceeding without cache due to backend fetch failure and no valid local cache.")
            # Reset cache state if fetch fails and no local cache exists
            PAIRS_CACHE = {"data": None, "db_embeddings": None, "last_updated_timestamp": None}
        # Log total duration even on failure
        logger.info(f"init_cache: Initialization failed. Total duration: {time.time() - overall_start_time:.2f}s.")

    return PAIRS_CACHE

async def update_cache(fetch_all_pairs_async):
    # Force a fetch and save, bypassing expiry check by deleting local file first.
    global PAIRS_CACHE
    start_time = time.time()
    logger.info("update_cache: Starting force update of cache from backend...")

    # Temporarily remove local cache to force fetch in init_cache
    if os.path.exists(LOCAL_CACHE_FILE):
        try:
            os.remove(LOCAL_CACHE_FILE)
            logger.info(f"update_cache: Temporarily removed {LOCAL_CACHE_FILE} to force refresh.")
        except Exception as e:
            logger.error(f"update_cache: Could not remove local cache file {LOCAL_CACHE_FILE} for refresh: {e}")

    # Call init_cache which will now be forced to fetch
    await init_cache(fetch_all_pairs_async)
    logger.info(f"update_cache: Cache force update finished. Timestamp: {time.ctime(PAIRS_CACHE.get('last_updated_timestamp', 0))}. Duration: {time.time() - start_time:.2f}s")
    return PAIRS_CACHE
