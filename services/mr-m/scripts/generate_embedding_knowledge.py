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

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = BASE_DIR / "data" / "artifacts" / "knowledge_chunks.json"
DEFAULT_INDEX = BASE_DIR / "data" / "faiss.index"
DEFAULT_METADATA = BASE_DIR / "data" / "metadata.pkl"

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
    return hashlib.sha256((text or "").strip().encode("utf-8")).hexdigest()

def load_chunks(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def load_existing_hashes(path: Path) -> Set[str]:
    if not path.exists():
        return set()
    with path.open("rb") as f:
        metadata = pickle.load(f)
    return {get_text_hash(m.get("embedding_input", "")) for m in metadata}

def embed_chunks(client: OpenAI, model: str, chunks, seen_hashes: Set[str]):
    embeddings, metadata = [], []
    for chunk in tqdm(chunks, desc="🔢 Embedding chunks"):
        title = chunk.get("title", "Untitled")
        text = (chunk.get("text") or "").strip()
        source = chunk.get("source_path", "")
        if not text:
            continue

        embedding_input = f"Source: {source}\nTitle: {title}\nText: {text}"
        th = get_text_hash(embedding_input)
        if th in seen_hashes:
            continue
        seen_hashes.add(th)

        def call():
            return client.embeddings.create(model=model, input=embedding_input)

        try:
            resp = retry_with_backoff(call)
            vec = resp.data[0].embedding
            embeddings.append(vec)
            metadata.append({
                "id": chunk["id"],
                "chunk_id": chunk.get("chunk_id"),
                "title": title,
                "source_path": source,
                "token_count": chunk.get("token_count"),
                "text": text,
                "embedding_input": embedding_input,
            })
        except Exception as e:
            print(f"❌ Failed to embed chunk {chunk.get('id')}: {e}")
    return embeddings, metadata

def save_faiss_index(index_path: Path, index, metadata_path: Path, metadata):
    faiss.write_index(index, str(index_path))
    with metadata_path.open("wb") as f:
        pickle.dump(metadata, f)

def generate_embeddings(model: str, input_path: Path, index_path: Path, metadata_path: Path, force: bool = False):
    load_dotenv()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    chunks = load_chunks(input_path)
    print(f"📘 Loaded {len(chunks)} chunks")

    existing_hashes, existing_metadata, existing_index = set(), [], None
    if not force and metadata_path.exists() and index_path.exists():
        existing_hashes = load_existing_hashes(metadata_path)
        with metadata_path.open("rb") as f:
            existing_metadata = pickle.load(f)
        existing_index = faiss.read_index(str(index_path))
        print(f"🔁 Loaded {len(existing_metadata)} existing embeddings")
    else:
        print("⚠️ Starting fresh (no existing index or metadata found)")

    new_vecs, new_meta = embed_chunks(client, model, chunks, existing_hashes)
    if not new_vecs:
        print("⚠️ No new embeddings generated.")
        return

    vecs = np.array(new_vecs).astype("float32")
    index = existing_index or faiss.IndexFlatL2(vecs.shape[1])
    index.add(vecs)

    total_meta = existing_metadata + new_meta
    save_faiss_index(index_path, index, metadata_path, total_meta)
    print(f"\n✅ Saved {len(new_meta)} new embeddings")
    print(f"📦 Total index size: {index.ntotal} vectors")

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Generate FAISS index with OpenAI embeddings.")
    p.add_argument("--model", default="text-embedding-3-small")
    p.add_argument("--rebuild", action="store_true")
    p.add_argument("--input", default=str(DEFAULT_INPUT))
    p.add_argument("--index", default=str(DEFAULT_INDEX))
    p.add_argument("--metadata", default=str(DEFAULT_METADATA))
    args = p.parse_args()

    generate_embeddings(
        model=args.model,
        input_path=Path(args.input),
        index_path=Path(args.index),
        metadata_path=Path(args.metadata),
        force=args.rebuild,
    )
