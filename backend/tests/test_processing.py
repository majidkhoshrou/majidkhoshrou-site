import unittest
from pathlib import Path
from libs.processing import (
    split_text,
    clean_text,
    extract_all_body_text,
    process_html_file,
    process_pdf_file
)

class TestProcessing(unittest.TestCase):
    test_dir = Path(__file__).parent

    def test_split_text(self):
        text = "word " * 1200
        chunks = list(split_text(text, chunk_size=500))
        self.assertEqual(len(chunks), 3)
        self.assertTrue(all(len(c.split()) <= 500 for c in chunks))

    def test_clean_text(self):
        raw = "This   is \n a test.\tDone.   "
        cleaned = clean_text(raw)
        self.assertEqual(cleaned, "This is a test. Done.")

    def test_extract_all_body_text(self):
        html = """
        <html><body>
            <p>Visible</p>
            <div style="display: none;">Hidden</div>
            <script>console.log("skip");</script>
        </body></html>
        """
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        text = extract_all_body_text(soup)
        self.assertIn("Visible", text)
        self.assertIn("Hidden", text)
        self.assertNotIn("console.log", text)

    def test_process_html_file(self):
        path = self.test_dir / "test_sample.html"
        chunks = process_html_file(path)
        all_text = " ".join(c["text"] for c in chunks)
        self.assertIn("Visible Header", all_text)
        self.assertIn("This is a visible paragraph", all_text)
        self.assertIn("This is linked content", all_text)  # From linked.html

    def test_process_pdf_file(self):

        import fitz

        path = self.test_dir / "test_pdf.pdf"
        chunks = process_pdf_file(path)
        all_text = " ".join(c["text"] for c in chunks)

        self.assertIn("Hello from main PDF", all_text)

        # Just verify the link exists (we won't follow it)
        doc = fitz.open(str(path))
        links = doc[0].get_links()
        self.assertTrue(any("https://www.w3.org" in l.get("uri", "") for l in links))

if __name__ == "__main__":
    unittest.main()
