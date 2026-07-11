import { desc, eq } from "drizzle-orm";
import { articles as seedArticles, type Article } from "../app/data";
import generatedArticles from "../data/articles.generated.json";
import { getDb } from ".";
import { articles } from "./schema";

function toRecord(article: Article) {
  return { slug: article.slug, date: article.date, issue: article.issue, title: article.title, titleEn: article.titleEn, authors: article.authors, journal: article.journal, method: article.method, topics: JSON.stringify(article.topics), sourceUrl: article.sourceUrl, documentUrl: article.documentUrl, payload: JSON.stringify(article) };
}

async function syncSeedArticles() {
  const db = getDb();
  for (const article of [...(generatedArticles as Article[]), ...seedArticles]) {
    const record = toRecord(article);
    await db.insert(articles).values(record).onConflictDoUpdate({ target: articles.slug, set: { ...record } });
  }
}

function parsePayload(payload: string): Article { return JSON.parse(payload) as Article; }

export async function listArticles(): Promise<Article[]> {
  const allArticles = [...(generatedArticles as Article[]), ...seedArticles];
  try {
    await syncSeedArticles();
    const rows = await getDb().select({ payload: articles.payload }).from(articles).orderBy(desc(articles.date));
    return rows.map((row) => parsePayload(row.payload));
  } catch (error) {
    if (process.env.NODE_ENV !== "production") return allArticles;
    throw error;
  }
}

export async function findArticle(slug: string): Promise<Article | undefined> {
  const allArticles = [...(generatedArticles as Article[]), ...seedArticles];
  try {
    await syncSeedArticles();
    const [row] = await getDb().select({ payload: articles.payload }).from(articles).where(eq(articles.slug, slug)).limit(1);
    return row ? parsePayload(row.payload) : undefined;
  } catch (error) {
    if (process.env.NODE_ENV !== "production") return allArticles.find((article) => article.slug === slug);
    throw error;
  }
}

