import time
import unittest
from unittest.mock import patch

from ml.tools import SourceLookupRequest, SourceLookupTool, ToolTimeout


class SourceLookupToolTest(unittest.TestCase):
    def request(self, owner="u1"):
        return SourceLookupRequest("u1", owner, "оперативная память", [{"page": 1, "text": "Кэш ускоряет доступ к оперативной памяти."}])

    def test_contract_and_minimal_rights(self):
        result = SourceLookupTool().run(self.request())
        self.assertEqual("ok", result.status)
        self.assertEqual(1, result.passages[0]["page"])
        self.assertEqual("tool_forbidden", SourceLookupTool().run(self.request("u2")).status)

    def test_timeout_is_explicit(self):
        def slow(_):
            time.sleep(0.03)
        with patch.object(SourceLookupTool, "_lookup", side_effect=slow):
            with self.assertRaises(ToolTimeout):
                SourceLookupTool(timeout_seconds=0.001).run(self.request())


if __name__ == "__main__":
    unittest.main()
