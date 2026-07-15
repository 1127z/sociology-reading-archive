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
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "articles.generated.json"
FALLBACK_QUEUE_FILE = ROOT / "data" / "cnki_fallback_queue.json"
SEED_FILE = ROOT / "app" / "data.ts"
DOCUMENT_DIR = ROOT / "public" / "documents"
SELECTION_CONFIG_FILE = ROOT / "config" / "reading_selection.json"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
MAX_EVIDENCE_CHARS = 60000
API_TIMEOUT_SECONDS = 45
HTML_TIMEOUT_SECONDS = 15
PDF_TIMEOUT_SECONDS = 20
TAIPEI_TZ = dt.timezone(dt.timedelta(hours=8))


def load_selection_config() -> dict:
    return json.loads(SELECTION_CONFIG_FILE.read_text(encoding="utf-8"))


def today_taipei() -> dt.date:
    return dt.datetime.now(TAIPEI_TZ).date()


def request_json(url: str, *, headers: dict[str, str] | None = None, body: dict | None = None) -> dict:
    payload = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    req = urllib.request.Request(url, data=payload, headers={"User-Agent": "sociology-reading-archive/1.0", **(headers or {})})
    with urllib.request.urlopen(req, timeout=API_TIMEOUT_SECONDS) as response:
        return json.load(response)


def request_text(url: str) -> tuple[str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "sociology-reading-archive/1.0"})
    with urllib.request.urlopen(req, timeout=HTML_TIMEOUT_SECONDS) as response:
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


def openalex_candidates(days: int | None = None) -> list[dict]:
    config = load_selection_config()
    days = days or config["retrieval"]["days"]
    since = (today_taipei() - dt.timedelta(days=days)).isoformat()
    params = urllib.parse.urlencode({
        "filter": f"from_publication_date:{since},concepts.id:C144024400,type:article|review",
        "sort": "cited_by_count:desc",
        "per-page": config["retrieval"]["openalex_rows"],
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
        relevance_terms = config["social_relevance_terms"]
        if len(abstract) < config["retrieval"]["min_abstract_chars"] or not any(term in relevance_text for term in relevance_terms):
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
            "isOpenAccess": bool((work.get("open_access") or {}).get("is_oa")),
        })
    return result


def crossref_candidates(days: int | None = None) -> list[dict]:
    config = load_selection_config()
    days = days or config["retrieval"]["days"]
    since = (today_taipei() - dt.timedelta(days=days)).isoformat()
    params = urllib.parse.urlencode({"query": "sociology", "filter": f"from-pub-date:{since},type:journal-article", "sort": "is-referenced-by-count", "order": "desc", "rows": config["retrieval"]["crossref_rows"], "select": "DOI,title,author,container-title,published,URL,abstract,volume,page,is-referenced-by-count,publisher,license,link"})
    items = request_json(f"https://api.crossref.org/works?{params}").get("message", {}).get("items", [])
    result = []
    for item in items:
        abstract = re.sub(r"<[^>]+>", " ", item.get("abstract", ""))
        relevance_text = f"{(item.get('title') or [''])[0]} {abstract}".lower()
        if len(abstract) < config["retrieval"]["min_abstract_chars"] or not any(term in relevance_text for term in config["social_relevance_terms"]):
            continue
        parts = item.get("published", {}).get("date-parts", [[]])[0]
        date = "-".join(str(x).zfill(2) for x in parts) if parts else ""
        licenses = [entry.get("URL", "") for entry in item.get("license", [])]
        has_open_license = any("creativecommons.org" in url.lower() for url in licenses)
        pdf_url = next((entry.get("URL", "") for entry in item.get("link", []) if entry.get("content-type") == "application/pdf"), "") if has_open_license else ""
        result.append({"provider": "Crossref", "title": (item.get("title") or [""])[0], "doi": item.get("DOI", ""), "date": date, "authors": [" ".join(filter(None, [a.get("given"), a.get("family")])) for a in item.get("author", [])], "journal": (item.get("container-title") or ["Crossref indexed work"])[0], "publisher": item.get("publisher", ""), "volume": item.get("volume", ""), "pages": item.get("page", ""), "sourceUrl": item.get("URL", ""), "abstract": html.unescape(abstract), "citations": item.get("is-referenced-by-count", 0), "type": "article", "fullTextUrl": "", "pdfUrl": pdf_url, "isOpenAccess": bool(pdf_url)})
    return result


def public_candidates() -> list[dict]:
    candidates = []
    for name, loader in (("OpenAlex", openalex_candidates), ("Crossref", crossref_candidates)):
        try:
            candidates.extend(loader())
        except Exception as error:
            print(f"::warning::{name} retrieval unavailable: {type(error).__name__}")
    return candidates


def contains_any(text: str, terms: list[str]) -> int:
    lowered = text.lower()
    return sum(1 for term in terms if term.lower() in lowered)


def hard_filter_reason(candidate: dict, config: dict, dois: set[str], titles: set[str]) -> str | None:
    title = candidate.get("title", "")
    abstract = candidate.get("abstract", "")
    if not title:
        return "missing_title"
    if candidate.get("doi", "").lower() in dois or normalize_title(title) in titles:
        return "duplicate"
    if candidate.get("type") not in {"article", "review"}:
        return "unsupported_type"
    if len(abstract) < config["retrieval"]["min_abstract_chars"]:
        return "short_abstract"
    if contains_any(title, config["excluded_title_terms"]):
        return "excluded_document_type"
    evidence_text = f"{title} {abstract}"
    if not contains_any(evidence_text, config["social_relevance_terms"]):
        return "weak_sociology_relevance"
    if not candidate.get("journal") or candidate.get("journal") in {"OpenAlex indexed work", "Crossref indexed work"}:
        return "unknown_venue"
    if not candidate.get("fullTextUrl") and not candidate.get("pdfUrl"):
        return "no_authorized_full_text"
    return None


def score_candidate(candidate: dict, config: dict | None = None) -> dict:
    config = config or load_selection_config()
    text = f"{candidate.get('title', '')} {candidate.get('abstract', '')}".lower()
    abstract_length = len(candidate.get("abstract", ""))
    teaching_hits = contains_any(text, config["teaching_terms"])
    method_hits = contains_any(text, config["method_terms"])
    relevance_hits = contains_any(text, config["social_relevance_terms"])
    advanced_hits = contains_any(text, config["advanced_terms"])
    focus_hits = contains_any(text, config["focus_terms"][today_taipei().strftime("%A")])

    teaching_value = min(25, 8 + teaching_hits * 2 + (5 if method_hits else 0))
    professional_importance = min(20, 5 + relevance_hits * 2 + focus_hits * 3 + (2 if candidate.get("doi") else 0))
    readability = 15 if 700 <= abstract_length <= 2200 else 12 if 500 <= abstract_length <= 3200 else 8
    readability = max(5, readability - min(5, advanced_hits * 2))
    research_training = min(15, 4 + method_hits * 3 + (3 if "mechanism" in text or "theory" in text else 0))
    journal = candidate.get("journal", "").lower()
    priority = any(name.lower() == journal for name in config["priority_journals"])
    source_quality = 15 if priority else 10 if candidate.get("doi") and candidate.get("journal") else 6
    full_text_availability = 10 if candidate.get("fullTextUrl") or candidate.get("pdfUrl") else 0
    breakdown = {
        "teaching_value": teaching_value,
        "professional_importance": professional_importance,
        "readability": readability,
        "research_training": research_training,
        "source_quality": source_quality,
        "full_text_availability": full_text_availability,
    }
    if advanced_hits >= 3:
        difficulty = "L3"
    elif readability >= 13 and method_hits <= 2:
        difficulty = "L1"
    else:
        difficulty = "L2"
    return {"total": sum(breakdown.values()), "breakdown": breakdown, "difficulty": difficulty}


def rank_candidates(candidates: list[dict], dois: set[str], titles: set[str], config: dict | None = None) -> list[dict]:
    config = config or load_selection_config()
    ranked = []
    for candidate in candidates:
        reason = hard_filter_reason(candidate, config, dois, titles)
        if reason:
            continue
        scored = dict(candidate)
        scored.update({"selectionScore": score_candidate(candidate, config)})
        if scored["selectionScore"]["total"] < config["retrieval"]["min_selection_score"]:
            continue
        ranked.append(scored)
    preferred = set(config["preferred_difficulty"])
    ranked.sort(key=lambda item: (item["selectionScore"]["difficulty"] in preferred, item["selectionScore"]["total"], item.get("citations", 0)), reverse=True)
    return ranked


def choose_candidate(candidates: list[dict], dois: set[str], titles: set[str]) -> dict | None:
    ranked = rank_candidates(candidates, dois, titles)
    return ranked[0] if ranked else None


def safe_oa_hostname(url: str) -> bool:
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    prohibited = ("sci-hub", "libgen", "z-lib", "zlibrary")
    return bool(host) and not any(term in host for term in prohibited)


def extract_pdf_text(url: str) -> str:
    if not safe_oa_hostname(url):
        return ""
    req = urllib.request.Request(url, headers={"User-Agent": "sociology-reading-archive/1.0"})
    with urllib.request.urlopen(req, timeout=PDF_TIMEOUT_SECONDS) as response:
        data = response.read(20_000_000)
        if not (data.startswith(b"%PDF") or response.headers.get_content_type() == "application/pdf"):
            return ""
    reader = PdfReader(BytesIO(data))
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
        if sum(map(len, parts)) >= MAX_EVIDENCE_CHARS:
            break
    return re.sub(r"\s+", " ", " ".join(parts)).strip()[:MAX_EVIDENCE_CHARS]


def add_evidence(candidate: dict) -> dict:
    enriched = dict(candidate)
    full_text = ""
    source = candidate.get("fullTextUrl", "")
    if source:
        try:
            full_text, _ = request_text(source)
        except Exception as error:
            print(f"Full-text HTML unavailable: {type(error).__name__}")
    if len(full_text) < load_selection_config()["retrieval"]["min_full_text_chars"] and candidate.get("pdfUrl"):
        try:
            full_text = extract_pdf_text(candidate["pdfUrl"])
            source = candidate["pdfUrl"]
        except Exception as error:
            print(f"Full-text PDF unavailable: {type(error).__name__}")
    if len(full_text) >= load_selection_config()["retrieval"]["min_full_text_chars"]:
        enriched.update({"evidenceBasis": "全文", "analysisDepth": "专家精读", "fullTextSource": source, "evidenceText": full_text, "confidence": "高"})
    else:
        enriched.update({"evidenceBasis": "摘要", "analysisDepth": "摘要解读", "fullTextSource": candidate.get("pdfUrl") or source or "未获得合法可解析全文", "evidenceText": candidate.get("abstract", ""), "confidence": "中"})
    return enriched


def select_reading_candidate(candidates: list[dict], dois: set[str], titles: set[str]) -> dict | None:
    config = load_selection_config()
    ranked = rank_candidates(candidates, dois, titles, config)
    attempt_limit = min(config["retrieval"]["shortlist_size"], config["retrieval"].get("max_full_text_attempts", 3))
    for candidate in ranked[:attempt_limit]:
        enriched = add_evidence(candidate)
        if enriched["evidenceBasis"] == "全文" or not config["retrieval"]["require_parsed_full_text"]:
            enriched["learningFocus"] = config["weekly_focus"][today_taipei().strftime("%A")]
            return enriched
    return None


def load_fallback_queue() -> list[dict]:
    if not FALLBACK_QUEUE_FILE.exists():
        return []
    queue = json.loads(FALLBACK_QUEUE_FILE.read_text(encoding="utf-8"))
    if not isinstance(queue, list):
        raise ValueError("CNKI fallback queue must be a JSON array")
    return queue


def select_fallback_candidate(queue: list[dict], dois: set[str], titles: set[str]) -> dict | None:
    for entry in queue:
        candidate = entry.get("candidate", {})
        doi = str(candidate.get("doi", "")).lower()
        if (doi and doi in dois) or normalize_title(candidate.get("title", "")) in titles:
            continue
        required = {"id", "title", "authors", "journal", "date", "sourceUrl", "evidenceText", "selectionScore"}
        missing = required - candidate.keys()
        if missing:
            raise ValueError(f"Fallback candidate missing fields: {sorted(missing)}")
        selected = dict(candidate)
        selected.update({
            "provider": "知网人工全文库",
            "evidenceBasis": "全文",
            "analysisDepth": "专家精读",
            "fullTextSource": "用户授权获取的知网全文（仅本地核验，不公开存储）",
            "confidence": "高",
            "learningFocus": load_selection_config()["weekly_focus"][today_taipei().strftime("%A")],
        })
        return selected
    return None


def remove_fallback_candidate(queue: list[dict], candidate_id: str) -> list[dict]:
    return [entry for entry in queue if entry.get("candidate", {}).get("id") != candidate_id]


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
    expert_args = (api_key, "你是该研究领域的资深社会学专家。" + common, "输出纯JSON并匹配模板：" + json.dumps(expert_schema, ensure_ascii=False) + "\n证据：" + json.dumps(evidence, ensure_ascii=False))
    reviewer_args = (api_key, "你是严格的社会科学方法审稿人。" + common, "输出纯JSON并匹配模板：" + json.dumps(reviewer_schema, ensure_ascii=False) + "\n证据：" + json.dumps(evidence, ensure_ascii=False))
    with ThreadPoolExecutor(max_workers=2) as executor:
        expert_future = executor.submit(deepseek_json, *expert_args)
        reviewer_future = executor.submit(deepseek_json, *reviewer_args)
        expert = expert_future.result()
        reviewer = reviewer_future.result()
    schema = {"title": "中文标题", "topics": ["主题"], "recommendation": "面向社会学本科生的推荐理由", "question": "研究问题", "selectionSource": "选题如何形成", "articleStructure": ["由全文确认的文章结构"], "thesis": "核心论点", "theory": [{"name": "概念或理论", "detail": "定义、关系与机制"}], "chain": [{"label": "论证步骤", "detail": "证据如何支持命题"}], "findings": ["区分直接发现、解释与外推"], "highlights": [{"label": "亮点", "detail": "说明"}], "prerequisiteKnowledge": ["阅读前应了解的概念"], "readingGuide": {"quickRead": "30分钟快速阅读路线", "closeRead": "必须精读的部分", "canSkim": "可暂时略读的部分"}, "learningExercises": ["复述、论证图、证据判断或迁移练习"], "questions": ["研究者思考题"], "terms": [{"term": "术语", "definition": "定义"}]}
    synthesis_prompt = "你是社会学精读主编。整合证据、领域专家意见和方法审稿意见，输出纯JSON并严格匹配模板。不得新增证据中没有的事实。\n模板：" + json.dumps(schema, ensure_ascii=False) + "\n证据：" + json.dumps(evidence, ensure_ascii=False) + "\n领域专家：" + json.dumps(expert, ensure_ascii=False) + "\n方法审稿：" + json.dumps(reviewer, ensure_ascii=False)
    synthesis = deepseek_json(api_key, "建立可追溯的论断—证据链，明确事实、解释、外推和未知。", synthesis_prompt)
    synthesis["selectionSource"] = selection_source(candidate)
    return {**synthesis, **expert, **reviewer, "evidenceBasis": candidate["evidenceBasis"], "analysisDepth": candidate["analysisDepth"], "fullTextSource": candidate["fullTextSource"], "confidence": candidate["confidence"], "difficultyLevel": candidate["selectionScore"]["difficulty"], "selectionScore": candidate["selectionScore"]["total"], "selectionBreakdown": candidate["selectionScore"]["breakdown"], "learningFocus": candidate["learningFocus"]}


def selection_source(candidate: dict) -> str:
    score = candidate.get("selectionScore", {})
    full_text_note = "并已确认可解析的合法开放全文" if candidate.get("provider") != "知网人工全文库" else "并已由用户提供的知网全文完成本地核验；原始全文未上传至网站或代码仓库"
    return f"面向社会学本科生的学习价值评分筛选；来源为{candidate.get('provider', '公开数据库')}，本周训练重点为‘{candidate.get('learningFocus', '综合阅读')}’，难度{score.get('difficulty', '待评估')}，总分{score.get('total', '待评估')}/100，{full_text_note}。"


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:72]
    return slug or f"sociology-reading-{today_taipei().isoformat()}"


def build_article(candidate: dict, summary: dict, issue: int) -> dict:
    slug = slugify(candidate["title"])
    today = today_taipei().isoformat()
    return {"slug": slug, "date": today, "issue": f"第 {issue:02d} 期", "title": summary["title"], "titleEn": candidate["title"], "authors": " · ".join(candidate["authors"]), "journal": candidate["journal"], "year": int((candidate.get("date") or today)[:4]), "volume": candidate.get("volume") or "在线发表", "pages": candidate.get("pages") or "在线发表", "doi": candidate.get("doi") or "暂无 DOI", "sourceUrl": candidate["sourceUrl"], "documentUrl": f"/documents/{today}-{slug}.md", "language": candidate.get("language", "英文"), **summary}


def validate_expert_summary(summary: dict) -> None:
    required = {"title", "method", "fieldPosition", "literatureDialogue", "contentFeatures", "researchFeatures", "criticalReview", "researchImplications", "evidenceBoundaries", "evidenceBasis", "analysisDepth", "fullTextSource", "confidence", "difficultyLevel", "selectionScore", "selectionBreakdown", "learningFocus", "prerequisiteKnowledge", "readingGuide", "learningExercises"}
    missing = required - summary.keys()
    if missing:
        raise ValueError(f"Expert analysis missing fields: {sorted(missing)}")
    if summary["evidenceBasis"] == "摘要" and summary["analysisDepth"] != "摘要解读":
        raise ValueError("Abstract-only evidence must be labeled 摘要解读")


def markdown(article: dict) -> str:
    lines = [f"# {article['title']}", "", f"**原题：** {article['titleEn']}", f"**作者：** {article['authors']}", f"**来源：** {article['journal']} ({article['year']})", f"**DOI：** {article['doi']}", f"**官方原文：** {article['sourceUrl']}", f"**难度：** {article['difficultyLevel']}", f"**学习重点：** {article['learningFocus']}", f"**学习价值评分：** {article['selectionScore']}/100", f"**分析依据：** {article['evidenceBasis']}", f"**分析深度：** {article['analysisDepth']}", f"**全文来源：** {article['fullTextSource']}", f"**证据置信度：** {article['confidence']}", "", "> 本精读由 AI 作为研究助理生成。所有判断受可获得证据约束，不能替代研究者阅读全文与核查。", ""]
    guide = article["readingGuide"]
    sections = [("阅读前知识", article["prerequisiteKnowledge"]), ("30分钟快速阅读", guide["quickRead"]), ("必须精读", guide["closeRead"]), ("可以略读", guide["canSkim"]), ("领域定位", article["fieldPosition"]), ("研究问题", article["question"]), ("选题来源", article["selectionSource"]), ("文献对话", article["literatureDialogue"]), ("文章结构", article["articleStructure"]), ("理论框架", article["theory"]), ("数据与方法", article["methods"]), ("分析思路", article["chain"]), ("主要结论", article["findings"]), ("经验贡献", article["empiricalContribution"]), ("理论贡献", article["theoreticalContribution"]), ("方法贡献", article["methodologicalContribution"]), ("内容特色", article["contentFeatures"]), ("研究特色", article["researchFeatures"]), ("批判性评价", article["criticalReview"]), ("证据边界", article["evidenceBoundaries"]), ("研究启发", article["researchImplications"]), ("学习训练", article["learningExercises"]), ("思考题", article["questions"])]
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
    candidates = json.loads(args.candidate_file.read_text(encoding="utf-8")) if args.candidate_file else public_candidates()
    candidate = select_reading_candidate(candidates, dois, titles)
    queue = load_fallback_queue()
    used_fallback = False
    if not candidate:
        candidate = select_fallback_candidate(queue, dois, titles)
        used_fallback = candidate is not None
    if not candidate:
        print("::error::No eligible public article and CNKI fallback queue is empty")
        return 0 if args.dry_run else 4
    print(f"Selected: {candidate['title']} ({candidate['provider']}, score={candidate['selectionScore']['total']}, difficulty={candidate['selectionScore']['difficulty']}, breakdown={candidate['selectionScore']['breakdown']})")
    if args.dry_run:
        return 0
    generated = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    summary = deepseek_summary(candidate, api_key)
    validate_expert_summary(summary)
    article = build_article(candidate, summary, len(generated) + 3)
    generated.insert(0, article)
    DATA_FILE.write_text(json.dumps(generated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    DOCUMENT_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT / "public" / article["documentUrl"].lstrip("/")).write_text(markdown(article), encoding="utf-8")
    if used_fallback:
        queue = remove_fallback_candidate(queue, candidate["id"])
        FALLBACK_QUEUE_FILE.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if len(queue) <= 2:
            print(f"::warning::CNKI fallback inventory is low: {len(queue)} article(s) remaining")
    print(f"Added: {article['slug']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())



