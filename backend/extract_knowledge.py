import uuid
import fitz  # PyMuPDF
import spacy
import json
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import datetime 
from urllib.parse import urljoin, urlparse
import os
import re
import tiktoken
from tqdm import tqdm
from io import BytesIO

# Initialize tokenizer and config
encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
MAX_TOKENS = 500
OVERLAP_TOKENS = 50

def count_tokens(text: str) -> int:
    return len(encoding.encode(text))

def split_text_into_chunks(text: str, max_tokens: int = 500, overlap: int = 50):
    tokens = encoding.encode(text)
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk = encoding.decode(tokens[start:end])
        chunks.append(chunk)
        start += max_tokens - overlap
    return chunks

def clean_text(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()

# Setup
nlp = spacy.load("en_core_web_sm")
html_dir = Path("templates")
pdf_dir = Path("static/pdfs")
output_path = Path("data/knowledge_chunks.json")

html_files = list(html_dir.glob("**/*.html"))
pdf_files = list(pdf_dir.glob("**/*.pdf"))
external_urls = []
knowledge_chunks = []

# === Process local HTML files ===
for html_file in tqdm(html_files, desc="Processing HTMLs"):
    base_dict = {
        'id': str(uuid.uuid4()),
        'created_at': datetime.datetime.now(datetime.UTC).isoformat(),
        'source_type': 'local',
        'source_path': str(html_file),
    }

    html = html_file.read_text(encoding='utf-8')
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["header", "nav", "footer", "script", "style"]):
        tag.decompose()

    title = soup.title.string if soup.title else "Untitled"
    base_dict['title'] = title

    text = clean_text(soup.get_text(strip=False))
    external_links = {}
    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        if href.startswith(('http://', 'https://')):
            external_links[a.get_text(strip=True)] = href
            if href not in external_urls:
                external_urls.append(href)
    base_dict['external_links'] = external_links

    chunks = split_text_into_chunks(text, max_tokens=MAX_TOKENS, overlap=OVERLAP_TOKENS)
    for idx, chunk in enumerate(chunks):
        chunk_dict = base_dict.copy()
        chunk_dict['text'] = chunk
        chunk_dict['token_count'] = count_tokens(chunk)
        chunk_dict['chunk_id'] = f"{chunk_dict['id']}_{idx+1}"
        knowledge_chunks.append(chunk_dict)

# === Process local PDF files ===
for pdf_file in tqdm(pdf_files, desc="Processing PDFs"):
    base_dict = {
        'id': str(uuid.uuid4()),
        'created_at': datetime.datetime.now(datetime.UTC).isoformat(),
        'source_type': 'local',
        'source_path': str(pdf_file),
        'title': pdf_file.stem
    }

    pdf_stream = BytesIO(pdf_file.read_bytes())
    doc = fitz.open(stream=pdf_stream, filetype="pdf")

    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()

    text = clean_text(text)
    chunks = split_text_into_chunks(text, max_tokens=MAX_TOKENS, overlap=OVERLAP_TOKENS)

    for idx, chunk in enumerate(chunks):
        chunk_dict = base_dict.copy()
        chunk_dict['text'] = chunk
        chunk_dict['token_count'] = count_tokens(chunk)
        chunk_dict['chunk_id'] = f"{chunk_dict['id']}_{idx+1}"
        knowledge_chunks.append(chunk_dict)

# === Process external URLs ===
for url in tqdm(external_urls, desc="Processing External URLs"):
    base_dict = {
        'id': str(uuid.uuid4()),
        'created_at': datetime.datetime.now(datetime.UTC).isoformat(),
        'source_type': 'external',
        'source_path': url
    }

    try:
        response = requests.get(url)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").lower()

        if "html" in content_type:
            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup(["header", "nav", "footer", "script", "style"]):
                tag.decompose()

            title = soup.title.string if soup.title else "Untitled"
            base_dict['title'] = title
            text = clean_text(soup.get_text(strip=False))

        elif "pdf" in content_type:
            pdf_stream = BytesIO(response.content)
            doc = fitz.open(stream=pdf_stream, filetype="pdf")

            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()

            base_dict['title'] = urlparse(url).path.split("/")[-1]
            text = clean_text(text)

        else:
            print(f"Unsupported content type: {content_type} for URL: {url}")
            continue

        chunks = split_text_into_chunks(text, max_tokens=MAX_TOKENS, overlap=OVERLAP_TOKENS)
        for idx, chunk in enumerate(chunks):
            chunk_dict = base_dict.copy()
            chunk_dict['text'] = chunk
            chunk_dict['token_count'] = count_tokens(chunk)
            chunk_dict['chunk_id'] = f"{chunk_dict['id']}_{idx+1}"
            knowledge_chunks.append(chunk_dict)

    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")

# === Save chunks to JSON ===
output_path.parent.mkdir(parents=True, exist_ok=True)
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(knowledge_chunks, f, indent=2, ensure_ascii=False)

print(f"\n✅ Done. Extracted and chunked {len(knowledge_chunks)} items.")
