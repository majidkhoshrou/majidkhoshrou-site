from pathlib import Path
import json
import faiss
import numpy as np
from typing import List, Dict, Any


def build_faiss_index(
    embeddings_path: Path,
    output_path: Path,
    force: bool = False
) -> None:
    """
    Build a FAISS index from precomputed OpenAI embeddings.

    Args:
        embeddings_path (Path): Path to the JSON file containing embeddings.
        output_path (Path): Path to save the FAISS index file.
        force (bool): If True, overwrite existing index file.
    """
    if output_path.exists() and not force:
        print(f"⚠️ FAISS index already exists at {output_path}, skipping. Use --force to overwrite.")
        return

    with embeddings_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not data:
        raise ValueError("No embeddings found to index.")

    vectors = np.array([item["embedding"] for item in data], dtype=np.float32)
    index = faiss.IndexFlatL2(vectors.shape[1])
    index.add(vectors)

    faiss.write_index(index, str(output_path))
    print(f"✅ FAISS index saved to {output_path}")

if __name__ == "__main__":
    build_faiss_index()
