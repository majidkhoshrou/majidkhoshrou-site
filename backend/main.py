import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv

from libs.processing import save_chunks
from libs.extract_knowledge import extract_chunks
from libs.generate_knowledge_embeddings import generate_embeddings
from libs.build_faiss_index import build_faiss_index


def main():
    parser = argparse.ArgumentParser(description="Run full pipeline: extract → embed → index")
    parser.add_argument("--html-dir", type=Path, default=Path("templates"), help="Directory with HTML files")
    parser.add_argument("--pdf-dir", type=Path, default=Path("pdfs"), help="Directory with PDF files")
    parser.add_argument("--chunk-out", type=Path, default=Path("data/knowledge_chunks.json"), help="Output for text chunks")
    parser.add_argument("--embed-out", type=Path, default=Path("data/knowledge_embeddings.json"), help="Output for embeddings")
    parser.add_argument("--faiss-out", type=Path, default=Path("data/knowledge_faiss.index"), help="Output for FAISS index")
    parser.add_argument("--model", default="text-embedding-3-small", help="OpenAI embedding model")
    parser.add_argument("--chunk-size", type=int, default=500, help="Number of words per chunk")
    parser.add_argument("--skip-html", action="store_true", help="Skip HTML extraction")
    parser.add_argument("--skip-pdf", action="store_true", help="Skip PDF extraction")
    parser.add_argument("--follow-links", action="store_true", help="Follow HTML links during extraction")
    parser.add_argument("--max-depth", type=int, default=1, help="Max depth for link-following")
    parser.add_argument("--force", action="store_true", help="Force re-embed and re-index")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    load_dotenv()

    # Step 1: Extract
    logger.info("📚 Extracting knowledge chunks...")
    chunks = extract_chunks(
        html_dir=args.html_dir,
        pdf_dir=args.pdf_dir,
        output_path=args.chunk_out,
        chunk_size=args.chunk_size,
        skip_html=args.skip_html,
        skip_pdf=args.skip_pdf,
        follow_links=args.follow_links,
        max_depth=args.max_depth
    )
    save_chunks(chunks, args.chunk_out)

    # Step 2: Embed
    logger.info("🧠 Generating embeddings...")
    embeddings = generate_embeddings(
        model=args.model,
        input_path=args.chunk_out,
        output_path=args.embed_out,
        force=args.force
    )

    # Step 3: Index
    logger.info("📦 Building FAISS index...")
    build_faiss_index(
        embeddings_path=args.embed_out,
        output_path=args.faiss_out,
        force=args.force
    )

    logger.info("✅ All steps completed successfully.")


if __name__ == "__main__":
    main()
