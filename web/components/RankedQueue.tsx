"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Check } from "lucide-react";

import { PRCard } from "@/components/PRCard";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { streamRanking } from "@/lib/api-client";
import type { AgentName, RankedPR } from "@/lib/types";

type PipelineStage =
  | "idle"
  | "starting"
  | "agents"
  | "synthesizing"
  | "critiquing"
  | "done"
  | "error";

interface RankedQueueProps {
  repoSlug: string;
  onComplete?: () => void;
}

const AGENT_LABELS: Record<AgentName, string> = {
  diff_analyst: "Diff",
  ticket_context: "Ticket",
  author_profile: "Author",
};

const AGENT_ORDER: AgentName[] = [
  "diff_analyst",
  "ticket_context",
  "author_profile",
];

interface PRProgress {
  pr_number: number;
  agents_done: Set<AgentName>;
}

export function RankedQueue({ repoSlug, onComplete }: RankedQueueProps) {
  const [stage, setStage] = useState<PipelineStage>("idle");
  const [totalPrs, setTotalPrs] = useState(0);
  const [progress, setProgress] = useState<Map<number, PRProgress>>(new Map());
  const [ranking, setRanking] = useState<RankedPR[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const closeRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (!repoSlug) return;

    setStage("starting");
    setTotalPrs(0);
    setProgress(new Map());
    setRanking([]);
    setErrorMsg(null);

    const handle = streamRanking(repoSlug, (type, data) => {
      const payload =
        data && typeof data === "object"
          ? (data as Record<string, unknown>)
          : ({} as Record<string, unknown>);

      if (type === "pipeline_started") {
        setTotalPrs((payload.total_prs as number) ?? 0);
        setStage("agents");
        return;
      }

      if (type === "agent_completed") {
        const agent = payload.agent as AgentName;
        const pr_number = payload.pr_number as number;
        setProgress((prev) => {
          const next = new Map(prev);
          const entry = next.get(pr_number) ?? {
            pr_number,
            agents_done: new Set<AgentName>(),
          };
          const updatedAgents = new Set(entry.agents_done);
          updatedAgents.add(agent);
          next.set(pr_number, { pr_number, agents_done: updatedAgents });
          return next;
        });
        return;
      }

      if (type === "synthesizer_completed") {
        const initial = (payload.ranking as RankedPR[]) ?? [];
        setRanking(initial);
        setStage("critiquing");
        return;
      }

      if (type === "critic_completed") {
        return;
      }

      if (type === "pipeline_done") {
        const final = (payload.final_ranking as RankedPR[]) ?? [];
        setRanking(final);
        setStage("done");
        onComplete?.();
        return;
      }

      if (type === "pipeline_failed") {
        setErrorMsg((payload.error as string) ?? "unknown error");
        setStage("error");
        onComplete?.();
      }
    });

    closeRef.current = handle.close;
    return () => {
      handle.close();
      closeRef.current = null;
    };
  }, [repoSlug]);

  const skeletonSlots = useMemo(
    () =>
      Array.from(
        { length: Math.max(totalPrs, 5) },
        (_, i) => i,
      ),
    [totalPrs],
  );

  if (stage === "idle") return null;

  if (stage === "error") {
    return (
      <Card className="border-rose-200 bg-rose-50 p-5 text-sm text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/30 dark:text-rose-300">
        <p className="font-semibold">Pipeline failed</p>
        <p className="mt-1 font-mono text-xs">{errorMsg}</p>
      </Card>
    );
  }

  if (ranking.length > 0) {
    const isRefining = stage === "critiquing";
    return (
      <div className="flex flex-col gap-4">
        {isRefining && (
          <div className="sticky top-3 z-20 -mx-1 px-1">
            <Card className="border-emerald-200 bg-white/95 p-3 text-xs text-zinc-700 shadow-sm backdrop-blur dark:border-emerald-900/40 dark:bg-zinc-950/95 dark:text-zinc-300">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <span className="relative flex size-2">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                    <span className="relative inline-flex size-2 rounded-full bg-emerald-500" />
                  </span>
                  Critic refining ranking — positions may shift.
                </div>
                <div className="hidden h-1 w-32 overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-800 sm:block">
                  <div className="h-full w-full animate-[pulse_1.5s_ease-in-out_infinite] bg-emerald-500" />
                </div>
              </div>
            </Card>
          </div>
        )}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {ranking.map((pr) => (
            <PRCard key={pr.pr_number} pr={pr} repoSlug={repoSlug} />
          ))}
        </div>
      </div>
    );
  }

  const progressArray = Array.from(progress.values());
  const totalExpectedAgents = totalPrs * AGENT_ORDER.length;
  const agentsCompleted = progressArray.reduce(
    (acc, p) => acc + p.agents_done.size,
    0,
  );
  const completionPct =
    totalExpectedAgents === 0
      ? 0
      : Math.round((agentsCompleted / totalExpectedAgents) * 100);

  return (
    <div className="flex flex-col gap-6">
      <div className="sticky top-3 z-20">
        <Card className="border-zinc-200 bg-white/95 p-4 shadow-sm backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/95">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-zinc-500 dark:text-zinc-500">
                {stage === "starting" && "Loading PRs"}
                {stage === "agents" && "Analyzing PRs"}
                {stage === "synthesizing" && "Synthesizing ranking"}
                {stage === "critiquing" && "Critic reviewing"}
              </p>
              <p className="mt-1 font-mono text-sm text-zinc-700 dark:text-zinc-300">
                {agentsCompleted}/{totalExpectedAgents || "?"} agent calls
                complete
              </p>
            </div>
            <span className="font-mono text-2xl font-semibold tabular-nums text-zinc-950 dark:text-zinc-50">
              {completionPct}%
            </span>
          </div>
          <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-800">
            <div
              className="h-full bg-emerald-500 transition-all duration-500 ease-out"
              style={{ width: `${completionPct}%` }}
            />
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {progressArray.length > 0
          ? progressArray.map((p) => <ProgressCard key={p.pr_number} progress={p} />)
          : skeletonSlots.map((i) => <SkeletonCard key={i} />)}
      </div>
    </div>
  );
}

function ProgressCard({ progress }: { progress: PRProgress }) {
  return (
    <Card className="flex items-center justify-between border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
      <div className="flex items-center gap-2 font-mono text-sm">
        <span className="text-zinc-500 dark:text-zinc-500">PR</span>
        <span className="font-semibold text-zinc-950 dark:text-zinc-50">
          {progress.pr_number}
        </span>
      </div>
      <div className="flex gap-1.5">
        {AGENT_ORDER.map((agent) => {
          const done = progress.agents_done.has(agent);
          return (
            <span
              key={agent}
              className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 font-mono text-[10px] font-medium ${
                done
                  ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-400"
                  : "bg-zinc-100 text-zinc-400 dark:bg-zinc-900 dark:text-zinc-600"
              }`}
            >
              {done && <Check className="size-2.5" />}
              {AGENT_LABELS[agent]}
            </span>
          );
        })}
      </div>
    </Card>
  );
}

function SkeletonCard() {
  return (
    <Card className="border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
      <div className="flex items-center justify-between gap-3">
        <Skeleton className="h-4 w-20" />
        <div className="flex gap-1.5">
          <Skeleton className="h-5 w-12" />
          <Skeleton className="h-5 w-12" />
          <Skeleton className="h-5 w-12" />
        </div>
      </div>
    </Card>
  );
}
