import { ApprovalCard } from "./approval-card";
import {
  createServiceClient,
  type AgentName,
  type AgentOutputRow,
} from "@/lib/supabase";

export const dynamic = "force-dynamic";

const SECTIONS: Array<{ agent: AgentName; title: string }> = [
  { agent: "email_ops", title: "Email Ops queue" },
  { agent: "content_ops", title: "Content Ops queue" },
];

async function fetchPending(): Promise<AgentOutputRow[]> {
  const supabase = createServiceClient();
  const { data, error } = await supabase
    .from("agent_outputs")
    .select(
      "id, agent_name, output_type, target_ref, payload, status, reviewed_at, reviewed_by, review_notes, shipped_at, shipped_ref, created_at, updated_at",
    )
    .eq("status", "pending_review")
    .order("created_at", { ascending: false });

  if (error) {
    throw new Error(`Failed to load pending queue: ${error.message}`);
  }
  return (data ?? []) as AgentOutputRow[];
}

export default async function QueuePage() {
  const rows = await fetchPending();

  const grouped: Record<AgentName, AgentOutputRow[]> = {
    email_ops: [],
    content_ops: [],
  };
  for (const row of rows) {
    grouped[row.agent_name].push(row);
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-12 sm:px-10">
      <header>
        <h1 className="font-serif text-6xl font-semibold tracking-tight text-[var(--al-ink)]">
          Pending review
        </h1>
        <p className="mt-4 max-w-2xl text-base leading-relaxed text-[var(--al-ink-soft)]">
          Proposals from the email-ops and content-ops agents. Nothing here
          reaches a customer until you approve it. Rejections require a note
          back to the agent loop.
        </p>
      </header>

      <div className="mt-12 space-y-16">
        {SECTIONS.map(({ agent, title }) => {
          const items = grouped[agent];
          return (
            <section key={agent}>
              <div className="flex items-baseline gap-3">
                <h2 className="font-serif text-[32px] italic leading-tight text-[var(--al-ink)]">
                  {title}
                </h2>
                <span className="inline-flex items-center rounded-full bg-[var(--al-red)] px-2.5 py-0.5 font-mono text-[12px] leading-none text-[var(--al-cream)]">
                  {items.length.toString().padStart(2, "0")}
                </span>
              </div>
              <div
                className="mt-3 h-px w-full"
                style={{ backgroundColor: "var(--al-stroke-ink)" }}
              />

              {items.length === 0 ? (
                <p className="mt-6 font-serif italic text-[var(--al-ink-mute)]">
                  No pending proposals.
                </p>
              ) : (
                <ul className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-2">
                  {items.map((row) => (
                    <li key={row.id}>
                      <ApprovalCard row={row} />
                    </li>
                  ))}
                </ul>
              )}
            </section>
          );
        })}
      </div>
    </div>
  );
}
