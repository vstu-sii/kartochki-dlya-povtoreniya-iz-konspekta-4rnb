import unittest
from unittest.mock import MagicMock, patch

from backend.pdf_extractor import clean_text, extract_pdf_pages


class PdfExtractorTest(unittest.TestCase):
    def test_clean_text_repairs_hyphenation_and_whitespace(self):
        self.assertEqual("распределённая система\n\nНовый абзац", clean_text("распределён-\nная   система\n\n\nНовый\tабзац"))

    def test_repeated_header_is_removed(self):
        fake_reader = MagicMock()
        fake_reader.is_encrypted = False
        fake_reader.pages = []
        for body in ("Первый содержательный абзац.", "Второй содержательный абзац.", "Третий содержательный абзац."):
            page = MagicMock()
            page.extract_text.return_value = f"Название курса\n{body}\n1"
            fake_reader.pages.append(page)
        with patch("backend.pdf_extractor.PdfReader", return_value=fake_reader):
            pages = extract_pdf_pages(b"fake-pdf")
        self.assertEqual(3, len(pages))
        self.assertTrue(all("Название курса" not in page.text for page in pages))

    def test_ocr_is_used_for_a_scanned_page(self):
        fake_reader = MagicMock()
        fake_reader.is_encrypted = False
        page = MagicMock()
        page.extract_text.return_value = ""
        fake_reader.pages = [page]
        with patch("backend.pdf_extractor.PdfReader", return_value=fake_reader), patch(
            "backend.pdf_extractor._ocr_pages", return_value={1: "Распознанный учебный текст содержит важное определение."}
        ):
            pages = extract_pdf_pages(b"fake-pdf")
        self.assertEqual("ocr", pages[0].method)
        self.assertIn("важное определение", pages[0].text)


if __name__ == "__main__":
    unittest.main()
