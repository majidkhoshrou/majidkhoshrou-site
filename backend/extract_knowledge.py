import argparse
from pathlib import Path
from libs.processing import process_html_file, process_pdf_file, save_chunks
import logging
from tqdm import tqdm


def main():
    parser = argparse.ArgumentParser(description="Extract knowledge chunks from HTML and PDF files.")

    parser.add_argument(
        "--html-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "docs",
        help="Directory containing HTML files (default: ../docs)"
    )
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "pdfs",
        help="Directory containing PDF files (default: ./pdfs)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "data" / "knowledge_chunks.json",
        help="Path to output JSON file (default: ./data/knowledge_chunks.json)"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=500,
        help="Number of words per chunk (default: 500)"
    )
    parser.add_argument(
        "--skip-html",
        action="store_true",
        help="Skip processing HTML files"
    )
    parser.add_argument(
        "--skip-pdf",
        action="store_true",
        help="Skip processing PDF files"
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    logger.info(f"📂 HTML directory: {args.html_dir}")
    logger.info(f"📂 PDF directory: {args.pdf_dir}")
    logger.info(f"📄 Output file: {args.output}")
    logger.info(f"🔧 Chunk size: {args.chunk_size}")

    chunks = []
    seen_html_links = set()
    seen_pdf_links = set()

    if not args.skip_html:
        html_files = list(args.html_dir.glob("*.html"))
        for path in tqdm(html_files, desc="Processing HTML files"):
            if path not in seen_html_links:
                seen_html_links.add(path)
                html_chunks = process_html_file(path, chunk_size=args.chunk_size)
                chunks.extend(c for c in html_chunks if len(c["text"].strip().split()) > 10)

    if not args.skip_pdf and args.pdf_dir.exists():
        pdf_files = list(args.pdf_dir.glob("*.pdf"))
        for path in tqdm(pdf_files, desc="Processing PDF files"):
            if path not in seen_pdf_links:
                seen_pdf_links.add(path)
                pdf_chunks = process_pdf_file(path, chunk_size=args.chunk_size)
                chunks.extend(c for c in pdf_chunks if len(c["text"].strip().split()) > 10)

    save_chunks(chunks, args.output)


if __name__ == "__main__":
    main()
