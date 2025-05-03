import asyncio
import time
import numpy as np
from sentence_transformers import SentenceTransformer
import torch

MODEL = None
PAIRS_CACHE = {
    "data": None,
    "last_updated": None,
    "db_embeddings": None
}

async def load_model_async():
    global MODEL
    if MODEL is None:
        print(f"cuda available: {torch.cuda.is_available()}")
        loop = asyncio.get_event_loop()
        MODEL = await loop.run_in_executor(
            None,
            lambda: SentenceTransformer("Snowflake/snowflake-arctic-embed-l-v2.0", device="cuda")
        )
        print("Model loaded successfully")
    return MODEL

async def init_cache(fetch_all_pairs_async):
    global PAIRS_CACHE
    await load_model_async()
    all_pairs = await fetch_all_pairs_async()
    pairs_with_embeddings = [p for p in all_pairs if p.get("vector_embedding")]
    db_embs = []
    for p in pairs_with_embeddings:
        from base64 import b64decode
        emb_bytes = b64decode(p["vector_embedding"])
        emb = np.frombuffer(emb_bytes, dtype=np.float32)
        db_embs.append(emb)
    PAIRS_CACHE["data"] = pairs_with_embeddings
    PAIRS_CACHE["last_updated"] = time.time()
    if db_embs:
        PAIRS_CACHE["db_embeddings"] = np.stack(db_embs)
    print(f"Cache initialized with {len(pairs_with_embeddings)} pairs and embeddings")
    return PAIRS_CACHE

async def update_cache(fetch_all_pairs_async):
    print("Updating cache...")
    await init_cache(fetch_all_pairs_async)
    print(f"Cache updated at {time.ctime(PAIRS_CACHE['last_updated'])}")
    return PAIRS_CACHE
