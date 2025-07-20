import os
import json
import time
import random
import hashlib
import argparse
from pathlib import Path
from typing import Callable, Any, Dict, List, Set

from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm


def retry_with_backoff(fn: Callable[[], Any], retries: int = 5) -> Any:
    """
    Execute a callable with exponential backoff retry logic.
    """
    for attempt in range(retries):
        try:
            return fn()
        except Exception as e:
            wait = (2 ** attempt) + random.uniform(0, 1)
            print(f"⏳ Retry {attempt + 1}/{retries} in {wait:.2f}s due to error: {e}")
            time.sleep(wait)
    raise RuntimeError("Failed after multiple retries.")


def get_text_hash(text: str) -> str:
    """
    Generate a SHA-256 hash from a given text string.
    """
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def load_existing_hashes(path: Path) -> Set[str]:
    """
    Load a set of SHA-256 hashes from an existing embedding file.
    """
    if not path.exists():
        return set()

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return {get_text_hash(item["text"]) for item in data if "text" in item}


def embed_chunks(
    client: OpenAI,
    model: str,
    chunks: List[Dict[str, Any]],
    seen_hashes: Set[str]
) -> List[Dict[str, Any]]:
    """
    Generate OpenAI embeddings for a list of text chunks.
    """
    embeddings = []

    for chunk in tqdm(chunks, desc="🔢 Embedding chunks"):
        text = chunk.get("text", "")
        if not text.strip():
            print(f"⚠️ Skipping empty chunk {chunk.get('id')}")
            continue

        text_hash = get_text_hash(text)
        if text_hash in seen_hashes:
            print(f"🔁 Skipping duplicate chunk {chunk.get('id')}")
            continue
        seen_hashes.add(text_hash)

        def create_embedding() -> Any:
            return client.embeddings.create(model=model, input=text)

        try:
            response = retry_with_backoff(create_embedding)
            embedding = response.data[0].embedding

            if not isinstance(embedding, list) or not embedding:
                raise ValueError("Invalid embedding returned.")

            embeddings.append({
                "id": chunk["id"],
                "source": chunk.get("source", ""),
                "title": chunk.get("title", ""),
                "timestamp": chunk.get("timestamp", ""),
                "text": text,
                "embedding": embedding
            })

        except Exception as e:
            print(f"❌ Failed to embed chunk {chunk.get('id')}: {e}")

    return embeddings


def load_chunks(path: Path) -> List[Dict[str, Any]]:
    """
    Load a list of text chunks from a JSON file.
    """
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_embeddings(path: Path, embeddings: List[Dict[str, Any]]) -> None:
    """
    Save a list of embedding results to a JSON file.
    """
    with path.open("w", encoding="utf-8") as f:
        json.dump(embeddings, f, ensure_ascii=False, indent=2)


def load_existing_embeddings(path: Path) -> List[Dict[str, Any]]:
    """
    Load a list of existing embedding records from a JSON file.
    """
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def generate_embeddings(
    model: str,
    input_path: Path,
    output_path: Path,
    force: bool = False
) -> List[Dict[str, Any]]:
    """
    Generates OpenAI embeddings from a JSON file of text chunks.

    Args:
        model (str): OpenAI model name.
        input_path (Path): Path to the input JSON containing text chunks.
        output_path (Path): Path to save the embeddings JSON.
        force (bool): If True, ignore existing embeddings and reprocess all.

    Returns:
        List[Dict[str, Any]]: The list of all embeddings saved.
    """
    load_dotenv()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    chunks = load_chunks(input_path)
    print(f"📘 Loaded {len(chunks)} chunks")

    existing_embeddings = []
    seen_hashes = set()

    if not force:
        existing_embeddings = load_existing_embeddings(output_path)
        seen_hashes = {get_text_hash(e["text"]) for e in existing_embeddings}
        print(f"🔎 Loaded {len(seen_hashes)} existing hashes")
    else:
        print("⚠️ Rebuilding embeddings from scratch (ignoring existing file)")

    new_embeddings = embed_chunks(client, model, chunks, seen_hashes)
    total_embeddings = existing_embeddings + new_embeddings

    save_embeddings(output_path, total_embeddings)
    print(f"✅ Saved {len(new_embeddings)} new, total {len(total_embeddings)} embeddings")

    return total_embeddings


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate OpenAI embeddings for text chunks.")
    parser.add_argument("--model", default="text-embedding-3-small", help="Embedding model to use.")
    parser.add_argument("--batch_size", type=int, default=1, help="Batch size (not implemented yet)")
    parser.add_argument("--rebuild", action="store_true", help="Force re-embedding all chunks from scratch.")
    args = parser.parse_args()

    generate_embeddings(model=args.model, rebuild=args.rebuild)
