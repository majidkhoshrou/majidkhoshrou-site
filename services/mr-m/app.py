# backend/app.py
import os
from pathlib import Path
from functools import lru_cache

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS  # keep if you use it
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix

import json
from assist.tools import TOOLS
from assist.handlers_sql import latest_publications, coauthors_of, venues_of

from libs.search import get_faiss_index, load_metadata_pickle, query_index, build_rag_query
from libs.analytics import log_visit, load_analytics_data, summarize_analytics
from libs.ratelimiter import check_and_increment_ip, get_ip_quota
from libs.challenge import is_trusted, mark_trusted, burst_ok, verify_challenge
from libs.contact import send_contact_email
from libs.utils import (
    get_secret_key,
    get_turnstile_site_key,
    get_openai_client,
)

# ------------------------------
# 🔐 Environment
# ------------------------------
load_dotenv()

# ------------------------------
# ⚙️ Flask
# ------------------------------
app = Flask(__name__, static_folder="static", template_folder="templates")
# Safe placeholder; real key set lazily below
app.secret_key = os.getenv("SECRET_KEY", "dev-fallback-not-for-prod")

# If you’re behind a trusted proxy (ALB/CloudFront), optionally enable ProxyFix
if os.getenv("TRUST_PROXY", "false").lower() == "true":
    num = int(os.getenv("NUM_PROXIES", "1"))  # ALB only=1, CloudFront+ALB=2
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=num, x_proto=num, x_host=num, x_port=num)

app.jinja_env.globals.update(request=request)

# ------------------------------
# Flask 3.x: use before_request + a one-time flag (replaces before_first_request)
# --- keep this near your other Flask hooks in app.py ---

_secret_inited = False

@app.before_request
def _init_secret_key_once():
    global _secret_inited
    # Do NOT perform heavy init during health checks
    if _secret_inited or request.path == "/healthz":
        return
    app.secret_key = get_secret_key()  # may fetch from SSM
    _secret_inited = True

@app.get("/healthz")
def healthz():
    # No work, no SSM, no DB, just say we're alive
    return {"ok": True}, 200

# ------------------------------

def get_client_ip():
    # Cloudflare first (when fronted by CF), else API Gateway/ALB XFF, else remote_addr
    ip = request.headers.get("CF-Connecting-IP")
    if ip:
        return ip
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.remote_addr or "0.0.0.0"

# ------------------------------
# 📂 Lazy FAISS index & metadata
# ------------------------------
@lru_cache(maxsize=1)
def load_vector_store():
    data_dir = Path(__file__).resolve().parent / "data"
    faiss_index_path = data_dir / "faiss.index"
    chunks_path = data_dir / "metadata.pkl"
    index = get_faiss_index(faiss_index_path)
    metadata = load_metadata_pickle(chunks_path)
    try:
        print(f"✅ FAISS index loaded with {index.ntotal} vectors")
    except Exception:
        pass
    return index, metadata

# ------------------------------
# 🌐 Frontend Page Routes
# ------------------------------
@app.route("/")
def home():
    return render_template("index.html")

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
    return render_template("ask-mr-m.html", TURNSTILE_SITE_KEY=get_turnstile_site_key())

@app.route("/analytics")
def analytics():
    return render_template("analytics.html")

# ------------------------------
# 🤖 Mr M Chat Endpoint
# ------------------------------
@app.route("/api/chat", methods=["POST"])
def chat():
    import json
    from assist.tools import TOOLS
    from assist.handlers_sql import latest_publications, coauthors_of, venues_of
    from assist.names import canonicalize_author  # <— NEW

    ip = get_client_ip()

    data = request.get_json(force=True) or {}
    message = data.get("message")
    history = data.get("history", [])          # [{role, content}]
    token = data.get("cf-turnstile-response") or data.get("recaptcha_token")
    action = data.get("action") or data.get("recaptcha_action") or "chat"

    if not message:
        return jsonify({"error": "Message is required."}), 400

    # 0) Small burst limiter
    if not burst_ok(ip):
        return jsonify({
            "error": "Too many requests. Please wait a moment and try again.",
            "code": "burst"
        }), 429

    # 1) Adaptive challenge: only when not yet trusted
    if not is_trusted(ip):
        ok, info = verify_challenge(token, ip, expected_action=action)
        print("[turnstile]", info)
        if not ok:
            return jsonify({"error": "challenge_failed", "info": info}), 403
        mark_trusted(ip)

    # 2) Daily/IP limit
    if not check_and_increment_ip(ip):
        return jsonify({
            "error": "You've reached your daily limit. Try again tomorrow.",
            "code": "daily"
        }), 429

    try:
        # 3) Router-first: let the model decide (publications vs knowledge)
        client = get_openai_client()

        router_system = {
            "role": "system",
            "content": (
                "Decide which tool to call.\n"
                "- If the question is about publication metadata (latest/first N, co-authors, venues), call query_publications.\n"
                "- Otherwise, call search_knowledge with the user's text.\n"
                "- Use the canonical author name 'Khoshrou, Abdolrahman' when the user refers to Majid.\n"
                "- Do NOT treat 'Mr-M' (the assistant) as a person/author. Mr-M is Majid's (Abdolrahman's) AI-Assistant.\n"
                "- If neither tool applies, do not call tools."
            )
        }
        MAX_HISTORY_MESSAGES = 12
        trimmed_history = history[-MAX_HISTORY_MESSAGES:]
        router_messages = [router_system, *trimmed_history, {"role": "user", "content": message}]

        router_resp = client.chat.completions.create(
            model="gpt-4o-mini",          # tool-capable model
            messages=router_messages,
            tools=TOOLS,
            tool_choice="auto"
        )

        tool_calls = router_resp.choices[0].message.tool_calls or []
        if tool_calls:
            for t in tool_calls:
                name = t.function.name
                args = json.loads(t.function.arguments or "{}")

                if name == "query_publications":
                    sel    = args["select"]
                    # NEW: normalize nicknames/misspellings; block 'Mr-M'
                    author = canonicalize_author(args.get("author"))
                    limit  = args.get("limit", 5)
                    first  = args.get("first", False)

                    # If the model tried to use 'Mr-M' as the author, don't hit the DB
                    if author is None:
                        return jsonify({
                            "reply": "Mr-M is the assistant, not the author of publications. "
                                     "Try asking about Majid (Abdolrahman Khoshrou)."
                        }), 200

                    if sel == "rows":
                        rows = latest_publications(author, limit=limit, first=first)
                        if not rows:
                            return jsonify({"reply": "_No results found._"}), 200

                        # Format as numbered list
                        lines = []
                        for i, r in enumerate(rows, start=1):
                            lines.append(
                                f"{i}. {r['title']} ({r['year']})\n"
                                f"   Authors: {r['authors']}\n"
                                f"   Venue: {r.get('venue','')}"
                            )

                        return jsonify({"reply": "\n".join(lines)}), 200

                    if sel == "coauthors":
                        names = coauthors_of(author)
                        reply = "_No co-authors found._" if not names else "**Co-authors:** " + ", ".join(names)
                        return jsonify({"reply": reply}), 200

                    if sel == "venues":
                        items = venues_of(author)
                        if not items:
                            return jsonify({"reply": "_No venues found._"}), 200
                        hdr = "| Venue | Count |\n|---|---|"
                        lines = [f"| {v} | {c} |" for v, c in items]
                        return jsonify({"reply": "\n".join([hdr] + lines)}), 200

                if name == "search_knowledge":
                    # Use your FAISS pipeline with the requested top_k (default 5)
                    top_k = int(args.get("top_k", 5)) or 5

                    index, metadata = load_vector_store()
                    rag_query = build_rag_query(trimmed_history, message, max_tokens=4000)
                    chunks = query_index(rag_query, index, metadata, top_k=top_k)

                    context = "\n\n".join([f"Source: {c['source_path']}\n{c['text']}" for c in chunks])
                    qa_messages = [
                        {
                            "role": "system",
                            "content": (
                                "Hello! I am Mr M — Majid's professional AI assistant.\n"
                                "Answer only using the provided CONTEXT. "
                                "If the context does not include the answer, say you don't know."
                            )
                        },
                        {"role": "system", "content": f"CONTEXT:\n{context}"},
                        *trimmed_history,
                        {"role": "user", "content": message}
                    ]
                    qa_resp = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=qa_messages
                    )
                    reply = qa_resp.choices[0].message.content.strip()
                    return jsonify({"reply": reply}), 200

        # 4) Fallback — your original RAG flow (in case no tool was chosen)
        index, metadata = load_vector_store()
        rag_query = build_rag_query(trimmed_history, message, max_tokens=4000)
        relevant_chunks = query_index(rag_query, index, metadata, top_k=5)
        context = "\n\n".join([f"Source: {c['source_path']}\n{c['text']}" for c in relevant_chunks])

        system_prompt = {
            "role": "system",
            "content": (
                "Hello! I am Mr M — Majid's professional AI assistant. "
                "I specialize in answering questions about Majid's background, research, publications, work experience, and projects. "
                "You may only answer using the provided CONTEXT. "
                "If the context does not include the answer, politely say you don't know. Never make assumptions."
            )
        }
        context_prompt = {"role": "system", "content": f"CONTEXT:\n{context}"}
        user_prompt = {"role": "user", "content": message}
        messages = [system_prompt, context_prompt, *trimmed_history, user_prompt]

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        reply = response.choices[0].message.content.strip()
        return jsonify({"reply": reply}), 200

    except Exception as e:
        print("❌ Error:", e)
        return jsonify({"error": "An error occurred while generating a response."}), 500

# ------------------------------
# 📊 Quota API Endpoint
# ------------------------------
@app.route("/api/quota", methods=["GET"])
def quota():
    ip = get_client_ip()
    return jsonify(get_ip_quota(ip))

# ------------------------------
# 📊 Analytics API Endpoints
# ------------------------------

@app.route("/api/log-visit", methods=["POST"])
def api_log_visit():
    try:
        log_visit()  # now auto-picks /tmp on Lambda, ./data locally
    except Exception as e:
        app.logger.warning("log_visit failed: %s", e)
    return {"status": "logged"}


@app.route("/api/analytics-data", methods=["GET"])
def api_analytics_data():
    return load_analytics_data()

@app.route("/api/analytics-summary", methods=["GET"])
def api_analytics_summary():
    return jsonify(summarize_analytics())

# ------------------------------
# 📫 Contact API Endpoint
# ------------------------------
@app.route("/api/contact", methods=["POST"])
def api_contact():
    ip = get_client_ip()
    data = request.get_json(silent=True) or request.form
    try:
        result = send_contact_email(
            name=data.get("name", ""),
            email=data.get("email", ""),
            message=data.get("message", ""),
            ip=ip,
            honeypot=data.get("company", "") or data.get("hp_field", ""),
            submitted_at=data.get("submitted_at") or data.get("form_started", ""),
        )
        if result.get("ok"):
            return jsonify({"status": "sent"}), 200
        else:
            return jsonify({"error": result.get("error", "Email send failed")}), 400
    except Exception as e:
        app.logger.exception("contact failed")
        return jsonify({"error": "contact_send_exception"}), 500

# ------------------------------
# 🚀 Launch (local only)
# ------------------------------
if __name__ == "__main__":
    # Default to 5000 locally; your Lambda container sets PORT=8080
    app.run(host="0.0.0.0", port=5000, debug=True)
