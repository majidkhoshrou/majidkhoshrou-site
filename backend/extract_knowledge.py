import argparse
from pathlib import Path
from libs.processing import process_html_file, process_pdf_file, save_chunks

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

    print(f"📂 HTML directory: {args.html_dir}")
    print(f"📂 PDF directory: {args.pdf_dir}")
    print(f"📄 Output file: {args.output}")
    print(f"🔧 Chunk size: {args.chunk_size}")

    chunks = []

    if not args.skip_html:
        for path in args.html_dir.glob("*.html"):
            chunks.extend(process_html_file(path, chunk_size=args.chunk_size))

    if not args.skip_pdf and args.pdf_dir.exists():
        for path in args.pdf_dir.glob("*.pdf"):
            chunks.extend(process_pdf_file(path, chunk_size=args.chunk_size))

    save_chunks(chunks, args.output)


if __name__ == "__main__":
    main()
