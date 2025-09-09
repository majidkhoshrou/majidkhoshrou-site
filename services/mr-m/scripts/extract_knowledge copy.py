import uuid
import fitz  # PyMuPDF
import spacy
import json
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import datetime
from urllib.parse import urlparse
import re
import tiktoken
from tqdm import tqdm
from io import BytesIO

# ---------- Paths (repo-relative, NOT cwd-relative)
BASE_DIR = Path(__file__).resolve().parent.parent     # …/mr-m
TEMPLATES_DIR = BASE_DIR / "templates"                # HTML source
PDF_DIR = BASE_DIR / "static" / "pdfs"                # PDF source
OUTPUT_PATH = BASE_DIR / "data" / "artifacts" / "knowledge_chunks.json"
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# ---------- Tokenizer & helpers
encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
MAX_TOKENS = 500
OVERLAP_TOKENS = 50

def count_tokens(text: str) -> int:
    return len(encoding.encode(text))

def split_text_into_chunks(text: str, max_tokens: int = 500, overlap: int = 50):
    tokens = encoding.encode(text or "")
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk = encoding.decode(tokens[start:end])
        chunks.append(chunk)
        start += max_tokens - overlap
    return chunks

def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()

# ---------- Collect sources
html_files = list(TEMPLATES_DIR.rglob("*.html"))
pdf_files = list(PDF_DIR.rglob("*.pdf"))
external_urls = []
knowledge_chunks = []

# ---------- Process local HTML
for html_file in tqdm(html_files, desc="Processing HTMLs"):
    base = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "source_type": "local",
        "source_path": str(html_file.relative_to(BASE_DIR)),
    }

    html = html_file.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["header", "nav", "footer", "script", "style"]):
        tag.decompose()

    title = (soup.title.string or "").strip() if soup.title else "Untitled"
    base["title"] = title

    text = clean_text(soup.get_text(strip=False))
    external_links = {}
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("http://", "https://")):
            external_links[a.get_text(strip=True)] = href
            if href not in external_urls:
                external_urls.append(href)
    base["external_links"] = external_links

    for idx, chunk in enumerate(split_text_into_chunks(text, MAX_TOKENS, OVERLAP_TOKENS), start=1):
        knowledge_chunks.append({
            **base,
            "text": chunk,
            "token_count": count_tokens(chunk),
            "chunk_id": f"{base['id']}_{idx}",
        })

# ---------- Process local PDFs
for pdf_file in tqdm(pdf_files, desc="Processing PDFs"):
    base = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "source_type": "local",
        "source_path": str(pdf_file.relative_to(BASE_DIR)),
    }

    pdf_stream = BytesIO(pdf_file.read_bytes())
    doc = fitz.open(stream=pdf_stream, filetype="pdf")

    # Title
    meta = doc.metadata or {}
    title = (meta.get("title") or "").strip()
    if not title or title.lower().startswith("untitled") or len(title) < 5:
        try:
            first = doc[0]
            data = first.get_text("dict")
            candidates = []
            for block in data.get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        txt = (span.get("text") or "").strip()
                        if txt and len(txt.split()) > 3:
                            candidates.append((span.get("size", 0), txt))
            title = sorted(candidates, key=lambda x: -x[0])[0][1] if candidates else pdf_file.stem
        except Exception:
            title = pdf_file.stem
    base["title"] = title

    # Text
    text = "".join(page.get_text("text") for page in doc)
    doc.close()
    text = clean_text(text)

    for idx, chunk in enumerate(split_text_into_chunks(text, MAX_TOKENS, OVERLAP_TOKENS), start=1):
        knowledge_chunks.append({
            **base,
            "text": chunk,
            "token_count": count_tokens(chunk),
            "chunk_id": f"{base['id']}_{idx}",
        })

# ---------- Process external URLs
for url in tqdm(external_urls, desc="Processing External URLs"):
    base = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "source_type": "external",
        "source_path": url,
    }
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        ctype = (resp.headers.get("Content-Type") or "").lower()

        if "html" in ctype:
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["header", "nav", "footer", "script", "style"]):
                tag.decompose()
            base["title"] = (soup.title.string or "").strip() if soup.title else "Untitled"
            text = clean_text(soup.get_text(strip=False))

        elif "pdf" in ctype:
            pdf_stream = BytesIO(resp.content)
            doc = fitz.open(stream=pdf_stream, filetype="pdf")
            text = "".join(page.get_text("text") for page in doc)
            doc.close()
            base["title"] = Path(urlparse(url).path).name or "Untitled"
            text = clean_text(text)

        else:
            print(f"Unsupported content type: {ctype} for URL: {url}")
            continue

        for idx, chunk in enumerate(split_text_into_chunks(text, MAX_TOKENS, OVERLAP_TOKENS), start=1):
            knowledge_chunks.append({
                **base,
                "text": chunk,
                "token_count": count_tokens(chunk),
                "chunk_id": f"{base['id']}_{idx}",
            })

    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")

# ---------- Save
with OUTPUT_PATH.open("w", encoding="utf-8") as f:
    json.dump(knowledge_chunks, f, indent=2, ensure_ascii=False)

print(f"\n✅ Done. Extracted and chunked {len(knowledge_chunks)} items.")
