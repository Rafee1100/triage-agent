"use client";

import { useState } from "react";
import { Bot } from "lucide-react";

import { RankedQueue } from "@/components/RankedQueue";
import { TelegramSubscriptionPanel } from "@/components/TelegramSubscriptionPanel";
import { TriageForm } from "@/components/TriageForm";
import { Dialog } from "@/components/ui/dialog";

export default function Home() {
  const [submittedSlug, setSubmittedSlug] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [briefOpen, setBriefOpen] = useState(false);

  const handleSubmit = (slug: string) => {
    setSubmittedSlug(slug);
    setBusy(true);
  };

  const handleComplete = () => {
    setBusy(false);
  };

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-950 dark:bg-zinc-950 dark:text-zinc-50">
      <div className="mx-auto max-w-4xl px-6 py-12 sm:py-16">
        <header className="mb-10 sm:mb-14">
          <div className="mb-4 inline-flex h-9 w-9 items-center justify-center rounded-lg bg-zinc-950 font-mono text-sm font-semibold text-zinc-50 dark:bg-zinc-50 dark:text-zinc-950">
            TP
          </div>
          <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            TriagePilot
          </h1>
          <p className="mt-3 max-w-2xl text-base leading-relaxed text-zinc-600 dark:text-zinc-400">
            A multi-agent AI that reads every open pull request in your repo —
            diffs, linked issues, author track records, and cross-PR
            dependencies — then ranks them by what actually needs your review
            attention. Catches the cases where the GitHub label is wrong and
            tells you why.
          </p>
          <p className="mt-2 max-w-2xl text-sm text-zinc-500 dark:text-zinc-500">
            Paste a public GitHub repo below. The pipeline streams its
            reasoning as it works.
          </p>
        </header>

        <section className="mb-10">
          <TriageForm onSubmit={handleSubmit} busy={busy} />
          <p className="mt-2 text-xs text-zinc-500 dark:text-zinc-500">
            Try{" "}
            <button
              type="button"
              onClick={() => handleSubmit("kubernetes/kubernetes")}
              className="cursor-pointer font-mono text-zinc-700 underline-offset-2 hover:underline dark:text-zinc-300"
            >
              kubernetes/kubernetes
            </button>{" "}
            or{" "}
            <button
              type="button"
              onClick={() => handleSubmit("vercel/next.js")}
              className="cursor-pointer font-mono text-zinc-700 underline-offset-2 hover:underline dark:text-zinc-300"
            >
              vercel/next.js
            </button>
            .
          </p>
        </section>

        {submittedSlug && (
          <RankedQueue repoSlug={submittedSlug} onComplete={handleComplete} />
        )}
      </div>

      <button
        type="button"
        onClick={() => setBriefOpen(true)}
        aria-label="Configure Telegram morning brief"
        className="fixed bottom-6 right-6 z-30 inline-flex size-14 cursor-pointer items-center justify-center rounded-full bg-zinc-950 text-zinc-50 shadow-lg shadow-zinc-950/20 ring-1 ring-zinc-800 transition hover:scale-105 hover:bg-zinc-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 dark:bg-emerald-500 dark:text-zinc-950 dark:ring-emerald-400 dark:hover:bg-emerald-400"
      >
        <Bot className="size-6" />
      </button>

      <Dialog
        open={briefOpen}
        onOpenChange={setBriefOpen}
        title="Morning brief via Telegram"
        description="Bring your own bot. The token and chat ID are stored locally on this server."
      >
        <TelegramSubscriptionPanel />
      </Dialog>
    </div>
  );
}
