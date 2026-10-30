"""Formula preservation through extraction, generation and the real guard."""
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import fitz
from backend.pdf_extractor import extract_pdf_pages
from backend.pdf_math import math_page_text
from backend.quality_guards import validate_model_card
from ml.models.baseline import BaselineModel


class QuietTrace:
    def record(self, *args, **kwargs):
        pass


class PdfMathTests(unittest.TestCase):
    def test_real_pdf_preserves_all_reference_formulas(self):
        fixtures = Path(__file__).parent / "fixtures"
        pages = extract_pdf_pages((fixtures/"lab5-formulas-source.pdf").read_bytes())
        expected = json.loads((fixtures/"lab5-formulas-expected.json").read_text(encoding="utf-8"))
        self.assertEqual(len(expected), 39)
        self.assertEqual([p.method for p in pages], ["math_layout", "math_layout"])
        for row in expected:
            with self.subTest(formula=row["id"]):
                self.assertIn(row["expected_latex"], pages[row["page"]-1].text)
        # Exhaustive batch coverage, not a claim that one requested set contains
        # every formula from the source. Public API remains limited to 5..10.
        model = BaselineModel(QuietTrace())
        with patch.dict(os.environ, {"MODEL_PROVIDER": "deterministic"}):
            for page in pages:
                formulas = [r["expected_latex"] for r in expected if r["page"] == page.page]
                for start in range(0,len(formulas),10):
                    batch = formulas[start:start+10]
                    source = "\n".join(batch)
                    result = model.generate({"document_id": "formula-batch", "pages": [{"page":page.page,"text":source}], "requested_card_count":10, "language":"ru", "user_id":"math-owner", "resource_owner_id":"math-owner"})
                    self.assertEqual([c["reference_answer"] for c in result["cards"]],batch)
                    for card in result["cards"]:
                        self.assertIsNone(validate_model_card(card,{page.page:source}))

    def test_geometry_uses_unseen_symbols_and_preserves_prose_fallback(self):
        # An independent generated layout rules out lookup by file hash/content.
        with fitz.open() as doc:
            page = doc.new_page()
            for i, (base, exponent) in enumerate((("z","7"),("q","4"),("w","9"))):
                y=100+i*55
                page.insert_text((70,y),base,fontsize=14)
                page.insert_text((79,y-6),exponent,fontsize=9)
                page.insert_text((90,y),"=",fontsize=14)
                page.insert_text((110,y-8),"u",fontsize=14)
                page.draw_line((109,y-4),(120,y-4))
                page.insert_text((110,y+13),"v",fontsize=14)
            text=math_page_text(page)
            for base,exponent in (("z","7"),("q","4"),("w","9")):
                self.assertIn(base+"^{"+exponent+"}",text)
            self.assertEqual(text.count(r"\frac{u}{v}"),3)
        with fitz.open() as doc:
            page=doc.new_page()
            page.insert_text((70,100),"A normal paragraph with x = 3.")
            self.assertIsNone(math_page_text(page))


if __name__ == "__main__":
    unittest.main()
