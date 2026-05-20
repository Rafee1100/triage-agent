export type AIPriority = "high" | "medium" | "low";

export interface RankedPR {
  pr_number: number;
  rank: number;
  reasoning: string;
  ai_priority: AIPriority;
  label_disagreement: boolean;
  title?: string;
  author_login?: string | null;
  url?: string;
  ticket_priority_label?: string | null;
}

export type AgentName =
  | "diff_analyst"
  | "ticket_context"
  | "author_profile";

export interface Subscription {
  id: string;
  chat_id: string;
  repo: string;
  hour: number;
  minute: number;
  timezone: string;
  bot_token_masked: string;
  created_at: string;
}

export interface SubscriptionCreate {
  bot_token: string;
  chat_id: string;
  repo: string;
  hour: number;
  minute: number;
  timezone: string;
}
