import Link from "next/link";
import { listArticles } from "../db/repository";
import { ReadingToggle, SiteFooter, SiteHeader } from "./components";

export const dynamic = "force-dynamic";

export default async function Home() {
  const articles = await listArticles();
  const article = articles[0];
  const total = String(articles.length).padStart(2, "0");
  const methods = String(new Set(articles.map((item) => item.method)).size).padStart(2, "0");
  return (
    <main>
      <SiteHeader />
      <section className="hero shell">
        <div className="hero-copy">
          <span className="eyebrow">DAILY SOCIOLOGY · {article.issue}</span>
          <h1>每天读一篇，<br />慢慢形成自己的<span>问题意识</span>。</h1>
          <p>这里不只收藏论文，更拆解一篇研究如何提出问题、组织证据、建立理论并得出结论。</p>
          <div className="hero-actions"><Link className="primary" href={`/articles/${article.slug}`}>开始今日精读 <span>→</span></Link><Link className="secondary" href="/library">查看全部文献</Link></div>
        </div>
        <aside className="reading-stats" aria-label="阅读统计">
          <div className="seal">SOC<br />READ</div>
          <p>阅读档案从今天开始</p>
          <div className="stat-grid"><div><strong>{total}</strong><span>累计文献</span></div><div><strong>{total}</strong><span>连续阅读</span></div><div><strong>{methods}</strong><span>研究方法</span></div></div>
        </aside>
      </section>

      <section className="today shell">
        <div className="section-heading"><div><span className="eyebrow">TODAY&apos;S READING</span><h2>今日精读</h2></div><time>{article.date.replaceAll("-", " / ")}</time></div>
        <article className="feature-article">
          <div className="feature-index"><span>{article.issue}</span><strong>{article.journal === "arXiv preprint" ? "ARXIV" : "ASR"}</strong><small>{article.method}</small></div>
          <div className="feature-main">
            <div className="meta">{article.journal} · {article.volume} · {article.pages}</div>
            <h2>{article.title}</h2><p className="english-title">{article.titleEn}</p>
            <p className="authors">{article.authors}</p>
            <div className="topics">{article.topics.map((topic) => <span key={topic}>{topic}</span>)}</div>
          </div>
          <div className="feature-note"><span className="eyebrow">WHY READ IT</span><p>{article.recommendation}</p><Link href={`/articles/${article.slug}`}>进入完整精读 <span>↗</span></Link><ReadingToggle slug={article.slug} /></div>
        </article>
      </section>

      <section className="method shell" id="method">
        <div className="method-intro"><span className="eyebrow">READING METHOD</span><h2>不止读懂结论，<br />更要看懂研究是怎样完成的。</h2></div>
        <ol>
          <li><b>01</b><div><h3>问题从哪里来</h3><p>识别经验困惑、文献缺口与概念张力。</p></div></li>
          <li><b>02</b><div><h3>证据如何组织</h3><p>追踪资料、方法与论证链条是否匹配。</p></div></li>
          <li><b>03</b><div><h3>还能怎样追问</h3><p>区分作者结论、合理外推与尚待证明之处。</p></div></li>
        </ol>
      </section>
      <SiteFooter />
    </main>
  );
}
