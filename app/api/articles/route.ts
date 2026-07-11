import { listArticles } from "../../../db/repository";

export async function GET() {
  try { return Response.json({ articles: await listArticles() }); }
  catch (error) { return Response.json({ error: error instanceof Error ? error.message : "Unable to load articles" }, { status: 500 }); }
}
