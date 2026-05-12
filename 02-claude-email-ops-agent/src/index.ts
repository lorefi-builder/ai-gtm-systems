import { loadConfig } from './config.js';
import { createPool, withTransaction } from './db.js';
import { fetchUnderperformingExperiments, writeAgentOutput } from './queue.js';
import { createAnthropicClient, generateSubjectLineProposals } from './agent.js';
import type { UnderperformingExperiment } from './schema.js';

async function main(): Promise<void> {
  const config = loadConfig();

  console.log(
    `[email-ops] starting agent_name=${config.AGENT_NAME} dry_run=${config.DRY_RUN} ` +
      `min_sample_size=${config.MIN_SAMPLE_SIZE} signal_rate_threshold=${config.OPEN_RATE_THRESHOLD}`,
  );

  const pool = createPool({ connectionString: config.DATABASE_URL });
  const anthropic = createAnthropicClient(config.ANTHROPIC_API_KEY);

  let shuttingDown = false;
  const shutdown = async (signal: string): Promise<void> => {
    if (shuttingDown) return;
    shuttingDown = true;
    console.log(`[email-ops] received ${signal}, shutting down`);
    try {
      await pool.end();
    } catch (err) {
      console.error('[email-ops] error closing pg pool:', err);
    }
  };
  process.on('SIGINT', () => void shutdown('SIGINT'));
  process.on('SIGTERM', () => void shutdown('SIGTERM'));

  let exitCode = 0;
  try {
    const candidates = await fetchCandidates(pool, config);

    if (candidates.length === 0) {
      console.log('[email-ops] no underperforming experiments matched. nothing to propose.');
      return;
    }

    console.log(`[email-ops] found ${candidates.length} underperforming experiment(s)`);

    for (const experiment of candidates) {
      await processExperiment(pool, anthropic, config, experiment);
    }
  } catch (err) {
    exitCode = 1;
    console.error('[email-ops] fatal:', err instanceof Error ? err.stack ?? err.message : err);
  } finally {
    await shutdown('completion');
    process.exit(exitCode);
  }
}

async function fetchCandidates(
  pool: ReturnType<typeof createPool>,
  config: ReturnType<typeof loadConfig>,
): Promise<UnderperformingExperiment[]> {
  const client = await pool.connect();
  try {
    return await fetchUnderperformingExperiments(
      client,
      config.OPEN_RATE_THRESHOLD,
      config.MIN_SAMPLE_SIZE,
    );
  } finally {
    client.release();
  }
}

async function processExperiment(
  pool: ReturnType<typeof createPool>,
  anthropic: ReturnType<typeof createAnthropicClient>,
  config: ReturnType<typeof loadConfig>,
  experiment: UnderperformingExperiment,
): Promise<void> {
  const ratePct = (experiment.current_signal_rate * 100).toFixed(2);
  console.log(
    `[email-ops] experiment="${experiment.name}" primary_metric=${experiment.primary_metric} ` +
      `current_signal_rate=${ratePct}% n=${experiment.sample_size}`,
  );

  const proposals = await generateSubjectLineProposals(
    { anthropic },
    {
      experiment_name: experiment.name,
      current_subject: experiment.current_subject,
      current_signal_rate: experiment.current_signal_rate,
      sample_size: experiment.sample_size,
      primary_metric: experiment.primary_metric,
    },
  );

  const payload = {
    source_variant_id: experiment.variant_id,
    source_subject: experiment.current_subject,
    source_primary_metric: experiment.primary_metric,
    source_signal_rate: experiment.current_signal_rate,
    source_sample_size: experiment.sample_size,
    proposals: proposals.proposals,
  };

  if (config.DRY_RUN) {
    console.log(
      `[email-ops] DRY_RUN — would insert into gtm.agent_outputs:\n${JSON.stringify(
        {
          agent_name: config.AGENT_NAME,
          output_type: 'subject_line_variant',
          target_ref: experiment.experiment_id,
          payload,
        },
        null,
        2,
      )}`,
    );
    return;
  }

  const insertedId = await withTransaction(pool, async (client) => {
    return writeAgentOutput(client, {
      agentName: config.AGENT_NAME,
      outputType: 'subject_line_variant',
      targetRef: experiment.experiment_id,
      payload,
    });
  });

  console.log(
    `[email-ops] inserted agent_outputs.id=${insertedId} status=pending_review ` +
      `experiment_id=${experiment.experiment_id}`,
  );
}

main().catch((err: unknown) => {
  console.error('[email-ops] unhandled:', err instanceof Error ? err.stack ?? err.message : err);
  process.exit(1);
});
