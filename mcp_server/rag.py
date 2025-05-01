#### embedding model from huggingface- example from website

from sentence_transformers import SentenceTransformer
import torch
print(f"cuda available: {torch.cuda.is_available()}") 
# Load the model on GPU
model_name = 'Snowflake/snowflake-arctic-embed-l-v2.0'
model = SentenceTransformer(model_name, device='cuda')

# # Define the queries and documents
# queries = ['what is snowflake?', 'Where can I get the best tacos?']
# documents = ['The Data Cloud!', 'Mexico City of Course!']

# # Compute embeddings on GPU
# query_embeddings = model.encode(queries, prompt_name="query")
# document_embeddings = model.encode(documents)

# # Compute cosine similarity scores
# scores = model.similarity(query_embeddings, document_embeddings)

# # Output the results
# for query, query_scores in zip(queries, scores):
#     doc_score_pairs = list(zip(documents, query_scores))
#     doc_score_pairs = sorted(doc_score_pairs, key=lambda x: x[1], reverse=True)
#     print("Query:", query)
#     for document, score in doc_score_pairs:
#         print(score, document)



### function create embeddings for a text
from main import HEADERS, BASE_URL, httpx
from base64 import b64encode
import numpy as np

def generate_embeddings_for_contrasting():
    '''
    1. Fetch all contrast pairs with missing embeddings (paginated)
    2. Generate embeddings for each ("item1 vs item2")
    3. Batch update pairs with new embeddings
    '''
    count = 1000
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
        batch_pairs = all_pairs[i:i+batch_size]
        batch_texts = texts[i:i+batch_size]
        print(f"Encoding batch {i//batch_size+1} ({len(batch_texts)} pairs)...")
        embeddings = model.encode(batch_texts)
        # Ensure embeddings is a numpy array
        if not isinstance(embeddings, np.ndarray):
            embeddings = np.array(embeddings)
        # Convert each embedding to base64
        updates = []
        for pair, emb in zip(batch_pairs, embeddings):
            emb_bytes = emb.astype(np.float32).tobytes()
            emb_b64 = b64encode(emb_bytes).decode('utf-8')
            updates.append({"id": pair["id"], "vector_embedding": emb_b64})
        # Send batch update
        patch_data = {"updates": updates}
        patch_resp = httpx.patch(f"{BASE_URL}/contrast-pairs/update/", json=patch_data, headers=HEADERS)
        if patch_resp.status_code == 200:
            print(f"Batch {i//batch_size+1}: Updated {len(updates)} pairs.")
        else:
            print(f"Batch {i//batch_size+1}: Error {patch_resp.status_code}: {patch_resp.text}")
    print("Embedding generation and update complete.")


def get_similar_pairs(pair_string:str,k:int=10):
    '''performs rag to get k most similar pairs to a given pair
    flow:
        1. gets all pairs from GET with pagination (1000)
        2. then search with rag for k most similar pairs
        3. return pairs  
    '''
    pass


if __name__ == "__main__":
    generate_embeddings_for_contrasting()

### generate embedding for contrasting ()

###get contrasting pairs (pairs list)