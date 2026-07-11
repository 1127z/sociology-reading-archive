import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const root = new URL("../", import.meta.url);
const generated = JSON.parse(await readFile(new URL("data/articles.generated.json", root), "utf8"));

test("generated articles have unique slugs and documents", async () => {
  assert.equal(new Set(generated.map((article) => article.slug)).size, generated.length);
  for (const article of generated) {
    assert.match(article.sourceUrl, /^https:\/\//);
    assert.match(article.documentUrl, /^\/documents\//);
    const document = await readFile(new URL(`public${article.documentUrl}`, root), "utf8");
    assert.ok(document.length > 100);
  }
});

