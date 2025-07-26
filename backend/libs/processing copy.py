import uuid
import fitz
import spacy
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from pathlib import Path
import datetime
from tqdm import tqdm

nlp = spacy.load("en_core_web_sm")
MAX_TOKENS = 1000

CACHE_DIR = Path(".cache_linked")
CACHE_DIR.mkdir(exist_ok=True)

def make_chunk(path, title, text, chunk_index, block=None, source_url=None, parent_source=None, source_type="html"):
    return {
        "id": str(uuid.uuid4()),
        "source_type": source_type,
        "source_path": str(path) if path else None,
        "title": title,
        "text": text,
        "metadata": {
            "chunk_index": chunk_index,
            "created_at": datetime.datetime.now(datetime.UTC),
            "source_url": source_url,
            "parent_source": str(parent_source) if parent_source else None,
            "source_domain": urlparse(source_url).netloc if source_url else "local",
            "links": extract_links_from_block(block) if block else []
        }
    }

def extract_links_from_block(block):
    links = []
    for a in block.find_all("a"):
        href = a.get("href", "").strip()
        if href:
            links.append({"text": a.get_text(strip=True), "href": href})
    return links

def extract_first_level_links(soup):
    links = []
    for a in soup.find_all("a"):
        href = a.get("href", "").strip()
        if not href or href.startswith("#") or href.lower().startswith("mailto:"):
            continue
        links.append({
            "href": href,
            "text": a.get_text(strip=True)
        })
    return links

def chunk_text(text, chunk_index_start, path, title, block, source_url, parent_source, source_type):
    doc = nlp(text)
    chunks = []
    current_chunk, token_count, chunk_index = "", 0, chunk_index_start

    for sent in doc.sents:
        sentence_text = sent.text.strip()
        if not sentence_text:
            continue
        sent_len = len(sent)
        if token_count + sent_len > MAX_TOKENS:
            if current_chunk.strip():
                chunks.append(make_chunk(path, title, current_chunk.strip(), chunk_index, block, source_url, parent_source, source_type))
                chunk_index += 1
                current_chunk, token_count = "", 0
        current_chunk += " " + sentence_text
        token_count += sent_len

    if current_chunk.strip():
        chunks.append(make_chunk(path, title, current_chunk.strip(), chunk_index, block, source_url, parent_source, source_type))
    return chunks

def process_html_file(path, source_url=None, parent_source=None, is_remote=False, visited=None):
    html = path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    # ✅ STEP 1: Extract links before cleaning
    link_refs = extract_first_level_links(soup)

    # ✅ STEP 2: Remove noisy tags *after* extracting links
    for tag in soup(["header", "nav", "footer", "script", "style"]):
        tag.decompose()

    # ✅ STEP 3: Prepare chunkable content
    title = soup.title.string.strip() if soup.title else "Untitled"
    candidates = soup.find_all(["p", "section", "article", "li"])

    chunks = []
    chunk_index = 0
    for block in candidates:
        text = block.get_text(separator=" ", strip=True)
        if not text:
            continue
        block_chunks = chunk_text(
            text, chunk_index, path, title, block,
            source_url, parent_source, source_type="html"
        )
        chunks.extend(block_chunks)
        chunk_index += len(block_chunks)

    # ✅ STEP 4: Follow 1-level links
    if visited is None:
        visited = set()

    for link in link_refs:
        href = link["href"]
        if href in visited:
            continue
        visited.add(href)

        try:
            if href.lower().endswith(".pdf"):
                pdf_chunks = process_pdf_file(href, parent_source=path)
                chunks.extend(pdf_chunks)
            else:  # HTML or web page
                response = requests.get(href, timeout=10)
                response.raise_for_status()
                filename = Path(urlparse(href).path).name or f"temp_{uuid.uuid4().hex}.html"
                temp_path = Path("/tmp") / filename
                temp_path.write_text(response.text, encoding="utf-8")
                linked_chunks, _ = process_html_file(
                    temp_path,
                    source_url=href,
                    parent_source=path,
                    is_remote=True,
                    visited=visited,
                )
                chunks.extend(linked_chunks)

        except Exception as e:
            print(f"⚠️ Failed to fetch linked content from {href}: {e}")

    return chunks, soup

def process_pdf_file(url_or_path, parent_source=None):
    if isinstance(url_or_path, str) and url_or_path.startswith("http"):
        response = requests.get(url_or_path)
        response.raise_for_status()
        doc = fitz.open("pdf", response.content)
        source_url = url_or_path
        source_path = None
    else:
        doc = fitz.open(str(url_or_path))
        source_url = None
        source_path = str(url_or_path)

    chunks = []
    title = "PDF Document"
    chunk_index = 0

    for page in doc:
        text = page.get_text().strip()
        if not text:
            continue
        page_chunks = chunk_text(text, chunk_index, source_path, title, block=None, source_url=source_url, parent_source=parent_source, source_type="pdf")
        chunks.extend(page_chunks)
        chunk_index += len(page_chunks)

    return chunks

def extract_all_chunks(html_dir: Path, pdf_dir: Path, output_path: Path) -> list:
    chunks = []
    visited_links = set()

    for html_file in tqdm(list(html_dir.glob("*.html")), desc="🧠 HTML files"):
        html_chunks, _ = process_html_file(html_file, visited=visited_links)
        chunks.extend(html_chunks)

    for pdf_file in tqdm(list(pdf_dir.glob("*.pdf")), desc="📕 PDF files"):
        pdf_chunks = process_pdf_file(pdf_file)
        chunks.extend(pdf_chunks)

    print(f"✅ Extracted {len(chunks)} total chunks.")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    return chunks
