# Majid Khoshrou Personal Website and AI Assistant

This repository contains my personal homepage, portfolio, and an AI-powered assistant chatbot.

---

## 📂 Repository Structure

```
/
├── frontend/
│   ├── index.html
│   ├── about.html
│   ├── research.html
│   ├── projects.html
│   ├── talks.html
│   ├── contact.html
│   ├── chat.html
│   ├── css/
│   │   ├── style.css
│   │   ├── chat-style.css
│   │   └── publications-style.css
│   ├── js/
│   │   ├── chat.js
│   │   └── publications.js
│   └── data/
│       └── publications.json
│
└── backend/
    ├── app.py
    ├── requirements.txt
    └── (future) retrieval scripts, embeddings, PDF parsers
```

---

## 🌐 Frontend

The frontend is a static website containing:

- **Home** — overview and highlights
- **About Me** — professional background and skills
- **Projects** — selected work and open-source contributions
- **Research** — publications loaded dynamically from `publications.json`
- **Talks** — embedded PhD defense video
- **CV** — printable HTML CV
- **Contact** — email and social links
- **Chat** — AI assistant interface

Deployed via GitHub Pages or Netlify.

---

## 🧠 Backend

The backend is a Python Flask API providing chat functionality:

- Accepts POST requests to `/api/chat`
- Forwards user questions to OpenAI GPT-4
- Returns answers to the frontend chat UI

Planned future capabilities:

- Retrieval-Augmented Generation (RAG) using:
  - `publications.json`
  - PDF parsing
  - Site-wide content indexing
- Embedding pipelines for semantic search

---

## 🚀 Deployment

### Frontend
Deploy to GitHub Pages:

1. Commit the `frontend/` folder.
2. Configure Pages to serve from `/frontend`.

or deploy via Netlify or Vercel.

### Backend
Deploy Flask API:

1. Create a Python environment.
2. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Set your OpenAI API key:

   ```
   export OPENAI_API_KEY="sk-..."
   ```

4. Run locally:

   ```
   python app.py
   ```

5. Deploy to Render, fly.io, Heroku, or your preferred host.

---

## 🛣️ Roadmap

- [x] Frontend static site complete
- [x] Dynamic publications loading
- [x] Initial chat interface connected to OpenAI
- [ ] Retrieval over `publications.json`
- [ ] PDF parsing and chunking
- [ ] Embedding content for vector search
- [ ] Full retrieval-augmented chatbot

---

## 📄 License

This project is licensed under the MIT License.

---

## ✨ Acknowledgments

- [OpenAI API](https://platform.openai.com)
- [Flask](https://flask.palletsprojects.com/)
- [GitHub Pages](https://pages.github.com)
