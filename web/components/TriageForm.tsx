"use client";

import { useState, type FormEvent } from "react";
import { ArrowRight, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const REPO_REGEX = /^[\w.-]+\/[\w.-]+$/;

interface TriageFormProps {
  onSubmit: (repoSlug: string) => void;
  busy?: boolean;
}

export function TriageForm({ onSubmit, busy = false }: TriageFormProps) {
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = value.trim();
    if (!REPO_REGEX.test(trimmed)) {
      setError("Expected format: owner/repo (e.g. kubernetes/kubernetes)");
      return;
    }
    setError(null);
    onSubmit(trimmed);
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex w-full flex-col gap-2 sm:flex-row sm:items-start"
    >
      <div className="flex-1">
        <Input
          type="text"
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            if (error) setError(null);
          }}
          placeholder="owner/repo"
          autoComplete="off"
          spellCheck={false}
          disabled={busy}
          className="h-11 font-mono text-sm"
          aria-label="GitHub repository in owner/repo format"
          aria-invalid={error ? "true" : "false"}
        />
        {error && (
          <p className="mt-1.5 text-xs text-rose-600 dark:text-rose-400">
            {error}
          </p>
        )}
      </div>
      <Button
        type="submit"
        disabled={busy || !value.trim()}
        className="h-11 px-5 font-medium"
      >
        {busy ? (
          <>
            <Loader2 className="size-4 animate-spin" />
            Triaging…
          </>
        ) : (
          <>
            Triage now
            <ArrowRight className="size-4" />
          </>
        )}
      </Button>
    </form>
  );
}
