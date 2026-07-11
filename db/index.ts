import { drizzle } from "drizzle-orm/d1";
import * as schema from "./schema";

export function getDb() {
  const binding = (globalThis as typeof globalThis & { __SITES_DB__?: D1Database }).__SITES_DB__;
  if (!binding) {
    throw new Error("Cloudflare D1 binding `DB` is unavailable in this request context.");
  }
  return drizzle(binding, { schema });
}
