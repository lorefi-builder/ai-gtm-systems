import 'dotenv/config';
import { z } from 'zod';

const RawEnv = z.object({
  ANTHROPIC_API_KEY: z.string().min(1, 'ANTHROPIC_API_KEY is required'),
  DATABASE_URL: z.string().min(1, 'DATABASE_URL is required'),
  AGENT_NAME: z.string().min(1).default('email_ops'),
  DRY_RUN: z
    .string()
    .default('true')
    .transform((v) => v.toLowerCase() === 'true'),
  MIN_SAMPLE_SIZE: z
    .string()
    .default('100')
    .transform((v) => Number.parseInt(v, 10))
    .refine((n) => Number.isFinite(n) && n >= 0, 'MIN_SAMPLE_SIZE must be a non-negative integer'),
  OPEN_RATE_THRESHOLD: z
    .string()
    .default('0.18')
    .transform((v) => Number.parseFloat(v))
    .refine(
      (n) => Number.isFinite(n) && n >= 0 && n <= 1,
      'OPEN_RATE_THRESHOLD must be between 0 and 1',
    ),
});

export type Config = z.infer<typeof RawEnv>;

export function loadConfig(): Config {
  const parsed = RawEnv.safeParse(process.env);
  if (!parsed.success) {
    const issues = parsed.error.issues.map((i) => `  - ${i.path.join('.')}: ${i.message}`).join('\n');
    throw new Error(`Invalid environment configuration:\n${issues}`);
  }
  return parsed.data;
}
