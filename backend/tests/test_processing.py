import unittest
from pathlib import Path
from bs4 import BeautifulSoup
from unittest.mock import patch, MagicMock
from libs.processing import (
    clean_text,
    sentence_tokenize,
    split_text,
    extract_all_body_text,
    process_html_file,
    process_pdf_file,
    save_chunks
)
import tempfile
import json
import os


class TestProcessingFunctions(unittest.TestCase):
    def test_clean_text(self):
        dirty = "Some  text\n with\twhitespace."
        clean = clean_text(dirty)
        self.assertEqual(clean, "Some text with whitespace.")

    def test_sentence_tokenize(self):
        text = "This is one. This is two."
        sentences = sentence_tokenize(text)
        self.assertEqual(sentences, ["This is one.", "This is two."])

    def test_split_text(self):
        text = "This is sentence one. This is sentence two.\n\nThis is another paragraph with more sentences."
        chunks = list(split_text(text, chunk_size=10))
        self.assertTrue(all(len(c.split()) <= 10 for c in chunks))

    def test_extract_all_body_text(self):
        html = """
        <html><head><title>Title</title></head>
        <body><h1>Header</h1><p>Paragraph</p><script>ignore()</script></body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        text = extract_all_body_text(soup)
        self.assertIn("Header", text)
        self.assertIn("Paragraph", text)
        self.assertNotIn("ignore", text)

    def test_process_html_file_local(self):
        html_content = "<html><body><p>This is a test HTML document with enough words to exceed the minimum chunk threshold.</p></body></html>"
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.html"
            path.write_text(html_content)
            chunks = process_html_file(path, chunk_size=50)
            self.assertGreater(len(chunks), 0)

    @patch("libs.processing.requests.get")
    def test_process_html_file_external_link(self, mock_get):
        html_content = '<html><body><a href="https://example.com">Example</a></body></html>'
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html><body><p>This is some External page text used for testing external HTML link extraction and chunking.</p></body></html>'
        mock_get.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.html"
            path.write_text(html_content)
            chunks = process_html_file(path, chunk_size=50)
            self.assertTrue(any("External page text" in c["text"] for c in chunks))

    def test_save_chunks(self):
        chunks = [
            {"id": "test_1", "source": "source.html", "text": "Some text."},
            {"id": "test_2", "source": "source.html", "text": "More text."}
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "chunks.json"
            save_chunks(chunks, output_path)
            self.assertTrue(output_path.exists())
            with open(output_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.assertEqual(len(data), 2)


if __name__ == "__main__":
    unittest.main()
