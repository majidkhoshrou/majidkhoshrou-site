import re
import json
import traceback
import logging
from pathlib import Path
from typing import List, Dict, Iterator, Set
from bs4 import BeautifulSoup
import fitz  # PyMuPDF
import spacy
import requests

logger = logging.getLogger(__name__)
nlp = spacy.load("en_core_web_sm")


def clean_text(text: str) -> str:
    """Normalize all whitespace into single spaces and trim."""
    return re.sub(r'\s+', ' ', text).strip()


def sentence_tokenize(text: str) -> List[str]:
    """Safely tokenize text into sentences using SpaCy with fallback."""
    try:
        return [sent.text.strip() for sent in nlp(text).sents]
    except Exception:
        return [text]


def split_text(text: str, chunk_size: int = 500, overlap: int = 50) -> Iterator[str]:
    """
    Sentence-aware word-based chunking with optional overlap.
    Preserves semantic flow for embedding input.
    """
    paragraphs = re.split(r'\n{2,}', text)
    paragraphs = [clean_text(p) for p in paragraphs if p.strip()]
    
    for paragraph in paragraphs:
        sentences = sentence_tokenize(paragraph)
        current_chunk = []
        current_word_count = 0

        for sentence in sentences:
            word_count = len(sentence.split())
            if current_word_count + word_count <= chunk_size:
                current_chunk.append(sentence)
                current_word_count += word_count
            else:
                if current_chunk:
                    yield " ".join(current_chunk)
                    if overlap > 0:
                        current_chunk = current_chunk[-1 * (overlap // 10):]  # Approx overlap
                        current_word_count = sum(len(s.split()) for s in current_chunk)
                    else:
                        current_chunk = []
                        current_word_count = 0
                current_chunk.append(sentence)
                current_word_count += word_count

        if current_chunk:
            yield " ".join(current_chunk)


def extract_all_body_text(soup: BeautifulSoup) -> str:
    """Extract all text content from the <body>, skipping scripts and styles."""
    if not soup.body:
        return ""
    texts = []
    for tag in soup.body.find_all(True):
        if tag.name in {"script", "style", "noscript"}:
            continue
        text = tag.get_text(separator=" ", strip=True)
        if text:
            texts.append(text)
    return "\n\n".join(texts)


def extract_title_from_html(soup: BeautifulSoup) -> str:
    """Extract title from <title> tag or first <h1>."""
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    h1 = soup.find("h1")
    return h1.text.strip() if h1 else ""


def is_probably_html(href: str) -> bool:
    bad_exts = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".css", ".js", ".zip", ".mp4", ".ico", ".svg", ".woff")
    return not any(href.lower().endswith(ext) for ext in bad_exts)


def extract_first_level_html_links(path: Path, soup: BeautifulSoup, seen_links: Set[str]) -> str:
    """Follows internal/external links to HTML-like pages and extracts text."""
    texts = []

    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        if not is_probably_html(href):
            continue

        if href.startswith("http"):
            if href in seen_links:
                continue
            seen_links.add(href)
            try:
                headers = {"User-Agent": "Mozilla/5.0 (MajidBot/1.0)"}
                response = requests.get(href, headers=headers, timeout=5)
                response.raise_for_status()
                linked_soup = BeautifulSoup(response.text, "html.parser")
                linked_text = extract_all_body_text(linked_soup)
                texts.append(linked_text)
            except Exception as e:
                logger.warning(f"Skipping external link {href}: {e}")
        else:
            linked_path = (path.parent / href).resolve()
            key = str(linked_path)
            if key in seen_links:
                continue
            seen_links.add(key)
            if linked_path.exists():
                try:
                    with linked_path.open("r", encoding="utf-8") as f:
                        html = f.read()
                    linked_soup = BeautifulSoup(html, "html.parser")
                    linked_text = extract_all_body_text(linked_soup)
                    texts.append(linked_text)
                except Exception as e:
                    logger.warning(f"Skipping local link {href}: {e}")

    return "\n\n".join(texts)


def process_html_file(path: Path, chunk_size: int = 500, overlap: int = 50, seen_links: Set[str] = None) -> List[Dict[str, str]]:
    seen_links = seen_links or set()
    try:
        with path.open("r", encoding="utf-8") as f:
            html = f.read()
        soup = BeautifulSoup(html, "html.parser")

        base_text = extract_all_body_text(soup)
        linked_text = extract_first_level_html_links(path, soup, seen_links)
        full_text = clean_text(base_text + "\n\n" + linked_text)
        title = extract_title_from_html(soup)

        return [
            {
                "id": f"html_{path.name}_{idx}",
                "source": path.name,
                "type": "html",
                "chunk_index": idx,
                "title": title,
                "text": chunk
            }
            for idx, chunk in enumerate(split_text(full_text, chunk_size, overlap))
            if len(chunk.strip().split()) > 10
        ]
    except Exception as e:
        logger.error(f"Error processing HTML file '{path.name}': {e}")
        traceback.print_exc()
        return []


def extract_first_level_pdf_links(doc: fitz.Document, base_path: Path, seen_links: Set[str]) -> str:
    texts = []
    for page in doc:
        links = page.get_links()
        for link in links:
            uri = link.get("uri", "")
            if uri.endswith(".pdf") and not uri.startswith("http"):
                linked_path = (base_path.parent / uri).resolve()
                key = str(linked_path)
                if key in seen_links:
                    continue
                seen_links.add(key)
                if linked_path.exists():
                    try:
                        subdoc = fitz.open(str(linked_path))
                        text = "\n\n".join(p.get_text() for p in subdoc)
                        texts.append(text)
                    except Exception as e:
                        logger.warning(f"Skipping linked PDF {uri}: {e}")
    return "\n\n".join(texts)


def process_pdf_file(path: Path, chunk_size: int = 500, overlap: int = 50, seen_links: Set[str] = None) -> List[Dict[str, str]]:
    seen_links = seen_links or set()
    try:
        doc = fitz.open(str(path))
        main_text = "\n\n".join(p.get_text() for p in doc)
        linked_text = extract_first_level_pdf_links(doc, path, seen_links)
        full_text = clean_text(main_text + "\n\n" + linked_text)
        full_text = full_text.encode("utf-8", errors="ignore").decode()

        return [
            {
                "id": f"pdf_{path.name}_{idx}",
                "source": path.name,
                "type": "pdf",
                "chunk_index": idx,
                "title": "",  # Optional: use doc.metadata.get("title", "")
                "text": chunk
            }
            for idx, chunk in enumerate(split_text(full_text, chunk_size, overlap))
            if len(chunk.strip().split()) > 10
        ]
    except Exception as e:
        logger.error(f"Error processing PDF file '{path.name}': {e}")
        traceback.print_exc()
        return []


def save_chunks(chunks: List[Dict[str, str]], output_path: Path) -> None:
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(chunks)} chunks to {output_path.name}")
    except Exception as e:
        logger.error(f"Error saving output: {e}")
        traceback.print_exc()
