import uuid
import fitz  # PyMuPDF
import spacy
import json
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin, urlparse
import os
import re
from collections import OrderedDict

from io import BytesIO


# def remove_duplicate_sentences(text: str) -> str:
#     # Split into sentences (basic split by punctuation)
#     sentences = re.split(r'(?<=[.!?])\s+', text.strip())

#     seen = OrderedDict()
#     for sentence in sentences:
#         clean = sentence.strip()
#         if clean and clean not in seen:
#             seen[clean] = None

#     return " ".join(seen.keys())

# =================================
# {
#         "id": str(uuid.uuid4()),
#         "source_type": source_type,
#         "source_path": str(path) if path else None,
#         "title": title,
#         "text": text,
#         "metadata": {
#             "chunk_index": chunk_index,
#             "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
#             "source_url": source_url,
#             "parent_source": str(parent_source) if parent_source else None,
#             "links": extract_links_from_block(block) if block else []
#         }
# }

# html_files = [Path("templates/page1.html")]
# pdf_files = [Path("static/pdfs/report.pdf")]
# external_urls = [
#     "https://example.com/somepage.html",
#     "https://pure.tudelft.nl/some.pdf"
# ]

# all_sources = html_files + pdf_files + external_urls  # mixed list

# for item in all_sources:
#     if isinstance(item, str) and item.startswith(("http://", "https://")):
#         print(f"{item} → external")
#     else:
#         print(f"{item} → local")



nlp = spacy.load("en_core_web_sm")
MAX_TOKENS = 500

def clean_text(text: str) -> str:
    """Normalize whitespace to single spaces and trim."""
    return re.sub(r'\s+', ' ', text).strip()

html_dir = Path("templates")
pdf_dir = Path("static/pdfs")
output_path = Path("data/knowledge_chunks.json")

html_files = list(html_dir.glob("**/*.html"))
pdf_files = list(pdf_dir.glob("**/*.pdf"))
external_urls = []

# read local html file
html_file = [ i for i in html_files if 'about' in str(i) ][0]
# html_file = "https://pure.tudelft.nl/ws/files/56847223/Applied_Energy_LSBoosting_LoadForecast_002_.pdf"
# html_file = "https://github.com/OpenSTEF/openstef"

knowledge_chunks = []

for html_file in html_files:

    aux_dict = {'id': str(uuid.uuid4()), 'source_type': 'local', 'source_path': str(html_file)}

    print("=="*20)
    print('html_file:', html_file)
    print("=="*20)
    html = Path(html_file).read_text(encoding='utf-8')
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["header", "nav", "footer", "script", "style"]):
            tag.decompose()
    
    title = soup.title.string if soup.title else "No Title"
    aux_dict['title'] = title

    text = (clean_text(soup.get_text(strip=False)))
    aux_dict['text'] = text

    a_tags_with_href = soup.find_all('a', href=True)
    ext_links = {}
    for a in a_tags_with_href:
        href = a['href'].strip()
        if href.startswith(('http://', 'https://')):
            ext_links[a.get_text(strip=True)] = href
            if href not in external_urls:
                external_urls.append(href)

    aux_dict['external_links'] = ext_links
    knowledge_chunks.append(aux_dict)

print('html_files:', html_files)
print('external_urls:', external_urls)

with open(output_path, "w", encoding="utf-8") as f:
        json.dump(knowledge_chunks, f, indent=2, ensure_ascii=False)

    # for a in a_tags_with_href:
    #     if a['href'].startswith('http://') or a['href'].startswith('https://'):
    #         print(a.get_text(), a['href'])
    #         external_urls.append(a['href'])






# # Download the PDF
# response = requests.get(html_file)
# print('response.raise_for_status():', response.raise_for_status())
# ctype = response.headers.get("Content-Type", "").lower()
# print('ctype:', ctype)





# # Load the PDF from memory
# pdf_stream = BytesIO(response.content)
# doc = fitz.open(stream=pdf_stream, filetype="pdf")

# # Extract text from all pages
# text = ""
# for page in doc:
#     text += page.get_text()

# doc.close()

# print(clean_text(text)[:2000])  # preview first 1000 characters


# # Determine if it's a URL or a local file
# if str(html_file).startswith(('http://', 'https://')):
#     # External URL
#     response = requests.get(html_file)
#     response.raise_for_status()  # optional: raises error for bad status
#     html = response.text
# else:
#     # Local file
#     html = Path(html_file).read_text(encoding='utf-8')



# html = html_file.read_text(encoding="utf-8")

