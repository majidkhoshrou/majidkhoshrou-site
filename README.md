# majidkhoshrou-site

[![AWS SAM](https://img.shields.io/badge/AWS-SAM-orange?logo=amazon-aws)](https://aws.amazon.com/serverless/sam/)
[![Docker](https://img.shields.io/badge/Docker-blue?logo=docker)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.12+-blue?logo=python)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)

**Ask Mr M** — a personalized AI assistant powered by Retrieval-Augmented Generation (RAG).  
It answers questions about Majid Khoshrou’s professional and academic work by retrieving knowledge from embedded content (research, talks, projects, and more).

This repo uses **Infrastructure as Code (IaC)** with **AWS SAM + CloudFormation** to deploy a **Flask** application to **AWS Lambda** behind **API Gateway**. Local development is supported via **Docker**/**docker-compose**.

---

## 🚀 Features

- **RAG-based QA** with OpenAI embeddings + FAISS vector search
- **Flask backend** serving both API and web frontend
- **Serverless deployment** to **AWS Lambda** via **SAM/CloudFormation**
- **Local development** with Docker / docker-compose
- **IaC**: reproducible, versioned infra in `infra/aws-sam/template.yaml`
- **Knowledge ingestion pipeline** (extract + embed)
- **Utilities**: analytics, contact, reCAPTCHA, rate limiting, etc.

---

## 📂 Project Structure

> All application code is under **`services/mr-m/`**. The top-level `services/` folder is structured to allow additional services in the future.

```
.
├── LICENSE
├── README.md
├── docker-compose.yml
├── infra/
│   └── aws-sam/
│       ├── template.yaml        # CloudFormation (IaC) for AWS resources
│       └── samconfig.toml       # SAM CLI config
└── services/
    ├── uv.lock                  # dependency lock (if used)
    ├── README.md                # service-level docs (optional)
    ├── .dump/                   # (optional) data dumps
    ├── .venv/                   # (local venv, ignored)
    └── mr-m/                    # === main application ===
        ├── app.py               # Flask entry (local)
        ├── handler.py           # Lambda handler (WSGI/Flask)
        ├── main.py              # App bootstrap
        ├── Dockerfile
        ├── Dockerfile.lambda
        ├── pyproject.toml
        ├── requirements.txt
        ├── .env                 # local env vars (ignored)
        ├── .env.prod            # production env sample (optional)
        ├── .dockerignore
        ├── .python-version
        ├── data/
        ├── libs/
        │   ├── analytics.py
        │   ├── challenge.py
        │   ├── contact.py
        │   ├── make_gif_from_dir.py
        │   ├── ratelimiter.py
        │   ├── recaptcha.py
        │   ├── search.py
        │   └── utils.py
        ├── scripts/
        │   ├── extract_knowledge.py
        │   └── generate_embedding_knowledge.py
        ├── static/              # css, js, images, pdfs, videos
        ├── templates/           # analytics.html, ask-mr-m.html, ...
        └── tests/
```

---

## 🛠️ Setup & Development

### Prerequisites
- [Docker](https://www.docker.com/)
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- Python 3.12+ (for scripts and testing)

> Configure environment variables in `services/mr-m/.env` (and/or `.env.prod`) as needed for local/dev vs prod.

---

### 🔹 Run Locally (Docker)

```bash
# From repo root
docker-compose up --build
```
Your Flask app will be available at http://localhost:5000.

---

### 🔹 Deploy to AWS (SAM + Lambda)

```bash
# From repo root
cd infra/aws-sam

# Build the serverless application (uses template.yaml)
sam build

# Deploy (first time: --guided to capture parameters)
sam deploy --guided
```

- **IaC**: `template.yaml` defines the Lambda function, permissions, and API Gateway.  
- **Runtime**: Flask is served by Lambda via `services/mr-m/handler.py`.  
- **Output**: SAM prints the API Gateway URL on success.

---

## 📚 Knowledge Management

Update Mr M’s knowledge base with the included scripts:

```bash
# Extract text from PDFs, HTML, or external sources
python services/mr-m/scripts/extract_knowledge.py

# Generate embeddings and build FAISS index
python services/mr-m/scripts/generate_embedding_knowledge.py
```

---

## 🧪 Testing

```bash
cd services/mr-m
pytest
```

---

## 📦 Key Files

- `services/mr-m/Dockerfile` – Local container
- `services/mr-m/Dockerfile.lambda` – AWS Lambda container image
- `infra/aws-sam/template.yaml` – IaC (CloudFormation/SAM) for deployment
- `infra/aws-sam/samconfig.toml` – SAM CLI configuration
- `docker-compose.yml` – Local dev stack

---

## 📜 License

This project is licensed under the [MIT License](./LICENSE).
