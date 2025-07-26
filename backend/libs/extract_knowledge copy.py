import argparse
import logging
from pathlib import Path
from typing import List, Dict

from tqdm import tqdm
from libs.processing import process_html_file, process_pdf_file, save_chunks


def extract_chunks(
    html_dir: Path,
    pdf_dir: Path,
    output_path: Path,
    chunk_size: int = 500,
    skip_html: bool = False,
    skip_pdf: bool = False,
    follow_links: bool = True,
    max_depth: int = 1
) -> List[Dict[str, str]]:
    """
    Extracts knowledge chunks from HTML and PDF files.

    Args:
        html_dir (Path): Directory containing HTML files.
        pdf_dir (Path): Directory containing PDF files.
        output_path (Path): Path to save the output JSON file.
        chunk_size (int): Number of words per chunk.
        skip_html (bool): If True, skip HTML processing.
        skip_pdf (bool): If True, skip PDF processing.
        follow_links (bool): Whether to follow internal/external links.
        max_depth (int): Maximum link-follow depth.

    Returns:
        List[Dict[str, str]]: List of extracted knowledge chunks.
    """
    logger = logging.getLogger(__name__)
    chunks = []
    seen_sources = set()

    if not skip_html and html_dir.exists():
        html_files = list(html_dir.glob("*.html"))
        for path in tqdm(html_files, desc="📄 Processing HTML files"):
            html_chunks = process_html_file(
                path,
                chunk_size=chunk_size,
                overlap=50,
                follow_links=follow_links,
                max_depth=max_depth,
                seen_links=seen_sources
            )
            chunks.extend(c for c in html_chunks if len(c["text"].strip().split()) > 10)

    if not skip_pdf and pdf_dir.exists():
        pdf_files = list(pdf_dir.glob("*.pdf"))
        for path in tqdm(pdf_files, desc="📕 Processing PDF files"):
            if path not in seen_sources:
                seen_sources.add(path)
                pdf_chunks = process_pdf_file(path, chunk_size=chunk_size)
                chunks.extend(c for c in pdf_chunks if len(c["text"].strip().split()) > 10)

    logger.info(f"✅ Extracted {len(chunks)} total chunks")
    save_chunks(chunks, output_path)
    return chunks


cwd = Path.cwd()
print(cwd)

def main():
    parser = argparse.ArgumentParser(description="Extract knowledge chunks from HTML and PDF files.")
    parser.add_argument("--html-dir", type=Path, default=Path("templates"), help="Directory with HTML files (default: ./templates)")
    parser.add_argument("--pdf-dir", type=Path, default=Path("static/pdfs"), help="Directory with PDF files (default: ./static)")
    parser.add_argument("--output", type=Path, default=Path("data/knowledge_chunks.json"), help="Output JSON path (default: ./data/knowledge_chunks.json)")
    parser.add_argument("--chunk-size", type=int, default=500, help="Words per chunk (default: 500)")
    parser.add_argument("--skip-html", action="store_true", help="Skip HTML processing")
    parser.add_argument("--skip-pdf", action="store_true", help="Skip PDF processing")
    parser.add_argument("--follow-links", action="store_true", help="Follow links inside HTML pages")
    parser.add_argument("--max-depth", type=int, default=1, help="Max link-follow depth (default: 1)")


    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    logger = logging.getLogger(__name__)

    logger.info(f"📂 HTML directory: {args.html_dir}")
    logger.info(f"📂 PDF directory: {args.pdf_dir}")
    logger.info(f"📄 Output file: {args.output}")
    logger.info(f"🔧 Chunk size: {args.chunk_size}")
    logger.info(f"🔗 Follow links: {args.follow_links} (max depth = {args.max_depth})")

    extract_chunks(
        html_dir=args.html_dir,
        pdf_dir=args.pdf_dir,
        output_path=args.output,
        chunk_size=args.chunk_size,
        skip_html=args.skip_html,
        skip_pdf=args.skip_pdf,
        follow_links=args.follow_links,
        max_depth=args.max_depth
    )


if __name__ == "__main__":
    main()
