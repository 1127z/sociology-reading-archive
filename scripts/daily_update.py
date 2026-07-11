#!/usr/bin/env python3
"""Retrieve, deduplicate, summarize, and publish one sociology reading.

Designed for both the daily schedule and script-change CI checks.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "articles.generated.json"
SEED_FILE = ROOT / "app" / "data.ts"
DOCUMENT_DIR = ROOT / "public" / "documents"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"


def request_json(url: str, *, headers: dict[str, str] | None = None, body: dict | None = None) -> dict:
    payload = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    req = urllib.request.Request(url, data=payload, headers={"User-Agent": "sociology-reading-archive/1.0", **(headers or {})})
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.load(response)


def normalize_title(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", html.unescape(value).lower())


def existing_keys() -> tuple[set[str], set[str]]:
    generated = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    seed = SEED_FILE.read_text(encoding="utf-8")
    dois = {str(item.get("doi", "")).lower() for item in generated if item.get("doi")}
    dois.update(match.lower() for match in re.findall(r'doi:\s*"([^"]+)"', seed) if "暂无" not in match)
    titles = {normalize_title(str(item.get("titleEn") or item.get("title", ""))) for item in generated}
    titles.update(normalize_title(match) for match in re.findall(r'titleEn:\s*"([^"]+)"', seed))
    return dois, titles


def abstract_from_inverted(index: dict[str, list[int]] | None) -> str:
    if not index:
        return ""
    positioned = sorted((position, word) for word, positions in index.items() for position in positions)
    return " ".join(word for _, word in positioned)


def openalex_candidates(days: int = 21) -> list[dict]:
    since = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    params = urllib.parse.urlencode({
        "filter": f"from_publication_date:{since},concepts.id:C144024400,type:article|review",
        "sort": "cited_by_count:desc",
        "per-page": 25,
        "select": "id,doi,title,publication_date,authorships,primary_location,open_access,abstract_inverted_index,cited_by_count,type",
    })
    payload = request_json(f"https://api.openalex.org/works?{params}")
    result = []
    for work in payload.get("results", []):
        location = work.get("primary_location") or {}
        source = location.get("source") or {}
        abstract = abstract_from_inverted(work.get("abstract_inverted_index"))
        relevance_text = f"{work.get('title', '')} {source.get('display_name', '')} {abstract}".lower()
        relevance_terms = ("sociolog", "social stratification", "social inequality", "social movement", "social class", "social network", "social institution", "ethnograph", "race and ethnicity", "gender inequality")
        if len(abstract) < 300 or not any(term in relevance_text for term in relevance_terms):
            continue
        result.append({
            "provider": "OpenAlex",
            "title": work.get("title", ""),
            "doi": (work.get("doi") or "").removeprefix("https://doi.org/"),
            "date": work.get("publication_date", ""),
            "authors": [a.get("author", {}).get("display_name", "") for a in work.get("authorships", [])],
            "journal": source.get("display_name") or "OpenAlex indexed work",
            "volume": "",
            "pages": "",
            "sourceUrl": (work.get("doi") or location.get("landing_page_url") or work.get("id")),
            "abstract": abstract,
            "citations": work.get("cited_by_count", 0),
            "type": work.get("type", "article"),
        })
    return result


def crossref_candidates(days: int = 21) -> list[dict]:
    since = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    params = urllib.parse.urlencode({"query": "sociology", "filter": f"from-pub-date:{since},type:journal-article", "sort": "is-referenced-by-count", "order": "desc", "rows": 20, "select": "DOI,title,author,container-title,published,URL,abstract,volume,page,is-referenced-by-count"})
    items = request_json(f"https://api.crossref.org/works?{params}").get("message", {}).get("items", [])
    result = []
    for item in items:
        abstract = re.sub(r"<[^>]+>", " ", item.get("abstract", ""))
        if len(abstract) < 300:
            continue
        parts = item.get("published", {}).get("date-parts", [[]])[0]
        date = "-".join(str(x).zfill(2) for x in parts) if parts else ""
        result.append({"provider": "Crossref", "title": (item.get("title") or [""])[0], "doi": item.get("DOI", ""), "date": date, "authors": [" ".join(filter(None, [a.get("given"), a.get("family")])) for a in item.get("author", [])], "journal": (item.get("container-title") or ["Crossref indexed work"])[0], "volume": item.get("volume", ""), "pages": item.get("page", ""), "sourceUrl": item.get("URL", ""), "abstract": html.unescape(abstract), "citations": item.get("is-referenced-by-count", 0), "type": "article"})
    return result


def choose_candidate(candidates: list[dict], dois: set[str], titles: set[str]) -> dict | None:
    fresh = [c for c in candidates if c.get("title") and c.get("doi", "").lower() not in dois and normalize_title(c["title"]) not in titles]
    fresh.sort(key=lambda c: (c.get("citations", 0), len(c.get("abstract", ""))), reverse=True)
    return fresh[0] if fresh else None


def deepseek_summary(candidate: dict, api_key: str) -> dict:
    schema = {"title": "中文标题", "method": "质性研究|定量研究|综述|混合研究", "topics": ["主题"], "recommendation": "推荐理由", "question": "研究问题", "selectionSource": "选题来源", "articleStructure": ["文章结构"], "thesis": "核心论点", "theory": [{"name": "理论", "detail": "说明"}], "methods": ["数据与方法"], "chain": [{"label": "步骤", "detail": "分析思路"}], "findings": ["结论"], "highlights": [{"label": "亮点", "detail": "说明"}], "limits": ["局限"], "questions": ["思考题"], "terms": [{"term": "术语", "definition": "定义"}]}
    prompt = "你是严谨的社会学文献编辑。只能依据给定元数据和摘要，不得声称读过未提供的全文；信息不足时明确写‘摘要未说明’。输出纯 JSON，字段完全匹配模板。\n模板：" + json.dumps(schema, ensure_ascii=False) + "\n文献：" + json.dumps(candidate, ensure_ascii=False)
    body = {"model": "deepseek-chat", "temperature": 0.2, "response_format": {"type": "json_object"}, "messages": [{"role": "system", "content": "输出可核验、克制、中文的社会学精读。"}, {"role": "user", "content": prompt}]}
    payload = request_json(DEEPSEEK_URL, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, body=body)
    return json.loads(payload["choices"][0]["message"]["content"])


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:72]
    return slug or f"sociology-reading-{dt.date.today().isoformat()}"


def build_article(candidate: dict, summary: dict, issue: int) -> dict:
    slug = slugify(candidate["title"])
    today = dt.date.today().isoformat()
    return {"slug": slug, "date": today, "issue": f"第 {issue:02d} 期", "title": summary["title"], "titleEn": candidate["title"], "authors": " · ".join(candidate["authors"]), "journal": candidate["journal"], "year": int((candidate.get("date") or today)[:4]), "volume": candidate.get("volume") or "在线发表", "pages": candidate.get("pages") or "在线发表", "doi": candidate.get("doi") or "暂无 DOI", "sourceUrl": candidate["sourceUrl"], "documentUrl": f"/documents/{today}-{slug}.md", "language": "英文", **summary}


def markdown(article: dict) -> str:
    lines = [f"# {article['title']}", "", f"**原题：** {article['titleEn']}", f"**作者：** {article['authors']}", f"**来源：** {article['journal']} ({article['year']})", f"**DOI：** {article['doi']}", f"**官方原文：** {article['sourceUrl']}", "", "> 本精读由公开元数据与摘要辅助生成，不能替代阅读全文。", ""]
    sections = [("研究问题", article["question"]), ("选题来源", article["selectionSource"]), ("文章结构", article["articleStructure"]), ("理论框架", article["theory"]), ("数据与方法", article["methods"]), ("分析思路", article["chain"]), ("主要结论", article["findings"]), ("亮点", article["highlights"]), ("局限", article["limits"]), ("思考题", article["questions"])]
    for heading, value in sections:
        lines += [f"## {heading}", ""]
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    label = item.get("name") or item.get("label") or ""
                    detail = item.get("detail") or ""
                    lines.append(f"- **{label}：** {detail}")
                else:
                    lines.append(f"- {item}")
        else:
            lines.append(str(value))
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--candidate-file", type=Path)
    args = parser.parse_args()
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key and not args.dry_run:
        print("DEEPSEEK_API_KEY is required", file=sys.stderr)
        return 2
    dois, titles = existing_keys()
    candidates = json.loads(args.candidate_file.read_text(encoding="utf-8")) if args.candidate_file else openalex_candidates() + crossref_candidates()
    candidate = choose_candidate(candidates, dois, titles)
    if not candidate:
        print("No eligible new article found")
        return 0
    print(f"Selected: {candidate['title']} ({candidate['provider']})")
    if args.dry_run:
        return 0
    generated = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    summary = deepseek_summary(candidate, api_key)
    article = build_article(candidate, summary, len(generated) + 3)
    generated.insert(0, article)
    DATA_FILE.write_text(json.dumps(generated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    DOCUMENT_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT / "public" / article["documentUrl"].lstrip("/")).write_text(markdown(article), encoding="utf-8")
    print(f"Added: {article['slug']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

