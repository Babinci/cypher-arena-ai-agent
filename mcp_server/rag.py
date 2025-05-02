#### embedding model from huggingface- example from website

from sentence_transformers import SentenceTransformer
import torch

print(f"cuda available: {torch.cuda.is_available()}")
# Load the model on GPU
model_name = "Snowflake/snowflake-arctic-embed-l-v2.0"
model = SentenceTransformer(model_name, device="cuda")

### function create embeddings for a text
from config import HEADERS, BASE_URL
import httpx
from base64 import b64encode, b64decode
import numpy as np
from pydantic import BaseModel, field_validator
import re
import asyncio

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




class PairStringInput(BaseModel):
    pair_string: str

    @field_validator("pair_string")
    @classmethod
    def must_match_vs_format(cls, v):
        if not re.match(r"^.+ vs .+$", v):
            raise ValueError("pair_string must be in the format 'Item1 vs Item2'")
        return v


async def fetch_page_async(client, page, count):
    params = {"page": page, "count": count, "vector_embedding": True}
    resp = await client.get(f"{BASE_URL}/contrast-pairs/", params=params, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()

async def fetch_all_pairs_async(count=800, max_concurrent=4):
    async with httpx.AsyncClient() as client:
        # Fetch first page to get total and results
        first = await fetch_page_async(client, 1, count)
        total = first.get("total", 0)
        results = first.get("results", [])
        num_pages = (total + count - 1) // count
        if num_pages <= 1:
            return results
        # Limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        async def sem_fetch(page):
            async with semaphore:
                return await fetch_page_async(client, page, count)
        # Prepare tasks for remaining pages
        tasks = [sem_fetch(page) for page in range(2, num_pages + 1)]
        pages = await asyncio.gather(*tasks)
        for page in pages:
            results.extend(page.get("results", []))
        return results

def fetch_all_pairs_sync(count=800, max_concurrent=4):
    """Sync wrapper for async fetch_all_pairs_async."""
    return asyncio.run(fetch_all_pairs_async(count, max_concurrent))

def fetch_all_pairs_direct():
    """Fetches all contrast pairs using the fetch_all=true parameter."""
    print("Fetching all pairs directly using fetch_all=true...")
    params = {"fetch_all": True}
    # vector_embedding is implicitly true when fetch_all=true according to docs
    try:
        resp = httpx.get(f"{BASE_URL}/contrast-pairs/", params=params, headers=HEADERS, timeout=None) # Allow long timeout for potentially large response
        resp.raise_for_status()
        data = resp.json()
        print(f"Successfully fetched {len(data)} pairs directly.")
        return data
    except httpx.RequestError as exc:
        print(f"An error occurred while requesting {exc.request.url!r}: {exc}")
        raise
    except httpx.HTTPStatusError as exc:
        print(f"Error response {exc.response.status_code} while requesting {exc.request.url!r}: {exc.response.text}")
        raise

def get_similar_pairs(pair_string: PairStringInput, k: int = 10):
    """
    1. Fetch all contrast pairs with embeddings (async)
    2. Generate embedding for the input pair_string
    3. Decode all DB embeddings
    4. Compute cosine similarity
    5. Return top k most similar pairs (with similarity score)
    """
    from base64 import b64decode
    import numpy as np
    # 1. Fetch all pairs with embeddings
    # print("Fetching contrast pairs with embeddings (async)...")
    all_pairs = fetch_all_pairs_sync()
    # Only keep pairs with a non-None embedding
    all_pairs = [p for p in all_pairs if p.get("vector_embedding")]
    # print(f"Found {len(all_pairs)} pairs with embeddings.")
    if not all_pairs:
        # print("No pairs with embeddings found.")
        return []
    # 2. Generate embedding for input pair_string
    input_text = pair_string.pair_string if isinstance(pair_string, PairStringInput) else pair_string
    input_emb = model.encode([input_text])[0]
    input_emb = input_emb.astype(np.float32)
    # 3. Decode all DB embeddings
    db_embs = []
    for p in all_pairs:
        emb_bytes = b64decode(p["vector_embedding"])
        emb = np.frombuffer(emb_bytes, dtype=np.float32)
        db_embs.append(emb)
    db_embs = np.stack(db_embs)
    # 4. Compute cosine similarity
    input_norm = input_emb / np.linalg.norm(input_emb)
    db_norms = db_embs / np.linalg.norm(db_embs, axis=1, keepdims=True)
    sims = np.dot(db_norms, input_norm)
    # 5. Sort and return top k
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
    # print(f"Top {k} most similar pairs to '{input_text}':")
    # for p in top_pairs:
    #     print(f"{p['item1']} vs {p['item2']} (id={p['id']}): similarity={p['similarity']:.4f}")
    return top_pairs

from pprint import pprint
if __name__ == "__main__":
    # generate_embeddings_for_contrasting()
    top_pairs = get_similar_pairs(pair_string="wirtualne vs cyfrowa", k=50)
    # pprint(f" Top pairs: {top_pairs}")
    for pair in top_pairs:
        print(f"id: {pair['id']} | {pair['item1']} vs {pair['item2']}")

### generate embedding for contrasting ()

###get contrasting pairs (pairs list)
