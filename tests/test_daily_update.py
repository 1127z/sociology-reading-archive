import importlib.util
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("daily_update", Path(__file__).parents[1] / "scripts" / "daily_update.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DailyUpdateTests(unittest.TestCase):
    def candidate(self, title="A Sociology Study", doi="10.1/new", journal="American Sociological Review"):
        abstract = ("This sociology study examines social inequality using interview evidence and theory. " * 12)
        return {"title": title, "doi": doi, "citations": 1, "journal": journal, "type": "article", "abstract": abstract, "fullTextUrl": "https://example.org/full", "pdfUrl": "", "provider": "OpenAlex"}

    def test_normalize_title(self):
        self.assertEqual(MODULE.normalize_title("Social Life: A Study"), "sociallifeastudy")

    def test_deduplicates_by_doi_and_title(self):
        rows = [self.candidate("Existing Paper", "10.1/x"), self.candidate("New Paper", "10.1/y")]
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

    def test_abstract_evidence_cannot_claim_expert_full_reading(self):
        summary = {key: [] for key in ("literatureDialogue", "contentFeatures", "researchFeatures", "criticalReview", "researchImplications", "evidenceBoundaries")}
        summary.update({"title": "标题", "method": "综述", "fieldPosition": "定位", "evidenceBasis": "摘要", "analysisDepth": "专家精读", "fullTextSource": "未获得", "confidence": "中"})
        with self.assertRaises(ValueError):
            MODULE.validate_expert_summary(summary)

    def test_selection_source_is_factual(self):
        source = MODULE.selection_source({"provider": "OpenAlex", "learningFocus": "社会学理论", "selectionScore": {"difficulty": "L1", "total": 82}})
        self.assertIn("OpenAlex", source)
        self.assertNotIn("专家推荐", source)

    def test_rejects_non_articles_and_missing_full_text(self):
        config = MODULE.load_selection_config()
        editorial = self.candidate("Editorial: Sociology", "10.1/editorial")
        self.assertEqual(MODULE.hard_filter_reason(editorial, config, set(), set()), "excluded_document_type")
        no_full_text = self.candidate()
        no_full_text["fullTextUrl"] = ""
        self.assertEqual(MODULE.hard_filter_reason(no_full_text, config, set(), set()), "no_authorized_full_text")

    def test_priority_journal_scores_higher(self):
        priority = MODULE.score_candidate(self.candidate())
        ordinary = MODULE.score_candidate(self.candidate(journal="Journal of General Studies"))
        self.assertGreater(priority["total"], ordinary["total"])
        self.assertIn(priority["difficulty"], {"L1", "L2", "L3"})

    def test_low_scoring_candidate_is_not_selected(self):
        weak = self.candidate(journal="Journal of General Studies")
        weak["abstract"] = "Sociology culture evidence. " * 20
        self.assertIsNone(MODULE.choose_candidate([weak], set(), set()))

    def fallback_entry(self, title="中文社会学研究", doi="10.1/cnki"):
        return {"candidate": {"id": "cnki-1", "title": title, "doi": doi, "authors": ["作者"], "journal": "社会学研究", "date": "2025-01-01", "sourceUrl": "https://kns.cnki.net/example", "evidenceText": "经全文核验的证据卡", "selectionScore": {"total": 82, "difficulty": "L2", "breakdown": {}}}}

    def test_cnki_fallback_skips_existing_articles(self):
        queue = [self.fallback_entry("已经发布", "10.1/old"), self.fallback_entry("待发布", "10.1/new")]
        queue[1]["candidate"]["id"] = "cnki-2"
        selected = MODULE.select_fallback_candidate(queue, {"10.1/old"}, {"已经发布"})
        self.assertEqual("cnki-2", selected["id"])
        self.assertEqual("全文", selected["evidenceBasis"])

    def test_cnki_fallback_is_removed_after_publish(self):
        queue = [self.fallback_entry(), self.fallback_entry("第二篇", "10.1/two")]
        queue[1]["candidate"]["id"] = "cnki-2"
        remaining = MODULE.remove_fallback_candidate(queue, "cnki-1")
        self.assertEqual(["cnki-2"], [row["candidate"]["id"] for row in remaining])

    def test_cnki_fallback_requires_audited_fields(self):
        with self.assertRaises(ValueError):
            MODULE.select_fallback_candidate([{"candidate": {"id": "broken"}}], set(), set())

    def test_committed_cnki_queue_contract(self):
        queue = MODULE.load_fallback_queue()
        self.assertEqual(6, len(queue))
        self.assertEqual(6, len({row["candidate"]["id"] for row in queue}))
        for row in queue:
            selected = MODULE.select_fallback_candidate([row], set(), set())
            self.assertGreaterEqual(selected["selectionScore"]["total"], 65)
            self.assertGreater(len(selected["evidenceText"]), 300)
            self.assertTrue(selected["sourceUrl"].startswith("https://"))


if __name__ == "__main__":
    unittest.main()




