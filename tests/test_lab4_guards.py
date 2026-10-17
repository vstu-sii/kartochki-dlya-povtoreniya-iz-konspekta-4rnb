import json
import unittest
from pathlib import Path

from backend.guards import authorize_model_tool, inspect_untrusted_text


class ProductionGuardsTest(unittest.TestCase):
    def test_attack_dataset(self):
        path = Path(__file__).parent / "security" / "attacks.jsonl"
        for line in path.read_text(encoding="utf-8").splitlines():
            case = json.loads(line)
            actual = "allow" if inspect_untrusted_text(case["text"]).allowed else "block"
            self.assertEqual(case["expected_after"], actual, case["id"])

    def test_model_cannot_choose_identity_or_mutating_action(self):
        self.assertTrue(authorize_model_tool(user_id="u1", resource_owner_id="u1", action="lookup_source").allowed)
        self.assertFalse(authorize_model_tool(user_id="u1", resource_owner_id="u2", action="lookup_source").allowed)
        self.assertFalse(authorize_model_tool(user_id="u1", resource_owner_id="u1", action="delete_session").allowed)


if __name__ == "__main__":
    unittest.main()
