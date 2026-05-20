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

export function RankedQueue({ repoSlug }: RankedQueueProps) {
  const [stage, setStage] = useState<PipelineStage>("idle");
  const [totalPrs, setTotalPrs] = useState(0);
  const [progress, setProgress] = useState<Map<number, PRProgress>>(new Map());
  const [finalRanking, setFinalRanking] = useState<RankedPR[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const closeRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (!repoSlug) return;

    setStage("starting");
    setTotalPrs(0);
    setProgress(new Map());
    setFinalRanking([]);
    setErrorMsg(null);

    const handle = streamRanking(repoSlug, (type, data) => {
      const payload = data as Record<string, unknown>;

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
        setStage("critiquing");
        return;
      }

      if (type === "critic_completed") {
        setStage("critiquing");
        return;
      }

      if (type === "pipeline_done") {
        const ranking = (payload.final_ranking as RankedPR[]) ?? [];
        setFinalRanking(ranking);
        setStage("done");
        return;
      }

      if (type === "error") {
        setErrorMsg((payload.error as string) ?? "unknown error");
        setStage("error");
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

  if (stage === "done") {
    return (
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {finalRanking.map((pr) => (
          <PRCard key={pr.pr_number} pr={pr} repoSlug={repoSlug} />
        ))}
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
      <Card className="border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
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
            className="h-full bg-emerald-500 transition-all duration-300"
            style={{ width: `${completionPct}%` }}
          />
        </div>
      </Card>

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
