import "server-only";

import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import { PGlite } from "@electric-sql/pglite";
import pg from "pg";

const databaseUrl = process.env.DATABASE_URL?.trim() ?? "";
let pool: pg.Pool | undefined;

// Local PGlite is kept on globalThis so route handlers, pages and server actions share one database in dev,
// where each is bundled separately.
const shared = globalThis as typeof globalThis & { __bricklineLocalDb?: Promise<PGlite> };

export async function sql<T = Record<string, unknown>>(text: string, params: unknown[] = []): Promise<T[]> {
  if (databaseUrl !== "") {
    pool ??= new pg.Pool({ connectionString: databaseUrl, max: 5 });
    return (await pool.query(text, params)).rows as T[];
  }
  shared.__bricklineLocalDb ??= startLocal().catch((error: unknown) => {
    shared.__bricklineLocalDb = undefined;
    throw error;
  });
  return (await (await shared.__bricklineLocalDb).query<T>(text, params)).rows;
}

async function startLocal(): Promise<PGlite> {
  const db = new PGlite();
  const dir = path.join(process.cwd(), "migrations");
  const files = (await readdir(dir).catch(() => [])).filter((f) => f.endsWith(".sql")).sort();
  for (const file of files) {
    await db.exec(await readFile(path.join(dir, file), "utf8"));
  }
  return db;
}
