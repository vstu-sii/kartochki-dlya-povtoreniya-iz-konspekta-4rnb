import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from ml.models.baseline import BaselineModel
from ml.tools import SourceLookupRequest, SourceLookupResult, SourceLookupTool
from ml.tracing.client import TraceClient


class SourceLookupToolTest(unittest.TestCase):
    def request(self, owner="u1", query="cache memory"):
        return SourceLookupRequest(
            "u1", owner, query,
            [{"page": 1, "text": "A cache speeds up access to memory."}],
        )

    def test_success_forbidden_and_empty_are_structured(self):
        success = SourceLookupTool().run(self.request())
        self.assertEqual("success", success.status)
        self.assertEqual(1, success.passages[0]["page"])
        forbidden = SourceLookupTool().run(self.request("u2"))
        self.assertEqual(("forbidden", "TOOL_FORBIDDEN"), (forbidden.status, forbidden.error_code))
        empty = SourceLookupTool().run(self.request(query="несуществующийтермин"))
        self.assertEqual("empty", empty.status)

    def test_300ms_work_returns_near_50ms_deadline(self):
        def slow(_request):
            time.sleep(0.3)
            return []

        with patch.object(SourceLookupTool, "_lookup", side_effect=slow):
            started = time.perf_counter()
            result = SourceLookupTool(timeout_seconds=0.05).run(self.request())
            elapsed = time.perf_counter() - started
        self.assertEqual("timeout", result.status)
        self.assertLess(elapsed, 0.18, f"deadline returned after {elapsed:.3f}s")
        self.assertGreaterEqual(elapsed, 0.04)

    def test_internal_exception_is_error(self):
        with patch.object(SourceLookupTool, "_lookup", side_effect=RuntimeError("boom")):
            result = SourceLookupTool().run(self.request())
        self.assertEqual(("error", "TOOL_ERROR"), (result.status, result.error_code))

    def test_model_falls_back_to_original_pages_after_tool_error(self):
        with tempfile.TemporaryDirectory() as directory:
            model = BaselineModel(TraceClient(str(Path(directory) / "trace.jsonl")))
            with patch.object(
                model.source_lookup,
                "run",
                return_value=SourceLookupResult("error", [], 1.2, False, "TOOL_ERROR"),
            ):
                result = model.generate({
                    "user_id": "u1",
                    "resource_owner_id": "u1",
                    "pages": [{"page": 1, "text": "Кэш ускоряет доступ к данным."}],
                    "requested_card_count": 1,
                })
        self.assertEqual("error_fallback_to_request_pages", result["tool_status"])
        self.assertEqual(1, len(result["cards"]))

    def test_model_cache_hit_keeps_usage_and_trace(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trace.jsonl"
            model = BaselineModel(TraceClient(str(path)))
            payload = {
                "user_id": "u1", "resource_owner_id": "u1",
                "pages": [{"page": 1, "text": "Кэш ускоряет доступ к данным."}],
                "requested_card_count": 1,
            }
            first = model.generate(payload)
            second = model.generate(payload)
            events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        self.assertFalse(first["cache_hit"])
        self.assertTrue(second["cache_hit"])
        self.assertGreater(first["usage"]["input_tokens"], 0)
        self.assertEqual("generate_cards_cache_hit", events[-1]["operation"])


if __name__ == "__main__":
    unittest.main()
