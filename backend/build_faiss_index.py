import json
import faiss
import numpy as np
from pathlib import Path

# Paths
project_root = Path(__file__).resolve().parent
data_dir = project_root / "data"
embedding_path = data_dir / "knowledge_embeddings.json"
index_path = data_dir / "faiss.index"
metadata_path = data_dir / "faiss_metadata.json"

# Load embeddings
with embedding_path.open("r", encoding="utf-8") as f:
    records = json.load(f)

# Prepare vectors and metadata
vectors = []
metadata = []

for r in records:
    vectors.append(r["embedding"])
    metadata.append({
        "id": r["id"],
        "source": r["source"],
        "text": r["text"]
    })

# Convert to float32 NumPy array
vectors_np = np.array(vectors).astype("float32")

# Create FAISS index
dimension = vectors_np.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(vectors_np)

# Save
faiss.write_index(index, str(index_path))
with metadata_path.open("w", encoding="utf-8") as f:
    json.dump(metadata, f, ensure_ascii=False, indent=2)

print(f"✅ FAISS index saved to: {index_path.name}")
print(f"🧠 Metadata saved to: {metadata_path.name}")
print(f"📦 Total vectors: {index.ntotal}")
