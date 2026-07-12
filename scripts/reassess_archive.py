#!/usr/bin/env python3
"""Reassess every legacy entry and atomically replace the public archive."""

from __future__ import annotations

import csv
import json
import os
import re
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

import daily_update as daily

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "data" / "archive_inventory.json"
AUDIT_JSON = ROOT / "data" / "archive_reassessment.json"
AUDIT_CSV = ROOT / "data" / "archive_reassessment.csv"


def openalex_candidate(item: dict) -> dict:
    if item.get("doi"):
        work = daily.request_json("https://api.openalex.org/works/" + urllib.parse.quote("https://doi.org/" + item["doi"], safe=""))
    else:
        params = urllib.parse.urlencode({"search": item["title"], "per-page": 5})
        results = daily.request_json(f"https://api.openalex.org/works?{params}").get("results", [])
        work = next((row for row in results if daily.normalize_title(row.get("title", "")) == daily.normalize_title(item["title"])), {})
    if not work:
        raise ValueError("metadata_not_found")
    location = work.get("primary_location") or {}
    source = location.get("source") or {}
    oa = work.get("best_oa_location") or {}
    return {
        "provider": "OpenAlex", "title": work.get("title", item["title"]),
        "doi": (work.get("doi") or "").removeprefix("https://doi.org/"),
        "date": work.get("publication_date", ""),
        "authors": [row.get("author", {}).get("display_name", "") for row in work.get("authorships", [])],
        "journal": source.get("display_name") or "OpenAlex indexed work",
        "volume": work.get("biblio", {}).get("volume") or "", "pages": "",
        "sourceUrl": work.get("doi") or location.get("landing_page_url") or item["sourceUrl"],
        "abstract": daily.abstract_from_inverted(work.get("abstract_inverted_index")),
        "citations": work.get("cited_by_count", 0), "type": work.get("type", "article"),
        "fullTextUrl": oa.get("landing_page_url") or "", "pdfUrl": oa.get("pdf_url") or "",
        "isOpenAccess": bool((work.get("open_access") or {}).get("is_oa")),
    }


def arxiv_candidate(item: dict) -> dict:
    arxiv_id = item["arxivId"]
    req = daily.urllib.request.Request(f"https://export.arxiv.org/api/query?id_list={arxiv_id}", headers={"User-Agent": "sociology-reading-archive/1.0"})
    with daily.urllib.request.urlopen(req, timeout=45) as response:
        root = ET.fromstring(response.read())
    ns = {"a": "http://www.w3.org/2005/Atom"}
    entry = root.find("a:entry", ns)
    if entry is None:
        raise ValueError("metadata_not_found")
    value = lambda name: re.sub(r"\s+", " ", entry.findtext(f"a:{name}", default="", namespaces=ns)).strip()
    return {
        "provider": "arXiv", "title": value("title"), "doi": "", "date": value("published")[:10],
        "authors": [value_node.findtext("a:name", default="", namespaces=ns) for value_node in entry.findall("a:author", ns)],
        "journal": "arXiv preprint", "volume": f"arXiv:{arxiv_id}", "pages": "预印本",
        "sourceUrl": f"https://arxiv.org/abs/{arxiv_id}", "abstract": value("summary"),
        "citations": 0, "type": "review", "fullTextUrl": "", "pdfUrl": f"https://arxiv.org/pdf/{arxiv_id}", "isOpenAccess": True,
    }


def candidate_for(item: dict) -> dict:
    return arxiv_candidate(item) if item.get("arxivId") else openalex_candidate(item)


def clear_seed_articles() -> None:
    text = daily.SEED_FILE.read_text(encoding="utf-8")
    start = text.index("export const articles: Article[] = [")
    end = text.index("export const getArticle", start)
    daily.SEED_FILE.write_text(text[:start] + "export const articles: Article[] = [];\n\n" + text[end:], encoding="utf-8")


def write_audit(rows: list[dict]) -> None:
    payload = {"standardVersion": daily.load_selection_config()["version"], "runDate": daily.today_taipei().isoformat(), "total": len(rows), "retained": sum(r["status"] == "retained" for r in rows), "deleted": sum(r["status"] == "deleted" for r in rows), "items": rows}
    AUDIT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with AUDIT_CSV.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["title", "doi", "status", "reason", "score", "difficulty", "evidenceBasis", "fullTextSource"])
        writer.writeheader(); writer.writerows({key: row.get(key, "") for key in writer.fieldnames} for row in rows)


def main() -> int:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise SystemExit("DEEPSEEK_API_KEY is required")
    config = daily.load_selection_config()
    items = json.loads(INVENTORY.read_text(encoding="utf-8"))
    retained, audit = [], []
    for item in items:
        row = {"title": item["title"], "doi": item.get("doi", ""), "status": "deleted", "reason": "", "score": "", "difficulty": "", "evidenceBasis": "", "fullTextSource": ""}
        try:
            candidate = candidate_for(item)
            reason = daily.hard_filter_reason(candidate, config, set(), set())
            score = daily.score_candidate(candidate, config)
            row.update({"score": score["total"], "difficulty": score["difficulty"]})
            if reason:
                row["reason"] = reason
            elif score["total"] < config["retrieval"]["min_selection_score"]:
                row["reason"] = "score_below_threshold"
            else:
                candidate["selectionScore"] = score
                candidate = daily.add_evidence(candidate)
                row.update({"evidenceBasis": candidate["evidenceBasis"], "fullTextSource": candidate["fullTextSource"]})
                if candidate["evidenceBasis"] != "全文":
                    row["reason"] = "full_text_not_parsed"
                else:
                    candidate["learningFocus"] = "领域导论与知识复盘"
                    summary = daily.deepseek_summary(candidate, api_key)
                    daily.validate_expert_summary(summary)
                    article = daily.build_article(candidate, summary, len(retained) + 1)
                    article["date"] = item["date"]
                    article["issue"] = f"第 {len(retained) + 1:02d} 期"
                    article["documentUrl"] = f"/documents/{item['date']}-{article['slug']}.md"
                    retained.append(article)
                    row.update({"status": "retained", "reason": "meets_current_standard"})
        except Exception as error:
            row["reason"] = f"assessment_error:{type(error).__name__}:{error}"
        audit.append(row)
        print(f"{row['status']}: {row['title']} ({row['reason']})")

    # Replace public state only after every item has received an audit result.
    clear_seed_articles()
    daily.DATA_FILE.write_text(json.dumps(list(reversed(retained)), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for path in daily.DOCUMENT_DIR.iterdir():
        if path.is_file():
            path.unlink()
    for article in retained:
        (ROOT / "public" / article["documentUrl"].lstrip("/")).write_text(daily.markdown(article), encoding="utf-8")
    write_audit(audit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
