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
  useEffect(() => {
    setRead(localStorage.getItem(`reading-status:${slug}`) === "read");
  }, [slug]);
  const toggle = () => {
    const next = !read;
    localStorage.setItem(`reading-status:${slug}`, next ? "read" : "unread");
    setRead(next);
  };
  return <div className="sync-control"><button className={read ? "read-button done" : "read-button"} onClick={toggle}>{read ? "✓ 已完成阅读" : "标记为已读"}</button></div>;
}

export function NotePad({ slug }: { slug: string }) {
  const [note, setNote] = useState("");
  const [saved, setSaved] = useState(false);
  useEffect(() => {
    setNote(localStorage.getItem(`reading-note:${slug}`) ?? "");
  }, [slug]);
  const save = () => {
    localStorage.setItem(`reading-note:${slug}`, note);
    setSaved(true);
    setTimeout(() => setSaved(false), 1600);
  };
  return (
    <section className="note-pad">
      <div><span className="eyebrow">MY NOTES</span><h2>我的阅读笔记</h2></div>
      <textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder="写下你的疑问、反驳或可以继续研究的想法……" aria-label="阅读笔记" />
      <button onClick={save}>{saved ? "已保存" : "保存笔记"}</button>
      <small>笔记保存在当前浏览器；接入账号系统后可跨设备同步。</small>
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

