from pathlib import Path
from typing import List, Dict, Any
import json
import numpy as np
import faiss
from openai import OpenAI
from dotenv import load_dotenv
import os
import tiktoken

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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


def query_index(
    question: str, 
    index: faiss.Index, 
    metadata: List[Dict[str, Any]], 
    top_k: int = 5
) -> List[Dict[str, Any]]:
    
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

def build_rag_query(history, current_message, max_tokens=2500):

    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")

    current_tokens = encoding.encode(current_message)
    current_token_count = len(current_tokens)

    # Ensure current message fits by reducing budget for history
    remaining_tokens = max_tokens - current_token_count
    if remaining_tokens < 0:
        # If the current message alone exceeds max_tokens, truncate it
        truncated_current = encoding.decode(current_tokens[:max_tokens])
        return truncated_current.strip()

    # Reverse user messages (most recent first)
    user_messages = [
        msg["content"] for msg in reversed(history)
        if msg["role"] == "user"
    ]

    total_tokens = 0
    selected = []

    for msg in user_messages:
        msg_tokens = encoding.encode(msg)
        token_count = len(msg_tokens)
        if total_tokens + token_count > remaining_tokens:
            break
        selected.insert(0, msg)
        total_tokens += token_count

    selected.append(current_message)
    return " ".join(selected).strip()


# Add distance
# something to do!
# for i, idx in enumerate(indices[0]):
#     if idx < len(metadata):
#         match = metadata[idx].copy()
#         match["distance"] = float(distances[0][i])
#         results.append(match)