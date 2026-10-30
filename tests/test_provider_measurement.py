import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import httpx

spec=importlib.util.spec_from_file_location("provider_measurement",Path(__file__).parent/"evidence/run_production_handoff.py")
measurement=importlib.util.module_from_spec(spec)
spec.loader.exec_module(measurement)

class MeasurementTests(unittest.TestCase):
    def test_failed_formula_response_is_saved_before_provider_assertion(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/"result.json"
            fake=MagicMock()
            fake.request.side_effect=[httpx.Response(200,json={"commit_sha":"test"}),httpx.Response(201,json={"model":"deterministic-grounded-v2","fallback_used":True,"fallback_reason":"gemini_invalid_output","validation_error":"quote_mismatch"})]
            with patch.object(measurement.httpx,"Client") as factory, patch("sys.argv",["measure","--base-url","https://example.invalid","--output",str(output),"--scenarios","1","--fixture","formula"]):
                factory.return_value.__enter__.return_value=fake
                self.assertEqual(measurement.main(),1)
            result=json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["status"],"failed")
            self.assertEqual(result["scenarios"][0]["generation"]["response"]["validation_error"],"quote_mismatch")
            self.assertEqual(result["scenarios"][0]["reviews"],[])

    def test_reference_copy_is_not_labelled_as_a_paraphrase(self):
        card={"card_id":"one","reference_answer":"Docker использует контейнеры."}
        provider={"model":"gemini-test","fallback_used":False,"usage":{"input_tokens":10,"output_tokens":5}}
        responses=[httpx.Response(200,json={"commit_sha":"test"}),httpx.Response(201,json={**provider,"card_set_id":"set","cards":[card]}),httpx.Response(201,json={"session_id":"session"})]
        responses += [httpx.Response(200,json={**provider,"persisted":True,"review_id":str(i)}) for i in range(5)]
        responses += [httpx.Response(200,json={"cards":[card]})]
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/"result.json";fake=MagicMock();fake.request.side_effect=responses
            with patch.object(measurement.httpx,"Client") as factory, patch("sys.argv",["measure","--base-url","https://example.invalid","--output",str(output),"--scenarios","1","--fixture","ordinary"]):
                factory.return_value.__enter__.return_value=fake
                self.assertEqual(measurement.main(),0)
            result=json.loads(output.read_text(encoding="utf-8"))
            row=result["scenarios"][0]["reviews"][0]
            self.assertEqual(row["answer_mode"],"reference_copy_not_paraphrase")
            self.assertEqual(row["student_answer"],card["reference_answer"])
