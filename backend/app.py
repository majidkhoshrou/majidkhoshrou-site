import os
import json
from pathlib import Path
from typing import List, Dict

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI

from libs.search import get_faiss_index, load_metadata_pickle, query_index, build_rag_query
from libs.analytics import log_visit, load_analytics_data, summarize_analytics

# ------------------------------
# 🔐 Load environment and OpenAI
# ------------------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

models = client.models.list()
print([m.id for m in models.data if "embedding" in m.id])

# ------------------------------
# ⚙️ Flask + CORS setup
# ------------------------------
app = Flask(__name__, static_folder="static", template_folder="templates")
app.jinja_env.globals.update(request=request)

# ------------------------------
# 📂 Load FAISS index & metadata
# ------------------------------
data_dir = Path(__file__).resolve().parent / "data"
faiss_index_path = data_dir / "faiss.index"
chunks_path = data_dir / "metadata.pkl"

index = get_faiss_index(faiss_index_path)
metadata = load_metadata_pickle(chunks_path)
print(f"✅ FAISS index loaded with {index.ntotal} vectors")

# ------------------------------
# 🌐 Frontend Page Routes
# ------------------------------
@app.route("/")
def home():
    return render_template("index.html")

# @app.route("/about")
# def about():
#     return render_template("about.html")

@app.route("/cv")
def cv():
    return render_template("cv.html")

@app.route("/projects")
def projects():
    return render_template("projects.html")

@app.route("/research")
def research():
    return render_template("research.html")

@app.route("/talks")
def talks():
    return render_template("talks.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/ask-mr-m")
def ask_mr_m():
    return render_template("ask-mr-m.html")

@app.route("/analytics")
def analytics():
    return render_template("analytics.html")

# ------------------------------
# 🤖 Mr M Chat Endpoint
# ------------------------------
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message")
    history = data.get("history", [])  # list of dicts: [{role, content}]

    if not message:
        return jsonify({"error": "Message is required."}), 400

    try:
        # Step 1: RAG - Find relevant knowledge
        rag_query = build_rag_query(history, message, max_tokens=2500)
        relevant_chunks = query_index(rag_query, index, metadata, top_k=5)
        context = "\n\n".join([f"Source: {c['source_path']}\n{c['text']}" for c in relevant_chunks])

        # Step 2: Build chat messages
        system_prompt =  {
                "role": "system",
                "content": (
                    "Hello! I am Mr M — Majid's professional AI assistant. "
                    "I specialize in answering questions about Majid's background, research, publications, work experience, and projects. "
                    "You may only answer using the provided CONTEXT. "
                    "If the context does not include the answer, politely say you don't know. Never make assumptions."
                )
            }
        
        context_prompt = { "role": "system", "content": f"CONTEXT:\n{context}" }
        user_prompt = { "role": "user", "content": message }
        
        # Step 3: Truncate history (optional, keeps last 6 exchanges = 12 messages)
        MAX_HISTORY_MESSAGES = 12
        trimmed_history = history[-MAX_HISTORY_MESSAGES:]

        # Step 4: Compose full message list
        messages = [
            system_prompt,
            context_prompt,
            *trimmed_history,   # Unpacks prior chat
            user_prompt
        ]

        # Step 5: Call OpenAI Chat API
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
# 📊 Analytics API Endpoints
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
    app.run(host="0.0.0.0", port=5000, debug=True)
