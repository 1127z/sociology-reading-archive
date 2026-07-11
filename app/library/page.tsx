import { LibraryExplorer, SiteFooter, SiteHeader } from "../components";
import { listArticles } from "../../db/repository";

export const dynamic = "force-dynamic";

export default async function LibraryPage() {
  const articles = await listArticles();
  return (
    <main><SiteHeader /><section className="library-hero shell"><span className="eyebrow">THE ARCHIVE</span><h1>文献库</h1><p>按主题、方法和关键词，重新找到你曾经认真读过的东西。</p></section><section className="library-body shell"><LibraryExplorer articles={articles} /></section><SiteFooter /></main>
  );
}
