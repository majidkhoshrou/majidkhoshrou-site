from pathlib import Path
from typing import List, Dict, Any
import os
import numpy as np
import faiss
import tiktoken
from functools import lru_cache
from libs.utils import get_openai_client  # reads OPENAI_API_KEY from env or SSM

@lru_cache(maxsize=1)
def _client():
    return get_openai_client()

def get_faiss_index(index_path: Path) -> faiss.Index:
    """Load a FAISS index from a given file path."""
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
    # Build the query embedding using a lazily created OpenAI client
    response = _client().embeddings.create(
        input=question,
        model="text-embedding-3-small"
    )
    query_vector = np.asarray(response.data[0].embedding, dtype="float32").reshape(1, -1)

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

    remaining_tokens = max_tokens - current_token_count
    if remaining_tokens < 0:
        return encoding.decode(current_tokens[:max_tokens]).strip()

    user_messages = [
        msg["content"] for msg in reversed(history)
        if msg.get("role") == "user"
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
