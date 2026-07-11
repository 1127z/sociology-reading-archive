"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import type { Article } from "./data";

export function SiteHeader() {
  return (
    <header className="site-header">
      <Link className="brand" href="/">
        <span className="brand-mark">研</span>
        <span><strong>社会学阅读档案</strong><small>SOCIOLOGY READING ARCHIVE</small></span>
      </Link>
      <nav aria-label="主导航">
        <Link href="/">今日精读</Link>
        <Link href="/library">文献库</Link>
        <a href="#method">阅读方法</a>
      </nav>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <span>始于 2026 · 张宇明的社会学阅读档案</span>
      <span>阅读不是收藏，而是形成自己的问题。</span>
    </footer>
  );
}

export function ReadingToggle({ slug }: { slug: string }) {
  const [read, setRead] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    fetch(`/api/progress/${slug}`, { signal: controller.signal })
      .then((response) => response.ok ? response.json() : Promise.reject(new Error("读取失败")))
      .then((data) => setRead(data.progress.status === "read"))
      .catch((reason) => { if (reason.name !== "AbortError") setError("状态暂时无法同步"); });
    return () => controller.abort();
  }, [slug]);
  const toggle = async () => {
    const next = !read; setBusy(true); setError("");
    try {
      const response = await fetch(`/api/progress/${slug}`, { method: "PATCH", headers: { "content-type": "application/json" }, body: JSON.stringify({ status: next ? "read" : "unread" }) });
      if (!response.ok) throw new Error("保存失败");
      setRead(next);
    } catch { setError("保存失败，请稍后重试"); } finally { setBusy(false); }
  };
  return <div className="sync-control"><button disabled={busy} className={read ? "read-button done" : "read-button"} onClick={toggle}>{busy ? "正在保存…" : read ? "✓ 已完成阅读" : "标记为已读"}</button>{error && <small className="sync-error">{error}</small>}</div>;
}

export function NotePad({ slug }: { slug: string }) {
  const [note, setNote] = useState("");
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    fetch(`/api/progress/${slug}`, { signal: controller.signal })
      .then((response) => response.ok ? response.json() : Promise.reject(new Error("读取失败")))
      .then((data) => setNote(data.progress.note || ""))
      .catch((reason) => { if (reason.name !== "AbortError") setError("笔记暂时无法同步"); });
    return () => controller.abort();
  }, [slug]);
  const save = async () => {
    setBusy(true); setError("");
    try {
      const response = await fetch(`/api/progress/${slug}`, { method: "PATCH", headers: { "content-type": "application/json" }, body: JSON.stringify({ note }) });
      if (!response.ok) throw new Error("保存失败");
      setSaved(true); setTimeout(() => setSaved(false), 1600);
    } catch { setError("保存失败，请稍后重试"); } finally { setBusy(false); }
  };
  return (
    <section className="note-pad">
      <div><span className="eyebrow">MY NOTES</span><h2>我的阅读笔记</h2></div>
      <textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder="写下你的疑问、反驳或可以继续研究的想法……" aria-label="阅读笔记" />
      <button disabled={busy} onClick={save}>{busy ? "正在保存…" : saved ? "已保存并同步" : "保存笔记"}</button>
      <small>{error || "笔记将保存到你的账号，并在设备间同步。"}</small>
    </section>
  );
}

export function LibraryExplorer({ articles }: { articles: Article[] }) {
  const [query, setQuery] = useState("");
  const [method, setMethod] = useState("全部方法");
  const filtered = useMemo(() => articles.filter((a) => {
    const haystack = [a.title, a.titleEn, a.authors, a.journal, ...a.topics].join(" ").toLowerCase();
    return haystack.includes(query.toLowerCase()) && (method === "全部方法" || a.method === method);
  }), [articles, query, method]);
  return (
    <>
      <div className="library-controls">
        <label className="search"><span>⌕</span><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="搜索题目、作者、期刊或关键词" /></label>
        <div className="method-tabs">{["全部方法", "质性研究", "定量研究", "综述"].map((m) => <button className={method === m ? "active" : ""} key={m} onClick={() => setMethod(m)}>{m}</button>)}</div>
      </div>
      <p className="result-count">共收录 {filtered.length} 篇文献</p>
      <div className="archive-list">
        {filtered.map((article) => (
          <Link className="archive-row" href={`/articles/${article.slug}`} key={article.slug}>
            <time>{article.date.slice(5).replace("-", ".")}<small>{article.year}</small></time>
            <div><span className="eyebrow">{article.journal} · {article.method}</span><h2>{article.title}</h2><p>{article.titleEn}</p><div className="tag-line">{article.topics.map((t) => <span key={t}>{t}</span>)}</div></div>
            <span className="row-arrow">↗</span>
          </Link>
        ))}
      </div>
    </>
  );
}
