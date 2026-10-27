"""A model-generated PDF quote must satisfy the application's real guard."""
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from backend.pdf_extractor import extract_pdf_pages
from backend.quality_guards import validate_model_card
from ml.models.baseline import BaselineModel


class QuietTrace:
    def record(self, *args, **kwargs):
        pass


class PdfGenerationContractTests(unittest.TestCase):
    def test_generated_quotes_pass_application_guard_for_real_pdf(self):
        fixture = Path(__file__).parent / "fixtures/lab5-devops-source.pdf"
        pages = extract_pdf_pages(fixture.read_bytes())
        source = {page.page: page.text for page in pages}
        with patch.dict(os.environ, {"MODEL_PROVIDER": "deterministic"}):
            result = BaselineModel(QuietTrace()).generate({
                "document_id": "quality-real-pdf-quote-contract",
                "pages": [{"page": page.page, "text": page.text} for page in pages],
                "requested_card_count": 5,
                "language": "ru",
                "user_id": "quality-contract-owner",
                "resource_owner_id": "quality-contract-owner",
            })
        self.assertEqual(len(result["cards"]), 5)
        for index, card in enumerate(result["cards"], start=1):
            with self.subTest(card=index, page=card["source_page"]):
                self.assertIsNone(
                    validate_model_card(card, source),
                    "Generated quote is rejected by the API; retain the original "
                    "source span when reflowing the display/reference text.",
                )


if __name__ == "__main__":
    unittest.main()
