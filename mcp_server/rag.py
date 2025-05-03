from sentence_transformers import SentenceTransformer
import torch
# Load the model on GPU
# model_name = "Snowflake/snowflake-arctic-embed-l-v2.0"
# model = SentenceTransformer(model_name, device="cuda")

### function create embeddings for a text
from config import HEADERS, BASE_URL
import httpx
from base64 import b64encode, b64decode
import numpy as np
import asyncio
from schemas import PairStringInput
from utils_cache import PAIRS_CACHE, load_model_async, init_cache, update_cache


def generate_embeddings_for_contrasting():
    """
    1. Fetch all contrast pairs with missing embeddings (paginated)
    2. Generate embeddings for each ("item1 vs item2")
    3. Batch update pairs with new embeddings
    """
    count = 4000
    page = 1
    params = {"page": page, "count": count, "vector_embedding": True}
    all_pairs = []
    print("Fetching contrast pairs with missing embeddings...")
    while True:
        resp = httpx.get(f"{BASE_URL}/contrast-pairs/", params=params, headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        # Filter for pairs with missing embedding
        missing = [p for p in results if p.get("vector_embedding") is None]
        all_pairs.extend(missing)
        if not data.get("next"):
            break
        page += 1
        params["page"] = page
    print(f"Found {len(all_pairs)} pairs needing embeddings.")
    if not all_pairs:
        print("No pairs to update.")
        return
    # Prepare texts for embedding
    texts = [f"{p['item1']} vs {p['item2']}" for p in all_pairs]
    # Batch process (in case of large number)
    batch_size = 256
    # Always get model instance
    model = asyncio.run(load_model_async()) if asyncio.get_event_loop().is_running() == False else None
    if model is None:
        model = asyncio.get_event_loop().run_until_complete(load_model_async())
    for i in range(0, len(texts), batch_size):
        batch_pairs = all_pairs[i : i + batch_size]
        batch_texts = texts[i : i + batch_size]
        print(f"Encoding batch {i//batch_size+1} ({len(batch_texts)} pairs)...")
        embeddings = model.encode(batch_texts)
        # Ensure embeddings is a numpy array
        if not isinstance(embeddings, np.ndarray):
            embeddings = np.array(embeddings)
        # Convert each embedding to base64
        updates = []
        for pair, emb in zip(batch_pairs, embeddings):
            emb_bytes = emb.astype(np.float32).tobytes()
            emb_b64 = b64encode(emb_bytes).decode("utf-8")
            updates.append({"id": pair["id"], "vector_embedding": emb_b64})
        # Send batch update
        patch_data = {"updates": updates}
        patch_resp = httpx.patch(
            f"{BASE_URL}/contrast-pairs/update/", json=patch_data, headers=HEADERS
        )
        if patch_resp.status_code == 200:
            print(f"Batch {i//batch_size+1}: Updated {len(updates)} pairs.")
        else:
            print(
                f"Batch {i//batch_size+1}: Error {patch_resp.status_code}: {patch_resp.text}"
            )
    print("Embedding generation and update complete.")
    # Optionally update cache after adding new embeddings
    asyncio.create_task(update_cache(fetch_all_pairs_async))


async def fetch_page_async(client: httpx.AsyncClient, page: int, count: int):
    params = {"page": page, "count": count, "vector_embedding": True}
    try:
        resp = await client.get(f"{BASE_URL}/contrast-pairs/", params=params, headers=HEADERS)
        resp.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        return resp.json()
    except httpx.RequestError as exc:
        print(f"An error occurred while requesting page {page}: {exc}")
        return None  # Return None or empty dict to indicate failure
    except Exception as exc:
        print(f"An unexpected error occurred fetching page {page}: {exc}")
        return None

async def fetch_all_pairs_async(count=200, max_concurrent=4, timeout=30.0):
    # Create client with timeout
    async with httpx.AsyncClient(timeout=timeout) as client:
        # Fetch first page to get total and results
        print(f"Fetching first page with count={count}...")
        first_page_data = await fetch_page_async(client, 1, count)
        if not first_page_data:
            print("Error fetching the first page. Aborting cache update.")
            return [] # Return empty list if first page fails

        total = first_page_data.get("total", 0)
        results = first_page_data.get("results", [])
        if not results:
             print("No results found on the first page.")
             # Decide if we should continue if first page is empty but total > 0?
             # For now, return if first page results are empty.
             return []

        print(f"Total pairs reported by backend: {total}")
        num_pages = (total + count - 1) // count
        print(f"Calculated number of pages: {num_pages}")

        if num_pages <= 1:
            print("All pairs fetched on the first page.")
            return results

        # Limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)

        async def sem_fetch(page):
            async with semaphore:
                print(f"Fetching page {page}/{num_pages}...")
                page_data = await fetch_page_async(client, page, count)
                return page_data.get("results", []) if page_data else []

        # Prepare tasks for remaining pages
        tasks = [sem_fetch(page) for page in range(2, num_pages + 1)]

        print(f"Fetching remaining {len(tasks)} pages concurrently (max {max_concurrent})...")
        page_results_list = await asyncio.gather(*tasks)

        # Extend the main results list with results from other pages
        for page_res in page_results_list:
            results.extend(page_res)

        print(f"Finished fetching all pages. Total pairs retrieved: {len(results)}")
        return results


async def get_similar_pairs(pair_string: PairStringInput, k: int = 10):
    """
    1. Use cached pairs with embeddings
    2. Generate embedding for the input pair_string
    3. Use pre-decoded DB embeddings from cache
    4. Compute cosine similarity
    5. Return top k most similar pairs (with similarity score)
    """
    # Always get model instance
    model = await load_model_async()
    # Check if cache is initialized
    if PAIRS_CACHE["data"] is None:
        print("Cache not initialized, loading...")
        await init_cache(fetch_all_pairs_async)
    # Check if we have data in cache
    all_pairs = PAIRS_CACHE["data"]
    if not all_pairs:
        print("No pairs with embeddings found in cache.")
        return []
    # Generate embedding for input pair_string
    input_text = pair_string.pair_string if isinstance(pair_string, PairStringInput) else pair_string
    input_emb = model.encode([input_text])[0]
    input_emb = input_emb.astype(np.float32)
    # Use pre-computed embeddings from cache
    db_embs = PAIRS_CACHE["db_embeddings"]
    # Compute cosine similarity
    input_norm = input_emb / np.linalg.norm(input_emb)
    db_norms = db_embs / np.linalg.norm(db_embs, axis=1, keepdims=True)
    sims = np.dot(db_norms, input_norm)
    # Sort and return top k
    top_idx = np.argsort(sims)[::-1][:k]
    top_pairs = []
    for idx in top_idx:
        pair = all_pairs[idx]
        score = float(sims[idx])
        top_pairs.append({
            "id": pair["id"],
            "item1": pair["item1"],
            "item2": pair["item2"],
            # "similarity": score
        })
    return top_pairs


async def main():
    # Initialize cache at startup
    await init_cache(fetch_all_pairs_async)
    # Test the optimized function
    top_pairs = await get_similar_pairs(pair_string="wirtualne vs cyfrowa", k=50)
    for pair in top_pairs:
        print(f"id: {pair['id']} | {pair['item1']} vs {pair['item2']}")

if __name__ == "__main__":
    asyncio.run(main())

### generate embedding for contrasting ()

###get contrasting pairs (pairs list)
