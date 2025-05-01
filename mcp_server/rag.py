#### embedding model from huggingface

from sentence_transformers import SentenceTransformer
import torch
print(torch.cuda.is_available()) 
# Load the model on GPU
model_name = 'Snowflake/snowflake-arctic-embed-l-v2.0'
model = SentenceTransformer(model_name, device='cuda')

# Define the queries and documents
queries = ['what is snowflake?', 'Where can I get the best tacos?']
documents = ['The Data Cloud!', 'Mexico City of Course!']

# Compute embeddings on GPU
query_embeddings = model.encode(queries, prompt_name="query")
document_embeddings = model.encode(documents)

# Compute cosine similarity scores
scores = model.similarity(query_embeddings, document_embeddings)

# Output the results
for query, query_scores in zip(queries, scores):
    doc_score_pairs = list(zip(documents, query_scores))
    doc_score_pairs = sorted(doc_score_pairs, key=lambda x: x[1], reverse=True)
    print("Query:", query)
    for document, score in doc_score_pairs:
        print(score, document)



### function create embeddings for a text


def generate_embeddings_for_contrasting():
    ''' flow:
    1. gets all pairs from GET with pagination (1000)
    2. use model to generate embeddings for each pair 
    (update for each generated with PATH) <- maybe async?
    3. some code to generate embeddings only for pairs 
    that don't have embeddings (or flag from db TODO)
    '''
    pass


def get_similar_pairs(k:int=10):
    '''performs rag to get k most similar pairs to a given pair
    flow:
        1. gets all pairs from GET with pagination (1000)
        2. then search with rag for k most similar pairs
        3. return pairs  
    '''
    pass

### generate embedding for contrasting ()

###get contrasting pairs (pairs list)