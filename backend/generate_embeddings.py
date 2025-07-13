import os
import json
from openai import OpenAI
from dotenv import load_dotenv

# Load .env
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Load publications
data_path = os.path.join(os.path.dirname(__file__), "data/publications.json")
with open(data_path, "r") as f:
    publications = json.load(f)

embeddings = []

for i, pub in enumerate(publications):
    text = f"""
            Title: {pub.get("title", "")}
            Abstract: {pub.get("abstract", "")}
            Venue: {pub.get("venue", "")}
            Year: {pub.get("year", "")}
            """
    print(f"Embedding publication {i+1}/{len(publications)}: {pub.get('title','')}")

    response = client.embeddings.create(
        model="text-embedding-3-large",
        input=text
    )

    embedding_vector = response.data[0].embedding

    metadata = {
        "title": pub.get("title", ""),
        "authors": pub.get("authors", ""),
        "type": pub.get("type", ""),
        "venue": pub.get("venue", ""),
        "year": pub.get("year", ""),
        "publisher": pub.get("publisher", ""),
        "abstract": pub.get("abstract", "")
    }

    embeddings.append({
        "metadata": metadata,
        "embedding": embedding_vector
    })

output_path = os.path.join(os.path.dirname(__file__), "data/embeddings.json")
with open(output_path, "w") as f:
    json.dump(embeddings, f)

print("✅ Embeddings generated and saved.")
