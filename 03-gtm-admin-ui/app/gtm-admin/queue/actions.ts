"use server";

import { revalidatePath } from "next/cache";
import { createServiceClient } from "@/lib/supabase";
import { AlreadyActionedError } from "./errors";

const REVIEWER_EMAIL = "demo-reviewer@activationlabs.io";

/**
 * Flip a pending agent_output row to status='approved'.
 *
 * The `eq("status", "pending_review")` clause is a row-level guard: if a
 * second reviewer clicked Approve/Reject on the same card a beat earlier,
 * the row has already transitioned out of pending_review and this UPDATE
 * matches zero rows. We detect that and surface AlreadyActionedError so the
 * card can snap back in the UI rather than silently no-op-ing.
 *
 * Note: the database state-machine trigger (see
 * 01-postgres-gtm-schema/migrations/004_agent_queue.sql) is the canonical
 * enforcement — the guard here is just so the client can react sensibly.
 */
export async function approveOutput(id: string): Promise<void> {
  if (!id) throw new Error("approveOutput requires a row id");

  const supabase = createServiceClient();
  const { data, error } = await supabase
    .from("agent_outputs")
    .update({
      status: "approved",
      reviewed_at: new Date().toISOString(),
      reviewed_by: REVIEWER_EMAIL,
    })
    .eq("id", id)
    .eq("status", "pending_review")
    .select("id");

  if (error) throw new Error(`Failed to approve row ${id}: ${error.message}`);
  if (!data || data.length === 0) throw new AlreadyActionedError(id);

  revalidatePath("/gtm-admin/queue");
}

/**
 * Flip a pending agent_output row to status='rejected' with reviewer notes.
 *
 * Same row-level guard pattern as approveOutput: the WHERE-on-status clause
 * makes this idempotent across concurrent reviewers. Empty notes are
 * rejected client-side and re-checked here because the DB only enforces
 * "notes column exists", not "notes column is non-empty on reject".
 */
export async function rejectOutput(id: string, notes: string): Promise<void> {
  if (!id) throw new Error("rejectOutput requires a row id");
  const trimmed = notes.trim();
  if (trimmed.length === 0) {
    throw new Error("Rejection requires a non-empty reviewer note.");
  }

  const supabase = createServiceClient();
  const { data, error } = await supabase
    .from("agent_outputs")
    .update({
      status: "rejected",
      reviewed_at: new Date().toISOString(),
      reviewed_by: REVIEWER_EMAIL,
      review_notes: trimmed,
    })
    .eq("id", id)
    .eq("status", "pending_review")
    .select("id");

  if (error) throw new Error(`Failed to reject row ${id}: ${error.message}`);
  if (!data || data.length === 0) throw new AlreadyActionedError(id);

  revalidatePath("/gtm-admin/queue");
}
