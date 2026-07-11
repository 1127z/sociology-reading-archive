import { articles as seedArticles, type Article } from "../app/data";
import generatedArticles from "../data/articles.generated.json";

const allArticles = [...(generatedArticles as Article[]), ...seedArticles]
  .sort((a, b) => b.date.localeCompare(a.date));

export async function listArticles(): Promise<Article[]> {
  return allArticles;
}

export async function findArticle(slug: string): Promise<Article | undefined> {
  return allArticles.find((article) => article.slug === slug);
}


