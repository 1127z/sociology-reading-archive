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
MAX_EVIDENCE_CHARS = 60000


def request_json(url: str, *, headers: dict[str, str] | None = None, body: dict | None = None) -> dict:
    payload = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    req = urllib.request.Request(url, data=payload, headers={"User-Agent": "sociology-reading-archive/1.0", **(headers or {})})
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.load(response)


def request_text(url: str) -> tuple[str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "sociology-reading-archive/1.0"})
    with urllib.request.urlopen(req, timeout=45) as response:
        content_type = response.headers.get_content_type()
        if content_type not in {"text/html", "text/plain", "application/xhtml+xml"}:
            return "", content_type
        text = response.read(2_000_000).decode(response.headers.get_content_charset() or "utf-8", errors="replace")
        text = re.sub(r"<(script|style|nav|header|footer)[^>]*>.*?</\1>", " ", text, flags=re.I | re.S)
        text = html.unescape(re.sub(r"<[^>]+>", " ", text))
        text = re.sub(r"\s+", " ", text).strip()
        return text[:MAX_EVIDENCE_CHARS], content_type


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
        "select": "id,doi,title,publication_date,authorships,primary_location,best_oa_location,open_access,abstract_inverted_index,cited_by_count,type",
    })
    payload = request_json(f"https://api.openalex.org/works?{params}")
    result = []
    for work in payload.get("results", []):
        location = work.get("primary_location") or {}
        source = location.get("source") or {}
        oa_location = work.get("best_oa_location") or {}
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
            "fullTextUrl": oa_location.get("landing_page_url") or "",
            "pdfUrl": oa_location.get("pdf_url") or "",
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


def add_evidence(candidate: dict) -> dict:
    enriched = dict(candidate)
    full_text = ""
    source = candidate.get("fullTextUrl", "")
    if source:
        try:
            full_text, _ = request_text(source)
        except Exception as error:
            print(f"Full-text HTML unavailable: {type(error).__name__}")
    if len(full_text) >= 5000:
        enriched.update({"evidenceBasis": "全文", "analysisDepth": "专家精读", "fullTextSource": source, "evidenceText": full_text, "confidence": "高"})
    else:
        enriched.update({"evidenceBasis": "摘要", "analysisDepth": "摘要解读", "fullTextSource": candidate.get("pdfUrl") or source or "未获得合法可解析全文", "evidenceText": candidate.get("abstract", ""), "confidence": "中"})
    return enriched


def deepseek_json(api_key: str, system: str, prompt: str) -> dict:
    body = {"model": "deepseek-chat", "temperature": 0.15, "response_format": {"type": "json_object"}, "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}
    payload = request_json(DEEPSEEK_URL, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, body=body)
    return json.loads(payload["choices"][0]["message"]["content"])


def deepseek_summary(candidate: dict, api_key: str) -> dict:
    evidence = {k: v for k, v in candidate.items() if k != "abstract"}
    evidence["evidenceText"] = candidate["evidenceText"]
    expert_schema = {"fieldPosition": "领域定位", "literatureDialogue": ["文献对话"], "contentFeatures": [{"label": "内容特色", "detail": "分析"}], "theoreticalContribution": "理论贡献", "empiricalContribution": "经验贡献", "researchImplications": ["后续研究启发"]}
    reviewer_schema = {"method": "质性研究|定量研究|综述|混合研究", "methods": ["研究设计与数据"], "researchFeatures": [{"label": "研究特色", "detail": "分析"}], "criticalReview": ["批判性评价"], "methodologicalContribution": "方法贡献", "limits": ["局限"], "evidenceBoundaries": ["当前材料不能证明什么"]}
    common = "只能依据给定证据。若分析依据为摘要，禁止虚构样本量、变量、章节、引文、统计结果或全文论证；信息不足必须写‘当前证据未说明’。"
    expert = deepseek_json(api_key, "你是该研究领域的资深社会学专家。" + common, "输出纯JSON并匹配模板：" + json.dumps(expert_schema, ensure_ascii=False) + "\n证据：" + json.dumps(evidence, ensure_ascii=False))
    reviewer = deepseek_json(api_key, "你是严格的社会科学方法审稿人。" + common, "输出纯JSON并匹配模板：" + json.dumps(reviewer_schema, ensure_ascii=False) + "\n证据：" + json.dumps(evidence, ensure_ascii=False))
    schema = {"title": "中文标题", "topics": ["主题"], "recommendation": "专家推荐理由", "question": "研究问题", "selectionSource": "选题如何形成", "articleStructure": ["可由当前证据确认的结构；不确定则说明"], "thesis": "核心论点", "theory": [{"name": "概念或理论", "detail": "定义、关系与机制"}], "chain": [{"label": "论证步骤", "detail": "证据如何支持命题"}], "findings": ["区分直接发现、解释与外推"], "highlights": [{"label": "亮点", "detail": "说明"}], "questions": ["研究者思考题"], "terms": [{"term": "术语", "definition": "定义"}]}
    synthesis_prompt = "你是社会学精读主编。整合证据、领域专家意见和方法审稿意见，输出纯JSON并严格匹配模板。不得新增证据中没有的事实。\n模板：" + json.dumps(schema, ensure_ascii=False) + "\n证据：" + json.dumps(evidence, ensure_ascii=False) + "\n领域专家：" + json.dumps(expert, ensure_ascii=False) + "\n方法审稿：" + json.dumps(reviewer, ensure_ascii=False)
    synthesis = deepseek_json(api_key, "建立可追溯的论断—证据链，明确事实、解释、外推和未知。", synthesis_prompt)
    synthesis["selectionSource"] = selection_source(candidate)
    return {**synthesis, **expert, **reviewer, "evidenceBasis": candidate["evidenceBasis"], "analysisDepth": candidate["analysisDepth"], "fullTextSource": candidate["fullTextSource"], "confidence": candidate["confidence"]}


def selection_source(candidate: dict) -> str:
    return f"由自动检索流程从近期公开元数据中筛选；来源为{candidate.get('provider', '公开数据库')}，满足社会学主题、文章类型、摘要完整性与去重规则。"


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:72]
    return slug or f"sociology-reading-{dt.date.today().isoformat()}"


def build_article(candidate: dict, summary: dict, issue: int) -> dict:
    slug = slugify(candidate["title"])
    today = dt.date.today().isoformat()
    return {"slug": slug, "date": today, "issue": f"第 {issue:02d} 期", "title": summary["title"], "titleEn": candidate["title"], "authors": " · ".join(candidate["authors"]), "journal": candidate["journal"], "year": int((candidate.get("date") or today)[:4]), "volume": candidate.get("volume") or "在线发表", "pages": candidate.get("pages") or "在线发表", "doi": candidate.get("doi") or "暂无 DOI", "sourceUrl": candidate["sourceUrl"], "documentUrl": f"/documents/{today}-{slug}.md", "language": "英文", **summary}


def validate_expert_summary(summary: dict) -> None:
    required = {"title", "method", "fieldPosition", "literatureDialogue", "contentFeatures", "researchFeatures", "criticalReview", "researchImplications", "evidenceBoundaries", "evidenceBasis", "analysisDepth", "fullTextSource", "confidence"}
    missing = required - summary.keys()
    if missing:
        raise ValueError(f"Expert analysis missing fields: {sorted(missing)}")
    if summary["evidenceBasis"] == "摘要" and summary["analysisDepth"] != "摘要解读":
        raise ValueError("Abstract-only evidence must be labeled 摘要解读")


def markdown(article: dict) -> str:
    lines = [f"# {article['title']}", "", f"**原题：** {article['titleEn']}", f"**作者：** {article['authors']}", f"**来源：** {article['journal']} ({article['year']})", f"**DOI：** {article['doi']}", f"**官方原文：** {article['sourceUrl']}", f"**分析依据：** {article['evidenceBasis']}", f"**分析深度：** {article['analysisDepth']}", f"**全文来源：** {article['fullTextSource']}", f"**证据置信度：** {article['confidence']}", "", "> 本精读由 AI 作为研究助理生成。所有判断受可获得证据约束，不能替代研究者阅读全文与核查。", ""]
    sections = [("领域定位", article["fieldPosition"]), ("研究问题", article["question"]), ("选题来源", article["selectionSource"]), ("文献对话", article["literatureDialogue"]), ("文章结构", article["articleStructure"]), ("理论框架", article["theory"]), ("数据与方法", article["methods"]), ("分析思路", article["chain"]), ("主要结论", article["findings"]), ("经验贡献", article["empiricalContribution"]), ("理论贡献", article["theoreticalContribution"]), ("方法贡献", article["methodologicalContribution"]), ("内容特色", article["contentFeatures"]), ("研究特色", article["researchFeatures"]), ("批判性评价", article["criticalReview"]), ("证据边界", article["evidenceBoundaries"]), ("研究启发", article["researchImplications"]), ("思考题", article["questions"])]
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
    candidate = add_evidence(candidate)
    summary = deepseek_summary(candidate, api_key)
    validate_expert_summary(summary)
    article = build_article(candidate, summary, len(generated) + 3)
    generated.insert(0, article)
    DATA_FILE.write_text(json.dumps(generated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    DOCUMENT_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT / "public" / article["documentUrl"].lstrip("/")).write_text(markdown(article), encoding="utf-8")
    print(f"Added: {article['slug']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


