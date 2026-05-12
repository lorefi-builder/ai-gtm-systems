import Anthropic from '@anthropic-ai/sdk';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { AgentOutput, type AgentOutput as AgentOutputT } from './schema.js';

// Model pin. Verify against the latest Anthropic API docs before bumping:
// https://docs.claude.com/en/docs/about-claude/models
const MODEL_ID = 'claude-sonnet-4-6-20251015';

const MAX_TOKENS = 1500;
const TEMPERATURE = 0.7;

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROMPTS_DIR = resolve(__dirname, '..', 'prompts');

export interface ProposalContext {
  experiment_name: string;
  current_subject: string;
  current_open_rate: number;
  sample_size: number;
  recent_winners?: string[];
}

export interface AgentDeps {
  anthropic: Anthropic;
}

export function createAnthropicClient(apiKey: string): Anthropic {
  return new Anthropic({ apiKey });
}

/**
 * Renders a {{token}} template against a string-keyed dictionary. Strict:
 * any token in the template that isn't in `vars` throws. Keeps prompt rot
 * loud instead of silently injecting "undefined".
 */
function renderTemplate(template: string, vars: Record<string, string>): string {
  return template.replace(/{{\s*([a-zA-Z0-9_]+)\s*}}/g, (_match, key: string) => {
    if (!(key in vars)) {
      throw new Error(`Template variable not provided: ${key}`);
    }
    return vars[key] ?? '';
  });
}

function formatRecentWinners(winners: string[] | undefined): string {
  if (!winners || winners.length === 0) {
    return '(no recent winners available — rely on the brand-voice guidance in the system prompt)';
  }
  return winners.map((s) => `- ${s}`).join('\n');
}

async function loadPrompts(): Promise<{ system: string; userTemplate: string }> {
  const [system, userTemplate] = await Promise.all([
    readFile(resolve(PROMPTS_DIR, 'system.md'), 'utf8'),
    readFile(resolve(PROMPTS_DIR, 'user-template.md'), 'utf8'),
  ]);
  return { system, userTemplate };
}

/**
 * Calls Claude to generate two subject-line proposals. Validates the response
 * strictly against the zod schema — anything off-format throws. We never
 * silently coerce, because a malformed proposal would land in the queue
 * looking authoritative.
 */
export async function generateSubjectLineProposals(
  deps: AgentDeps,
  context: ProposalContext,
): Promise<AgentOutputT> {
  const { system, userTemplate } = await loadPrompts();

  const userMessage = renderTemplate(userTemplate, {
    experiment_name: context.experiment_name,
    current_subject: context.current_subject,
    current_open_rate_pct: `${(context.current_open_rate * 100).toFixed(2)}%`,
    sample_size: context.sample_size.toString(),
    recent_winners: formatRecentWinners(context.recent_winners),
  });

  const response = await deps.anthropic.messages.create({
    model: MODEL_ID,
    max_tokens: MAX_TOKENS,
    temperature: TEMPERATURE,
    system,
    messages: [{ role: 'user', content: userMessage }],
  });

  const textBlock = response.content.find((block) => block.type === 'text');
  if (!textBlock || textBlock.type !== 'text') {
    throw new Error(
      `Claude response contained no text block. stop_reason=${response.stop_reason ?? 'unknown'}`,
    );
  }

  const raw = textBlock.text.trim();

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    throw new Error(
      `Claude response was not valid JSON: ${msg}. First 200 chars: ${raw.slice(0, 200)}`,
    );
  }

  const result = AgentOutput.safeParse(parsed);
  if (!result.success) {
    throw new Error(
      `Claude response failed schema validation: ${result.error.toString()}`,
    );
  }

  return result.data;
}
