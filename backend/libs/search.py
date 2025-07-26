from pathlib import Path
from typing import List, Dict, Any
import json
import numpy as np
import faiss
from openai import OpenAI
from dotenv import load_dotenv
import os

def get_faiss_index(index_path: Path) -> faiss.Index:
    """
    Load a FAISS index from a given file path.

    Args:
        index_path (Path): Path to the FAISS index file.

    Returns:
        faiss.Index: The loaded FAISS index.
    """
    return faiss.read_index(str(index_path))

def load_metadata_pickle(path: Path) -> List[Dict]:
    import pickle
    with open(path, "rb") as f:
        return pickle.load(f)



load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def query_index(question: str, index, metadata: List[Dict], top_k: int = 5) -> List[Dict]:
    response = client.embeddings.create(
        input=question,
        model="text-embedding-3-small"
    )
    query_vector = np.array(response.data[0].embedding).astype("float32").reshape(1, -1)

    distances, indices = index.search(query_vector, top_k)

    results = []
    for i, idx in enumerate(indices[0]):
        if idx < len(metadata):
            results.append(metadata[idx])
    return results


# Add distance
# something to do!
# for i, idx in enumerate(indices[0]):
#     if idx < len(metadata):
#         match = metadata[idx].copy()
#         match["distance"] = float(distances[0][i])
#         results.append(match)