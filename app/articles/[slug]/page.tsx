import { notFound } from "next/navigation";
import { NotePad, ReadingToggle, SiteFooter, SiteHeader } from "../../components";
import { findArticle } from "../../../db/repository";

export const dynamic = "force-dynamic";

export default async function ArticlePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params; const article = await findArticle(slug); if (!article) notFound();
  return (
    <main><SiteHeader />
      <article className="article-shell shell">
        <header className="article-hero">
          <div><span className="eyebrow">{article.issue} · {article.date}</span><h1>{article.title}</h1><p className="article-title-en">{article.titleEn}</p><p>{article.authors}</p><div className="topics">{article.topics.map((t) => <span key={t}>{t}</span>)}</div></div>
          <aside><span className="eyebrow">PUBLICATION</span><strong>{article.journal}</strong><p>{article.year} · {article.volume} · {article.pages}</p><a href={article.sourceUrl} target="_blank" rel="noreferrer">阅读官方原文 ↗</a><a className="doc-link" href={article.documentUrl}>下载精读文档 ↓</a><ReadingToggle slug={article.slug} /></aside>
        </header>
        <div className="article-layout">
          <nav className="article-toc"><span>本篇目录</span>{["研究问题", "理论框架", "研究方法", "论证链条", "主要结论", "亮点与局限", "思考题"].map((x, i) => <a href={`#s${i + 1}`} key={x}>{String(i + 1).padStart(2, "0")} {x}</a>)}</nav>
          <div className="article-content">
            <section className="lead-box"><span className="eyebrow">核心判断</span><p>{article.recommendation}</p></section>
            <section id="s1"><span className="section-num">01</span><h2>研究问题与问题意识</h2><p>{article.thesis}</p><blockquote>{article.question}</blockquote></section>
            <section id="s2"><span className="section-num">02</span><h2>理论框架</h2><div className="theory-grid">{article.theory.map((x) => <div key={x.name}><h3>{x.name}</h3><p>{x.detail}</p></div>)}</div></section>
            <section id="s3"><span className="section-num">03</span><h2>数据与研究方法</h2><ul>{article.methods.map((x) => <li key={x}>{x}</li>)}</ul></section>
            <section id="s4"><span className="section-num">04</span><h2>分析思路与论证链条</h2><ol className="argument-chain">{article.chain.map((x, i) => <li key={x.label}><b>{String(i + 1).padStart(2, "0")}</b><div><h3>{x.label}</h3><p>{x.detail}</p></div></li>)}</ol></section>
            <section id="s5"><span className="section-num">05</span><h2>主要结论</h2><ul>{article.findings.map((x) => <li key={x}>{x}</li>)}</ul></section>
            <section id="s6"><span className="section-num">06</span><h2>亮点与可批判之处</h2><div className="highlight-list">{article.highlights.map((x) => <div key={x.label}><b>{x.label}</b><p>{x.detail}</p></div>)}</div><h3 className="subhead">研究局限</h3><ul>{article.limits.map((x) => <li key={x}>{x}</li>)}</ul></section>
            <section id="s7"><span className="section-num">07</span><h2>阅读思考题</h2><ol className="questions">{article.questions.map((x, i) => <li key={x}><b>{i + 1}</b><p>{x}</p></li>)}</ol></section>
            <section><span className="section-num">08</span><h2>核心术语</h2><dl>{article.terms.map((x) => <div key={x.term}><dt>{x.term}</dt><dd>{x.definition}</dd></div>)}</dl></section>
            <NotePad slug={article.slug} />
          </div>
        </div>
      </article><SiteFooter /></main>
  );
}
