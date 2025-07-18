import re
import json
import traceback
import logging
from pathlib import Path
from typing import List, Dict, Iterator, Set
from bs4 import BeautifulSoup
import fitz  # PyMuPDF
import spacy
from urllib.parse import urlparse
import requests

logger = logging.getLogger(__name__)

# Load SpaCy English model once
nlp = spacy.load("en_core_web_sm")


def sentence_tokenize(text: str) -> List[str]:
    """Uses SpaCy to split text into sentences."""
    return [sent.text.strip() for sent in nlp(text).sents]


def split_text(text: str, chunk_size: int = 500) -> Iterator[str]:
    """
    Yields chunks that preserve paragraph boundaries and group complete sentences
    without exceeding the chunk_size (in words). Ideal for LLM embedding and long-context input.
    """
    paragraphs = re.split(r'\n{2,}', text)
    cleaned_paragraphs = [clean_text(p) for p in paragraphs if len(p.strip()) > 0]

    for paragraph in cleaned_paragraphs:
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
                current_chunk = [sentence]
                current_word_count = word_count

        if current_chunk:
            yield " ".join(current_chunk)


def clean_text(text: str) -> str:
    """Cleans whitespace and joins text into a single line."""
    return re.sub(r'\s+', ' ', text).strip()


def extract_all_body_text(soup: BeautifulSoup) -> str:
    """Extracts all visible and hidden text from <body>, skipping head/scripts."""
    body = soup.body
    if not body:
        return ""

    text_parts = []
    for tag in body.find_all(True):
        if tag.name in {"script", "style", "noscript"}:
            continue
        text = tag.get_text(separator=" ", strip=True)
        if text:
            text_parts.append(text)

    return "\n\n".join(text_parts)


from urllib.parse import urlparse
import requests

def is_probably_html(href: str) -> bool:
    """Return True if the link is likely pointing to an HTML page."""
    bad_exts = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".css", ".js", ".zip", ".mp4", ".ico", ".svg", ".woff")
    return not any(href.lower().endswith(ext) for ext in bad_exts)

def extract_first_level_html_links(path: Path, soup: BeautifulSoup, seen_links: Set[str]) -> str:
    """Follows internal and external HTML-like links (1-level only) and extracts their text."""
    texts = []

    for tag in soup.find_all("a", href=True):
        href = tag["href"]

        if not is_probably_html(href):
            continue

        if href.startswith("http"):
            # External link
            if href in seen_links:
                continue
            seen_links.add(href)
            try:
                response = requests.get(href, timeout=5)
                response.raise_for_status()
                linked_soup = BeautifulSoup(response.text, "html.parser")
                linked_text = extract_all_body_text(linked_soup)
                texts.append(linked_text)
            except Exception as e:
                logger.warning(f"Skipping external link {href}: {e}")
        else:
            # Local link
            linked_path = (path.parent / href).resolve()
            key = str(linked_path)
            if key in seen_links:
                continue
            seen_links.add(key)
            if linked_path.exists() and linked_path.is_file():
                try:
                    with linked_path.open("r", encoding="utf-8") as f:
                        html = f.read()
                    linked_soup = BeautifulSoup(html, "html.parser")
                    linked_text = extract_all_body_text(linked_soup)
                    texts.append(linked_text)
                except Exception as e:
                    logger.warning(f"Skipping local link {href}: {e}")

    return "\n\n".join(texts)


def process_html_file(path: Path, chunk_size: int = 500, seen_links: Set[Path] = None) -> List[Dict[str, str]]:
    """
    Processes an HTML file by extracting all visible and hidden text from the body,
    including one level of local and external HTML links. Skips <head> section entirely.
    """
    seen_links = seen_links or set()
    try:
        with path.open("r", encoding="utf-8") as f:
            html = f.read()
        soup = BeautifulSoup(html, "html.parser")

        base_text = extract_all_body_text(soup)
        linked_text = extract_first_level_html_links(path, soup, seen_links)
        full_text = clean_text(base_text + "\n\n" + linked_text)

        return [
            {
                "id": f"html_{path.name}_{idx}",
                "source": path.name,
                "text": chunk
            }
            for idx, chunk in enumerate(split_text(full_text, chunk_size))
            if len(chunk.strip().split()) > 10
        ]
    except Exception as e:
        logger.error(f"Error processing HTML file '{path.name}': {e}")
        traceback.print_exc()
        return []


def extract_first_level_pdf_links(doc: fitz.Document, base_path: Path, seen_links: Set[Path]) -> str:
    """Follows first-level internal PDF links and extracts text (1-level only)."""
    texts = []
    for page in doc:
        links = page.get_links()
        for link in links:
            uri = link.get("uri", "")
            if uri and uri.endswith(".pdf") and not uri.startswith("http"):
                linked_path = (base_path.parent / uri).resolve()
                if linked_path in seen_links:
                    continue
                seen_links.add(linked_path)
                if linked_path.exists() and linked_path.is_file():
                    try:
                        subdoc = fitz.open(str(linked_path))
                        text = "\n\n".join(p.get_text() for p in subdoc)
                        texts.append(text)
                    except Exception as e:
                        logger.warning(f"Skipping linked PDF {uri}: {e}")
    return "\n\n".join(texts)


def process_pdf_file(path: Path, chunk_size: int = 500, seen_links: Set[Path] = None) -> List[Dict[str, str]]:
    """
    Processes a PDF file by extracting text content from the file,
    including text from one level of local .pdf links (non-recursive).
    """
    seen_links = seen_links or set()
    try:
        doc = fitz.open(str(path))
        main_text = "\n\n".join(page.get_text() for page in doc)
        linked_text = extract_first_level_pdf_links(doc, path, seen_links)
        full_text = clean_text(main_text + "\n\n" + linked_text)

        return [
            {
                "id": f"pdf_{path.name}_{idx}",
                "source": path.name,
                "text": chunk
            }
            for idx, chunk in enumerate(split_text(full_text, chunk_size))
            if len(chunk.strip().split()) > 10
        ]
    except Exception as e:
        logger.error(f"Error processing PDF file '{path.name}': {e}")
        traceback.print_exc()
        return []


def save_chunks(chunks: List[Dict[str, str]], output_path: Path) -> None:
    """Saves chunk data as JSON to the given output path."""
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(chunks)} chunks to {output_path.name}")
    except Exception as e:
        logger.error(f"Error saving output: {e}")
        traceback.print_exc()