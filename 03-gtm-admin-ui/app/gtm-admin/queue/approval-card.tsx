"use client";

import { useState, useTransition } from "react";
import { approveOutput, rejectOutput } from "./actions";
import { relativeTime } from "@/lib/format";
import type { AgentOutputRow, OutputType } from "@/lib/supabase";

interface ApprovalCardProps {
  row: AgentOutputRow;
}

type CardState =
  | { kind: "idle" }
  | { kind: "rejecting" }
  | { kind: "dismissed" }
  | { kind: "error"; message: string };

type LiftBucket = "high" | "medium" | "low";

interface Proposal {
  variant_name?: string;
  subject?: string;
  subject_line?: string;
  rationale?: string;
  reasoning?: string;
  predicted_lift_qualitative?: LiftBucket;
}

const TYPE_LABEL: Record<OutputType, string> = {
  subject_line_variant: "Email subject line",
  blog_draft: "Blog post draft",
  ad_copy: "Ad copy",
  social_caption: "Social caption",
};

const TYPE_EMOJI: Record<OutputType, string> = {
  subject_line_variant: "📩",
  blog_draft: "📝",
  ad_copy: "🎯",
  social_caption: "💬",
};

function asString(value: unknown): string | null {
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function pickPrimaryContent(payload: Record<string, unknown>): string | null {
  const candidates = [
    "headline",
    "subject_line",
    "subject",
    "title",
    "caption",
    "slug",
  ];
  for (const key of candidates) {
    const v = asString(payload[key]);
    if (v) return v;
  }
  const skip = new Set([
    "slug",
    "source_variant_id",
    "source_subject",
    "source_primary_metric",
    "source_signal_rate",
    "source_sample_size",
    "predicted_lift_qualitative",
    "variant_name",
  ]);
  for (const [key, val] of Object.entries(payload)) {
    if (skip.has(key)) continue;
    const v = asString(val);
    if (v) return v;
  }
  return null;
}

function pickRationale(payload: Record<string, unknown>): string | null {
  return (
    asString(payload.rationale) ??
    asString(payload.reasoning) ??
    asString(payload.description) ??
    null
  );
}

function liftPillCopy(bucket: LiftBucket | undefined): string | null {
  if (bucket === "high") return "Strong bet";
  if (bucket === "medium") return "Moderate";
  if (bucket === "low") return "Low confidence";
  return null;
}

function CheckIcon() {
  return (
    <svg
      viewBox="0 0 12 12"
      fill="none"
      aria-hidden
      className="h-3 w-3"
    >
      <path
        d="M2 6l3 3 5-6"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function XIcon() {
  return (
    <svg
      viewBox="0 0 12 12"
      fill="none"
      aria-hidden
      className="h-3 w-3"
    >
      <path
        d="M2 2l8 8M10 2l-8 8"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

function LiftPill({ bucket }: { bucket: LiftBucket | undefined }) {
  const copy = liftPillCopy(bucket);
  if (!copy) return null;
  const base =
    "inline-flex items-center rounded-full px-2.5 py-0.5 font-sans text-[11px] font-semibold uppercase tracking-wide";
  if (bucket === "high") {
    return (
      <span
        className={base}
        style={{
          backgroundColor: "var(--al-gold)",
          color: "var(--al-ink)",
        }}
      >
        {copy}
      </span>
    );
  }
  if (bucket === "medium") {
    return (
      <span
        className={base}
        style={{
          backgroundColor: "var(--al-orange)",
          color: "var(--al-cream)",
        }}
      >
        {copy}
      </span>
    );
  }
  return (
    <span
      className={base}
      style={{
        backgroundColor: "transparent",
        color: "var(--al-ink-mute)",
        border: "1px solid var(--al-stroke-ink)",
      }}
    >
      {copy}
    </span>
  );
}

function ProposalMiniCard({
  label,
  headline,
  rationale,
  lift,
}: {
  label?: string;
  headline: string;
  rationale?: string | null;
  lift?: LiftBucket;
}) {
  return (
    <div
      className="rounded-md p-4"
      style={{
        backgroundColor: "var(--al-cream)",
        border: "1px solid var(--al-stroke-ink)",
      }}
    >
      {label ? (
        <div
          className="font-mono text-[10px] uppercase tracking-wider"
          style={{ color: "var(--al-ink-mute)" }}
        >
          {label}
        </div>
      ) : null}
      <p
        className={`font-serif text-[17px] leading-snug ${label ? "mt-2" : ""}`}
        style={{ color: "var(--al-ink)" }}
      >
        &ldquo;{headline}&rdquo;
      </p>
      {rationale ? (
        <p
          className="mt-2 text-[13px] leading-relaxed"
          style={{ color: "var(--al-ink-soft)" }}
        >
          {rationale}
        </p>
      ) : null}
      {lift ? (
        <div className="mt-2">
          <LiftPill bucket={lift} />
        </div>
      ) : null}
    </div>
  );
}

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

  const payload = row.payload as Record<string, unknown>;
  const proposals = Array.isArray(payload.proposals)
    ? (payload.proposals as Proposal[])
    : null;

  const sourceSubject = asString(payload.source_subject);
  const sourceMetric = asString(payload.source_primary_metric);
  const sourceRate = asNumber(payload.source_signal_rate);
  const sourceSamples = asNumber(payload.source_sample_size);
  const hasSourceContext = Boolean(
    sourceSubject || sourceRate !== null || sourceMetric,
  );

  const typeLabel = TYPE_LABEL[row.output_type] ?? row.output_type;
  const typeEmoji = TYPE_EMOJI[row.output_type] ?? "•";

  const isPendingStatus = row.status === "pending_review";

  return (
    <article
      className={[
        "group relative overflow-hidden rounded-xl bg-[var(--al-cream-warm)]",
        "border border-[color:var(--al-stroke-ink)] hover:border-[color:var(--al-stroke-red)]",
        "p-6 transition-all duration-200 ease-out-soft",
        dismissed
          ? "pointer-events-none translate-x-2 opacity-0"
          : "translate-x-0 opacity-100",
      ].join(" ")}
      aria-busy={isPending || undefined}
    >
      {isPendingStatus ? (
        <span
          aria-hidden
          className="absolute inset-y-0 left-0 w-[3px]"
          style={{ backgroundColor: "var(--al-red)" }}
        />
      ) : null}

      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-base leading-none" aria-hidden>
            {typeEmoji}
          </span>
          <span
            className="font-serif text-[16px] italic"
            style={{ color: "var(--al-ink)" }}
          >
            {typeLabel}
          </span>
        </div>
        <span
          className="font-sans text-[11px] uppercase tracking-wide"
          style={{ color: "var(--al-ink-mute)" }}
        >
          {relativeTime(row.created_at)}
        </span>
      </div>

      {hasSourceContext ? (
        <p
          className="mb-5 mt-3 text-[13px] leading-relaxed"
          style={{ color: "var(--al-ink-soft)" }}
        >
          Replacing:{" "}
          {sourceSubject ? (
            <em>&ldquo;{sourceSubject}&rdquo;</em>
          ) : (
            <em>previous variant</em>
          )}
          {sourceRate !== null || sourceMetric || sourceSamples !== null ? (
            <> — currently </>
          ) : null}
          {sourceRate !== null ? (
            <span className="font-mono">{(sourceRate * 100).toFixed(1)}%</span>
          ) : null}
          {sourceMetric ? (
            <>
              {sourceRate !== null ? " " : ""}
              {sourceMetric}
            </>
          ) : null}
          {sourceSamples !== null ? (
            <>
              , <span className="font-mono">n={sourceSamples}</span> exposures
            </>
          ) : null}
        </p>
      ) : (
        <div className="mt-5" />
      )}

      {proposals && proposals.length === 2 ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {proposals.map((p, idx) => {
            const headline =
              asString(p.subject) ??
              asString(p.subject_line) ??
              "(missing subject)";
            const rationale =
              asString(p.rationale) ?? asString(p.reasoning);
            return (
              <ProposalMiniCard
                key={p.variant_name ?? idx}
                label={idx === 0 ? "OPTION A" : "OPTION B"}
                headline={headline}
                rationale={rationale}
                lift={p.predicted_lift_qualitative}
              />
            );
          })}
        </div>
      ) : (
        (() => {
          const headline = pickPrimaryContent(payload) ?? "(no content)";
          const rationale = pickRationale(payload);
          return (
            <ProposalMiniCard
              headline={headline}
              rationale={rationale}
            />
          );
        })()
      )}

      {state.kind === "rejecting" ? (
        <div className="mt-5 space-y-2">
          <label
            htmlFor={`notes-${row.id}`}
            className="block font-mono text-[10px] uppercase tracking-wider"
            style={{ color: "var(--al-ink-mute)" }}
          >
            Reviewer note (required)
          </label>
          <textarea
            id={`notes-${row.id}`}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="What needs to change before this can ship?"
            rows={3}
            className="block w-full rounded-md px-3 py-2 text-sm focus:outline-none"
            style={{
              backgroundColor: "var(--al-cream)",
              border: "1px solid var(--al-stroke-ink)",
              color: "var(--al-ink)",
            }}
          />
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={handleRejectSubmit}
              disabled={isPending}
              className="inline-flex items-center gap-1.5 rounded-md bg-[var(--al-red)] px-5 py-2.5 font-sans text-sm font-semibold text-[var(--al-cream)] transition-colors duration-200 hover:bg-[var(--al-red-deep)] disabled:opacity-50"
            >
              <CheckIcon />
              Confirm reject
            </button>
            <button
              type="button"
              onClick={() => {
                setState({ kind: "idle" });
                setNotes("");
                clearError();
              }}
              className="inline-flex items-center rounded-md px-3 py-2.5 font-sans text-sm text-[var(--al-ink-mute)] transition-colors duration-200 hover:text-[var(--al-ink-soft)]"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="mt-6 flex gap-3">
          <button
            type="button"
            onClick={handleApprove}
            disabled={isPending}
            className="inline-flex items-center gap-1.5 rounded-md bg-[var(--al-red)] px-5 py-2.5 font-sans text-sm font-semibold text-[var(--al-cream)] transition-colors duration-200 hover:bg-[var(--al-red-deep)] disabled:opacity-50"
          >
            <CheckIcon />
            Approve
          </button>
          <button
            type="button"
            onClick={() => {
              setState({ kind: "rejecting" });
              clearError();
            }}
            disabled={isPending}
            className="inline-flex items-center gap-1.5 rounded-md border border-[color:var(--al-stroke-ink)] bg-transparent px-5 py-2.5 font-sans text-sm text-[var(--al-ink-soft)] transition-colors duration-200 hover:border-[color:var(--al-red)] hover:text-[var(--al-red)] disabled:opacity-50"
          >
            <XIcon />
            Reject
          </button>
        </div>
      )}

      {state.kind === "error" ? (
        <div
          role="alert"
          className="mt-4 rounded-md px-3 py-2 font-sans text-[12px]"
          style={{
            backgroundColor: "rgba(200, 16, 46, 0.08)",
            border: "1px solid var(--al-stroke-red)",
            color: "var(--al-red-deep)",
          }}
        >
          {state.message}
        </div>
      ) : null}
    </article>
  );
}
