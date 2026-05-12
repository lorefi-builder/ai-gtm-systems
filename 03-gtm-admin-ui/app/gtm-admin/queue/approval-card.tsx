"use client";

import { useState, useTransition } from "react";
import { approveOutput, rejectOutput } from "./actions";
import { relativeTime } from "@/lib/format";
import type { AgentOutputRow } from "@/lib/supabase";

interface ApprovalCardProps {
  row: AgentOutputRow;
}

type CardState =
  | { kind: "idle" }
  | { kind: "rejecting" }
  | { kind: "dismissed" }
  | { kind: "error"; message: string };

export function ApprovalCard({ row }: ApprovalCardProps) {
  const [state, setState] = useState<CardState>({ kind: "idle" });
  const [notes, setNotes] = useState("");
  const [isPending, startTransition] = useTransition();

  const dismissed = state.kind === "dismissed";

  function clearError() {
    if (state.kind === "error") setState({ kind: "idle" });
  }

  function handleApprove() {
    clearError();
    setState({ kind: "dismissed" });
    startTransition(async () => {
      try {
        await approveOutput(row.id);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Approval failed.";
        setState({ kind: "error", message });
      }
    });
  }

  function handleRejectSubmit() {
    clearError();
    if (notes.trim().length === 0) {
      setState({
        kind: "error",
        message: "Add a short note before rejecting.",
      });
      return;
    }
    setState({ kind: "dismissed" });
    startTransition(async () => {
      try {
        await rejectOutput(row.id, notes);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Rejection failed.";
        setState({ kind: "error", message });
      }
    });
  }

  const payloadJson = JSON.stringify(row.payload, null, 2);

  return (
    <article
      className={[
        "relative overflow-hidden rounded-lg border border-sand/10 bg-teal-slate/80",
        "border-l-4 border-l-coral",
        "p-6 shadow-[0_1px_0_rgba(255,255,255,0.03)_inset]",
        "transition-all duration-200 ease-out-soft",
        dismissed
          ? "pointer-events-none translate-x-2 opacity-0"
          : "translate-x-0 opacity-100",
      ].join(" ")}
      aria-busy={isPending || undefined}
    >
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="rounded-sm bg-coral/15 px-2 py-0.5 font-mono uppercase tracking-[0.14em] text-coral">
          {row.agent_name}
        </span>
        <span className="rounded-sm border border-sand/20 px-2 py-0.5 font-mono uppercase tracking-[0.14em] text-sand-muted">
          {row.output_type}
        </span>
        {row.target_ref ? (
          <span className="truncate font-mono text-[11px] text-sand-muted">
            target:{" "}
            <span className="text-sand">{row.target_ref}</span>
          </span>
        ) : null}
        <span className="ml-auto font-mono text-[11px] text-sand-muted">
          {relativeTime(row.created_at)}
        </span>
      </div>

      <pre className="mt-5 max-h-80 overflow-auto rounded-md border border-sand/10 bg-teal-deeper/80 p-4 font-mono text-[12px] leading-relaxed text-sand">
        {payloadJson}
      </pre>

      {state.kind === "rejecting" ? (
        <div className="mt-5 space-y-2">
          <label
            htmlFor={`notes-${row.id}`}
            className="block font-mono text-[11px] uppercase tracking-[0.14em] text-sand-muted"
          >
            Reviewer note (required)
          </label>
          <textarea
            id={`notes-${row.id}`}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="What needs to change before this can ship?"
            rows={3}
            className="block w-full rounded-md border border-sand/20 bg-teal-deeper/60 px-3 py-2 text-sm text-sand placeholder:text-sand-dim focus:border-coral/60 focus:outline-none"
          />
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={handleRejectSubmit}
              disabled={isPending}
              className="rounded-md border border-sand/40 px-4 py-1.5 font-mono text-xs uppercase tracking-[0.14em] text-sand transition-colors duration-200 ease-out-soft hover:border-sand hover:bg-sand/10 disabled:opacity-50"
            >
              Confirm reject
            </button>
            <button
              type="button"
              onClick={() => {
                setState({ kind: "idle" });
                setNotes("");
                clearError();
              }}
              className="rounded-md px-3 py-1.5 font-mono text-xs uppercase tracking-[0.14em] text-sand-muted transition-colors duration-200 ease-out-soft hover:text-sand"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="mt-5 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={handleApprove}
            disabled={isPending}
            className="rounded-md bg-coral px-4 py-1.5 font-mono text-xs font-medium uppercase tracking-[0.16em] text-teal-deep transition-all duration-200 ease-out-soft hover:bg-coral/90 disabled:opacity-50"
          >
            Approve
          </button>
          <button
            type="button"
            onClick={() => {
              setState({ kind: "rejecting" });
              clearError();
            }}
            disabled={isPending}
            className="rounded-md border border-sand/40 px-4 py-1.5 font-mono text-xs uppercase tracking-[0.14em] text-sand transition-all duration-200 ease-out-soft hover:border-sand hover:bg-sand/10 disabled:opacity-50"
          >
            Reject
          </button>
        </div>
      )}

      {state.kind === "error" ? (
        <div
          role="alert"
          className="mt-4 rounded-md border border-coral/40 bg-coral/10 px-3 py-2 font-mono text-[11px] text-coral"
        >
          {state.message}
        </div>
      ) : null}
    </article>
  );
}
