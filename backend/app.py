import os
import json
import faiss
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
from typing import List, Dict

# ------------------------------
# 🔐 Load environment and OpenAI
# ------------------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ------------------------------
# ⚙️ Flask + CORS setup
# ------------------------------
app = Flask(__name__)
CORS(app)

# ------------------------------
# 📂 Load FAISS index & metadata
# ------------------------------
data_dir = Path(__file__).resolve().parent / "data"
faiss_index_path = data_dir / "faiss.index"
faiss_metadata_path = data_dir / "faiss_metadata.json"

index = faiss.read_index(str(faiss_index_path))
with faiss_metadata_path.open("r", encoding="utf-8") as f:
    metadata = json.load(f)

print(f"✅ FAISS index loaded with {index.ntotal} vectors")

# ------------------------------
# 🔍 Semantic search
# ------------------------------
def find_similar_chunks(query: str, top_k: int = 5) -> List[Dict]:
    """Embed a query and return top_k most relevant chunks."""
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=query
    )
    query_vector = np.array(response.data[0].embedding, dtype="float32").reshape(1, -1)
    distances, indices = index.search(query_vector, top_k)
    return [metadata[i] for i in indices[0] if i < len(metadata)]

# ------------------------------
# 🤖 Chat endpoint (Mr. M)
# ------------------------------
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message")

    if not message:
        return jsonify({"error": "Message is required."}), 400

    try:
        relevant_chunks = find_similar_chunks(message)
        context = ""
        for chunk in relevant_chunks:
            context += f"Source: {chunk['source']}\n{chunk['text']}\n\n"

        # Mr. M prompt
        messages = [
            {
                "role": "system",
                "content": (
                    "Hello! I am Mr. M — Majid's professional AI assistant. "
                    "I specialize in answering questions about Majid's background, research, work experience, and publications. "
                    "You may only answer using the provided CONTEXT. "
                    "If the context does not include the answer, politely say you don't know. Never make assumptions."
                )
            },
            {
                "role": "system",
                "content": f"CONTEXT:\n{context}"
            },
            {
                "role": "user",
                "content": message
            }
        ]

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )

        reply = response.choices[0].message.content.strip()
        return jsonify({"reply": reply})

    except Exception as e:
        print("❌ Error:", e)
        return jsonify({"error": "An error occurred while generating a response."}), 500

# ------------------------------
# 🚀 Launch
# ------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
