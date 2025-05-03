from sentence_transformers import SentenceTransformer
import torch
import httpx
from base64 import b64encode, b64decode
import numpy as np
import asyncio
import time  # Add time import for logging
from schemas import PairStringInput
from utils_cache import PAIRS_CACHE, load_model_async, init_cache, update_cache
from config import logger, BASE_URL, HEADERS # Import logger, BASE_URL, HEADERS
# Import Context if available, handle optional dependency
try:
    from mcp.server.fastmcp import Context
except ImportError:
    Context = None # Define Context as None if mcp is not installed or available

# Load the model on GPU
# model_name = "Snowflake/snowflake-arctic-embed-l-v2.0"
# model = SentenceTransformer(model_name, device="cuda")

### function create embeddings for a text
def generate_embeddings_for_contrasting():
    """
    1. Fetch all contrast pairs with missing embeddings (paginated)
    2. Generate embeddings for each ("item1 vs item2")
    3. Batch update pairs with new embeddings
    """
    start_time = time.time()
    logger.info("Starting generate_embeddings_for_contrasting")
    count = 4000
    page = 1
    params = {"page": page, "count": count, "vector_embedding": True}
    all_pairs = []
    logger.info("Fetching contrast pairs with missing embeddings...")
    fetch_start_time = time.time()
    while True:
        page_fetch_start = time.time()
        logger.debug(f"generate_embeddings: Fetching page {page}...")
        try:
            resp = httpx.get(f"{BASE_URL}/contrast-pairs/", params=params, headers=HEADERS)
            resp.raise_for_status() # Raise HTTP errors
            data = resp.json()
            results = data.get("results", [])
            missing = [p for p in results if p.get("vector_embedding") is None]
            all_pairs.extend(missing)
            logger.debug(f"generate_embeddings: Page {page} fetch successful in {time.time() - page_fetch_start:.2f}s. Found {len(missing)} missing embeddings.")
            if not data.get("next"):
                break
            page += 1
            params["page"] = page
        except httpx.RequestError as exc:
            logger.error(f"generate_embeddings: HTTP Request error fetching page {page}: {exc}")
            break # Stop fetching on error
        except Exception as exc:
            logger.exception(f"generate_embeddings: Unexpected error fetching page {page}: {exc}")
            break # Stop fetching on unexpected error

    logger.info(f"generate_embeddings: Finished fetching pairs in {time.time() - fetch_start_time:.2f}s. Found {len(all_pairs)} pairs needing embeddings.")
    if not all_pairs:
        logger.info("generate_embeddings: No pairs to update.")
        return

    # Prepare texts for embedding
    texts = [f"{p['item1']} vs {p['item2']}" for p in all_pairs]
    # Batch process
    batch_size = 256
    model = None
    try:
        logger.info("generate_embeddings: Loading embedding model...")
        model_load_start = time.time()
        model = asyncio.run(load_model_async()) if not asyncio.get_event_loop().is_running() else None
        if model is None and asyncio.get_event_loop().is_running():
             # If in running loop (like inside FastAPI/MCP request), run differently
             model = asyncio.get_event_loop().run_until_complete(load_model_async())
        logger.info(f"generate_embeddings: Model loaded in {time.time() - model_load_start:.2f}s.")
    except Exception as e:
        logger.exception("generate_embeddings: Failed to load model.")
        return # Cannot proceed without model

    logger.info(f"generate_embeddings: Starting embedding generation for {len(texts)} texts in batches of {batch_size}...")
    total_updates = 0
    for i in range(0, len(texts), batch_size):
        batch_start_time = time.time()
        batch_pairs = all_pairs[i : i + batch_size]
        batch_texts = texts[i : i + batch_size]
        batch_num = i // batch_size + 1
        logger.info(f"generate_embeddings: Encoding batch {batch_num} ({len(batch_texts)} pairs)...")
        try:
            encode_start = time.time()
            # Disable progress bar to prevent tqdm errors
            embeddings = model.encode(batch_texts, show_progress_bar=False)
            logger.debug(f"generate_embeddings: Batch {batch_num} encoded in {time.time() - encode_start:.2f}s.")

            if not isinstance(embeddings, np.ndarray):
                embeddings = np.array(embeddings)

            updates = []
            for pair, emb in zip(batch_pairs, embeddings):
                try:
                    emb_bytes = emb.astype(np.float32).tobytes()
                    emb_b64 = b64encode(emb_bytes).decode("utf-8")
                    updates.append({"id": pair["id"], "vector_embedding": emb_b64})
                except Exception as e_inner:
                     logger.error(f"generate_embeddings: Error processing embedding for pair {pair.get('id')}: {e_inner}")

            if not updates:
                 logger.warning(f"generate_embeddings: No valid updates generated for batch {batch_num}.")
                 continue

            logger.info(f"generate_embeddings: Sending batch update {batch_num} ({len(updates)} pairs)...")
            patch_data = {"updates": updates}
            patch_start = time.time()
            patch_resp = httpx.patch(
                f"{BASE_URL}/contrast-pairs/update/", json=patch_data, headers=HEADERS
            )
            patch_duration = time.time() - patch_start
            if patch_resp.status_code == 200:
                total_updates += len(updates)
                logger.info(f"generate_embeddings: Batch {batch_num} update successful in {patch_duration:.2f}s. Updated {len(updates)} pairs.")
            else:
                logger.error(
                    f"generate_embeddings: Batch {batch_num} update failed. Status {patch_resp.status_code}, Duration: {patch_duration:.2f}s, Response: {patch_resp.text}"
                )
        except Exception as batch_err:
            logger.exception(f"generate_embeddings: Error processing batch {batch_num}: {batch_err}")

        logger.debug(f"generate_embeddings: Batch {batch_num} processed in {time.time() - batch_start_time:.2f}s.")

    logger.info(f"Embedding generation and update complete. Total pairs updated: {total_updates}. Total time: {time.time() - start_time:.2f}s.")
    # Optionally update cache after adding new embeddings
    logger.info("generate_embeddings: Triggering async cache update.")
    asyncio.create_task(update_cache(fetch_all_pairs_async))


async def fetch_page_async(client: httpx.AsyncClient, page: int, count: int):
    params = {"page": page, "count": count, "vector_embedding": True}
    logger.debug(f"fetch_page_async: Requesting page {page} with count {count}...")
    request_start_time = time.time()
    try:
        resp = await client.get(f"{BASE_URL}/contrast-pairs/", params=params, headers=HEADERS)
        resp.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        logger.debug(f"fetch_page_async: Page {page} received status {resp.status_code} in {time.time() - request_start_time:.2f}s.")
        return resp.json()
    except httpx.RequestError as exc:
        logger.error(f"fetch_page_async: HTTP Request error while requesting page {page} after {time.time() - request_start_time:.2f}s: {exc}")
        return None
    except Exception as exc:
        logger.exception(f"fetch_page_async: Unexpected error fetching page {page} after {time.time() - request_start_time:.2f}s: {exc}")
        return None


async def fetch_all_pairs_async(count=200, max_concurrent=4, timeout=30.0):
    overall_start_time = time.time()
    logger.info(f"Starting fetch_all_pairs_async with count={count}, max_concurrent={max_concurrent}, timeout={timeout}...")
    # Create client with timeout
    async with httpx.AsyncClient(timeout=timeout) as client:
        # Fetch first page to get total and results
        logger.info(f"fetch_all_pairs_async: Fetching first page...")
        first_page_start = time.time()
        first_page_data = await fetch_page_async(client, 1, count)
        logger.info(f"fetch_all_pairs_async: First page fetch took {time.time() - first_page_start:.2f}s.")

        if not first_page_data:
            logger.error("fetch_all_pairs_async: Error fetching the first page. Aborting fetch.")
            return [] # Return empty list if first page fails

        total = first_page_data.get("total", 0)
        results = first_page_data.get("results", [])
        if not results and total > 0:
             logger.warning(f"fetch_all_pairs_async: No results found on the first page, but backend reported total={total}.")
             # Continue fetching other pages despite empty first page if total > 0
        elif not results:
             logger.info("fetch_all_pairs_async: No results found on the first page and total is 0.")
             return []

        logger.info(f"fetch_all_pairs_async: Total pairs reported by backend: {total}")
        num_pages = (total + count - 1) // count
        logger.info(f"fetch_all_pairs_async: Calculated number of pages: {num_pages}")

        if num_pages <= 1:
            logger.info("fetch_all_pairs_async: All pairs fetched on the first page.")
            logger.info(f"fetch_all_pairs_async finished in {time.time() - overall_start_time:.2f}s. Retrieved {len(results)} pairs.")
            return results

        # Limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)

        async def sem_fetch(page):
            async with semaphore:
                logger.debug(f"fetch_all_pairs_async: Fetching page {page}/{num_pages}...")
                page_start_time = time.time()
                page_data = await fetch_page_async(client, page, count)
                duration = time.time() - page_start_time
                res_count = len(page_data.get("results", [])) if page_data else 0
                logger.debug(f"fetch_all_pairs_async: Page {page} fetched in {duration:.2f}s with {res_count} results.")
                return page_data.get("results", []) if page_data else []

        # Prepare tasks for remaining pages
        tasks = [sem_fetch(page) for page in range(2, num_pages + 1)]

        logger.info(f"fetch_all_pairs_async: Fetching remaining {len(tasks)} pages concurrently (max {max_concurrent})...")
        remaining_fetch_start = time.time()
        page_results_list = await asyncio.gather(*tasks)
        logger.info(f"fetch_all_pairs_async: Fetched remaining pages in {time.time() - remaining_fetch_start:.2f}s.")

        # Extend the main results list with results from other pages
        for page_res in page_results_list:
            results.extend(page_res)

        logger.info(f"Finished fetch_all_pairs_async in {time.time() - overall_start_time:.2f}s. Total pairs retrieved: {len(results)} (Expected based on total: {total})")
        if len(results) != total:
             logger.warning(f"fetch_all_pairs_async: Mismatch between retrieved pairs ({len(results)}) and reported total ({total}).")
        return results


async def get_similar_pairs(pair_string: PairStringInput, k: int = 10, ctx: Context = None):
    """
    1. Use cached pairs with embeddings
    2. Generate embedding for the input pair_string
    3. Use pre-decoded DB embeddings from cache
    4. Compute cosine similarity
    5. Return top k most similar pairs (with similarity score)
    Optionally reports progress using MCP context.
    """
    overall_start_time = time.time()
    input_text_log = pair_string.pair_string if isinstance(pair_string, PairStringInput) else pair_string
    logger.info(f"Entering get_similar_pairs for '{input_text_log}', k={k}")

    # Helper for safe progress reporting
    async def report_progress(step, total, message):
        if ctx and Context is not None:
            try:
                logger.debug(f"Reporting progress: Step {step}/{total} - {message}")
                await ctx.report_progress(step, total, message)
            except Exception as report_err:
                logger.warning(f"Failed to report progress: {report_err}")
        else:
            logger.debug(f"Progress (no ctx): Step {step}/{total} - {message}")

    total_steps = 4 # Define total steps for progress reporting

    # Step 1: Load model (already logged inside load_model_async)
    await report_progress(0, total_steps, "Loading embedding model...")
    model = await load_model_async()
    # Check if model loaded
    if model is None:
        logger.error("get_similar_pairs: Failed to load model.")
        return []

    # Step 2: Ensure cache is initialized
    await report_progress(1, total_steps, "Checking cache...")
    if PAIRS_CACHE["data"] is None:
        logger.warning("get_similar_pairs: Cache not initialized, attempting to initialize now...")
        cache_init_start = time.time()
        await init_cache(fetch_all_pairs_async)
        logger.info(f"get_similar_pairs: Cache initialization attempt took {time.time() - cache_init_start:.2f}s.")

    all_pairs = PAIRS_CACHE["data"]
    db_embs = PAIRS_CACHE["db_embeddings"]

    if not all_pairs or db_embs is None or len(db_embs) == 0:
        logger.error("get_similar_pairs: No pairs with embeddings found in cache after initialization attempt.")
        return []

    logger.info(f"get_similar_pairs: Found {len(all_pairs)} pairs with {len(db_embs)} embeddings (shape: {db_embs.shape}) in cache.")

    # Step 3: Generate input embedding
    await report_progress(2, total_steps, "Generating input embedding...")
    input_text = pair_string.pair_string if isinstance(pair_string, PairStringInput) else pair_string
    logger.debug(f"get_similar_pairs: Generating embedding for input: '{input_text}'")
    encode_start = time.time()
    try:
        # Disable progress bar to prevent tqdm errors
        input_emb = model.encode([input_text], show_progress_bar=False)[0]
        input_emb = input_emb.astype(np.float32)
        logger.debug(f"get_similar_pairs: Input embedding generated in {time.time() - encode_start:.2f}s.")
    except Exception as e:
        logger.exception(f"get_similar_pairs: Error generating embedding for input '{input_text}': {e}")
        return []

    # Step 4: Compute similarity
    await report_progress(3, total_steps, "Calculating similarities...")
    logger.debug(f"get_similar_pairs: Computing cosine similarities for {db_embs.shape[0]} cached embeddings...")
    sim_start = time.time()
    try:
        # Normalize input embedding
        input_norm_val = np.linalg.norm(input_emb)
        if input_norm_val == 0:
             logger.error("get_similar_pairs: Input embedding norm is zero. Cannot compute similarity.")
             return []
        input_norm = input_emb / input_norm_val

        # Normalize database embeddings
        db_norms_val = np.linalg.norm(db_embs, axis=1, keepdims=True)
        # Handle potential zero norms in db embeddings
        zero_norm_indices = np.where(db_norms_val == 0)[0]
        if len(zero_norm_indices) > 0:
            logger.warning(f"get_similar_pairs: Found {len(zero_norm_indices)} zero-norm embeddings in cache. Excluding them from similarity calculation.")
            # Set norms for zero-norm vectors to a small epsilon to avoid division by zero,
            # their dot product will be zero anyway if input_norm is not zero.
            # Or, more simply, ensure they result in zero similarity. We can handle this later.
            db_norms_val[zero_norm_indices] = 1e-9 # Avoid division by zero

        db_norms = db_embs / db_norms_val

        # Compute dot product (cosine similarity for normalized vectors)
        sims = np.dot(db_norms, input_norm)

        # Explicitly set similarity to -1 (or lowest possible) for zero-norm vectors if any
        # This ensures they are ranked last.
        if len(zero_norm_indices) > 0:
             sims[zero_norm_indices] = -1.0

        logger.debug(f"get_similar_pairs: Similarity computation took {time.time() - sim_start:.2f}s.")
    except Exception as e:
        logger.exception(f"get_similar_pairs: Error during similarity computation: {e}")
        return []

    # Step 5: Sort and return (considered part of step 4 for progress)
    logger.debug(f"get_similar_pairs: Sorting and selecting top {k} pairs...")
    sort_start = time.time()
    # Ensure k is not larger than the number of available similarities
    actual_k = min(k, len(sims))
    # Use argpartition for efficiency if k is much smaller than len(sims)
    # top_idx = np.argsort(sims)[::-1][:actual_k]
    if actual_k < len(sims) // 2 : # Heuristic for when argpartition is faster
        top_idx = np.argpartition(sims, -actual_k)[-actual_k:]
        # Need to sort the partitioned indices by similarity score
        top_sims = sims[top_idx]
        sorted_indices_of_top = np.argsort(top_sims)[::-1]
        top_idx = top_idx[sorted_indices_of_top]
    else: # Otherwise just sort all
         top_idx = np.argsort(sims)[::-1][:actual_k]

    top_pairs = []
    for idx in top_idx:
        # Ensure index is valid
        if idx < 0 or idx >= len(all_pairs):
            logger.error(f"get_similar_pairs: Invalid index {idx} obtained during sorting.")
            continue
        pair = all_pairs[idx]
        score = float(sims[idx])
        top_pairs.append({
            "id": pair["id"],
            "item1": pair["item1"],
            "item2": pair["item2"],
            "similarity": score # Include similarity score for debugging
        })
    logger.debug(f"get_similar_pairs: Sorting and selection took {time.time() - sort_start:.2f}s.")

    # Final progress update
    await report_progress(4, total_steps, "Completed similarity search.")
    logger.info(f"Exiting get_similar_pairs for '{input_text_log}'. Found {len(top_pairs)} similar pairs. Total duration: {time.time() - overall_start_time:.2f}s.")
    return top_pairs


async def main():
    # Initialize cache at startup
    await init_cache(fetch_all_pairs_async)
    # Test the optimized function
    test_start = time.time()
    top_pairs = await get_similar_pairs(pair_string="wirtualne vs cyfrowa", k=50)
    logger.info(f"Test call duration: {time.time() - test_start:.2f}s")
    for pair in top_pairs:
        print(f"id: {pair['id']} | {pair['item1']} vs {pair['item2']} | Sim: {pair.get('similarity', 'N/A'):.4f}")

if __name__ == "__main__":
    asyncio.run(main())

### generate embedding for contrasting ()

###get contrasting pairs (pairs list)
