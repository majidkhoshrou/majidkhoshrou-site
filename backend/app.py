import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
from typing import List, Dict

from libs.search import get_faiss_index, load_chunks, query_index
from libs.analytics import log_visit, load_analytics_data
from libs.analytics import log_visit, load_analytics_data, summarize_analytics

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
chunks_path = data_dir / "faiss_metadata.json"

index = get_faiss_index(faiss_index_path)
metadata = load_chunks(chunks_path)

print(f"✅ FAISS index loaded with {index.ntotal} vectors")

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
        relevant_chunks = query_index(message, index, metadata, top_k=5)
        context = ""
        for chunk in relevant_chunks:
            context += f"Source: {chunk['source']}\n{chunk['text']}\n\n"

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
# 📊 Visitor analytics
# ------------------------------
@app.route("/api/log-visit", methods=["POST"])
def api_log_visit():
    log_visit()
    return {"status": "logged"}

@app.route("/api/analytics-data", methods=["GET"])
def api_analytics_data():
    return load_analytics_data()

@app.route("/api/analytics-summary", methods=["GET"])
def api_analytics_summary():
    return jsonify(summarize_analytics())

# ------------------------------
# 🚀 Launch
# ------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
