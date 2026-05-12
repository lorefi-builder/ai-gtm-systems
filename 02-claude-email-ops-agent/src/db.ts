import pg from 'pg';

export type DbClient = pg.PoolClient;

export interface DbConfig {
  connectionString: string;
}

export function createPool(config: DbConfig): pg.Pool {
  return new pg.Pool({
    connectionString: config.connectionString,
    max: 4,
    idleTimeoutMillis: 10_000,
    application_name: 'claude-email-ops-agent',
  });
}

export async function withTransaction<T>(
  pool: pg.Pool,
  fn: (client: DbClient) => Promise<T>,
): Promise<T> {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    const result = await fn(client);
    await client.query('COMMIT');
    return result;
  } catch (err) {
    try {
      await client.query('ROLLBACK');
    } catch {
      // If ROLLBACK itself fails the connection is already broken; the original
      // error is what the caller needs to see.
    }
    throw err;
  } finally {
    client.release();
  }
}
