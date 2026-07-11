import importlib.util
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("daily_update", Path(__file__).parents[1] / "scripts" / "daily_update.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DailyUpdateTests(unittest.TestCase):
    def test_normalize_title(self):
        self.assertEqual(MODULE.normalize_title("Social Life: A Study"), "sociallifeastudy")

    def test_deduplicates_by_doi_and_title(self):
        rows = [{"title": "Existing Paper", "doi": "10.1/x", "citations": 9}, {"title": "New Paper", "doi": "10.1/y", "citations": 1}]
        selected = MODULE.choose_candidate(rows, {"10.1/x"}, {"other"})
        self.assertEqual(selected["title"], "New Paper")
        self.assertIsNone(MODULE.choose_candidate(rows[:1], set(), {"existingpaper"}))

    def test_rebuilds_openalex_abstract(self):
        self.assertEqual(MODULE.abstract_from_inverted({"world": [1], "hello": [0]}), "hello world")

    def test_slugify_is_url_safe(self):
        self.assertEqual(MODULE.slugify("Social Life & Inequality!"), "social-life-inequality")

    def test_empty_candidate_set_is_safe(self):
        self.assertIsNone(MODULE.choose_candidate([], set(), set()))

    def test_fallback_slug_is_dated(self):
        self.assertTrue(MODULE.slugify("中文标题").startswith("sociology-reading-"))


if __name__ == "__main__":
    unittest.main()


