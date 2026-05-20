"use client";

import { ArrowUpRight, AlertTriangle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { RankedPR } from "@/lib/types";
import { cn } from "@/lib/utils";

interface PRCardProps {
  pr: RankedPR;
  repoSlug: string;
}

const priorityTone: Record<string, string> = {
  high: "bg-rose-100 text-rose-900 dark:bg-rose-950/50 dark:text-rose-300",
  medium: "bg-amber-100 text-amber-900 dark:bg-amber-950/50 dark:text-amber-300",
  low: "bg-zinc-200 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300",
};

export function PRCard({ pr, repoSlug }: PRCardProps) {
  const url = pr.url ?? `https://github.com/${repoSlug}/pull/${pr.pr_number}`;
  const author = pr.author_login ? `@${pr.author_login}` : "@unknown";
  const aiTone =
    priorityTone[pr.ai_priority] ??
    "bg-zinc-200 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300";

  return (
    <Card className="flex flex-col gap-3 border-zinc-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md dark:border-zinc-800 dark:bg-zinc-950">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5 font-mono">
          <span className="inline-flex h-7 min-w-7 items-center justify-center rounded-md bg-zinc-950 px-2 text-xs font-semibold text-zinc-50 dark:bg-zinc-50 dark:text-zinc-950">
            #{pr.rank}
          </span>
          <span className="text-sm text-zinc-500 dark:text-zinc-500">
            PR {pr.pr_number}
          </span>
        </div>
        <span
          className={`rounded-md px-2 py-0.5 text-xs font-medium uppercase tracking-wide ${aiTone}`}
        >
          {pr.ai_priority}
        </span>
      </div>

      <div>
        <h3 className="text-base font-semibold leading-snug text-zinc-950 dark:text-zinc-50">
          {pr.title ?? `Pull request #${pr.pr_number}`}
        </h3>
        <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-500">
          by{" "}
          <span className="font-mono text-zinc-700 dark:text-zinc-300">
            {author}
          </span>
        </p>
      </div>

      {pr.label_disagreement && (
        <Badge
          variant="destructive"
          className="w-fit gap-1.5 px-2 py-1 text-[11px] font-medium normal-case tracking-normal"
        >
          <AlertTriangle className="size-3" />
          Labeled{" "}
          <span className="font-mono">
            {pr.ticket_priority_label ?? "unknown"}
          </span>{" "}
          · AI says <span className="font-mono">{pr.ai_priority}</span>
        </Badge>
      )}

      <p className="text-sm leading-relaxed text-zinc-700 dark:text-zinc-300">
        {pr.reasoning}
      </p>

      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className={cn(buttonVariants({ variant: "outline", size: "sm" }), "w-fit")}
      >
        Review on GitHub
        <ArrowUpRight className="size-3.5" />
      </a>
    </Card>
  );
}
