import { createClient, type SupabaseClient } from "@supabase/supabase-js";

export type AgentName = "email_ops" | "content_ops";

export type OutputType =
  | "subject_line_variant"
  | "blog_draft"
  | "ad_copy"
  | "social_caption";

export type OutputStatus =
  | "pending_review"
  | "approved"
  | "rejected"
  | "shipped";

export interface AgentOutputRow {
  id: string;
  agent_name: AgentName;
  output_type: OutputType;
  target_ref: string | null;
  payload: Record<string, unknown>;
  status: OutputStatus;
  reviewed_at: string | null;
  reviewed_by: string | null;
  review_notes: string | null;
  shipped_at: string | null;
  shipped_ref: string | null;
  created_at: string;
  updated_at: string;
}

export interface Database {
  gtm: {
    Tables: {
      agent_outputs: {
        Row: AgentOutputRow;
        Insert: Omit<AgentOutputRow, "id" | "created_at" | "updated_at"> & {
          id?: string;
          created_at?: string;
          updated_at?: string;
        };
        Update: Partial<AgentOutputRow>;
      };
    };
    Views: Record<string, never>;
    Functions: Record<string, never>;
    Enums: Record<string, never>;
    CompositeTypes: Record<string, never>;
  };
}

function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value || value.length === 0) {
    throw new Error(`Missing required env var: ${name}`);
  }
  return value;
}

export function createAnonClient(): SupabaseClient<Database, "gtm"> {
  const url = requireEnv("NEXT_PUBLIC_SUPABASE_URL");
  const key = requireEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY");
  return createClient<Database, "gtm">(url, key, {
    db: { schema: "gtm" },
    auth: { persistSession: false },
  });
}

export function createServiceClient(): SupabaseClient<Database, "gtm"> {
  const url = requireEnv("NEXT_PUBLIC_SUPABASE_URL");
  const key = requireEnv("SUPABASE_SERVICE_ROLE_KEY");
  return createClient<Database, "gtm">(url, key, {
    db: { schema: "gtm" },
    auth: { persistSession: false, autoRefreshToken: false },
  });
}
