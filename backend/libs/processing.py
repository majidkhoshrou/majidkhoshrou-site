import re
import json
import traceback
from pathlib import Path
from typing import List, Dict, Iterator
from bs4 import BeautifulSoup
import fitz  # PyMuPDF


def split_text(text: str, chunk_size: int = 500) -> Iterator[str]:
    """Yields chunks of text of approximately `chunk_size` words."""
    words = text.split()
    for i in range(0, len(words), chunk_size):
        yield " ".join(words[i:i + chunk_size])


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

    return " ".join(text_parts)


def extract_first_level_html_links(path: Path, soup: BeautifulSoup) -> str:
    """Follows internal .html links from a given file and extracts their text (1-level only)."""
    texts = []

    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        if href.endswith(".html") and not href.startswith("http"):
            linked_path = (path.parent / href).resolve()
            if linked_path.exists() and linked_path.is_file():
                try:
                    with linked_path.open("r", encoding="utf-8") as f:
                        html = f.read()
                    linked_soup = BeautifulSoup(html, "html.parser")
                    linked_text = extract_all_body_text(linked_soup)
                    texts.append(linked_text)
                except Exception as e:
                    print(f"⚠️ Skipping linked HTML {href}: {e}")

    return " ".join(texts)


def process_html_file(path: Path, chunk_size: int = 500) -> List[Dict[str, str]]:
    """
    Processes an HTML file by extracting all visible and hidden text from the body,
    including one level of local .html links. Skips <head> section entirely.

    Args:
        path (Path): Path to the HTML file.
        chunk_size (int): Number of words per text chunk.

    Returns:
        List[Dict[str, str]]: List of chunked text segments.
    """
    try:
        with path.open("r", encoding="utf-8") as f:
            html = f.read()

        soup = BeautifulSoup(html, "html.parser")

        # Extract base file content
        base_text = extract_all_body_text(soup)

        # Extract one level of internal .html link content
        linked_text = extract_first_level_html_links(path, soup)

        # Combine and clean
        full_text = clean_text(base_text + " " + linked_text)

        return [
            {
                "id": f"html_{path.name}_{idx}",
                "source": path.name,
                "text": chunk
            }
            for idx, chunk in enumerate(split_text(full_text, chunk_size))
        ]

    except Exception as e:
        print(f"❌ Error processing HTML file '{path.name}': {e}")
        traceback.print_exc()
        return []


def extract_first_level_pdf_links(doc: fitz.Document, base_path: Path) -> str:
    """Follows first-level internal PDF links and extracts text (1-level only)."""
    texts = []
    for page in doc:
        links = page.get_links()
        for link in links:
            uri = link.get("uri", "")
            if uri and uri.endswith(".pdf") and not uri.startswith("http"):
                linked_path = (base_path.parent / uri).resolve()
                if linked_path.exists() and linked_path.is_file():
                    try:
                        subdoc = fitz.open(str(linked_path))
                        text = "".join(p.get_text() for p in subdoc)
                        texts.append(text)
                    except Exception as e:
                        print(f"⚠️ Skipping linked PDF {uri}: {e}")
    return " ".join(texts)


def process_pdf_file(path: Path, chunk_size: int = 500) -> List[Dict[str, str]]:
    """
    Processes a PDF file by extracting text content from the file,
    including text from one level of local .pdf links (non-recursive).

    Args:
        path (Path): Path to the PDF file.
        chunk_size (int): Number of words per text chunk.

    Returns:
        List[Dict[str, str]]: List of chunked text segments.
    """
    try:
        doc = fitz.open(str(path))

        # Extract base document text
        main_text = "".join(page.get_text() for page in doc)

        # Extract one level of linked .pdf file content
        linked_text = extract_first_level_pdf_links(doc, path)

        # Combine and clean
        full_text = clean_text(main_text + " " + linked_text)

        return [
            {
                "id": f"pdf_{path.name}_{idx}",
                "source": path.name,
                "text": chunk
            }
            for idx, chunk in enumerate(split_text(full_text, chunk_size))
        ]

    except Exception as e:
        print(f"❌ Error processing PDF file '{path.name}': {e}")
        traceback.print_exc()
        return []
  

def save_chunks(chunks: List[Dict[str, str]], output_path: Path) -> None:
    """Saves chunk data as JSON to the given output path."""
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)

        print(f"✅ Saved {len(chunks)} chunks to {output_path.name}")
    except Exception as e:
        print(f"❌ Error saving output: {e}")
        traceback.print_exc()
