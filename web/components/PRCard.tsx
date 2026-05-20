"use client";

import { ArrowUpRight, AlertTriangle, Flame } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import type { RankedPR } from "@/lib/types";

interface PRCardProps {
  pr: RankedPR;
  repoSlug: string;
}

const priorityChrome: Record<
  string,
  { stripe: string; pill: string; dot: string; label: string }
> = {
  high: {
    stripe: "border-l-rose-500 dark:border-l-rose-400",
    pill: "bg-rose-50 text-rose-900 dark:bg-rose-950/60 dark:text-rose-200",
    dot: "bg-rose-500 dark:bg-rose-400",
    label: "Review now",
  },
  medium: {
    stripe: "border-l-amber-500 dark:border-l-amber-400",
    pill: "bg-amber-50 text-amber-900 dark:bg-amber-950/60 dark:text-amber-200",
    dot: "bg-amber-500 dark:bg-amber-400",
    label: "Review today",
  },
  low: {
    stripe: "border-l-zinc-300 dark:border-l-zinc-700",
    pill: "bg-zinc-100 text-zinc-700 dark:bg-zinc-900 dark:text-zinc-400",
    dot: "bg-zinc-400 dark:bg-zinc-500",
    label: "Can wait",
  },
};

export function PRCard({ pr, repoSlug }: PRCardProps) {
  const url = pr.url ?? `https://github.com/${repoSlug}/pull/${pr.pr_number}`;
  const author = pr.author_login ? `@${pr.author_login}` : "@unknown";
  const chrome = priorityChrome[pr.ai_priority] ?? priorityChrome.low;

  return (
    <Link
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className={`group flex cursor-pointer flex-col gap-3 rounded-xl border border-l-4 border-zinc-200 bg-white p-5 text-zinc-950 no-underline shadow-sm transition-all hover:-translate-y-0.5 hover:border-zinc-300 hover:shadow-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-950 focus-visible:ring-offset-2 dark:border-zinc-800 dark:bg-zinc-950 dark:text-zinc-50 dark:hover:border-zinc-700 dark:focus-visible:ring-zinc-50 ${chrome.stripe}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5 font-mono">
          <span className="inline-flex h-7 min-w-7 items-center justify-center rounded-md bg-zinc-950 px-2 text-xs font-semibold text-zinc-50 dark:bg-zinc-50 dark:text-zinc-950">
            #{pr.rank}
          </span>
          <span className="text-sm text-zinc-500 dark:text-zinc-500">
            PR {pr.pr_number}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ${chrome.pill}`}
          >
            <span className={`size-1.5 rounded-full ${chrome.dot}`} />
            {pr.ai_priority === "high" && (
              <Flame className="size-3" aria-hidden />
            )}
            {chrome.label}
          </span>
          <ArrowUpRight className="size-4 text-zinc-400 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-zinc-700 dark:text-zinc-600 dark:group-hover:text-zinc-300" />
        </div>
      </div>

      <div>
        <h3 className="text-base font-semibold leading-snug text-zinc-950 group-hover:underline dark:text-zinc-50">
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
    </Link>
  );
}
