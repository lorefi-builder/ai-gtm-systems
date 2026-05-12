import { ApprovalCard } from "./approval-card";
import {
  createAnonClient,
  type AgentName,
  type AgentOutputRow,
} from "@/lib/supabase";

export const dynamic = "force-dynamic";

const SECTIONS: Array<{ agent: AgentName; title: string }> = [
  { agent: "email_ops", title: "Email Ops queue" },
  { agent: "content_ops", title: "Content Ops queue" },
];

async function fetchPending(): Promise<AgentOutputRow[]> {
  const supabase = createAnonClient();
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
    <div className="space-y-12">
      <header className="space-y-3">
        <h1 className="font-serif text-4xl text-sand sm:text-5xl">
          Pending review
        </h1>
        <p className="max-w-2xl text-sand-muted">
          Proposals from the email-ops and content-ops agents. Nothing here
          reaches a customer until you approve it. Rejections require a note
          back to the agent loop.
        </p>
      </header>

      {SECTIONS.map(({ agent, title }) => {
        const items = grouped[agent];
        return (
          <section key={agent} className="space-y-5">
            <div className="flex items-baseline gap-3 border-b border-sand/10 pb-2">
              <h2 className="font-serif text-2xl text-sand">{title}</h2>
              <span className="font-mono text-xs uppercase tracking-[0.18em] text-sand-muted">
                [{items.length.toString().padStart(2, "0")}]
              </span>
            </div>

            {items.length === 0 ? (
              <p className="italic text-sand-muted">No pending proposals.</p>
            ) : (
              <ul className="grid grid-cols-1 gap-4 lg:grid-cols-2">
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
  );
}
