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

export interface Ranking {
  total_prs: number;
  ranking: RankedPR[];
}

export type AgentName =
  | "diff_analyst"
  | "ticket_context"
  | "author_profile";

export interface AgentCompletedEvent {
  agent: AgentName;
  pr_number: number;
  result: Record<string, unknown>;
}

export interface PipelineStartedEvent {
  total_prs: number;
}

export interface SynthesizerCompletedEvent {
  ranking: RankedPR[];
}

export interface CriticAdjustment {
  pr_number: number;
  new_rank: number;
  reason: string;
}

export interface CriticCompletedEvent {
  adjustments: CriticAdjustment[];
  overall_assessment: string;
}

export interface PipelineDoneEvent {
  final_ranking: RankedPR[];
}

export interface ErrorEvent {
  error: string;
}
