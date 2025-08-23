import os
import json
import time
import random
import hashlib
import argparse
from pathlib import Path
from typing import Callable, Any, Dict, List, Set

import numpy as np
import faiss
from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm
import pickle


def retry_with_backoff(fn: Callable[[], Any], retries: int = 5) -> Any:
    for attempt in range(retries):
        try:
            return fn()
        except Exception as e:
            wait = (2 ** attempt) + random.uniform(0, 1)
            print(f"⏳ Retry {attempt + 1}/{retries} in {wait:.2f}s due to error: {e}")
            time.sleep(wait)
    raise RuntimeError("Failed after multiple retries.")


def get_text_hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def load_chunks(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_existing_hashes(path: Path) -> Set[str]:
    if not path.exists():
        return set()
    with path.open("rb") as f:
        metadata = pickle.load(f)
    return {get_text_hash(m["embedding_input"]) for m in metadata}


def embed_chunks(client: OpenAI, model: str, chunks: List[Dict[str, Any]], seen_hashes: Set[str]) -> (List[List[float]], List[Dict[str, Any]]):
    embeddings = []
    metadata = []

    for chunk in tqdm(chunks, desc="🔢 Embedding chunks"):
        title = chunk.get("title", "Untitled")
        text = chunk.get("text", "").strip()
        source = chunk.get("source_path", "")

        if not text:
            continue

        embedding_input = f"Source: {source}\nTitle: {title}\nText: {text}"
        text_hash = get_text_hash(embedding_input)

        if text_hash in seen_hashes:
            continue
        seen_hashes.add(text_hash)

        def call_api():
            return client.embeddings.create(model=model, input=embedding_input)

        try:
            response = retry_with_backoff(call_api)
            embedding = response.data[0].embedding

            embeddings.append(embedding)
            metadata.append({
                "id": chunk["id"],
                "chunk_id": chunk.get("chunk_id"),
                "title": title,
                "source_path": chunk.get("source_path"),
                "token_count": chunk.get("token_count"),
                "text": text,
                "embedding_input": embedding_input  # 👈 add this
            })

        except Exception as e:
            print(f"❌ Failed to embed chunk {chunk.get('id')}: {e}")

    return embeddings, metadata


def save_faiss_index(index_path: Path, index, metadata_path: Path, metadata: List[Dict[str, Any]]):
    faiss.write_index(index, str(index_path))
    with metadata_path.open("wb") as f:
        pickle.dump(metadata, f)


def generate_embeddings(model: str, input_path: Path, index_path: Path, metadata_path: Path, force: bool = False):
    load_dotenv()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    chunks = load_chunks(input_path)
    print(f"📘 Loaded {len(chunks)} chunks")

    existing_hashes = set()
    existing_metadata = []
    existing_index = None

    if not force and metadata_path.exists() and index_path.exists():
        existing_hashes = load_existing_hashes(metadata_path)
        with metadata_path.open("rb") as f:
            existing_metadata = pickle.load(f)
        existing_index = faiss.read_index(str(index_path))
        print(f"🔁 Loaded {len(existing_metadata)} existing embeddings")
    else:
        print("⚠️ Starting fresh (no existing index or metadata found)")

    new_embeddings, new_metadata = embed_chunks(client, model, chunks, existing_hashes)

    if not new_embeddings:
        print("⚠️ No new embeddings generated.")
        return

    new_embeddings_np = np.array(new_embeddings).astype("float32")

    if existing_index is None:
        index = faiss.IndexFlatL2(len(new_embeddings_np[0]))
    else:
        index = existing_index
    index.add(new_embeddings_np)

    total_metadata = existing_metadata + new_metadata
    save_faiss_index(index_path, index, metadata_path, total_metadata)

    print(f"\n✅ Saved {len(new_metadata)} new embeddings")
    print(f"📦 Total index size: {index.ntotal} vectors")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate FAISS index with OpenAI embeddings.")
    parser.add_argument("--model", default="text-embedding-3-small", help="Embedding model to use.")
    parser.add_argument("--rebuild", action="store_true", help="Force full rebuild of index.")
    parser.add_argument("--input", default="data/knowledge_chunks.json", help="Input JSON file")
    parser.add_argument("--index", default="data/faiss.index", help="Output FAISS index file")
    parser.add_argument("--metadata", default="data/metadata.pkl", help="Output metadata file")
    args = parser.parse_args()

    generate_embeddings(
        model=args.model,
        input_path=Path(args.input),
        index_path=Path(args.index),
        metadata_path=Path(args.metadata),
        force=args.rebuild
    )
