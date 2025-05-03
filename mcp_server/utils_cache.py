import asyncio
import time
import numpy as np
from sentence_transformers import SentenceTransformer
import torch
import pickle
import os

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
    if MODEL is None:
        # print(f"cuda available: {torch.cuda.is_available()}")
        loop = asyncio.get_event_loop()
        MODEL = await loop.run_in_executor(
            None,
            lambda: SentenceTransformer("Snowflake/snowflake-arctic-embed-l-v2.0", device="cuda")
        )
        print("Model loaded successfully")
    return MODEL

def load_cache_from_file():
    """Attempts to load cache data from the local file."""
    if os.path.exists(LOCAL_CACHE_FILE):
        try:
            with open(LOCAL_CACHE_FILE, "rb") as f:
                cached_data = pickle.load(f)
                # Basic validation
                if isinstance(cached_data, dict) and "last_updated_timestamp" in cached_data:
                    return cached_data
                else:
                    print(f"Warning: Invalid cache file format found in {LOCAL_CACHE_FILE}.")
        except (pickle.UnpicklingError, EOFError, FileNotFoundError) as e:
            print(f"Warning: Could not load cache from {LOCAL_CACHE_FILE}. Error: {e}")
        except Exception as e:
            print(f"Warning: An unexpected error occurred while loading cache: {e}")
    return None

def save_cache_to_file(cache_data):
    """Saves the current cache data to the local file."""
    try:
        with open(LOCAL_CACHE_FILE, "wb") as f:
            pickle.dump(cache_data, f)
        # print(f"Cache saved successfully to {LOCAL_CACHE_FILE}.")
    except Exception as e:
        print(f"Warning: Failed to save cache to {LOCAL_CACHE_FILE}. Error: {e}")

async def init_cache(fetch_all_pairs_async):
    global PAIRS_CACHE
    await load_model_async()

    # 1. Try loading from local cache file
    loaded_cache = load_cache_from_file()
    if loaded_cache:
        cache_timestamp = loaded_cache.get("last_updated_timestamp", 0)
        current_time = time.time()
        if (current_time - cache_timestamp) < CACHE_EXPIRY_SECONDS:
            PAIRS_CACHE.update(loaded_cache)
            print(f"Cache loaded successfully from {LOCAL_CACHE_FILE} (updated {time.ctime(cache_timestamp)}).")
            return PAIRS_CACHE
        else:
            print(f"Local cache file {LOCAL_CACHE_FILE} is expired. Fetching fresh data.")

    # 2. If local cache is invalid, expired, or missing, fetch from backend
    print("Fetching fresh data for cache from backend...")
    try:
        all_pairs = await fetch_all_pairs_async()
        pairs_with_embeddings = [p for p in all_pairs if p.get("vector_embedding")]
        db_embs = []
        for p in pairs_with_embeddings:
            from base64 import b64decode
            try:
                emb_bytes = b64decode(p["vector_embedding"])
                emb = np.frombuffer(emb_bytes, dtype=np.float32)
                # Add dimension check if needed based on model output
                # Example: if emb.shape == (EXPECTED_DIM,):
                db_embs.append(emb)
                # else: print(f"Warning: Skipping pair {p['id']} due to unexpected embedding dimension.")
            except Exception as decode_err:
                print(f"Warning: Could not decode embedding for pair {p.get('id', 'N/A')}. Error: {decode_err}")

        # Update PAIRS_CACHE only if fetch was successful
        PAIRS_CACHE["data"] = pairs_with_embeddings
        PAIRS_CACHE["last_updated_timestamp"] = time.time()
        if db_embs:
            PAIRS_CACHE["db_embeddings"] = np.stack(db_embs)
        else:
             PAIRS_CACHE["db_embeddings"] = None # Ensure it's None if no valid embeddings

        # 3. Save the newly fetched data to local cache file
        save_cache_to_file(PAIRS_CACHE)
        print(f"Cache initialized with {len(pairs_with_embeddings)} pairs and embeddings from backend.")

    except Exception as fetch_err:
        print(f"ERROR: Failed to fetch data from backend during cache initialization: {fetch_err}")
        # Decide how to handle failure: raise error, use stale cache, or run without cache?
        # For now, let's proceed with potentially empty/stale cache if load was attempted
        if loaded_cache:
            print("Warning: Using potentially stale cache due to backend fetch failure.")
            PAIRS_CACHE.update(loaded_cache)
        else:
            print("Warning: Proceeding without cache due to backend fetch failure and no valid local cache.")
            # Reset cache state if fetch fails and no local cache exists
            PAIRS_CACHE = {"data": None, "db_embeddings": None, "last_updated_timestamp": None}

    return PAIRS_CACHE

async def update_cache(fetch_all_pairs_async):
    # This function might need rethinking - should it force a fetch or just call init?
    # For now, let's make it force a fetch and save, bypassing expiry check.
    global PAIRS_CACHE
    print("Force updating cache from backend...")
    # Temporarily remove local cache to force fetch in init_cache
    if os.path.exists(LOCAL_CACHE_FILE):
        try:
            os.remove(LOCAL_CACHE_FILE)
            print(f"Temporarily removed {LOCAL_CACHE_FILE} to force refresh.")
        except Exception as e:
            print(f"Warning: Could not remove local cache file for refresh: {e}")

    await init_cache(fetch_all_pairs_async)
    print(f"Cache force updated at {time.ctime(PAIRS_CACHE.get('last_updated_timestamp', 0))}")
    return PAIRS_CACHE
