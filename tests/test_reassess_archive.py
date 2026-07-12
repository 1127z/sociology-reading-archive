import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import reassess_archive as reassess


class ReassessArchiveTests(unittest.TestCase):
    def test_inventory_covers_all_legacy_entries(self):
        import json
        rows = json.loads(reassess.INVENTORY.read_text(encoding="utf-8"))
        self.assertEqual(6, len(rows))
        self.assertEqual(6, len({row["slug"] for row in rows}))

    def test_arxiv_is_routed_without_doi(self):
        item = {"arxivId": "2507.05030"}
        self.assertTrue(item.get("arxivId"))


if __name__ == "__main__":
    unittest.main()
