import { and, eq } from "drizzle-orm";
import { getDb } from "../../../../db";
import { articles, readingProgress } from "../../../../db/schema";

function userKey(request: Request) {
  const email = request.headers.get("oai-authenticated-user-email")?.trim().toLowerCase();
  if (email) return email;
  return process.env.NODE_ENV !== "production" ? "local-preview" : null;
}

async function articleExists(slug: string) {
  const [row] = await getDb().select({ slug: articles.slug }).from(articles).where(eq(articles.slug, slug)).limit(1);
  return Boolean(row);
}

export async function GET(request: Request, { params }: { params: Promise<{ slug: string }> }) {
  const user = userKey(request); if (!user) return Response.json({ error: "Authentication required" }, { status: 401 });
  const { slug } = await params;
  try {
    const [progress] = await getDb().select().from(readingProgress).where(and(eq(readingProgress.userKey, user), eq(readingProgress.articleSlug, slug))).limit(1);
    return Response.json({ progress: progress ?? { articleSlug: slug, status: "unread", note: "" } });
  } catch (error) {
    if (process.env.NODE_ENV !== "production") return Response.json({ progress: { articleSlug: slug, status: "unread", note: "" } });
    return Response.json({ error: error instanceof Error ? error.message : "Unable to load progress" }, { status: 500 });
  }
}

export async function PATCH(request: Request, { params }: { params: Promise<{ slug: string }> }) {
  const user = userKey(request); if (!user) return Response.json({ error: "Authentication required" }, { status: 401 });
  const { slug } = await params;
  try {
    if (!(await articleExists(slug))) return Response.json({ error: "Article not found" }, { status: 404 });
    const body = await request.json() as { status?: string; note?: string };
    if (body.status !== undefined && !["unread", "reading", "read"].includes(body.status)) return Response.json({ error: "Invalid status" }, { status: 400 });
    if (body.note !== undefined && body.note.length > 20000) return Response.json({ error: "Note is too long" }, { status: 400 });
    const db = getDb();
    const [current] = await db.select().from(readingProgress).where(and(eq(readingProgress.userKey, user), eq(readingProgress.articleSlug, slug))).limit(1);
    const values = { userKey: user, articleSlug: slug, status: body.status ?? current?.status ?? "unread", note: body.note ?? current?.note ?? "", updatedAt: Date.now() };
    await db.insert(readingProgress).values(values).onConflictDoUpdate({ target: [readingProgress.userKey, readingProgress.articleSlug], set: { status: values.status, note: values.note, updatedAt: values.updatedAt } });
    return Response.json({ progress: values });
  } catch (error) { return Response.json({ error: error instanceof Error ? error.message : "Unable to save progress" }, { status: 500 }); }
}
