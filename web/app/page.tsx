"use client";

import { useState } from "react";

import { RankedQueue } from "@/components/RankedQueue";
import { TriageForm } from "@/components/TriageForm";

export default function Home() {
  const [repoSlug, setRepoSlug] = useState<string>("");
  const [submittedSlug, setSubmittedSlug] = useState<string | null>(null);

  const handleSubmit = (slug: string) => {
    setRepoSlug(slug);
    setSubmittedSlug(slug);
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
          <p className="mt-3 max-w-xl text-base leading-relaxed text-zinc-600 dark:text-zinc-400">
            Your labels lie. We tell you the truth. Paste a GitHub repo, get
            the right review order.
          </p>
        </header>

        <section className="mb-10">
          <TriageForm
            onSubmit={handleSubmit}
            busy={submittedSlug !== null && submittedSlug === repoSlug}
          />
          <p className="mt-2 text-xs text-zinc-500 dark:text-zinc-500">
            Try{" "}
            <button
              type="button"
              onClick={() => handleSubmit("kubernetes/kubernetes")}
              className="font-mono text-zinc-700 underline-offset-2 hover:underline dark:text-zinc-300"
            >
              kubernetes/kubernetes
            </button>{" "}
            or{" "}
            <button
              type="button"
              onClick={() => handleSubmit("vercel/next.js")}
              className="font-mono text-zinc-700 underline-offset-2 hover:underline dark:text-zinc-300"
            >
              vercel/next.js
            </button>
            .
          </p>
        </section>

        {submittedSlug && <RankedQueue repoSlug={submittedSlug} />}
      </div>
    </div>
  );
}
