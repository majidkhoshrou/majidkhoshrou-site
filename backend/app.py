
from dotenv import load_dotenv
import os

# Force dotenv to load from the directory containing this script
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)

from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message")

    if not message:
        return jsonify({"error": "Message is required."}), 400

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are Majid Khoshrou’s professional assistant. Answer questions clearly and helpfully."
                },
                {
                    "role": "user",
                    "content": message
                }
            ]
        )
        answer = response.choices[0].message.content
        return jsonify({"reply": answer})
    except Exception as e:
        print("Error:", e)
        return jsonify({"error": "An error occurred while generating a response."}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
