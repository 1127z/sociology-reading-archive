import { sql } from "drizzle-orm";
import { index, integer, primaryKey, sqliteTable, text } from "drizzle-orm/sqlite-core";

export const articles = sqliteTable("articles", {
  slug: text("slug").primaryKey(),
  date: text("date").notNull(),
  issue: text("issue").notNull(),
  title: text("title").notNull(),
  titleEn: text("title_en").notNull(),
  authors: text("authors").notNull(),
  journal: text("journal").notNull(),
  method: text("method").notNull(),
  topics: text("topics").notNull(),
  sourceUrl: text("source_url").notNull(),
  documentUrl: text("document_url").notNull(),
  payload: text("payload").notNull(),
  createdAt: integer("created_at").notNull().default(sql`(unixepoch() * 1000)`),
}, (table) => [index("articles_date_idx").on(table.date), index("articles_method_idx").on(table.method)]);

export const readingProgress = sqliteTable("reading_progress", {
  userKey: text("user_key").notNull(),
  articleSlug: text("article_slug").notNull().references(() => articles.slug, { onDelete: "cascade" }),
  status: text("status").notNull().default("unread"),
  note: text("note").notNull().default(""),
  updatedAt: integer("updated_at").notNull().default(sql`(unixepoch() * 1000)`),
}, (table) => [primaryKey({ columns: [table.userKey, table.articleSlug] }), index("progress_user_idx").on(table.userKey)]);
