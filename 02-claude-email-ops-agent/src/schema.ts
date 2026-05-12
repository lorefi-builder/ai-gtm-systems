import { z } from 'zod';

export const PredictedLiftQualitative = z.enum(['low', 'medium', 'high']);
export type PredictedLiftQualitative = z.infer<typeof PredictedLiftQualitative>;

export const ProposedSubjectLine = z.object({
  variant_name: z
    .string()
    .min(1)
    .max(64)
    .regex(/^[a-z0-9_]+$/, 'variant_name must be lowercase snake_case'),
  subject: z.string().min(1).max(60),
  rationale: z.string().min(1).max(500),
  predicted_lift_qualitative: PredictedLiftQualitative,
});
export type ProposedSubjectLine = z.infer<typeof ProposedSubjectLine>;

export const AgentOutput = z.object({
  proposals: z.array(ProposedSubjectLine).length(2),
});
export type AgentOutput = z.infer<typeof AgentOutput>;

export const UnderperformingExperiment = z.object({
  experiment_id: z.string().uuid(),
  variant_id: z.string().uuid(),
  name: z.string(),
  primary_metric: z.string(),
  current_subject: z.string(),
  current_signal_rate: z.number().min(0).max(1),
  sample_size: z.number().int().nonnegative(),
});
export type UnderperformingExperiment = z.infer<typeof UnderperformingExperiment>;
