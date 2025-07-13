
import os
import json
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
from fuzzywuzzy import fuzz


# Force dotenv to load from the directory containing this script
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)

app = Flask(__name__)
CORS(app)


# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

backend_data_path = os.path.join(os.path.dirname(__file__), "data/publications.json")
# Load publications.json when the app starts
with open(backend_data_path, "r") as f:
    publications = json.load(f)

# def find_relevant_publications(query, max_results=3):
#     results = []
#     query_words = set(query.lower().split())

#     for pub in publications:
#         title_words = set(pub["title"].lower().split())
#         abstract_words = set(pub["abstract"].lower().split())

#         # Count how many words overlap
#         title_matches = len(query_words & title_words)
#         abstract_matches = len(query_words & abstract_words)

#         if title_matches + abstract_matches > 0:
#             results.append((title_matches + abstract_matches, pub))

#     # Sort by most matches
#     results.sort(reverse=True, key=lambda x: x[0])

#     # Return only the publications (not the match counts)
#     return [r[1] for r in results[:max_results]]

def find_relevant_publications(query, max_results=3):
    """
    Finds publications whose titles or abstracts are most similar to the query,
    using fuzzy string matching.
    """
    results = []
    for pub in publications:
        title_score = fuzz.partial_ratio(query.lower(), pub["title"].lower())
        abstract_score = fuzz.partial_ratio(query.lower(), pub["abstract"].lower())
        combined_score = (title_score + abstract_score) / 2
        results.append((combined_score, pub))
    results.sort(reverse=True, key=lambda x: x[0])
    return [r[1] for r in results[:max_results]]

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message")

    if not message:
        return jsonify({"error": "Message is required."}), 400

    try:
        # Retrieve relevant publications
        relevant_pubs = find_relevant_publications(message)

        # Build context string
        context = ""
        for pub in relevant_pubs:
            context += f"Title: {pub['title']}\n"
            context += f"Abstract: {pub['abstract']}\n\n"

        # Construct messages
        messages = [
            {
                "role": "system",
                "content": "You are Majid's professional assistant. Use the provided CONTEXT to answer questions factually. If the context is insufficient, say so."
            },
        ]

        if context:
            messages.append({
                "role": "system",
                "content": f"CONTEXT:\n{context}"
            })

        messages.append({
            "role": "user",
            "content": message
        })

        # Call OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )

        answer = response.choices[0].message.content

        return jsonify({"reply": answer})

    except Exception as e:
        print(e)
        return jsonify({"error": "An error occurred while generating a response."}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
