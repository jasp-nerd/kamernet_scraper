import postgres from "postgres";

let sqlInstance: ReturnType<typeof postgres> | null = null;

export function getDb() {
  if (!sqlInstance) {
    sqlInstance = postgres(process.env.DATABASE_URL!, {
      ssl: { rejectUnauthorized: false },
    });
  }
  return sqlInstance;
}
