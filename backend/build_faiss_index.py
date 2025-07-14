import os
import json
import faiss
import numpy as np

# Load embeddings
data_path = os.path.join(os.path.dirname(__file__), "data/embeddings.json")
with open(data_path, "r") as f:
    data = json.load(f)

# Extract embedding vectors and metadata
vectors = [d["embedding"] for d in data]
metadata = [d["metadata"] for d in data]

# Convert to numpy array
vectors_np = np.array(vectors).astype("float32")

# Build FAISS index
dimension = vectors_np.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(vectors_np)

print("✅ FAISS index built. Total vectors:", index.ntotal)

# Save index
faiss.write_index(index, "data/faiss.index")

# Save metadata separately
with open("data/faiss_metadata.json", "w") as f:
    json.dump(metadata, f)

print("✅ Index and metadata saved.")