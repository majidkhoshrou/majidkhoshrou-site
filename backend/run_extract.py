from pathlib import Path
from libs.processing import extract_all_chunks

from pathlib import Path

extract_all_chunks(
    html_dir=Path("templates"),
    pdf_dir=Path("pdfs"),
    output_path=Path("data/knowledge_chunks.json")
)

