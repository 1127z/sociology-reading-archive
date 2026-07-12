import { notFound } from "next/navigation";
import { NotePad, ReadingToggle, SiteFooter, SiteHeader } from "../../components";
import { findArticle } from "../../../db/repository";

export async function generateStaticParams() {
  const { listArticles } = await import("../../../db/repository");
  return (await listArticles()).map((article) => ({ slug: article.slug }));
}

export default async function ArticlePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params; const article = await findArticle(slug); if (!article) notFound();
  return (
    <main><SiteHeader />
      <article className="article-shell shell">
        <header className="article-hero">
          <div><span className="eyebrow">{article.issue} · {article.date}</span><h1>{article.title}</h1><p className="article-title-en">{article.titleEn}</p><p>{article.authors}</p><div className="topics">{article.topics.map((t) => <span key={t}>{t}</span>)}</div></div>
          <aside><span className="eyebrow">PUBLICATION</span><strong>{article.journal}</strong><p>{article.year} · {article.volume} · {article.pages}</p>{article.evidenceBasis && <p>难度：{article.difficultyLevel ?? "未分级"}<br />学习重点：{article.learningFocus ?? "综合阅读"}<br />学习价值：{article.selectionScore ?? "未评分"}/100<br />分析依据：{article.evidenceBasis} · {article.analysisDepth}<br />证据置信度：{article.confidence}</p>}<a href={article.sourceUrl} target="_blank" rel="noreferrer">阅读官方原文 ↗</a><a className="doc-link" href={article.documentUrl}>下载精读文档 ↓</a><ReadingToggle slug={article.slug} /></aside>
        </header>
        <div className="article-layout">
          <nav className="article-toc"><span>专家精读目录</span>{["领域定位", "问题与对话", "理论框架", "研究设计", "论证与发现", "研究贡献", "内容与研究特色", "批判与启发"].map((x, i) => <a href={`#s${i + 1}`} key={x}>{String(i + 1).padStart(2, "0")} {x}</a>)}</nav>
          <div className="article-content">
            <section className="lead-box"><span className="eyebrow">核心判断</span><p>{article.recommendation}</p></section>
            {article.readingGuide && <section><span className="section-num">00</span><h2>本科生阅读路线</h2>{article.prerequisiteKnowledge && <><h3>阅读前需要知道</h3><ul>{article.prerequisiteKnowledge.map((x) => <li key={x}>{x}</li>)}</ul></>}<h3>30分钟快速阅读</h3><p>{article.readingGuide.quickRead}</p><h3>必须精读</h3><p>{article.readingGuide.closeRead}</p><h3>可以暂时略读</h3><p>{article.readingGuide.canSkim}</p></section>}
            <section id="s1"><span className="section-num">01</span><h2>研究领域定位</h2><p>{article.fieldPosition ?? "当前精读尚未提供领域定位。"}</p></section>
            <section id="s2"><span className="section-num">02</span><h2>研究问题、选题来源与文献对话</h2><p>{article.thesis}</p><blockquote>{article.question}</blockquote><p>{article.selectionSource ?? "文章从既有文献的解释缺口与现实经验问题之间建立连接。"}</p>{article.literatureDialogue && <ul>{article.literatureDialogue.map((x) => <li key={x}>{x}</li>)}</ul>}<h3 className="subhead">文章结构</h3>{article.articleStructure && <ol>{article.articleStructure.map((x) => <li key={x}>{x}</li>)}</ol>}</section>
            <section id="s3"><span className="section-num">03</span><h2>理论框架</h2><div className="theory-grid">{article.theory.map((x) => <div key={x.name}><h3>{x.name}</h3><p>{x.detail}</p></div>)}</div></section>
            <section id="s4"><span className="section-num">04</span><h2>研究设计、数据与方法</h2><ul>{article.methods.map((x) => <li key={x}>{x}</li>)}</ul>{article.researchFeatures && <div className="highlight-list">{article.researchFeatures.map((x) => <div key={x.label}><b>{x.label}</b><p>{x.detail}</p></div>)}</div>}</section>
            <section id="s5"><span className="section-num">05</span><h2>分析思路、论证链条与主要发现</h2><ol className="argument-chain">{article.chain.map((x, i) => <li key={x.label}><b>{String(i + 1).padStart(2, "0")}</b><div><h3>{x.label}</h3><p>{x.detail}</p></div></li>)}</ol><ul>{article.findings.map((x) => <li key={x}>{x}</li>)}</ul></section>
            <section id="s6"><span className="section-num">06</span><h2>研究贡献</h2><h3>经验贡献</h3><p>{article.empiricalContribution ?? "当前精读尚未单独评估。"}</p><h3>理论贡献</h3><p>{article.theoreticalContribution ?? "当前精读尚未单独评估。"}</p><h3>方法贡献</h3><p>{article.methodologicalContribution ?? "当前精读尚未单独评估。"}</p></section>
            <section id="s7"><span className="section-num">07</span><h2>内容特色与研究特色</h2><div className="highlight-list">{(article.contentFeatures ?? article.highlights).map((x) => <div key={x.label}><b>{x.label}</b><p>{x.detail}</p></div>)}</div>{article.researchFeatures && <div className="highlight-list">{article.researchFeatures.map((x) => <div key={x.label}><b>{x.label}</b><p>{x.detail}</p></div>)}</div>}</section>
            <section id="s8"><span className="section-num">08</span><h2>批判性评价、证据边界与研究启发</h2><ul>{(article.criticalReview ?? article.limits).map((x) => <li key={x}>{x}</li>)}</ul>{article.evidenceBoundaries && <><h3 className="subhead">证据边界</h3><ul>{article.evidenceBoundaries.map((x) => <li key={x}>{x}</li>)}</ul></>} {article.researchImplications && <><h3 className="subhead">研究启发</h3><ul>{article.researchImplications.map((x) => <li key={x}>{x}</li>)}</ul></>}{article.learningExercises && <><h3 className="subhead">学习训练</h3><ul>{article.learningExercises.map((x) => <li key={x}>{x}</li>)}</ul></>}<h3 className="subhead">思考题</h3><ol className="questions">{article.questions.map((x, i) => <li key={x}><b>{i + 1}</b><p>{x}</p></li>)}</ol></section>
            <section><span className="section-num">09</span><h2>核心术语</h2><dl>{article.terms.map((x) => <div key={x.term}><dt>{x.term}</dt><dd>{x.definition}</dd></div>)}</dl></section>
            <NotePad slug={article.slug} />
          </div>
        </div>
      </article><SiteFooter /></main>
  );
}




