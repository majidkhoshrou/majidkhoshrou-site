# Ask Mr M – Personalized AI Assistant

**Mr M** is a personalized AI assistant trained on the complete professional and academic portfolio of Majid Khoshrou. It uses Retrieval-Augmented Generation (RAG) to answer questions about his research, projects, education, and publications by pulling directly from embedded content — including PDFs, HTML pages, and externally linked sources.

## 🔍 What It Does

- Indexes and embeds all knowledge sources from:
  - Static PDFs (e.g., papers, reports)
  - HTML content from `templates/`
  - External links mentioned in those HTML files
- Embeds content using OpenAI's `text-embedding-3-small` model
- Stores and retrieves vector representations using FAISS
- Uses GPT (via OpenAI API) to answer questions using only relevant context
- Available through a web interface and `/api/chat` endpoint
- Tracks visits and usage via basic analytics logging

## 🧠 Architecture Overview

1. **Knowledge Extraction**
   - `extract_knowledge.py`: extracts text, cleans it, splits it into overlapping chunks, and collects metadata.
   - Input: `templates/*.html`, `static/pdfs/*.pdf`, external URLs from `<a>` tags.
   - Output: `data/knowledge_chunks.json`

2. **Embedding & Indexing**
   - `generate_embedding_knowledge.py`: embeds the text chunks using OpenAI embeddings and stores them in FAISS.
   - Output:
     - `data/faiss.index`
     - `data/metadata.pkl`

3. **Web Application**
   - `app.py`: Flask-based frontend and backend.
   - `/api/chat`: handles user queries, retrieves top-k similar chunks, sends them as context to OpenAI's GPT, and returns the response.

4. **Frontend**
   - Static UI in `templates/ask-mr-m.html`
   - Includes a chat window to interact with Mr M in natural language.

## 🚀 How to Run (using `uv`)

1. **Install dependencies**

```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
