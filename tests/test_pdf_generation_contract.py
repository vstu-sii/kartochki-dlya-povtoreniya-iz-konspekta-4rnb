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


    def test_wrapped_quote_is_verbatim_and_invalid_quote_is_rejected(self):
        original = "Docker позволяет\n    запускать приложения в контейнерах."
        sentence = "Docker позволяет запускать приложения в контейнерах."
        quote = BaselineModel._original_source_quote(sentence, original)
        self.assertEqual(quote, original)
        with self.assertRaises(ValueError):
            BaselineModel._original_source_quote("Неподтверждённый текст", original)
        long_source = "слово\n" * 150
        quote = BaselineModel._original_source_quote(" ".join(long_source.split()), long_source)
        self.assertLessEqual(len(quote), 500)
        self.assertIn(quote, long_source)

    def test_pdf_upload_returns_201_and_persists_cards(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        from backend.database import Base, session_scope
        from backend.models import CardSet
        from backend.routers.ai import router

        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        sessions = sessionmaker(bind=engine, expire_on_commit=False)
        def isolated_session():
            with sessions() as db:
                yield db
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[session_scope] = isolated_session
        fixture = Path(__file__).parent / "fixtures/lab5-devops-source.pdf"
        try:
            with patch.dict(os.environ, {"MODEL_PROVIDER": "deterministic", "AI_SERVICE_URL": "inprocess"}), patch("backend.routers.ai.AI_SERVICE_URL", "inprocess"):
                with TestClient(app) as client:
                    response = client.post(
                        "/v1/ai/card-sets/from-pdf",
                        headers={"X-User-ID": "pdf-contract-owner"},
                        files={"file": (fixture.name, fixture.read_bytes(), "application/pdf")},
                        data={"requested_card_count": "5", "language": "ru"},
                    )
                    self.assertEqual(response.status_code, 201, response.text)
                    result = response.json()
                    self.assertEqual(len(result["cards"]), 5)
                    with sessions() as db:
                        persisted = db.get(CardSet, result["card_set_id"])
                        self.assertIsNotNone(persisted)
                        self.assertEqual(len(persisted.cards), 5)
                        self.assertEqual(
                            [card.source_quote for card in persisted.cards],
                            [card["source_quote"] for card in result["cards"]],
                        )
        finally:
            engine.dispose()

if __name__ == "__main__":
    unittest.main()
