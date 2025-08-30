# services/mr-m/assist/router.py
import json
from openai import OpenAI
from assist.tools import TOOLS
from assist.handlers_sql import latest_publications, coauthors_of, venues_of

client = OpenAI()

SYSTEM = """You are a publications assistant.
- When asked about publications, co-authors, or venues, call query_publications.
- Map "last N" -> first=false, limit=N; "first N" -> first=true, limit=N.
- Resolve 'his'/'her' using chat history if present.
- Default limit=5 if not specified."""

def handle_user_message(user_text: str, chat_history: list):
    # Basic Responses API call (tool-calling)
    resp = client.responses.create(
        model="gpt-4.1",  # use your preferred tool-capable model
        messages=[{"role":"system","content":SYSTEM}] + chat_history + [{"role":"user","content":user_text}],
        tools=TOOLS,
        tool_choice="auto",
    )

    for item in resp.output:
        if item.type == "function_call" and item.function.name == "query_publications":
            args = json.loads(item.function.arguments or "{}")
            select = args["select"]; author = args["author"]
            limit = args.get("limit", 5); first = args.get("first", False)

            if select == "rows":
                rows = latest_publications(author, limit=limit, first=first)
                return _format_rows(rows)
            if select == "coauthors":
                return _format_coauthors(coauthors_of(author))
            if select == "venues":
                return _format_venues(venues_of(author))

    # If no tool call, return the model text (rare in this flow)
    chunks = []
    for item in resp.output:
        if getattr(item, "content", None):
            for c in item.content:
                if c.type == "output_text":
                    chunks.append(c.text)
    return "".join(chunks) if chunks else "Sorry, I couldn't parse that."

def _format_rows(rows):
    if not rows: return "_No results found._"
    hdr = "| Year | Title | Authors | Venue |\n|---|---|---|---|"
    lines = [f"| {r['year']} | {r['title']} | {r['authors']} | {r.get('venue','')} |" for r in rows]
    return "\n".join([hdr] + lines)

def _format_coauthors(names):
    return "_No co-authors found._" if not names else "**Co-authors:** " + ", ".join(names)

def _format_venues(items):
    if not items: return "_No venues found._"
    hdr = "| Venue | Count |\n|---|---|"
    lines = [f"| {v} | {c} |" for v, c in items]
    return "\n".join([hdr] + lines)
