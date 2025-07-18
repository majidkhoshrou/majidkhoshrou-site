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

    This function attempts to call the given function up to `retries` times,
    waiting longer between each retry if an exception is raised.

    Args:
        fn (Callable): A zero-argument function or lambda to call.
        retries (int): Maximum number of attempts before raising an error.

    Returns:
        Any: The result returned by the successful execution of `fn`.

    Raises:
        RuntimeError: If all retries are exhausted and the function still fails.
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

    This is used to uniquely identify content and avoid embedding duplicates.

    Args:
        text (str): The text content to hash.

    Returns:
        str: A SHA-256 hash representing the text content.
    """
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def load_existing_hashes(path: Path) -> Set[str]:
    """
    Load a set of SHA-256 hashes from an existing embedding file.

    This function is used to prevent re-embedding content that has already
    been embedded previously by comparing text content hashes.

    Args:
        path (Path): Path to the existing JSON file containing embeddings.

    Returns:
        Set[str]: A set of SHA-256 hashes representing already embedded content.
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

    This function embeds each chunk of text using the specified OpenAI model,
    skipping any chunks that have already been embedded based on their text content.

    Args:
        client (OpenAI): Authenticated OpenAI client instance.
        model (str): Name of the embedding model to use (e.g., 'text-embedding-3-small').
        chunks (List[Dict[str, Any]]): List of chunks containing 'text', 'id', and optionally 'source'.
        seen_hashes (Set[str]): Set of SHA-256 hashes representing already embedded texts.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing the new embeddings and their metadata.
    """
    embeddings = []

    for chunk in tqdm(chunks, desc="Embedding chunks"):
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
                "text": text,
                "embedding": embedding
            })

        except Exception as e:
            print(f"❌ Failed to embed chunk {chunk.get('id')}: {e}")

    return embeddings


def load_chunks(path: Path) -> List[Dict[str, Any]]:
    """
    Load a list of text chunks from a JSON file.

    The JSON file should contain a list of dictionaries, each with at least
    a 'text' field, and optionally an 'id' and 'source'.

    Args:
        path (Path): Path to the input JSON file containing text chunks.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries representing the chunks.
    """
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_embeddings(path: Path, embeddings: List[Dict[str, Any]]) -> None:
    """
    Save a list of embedding results to a JSON file.

    This function will overwrite the file if it already exists.

    Args:
        path (Path): Path to the output JSON file.
        embeddings (List[Dict[str, Any]]): List of dictionaries containing embeddings and metadata.
    """
    with path.open("w", encoding="utf-8") as f:
        json.dump(embeddings, f, ensure_ascii=False, indent=2)

def load_existing_embeddings(path: Path) -> List[Dict[str, Any]]:
    """
    Load a list of existing embedding records from a JSON file.

    Args:
        path (Path): Path to the JSON file containing previously saved embeddings.

    Returns:
        List[Dict[str, Any]]: List of existing embeddings, or empty list if file not found.
    """
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    """
    Main function that orchestrates the embedding workflow.

    It performs the following steps:
    - Loads environment variables and CLI arguments
    - Initializes the OpenAI client and model
    - Loads text chunks from disk
    - Loads existing content hashes to avoid duplicates
    - Embeds all new chunks using the OpenAI API
    - Appends new embeddings to existing ones and saves the full result
    """
    load_dotenv()

    parser = argparse.ArgumentParser(description="Generate OpenAI embeddings for text chunks.")
    parser.add_argument("--model", default="text-embedding-3-small", help="Embedding model to use.")
    parser.add_argument("--batch_size", type=int, default=1, help="Batch size (not implemented yet)")
    args = parser.parse_args()

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    embedding_model = args.model

    # File paths
    project_root = Path(__file__).resolve().parent
    data_dir = project_root / "data"
    input_path = data_dir / "knowledge_chunks.json"
    output_path = data_dir / "knowledge_embeddings.json"

    # Load input chunks
    chunks = load_chunks(input_path)
    print(f"📘 Loaded {len(chunks)} chunks")

    # Load existing embeddings and hashes
    existing_embeddings = load_existing_embeddings(output_path)
    seen_hashes = {get_text_hash(e["text"]) for e in existing_embeddings}
    if seen_hashes:
        print(f"🔎 Loaded {len(seen_hashes)} existing content hashes")

    # Embed new chunks
    new_embeddings = embed_chunks(client, embedding_model, chunks, seen_hashes)
    total_embeddings = existing_embeddings + new_embeddings

    # Save all embeddings
    save_embeddings(output_path, total_embeddings)
    print(f"✅ Done. Saved {len(new_embeddings)} new and {len(total_embeddings)} total embeddings to {output_path}")

if __name__ == "__main__":
    main()
