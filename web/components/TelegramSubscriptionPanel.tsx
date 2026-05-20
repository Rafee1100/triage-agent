"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { ChevronDown, Loader2, Send, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  createSubscription,
  deleteSubscription,
  listSubscriptions,
  triggerSubscription,
} from "@/lib/api-client";
import type { Subscription } from "@/lib/types";

const REPO_REGEX = /^[\w.-]+\/[\w.-]+$/;

function browserTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  } catch {
    return "UTC";
  }
}

function formatTime(hour: number, minute: number): string {
  return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

export function TelegramSubscriptionPanel() {
  const [subs, setSubs] = useState<Subscription[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [botToken, setBotToken] = useState("");
  const [chatId, setChatId] = useState("");
  const [repo, setRepo] = useState("");
  const [time, setTime] = useState("09:00");
  const [tz, setTz] = useState(browserTimezone);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listSubscriptions();
      setSubs(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!REPO_REGEX.test(repo.trim())) {
      setError("Repo must be in owner/name format.");
      return;
    }
    const [hh, mm] = time.split(":").map((s) => parseInt(s, 10));
    if (Number.isNaN(hh) || Number.isNaN(mm)) {
      setError("Time must be HH:MM (24-hour).");
      return;
    }

    setSubmitting(true);
    try {
      await createSubscription({
        bot_token: botToken.trim(),
        chat_id: chatId.trim(),
        repo: repo.trim(),
        hour: hh,
        minute: mm,
        timezone: tz.trim() || "UTC",
      });
      setBotToken("");
      setChatId("");
      setRepo("");
      setSuccess("Brief scheduled.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    setError(null);
    try {
      await deleteSubscription(id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const handleTrigger = async (id: string) => {
    setError(null);
    setSuccess(null);
    try {
      await triggerSubscription(id);
      setSuccess("Brief sent. Check Telegram.");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <div>
      <details className="mb-5 rounded-lg border border-zinc-200 bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-900">
        <summary className="flex cursor-pointer items-center justify-between gap-2 px-3 py-2 text-xs font-medium text-zinc-700 hover:text-zinc-950 dark:text-zinc-300 dark:hover:text-zinc-50 [&::-webkit-details-marker]:hidden">
          <span>How do I get a bot token and chat ID?</span>
          <ChevronDown className="size-3.5 transition-transform [details[open]_&]:rotate-180" />
        </summary>
        <ol className="list-decimal space-y-2 px-3 pb-3 pl-7 text-xs leading-relaxed text-zinc-600 dark:text-zinc-400">
          <li>
            Open{" "}
            <a
              href="https://t.me/BotFather"
              target="_blank"
              rel="noopener noreferrer"
              className="font-mono text-zinc-900 underline-offset-2 hover:underline dark:text-zinc-100"
            >
              @BotFather
            </a>{" "}
            in Telegram, send <code className="rounded bg-zinc-200 px-1 font-mono text-[10px] dark:bg-zinc-800">/newbot</code>,
            and follow the prompts. Copy the HTTP API token it returns (looks
            like <code className="rounded bg-zinc-200 px-1 font-mono text-[10px] dark:bg-zinc-800">123456:ABC-DEF...</code>) into{" "}
            <strong>Bot token</strong> below.
          </li>
          <li>
            Open{" "}
            <a
              href="https://t.me/userinfobot"
              target="_blank"
              rel="noopener noreferrer"
              className="font-mono text-zinc-900 underline-offset-2 hover:underline dark:text-zinc-100"
            >
              @userinfobot
            </a>{" "}
            and press <strong>Start</strong>. It replies with your numeric{" "}
            <strong>Id</strong> — paste that into <strong>Chat ID</strong>.
            (For a group, add the bot to the group and use the group&apos;s
            negative ID instead.)
          </li>
          <li>
            <strong>Open a chat with your new bot and send it{" "}</strong>
            <code className="rounded bg-zinc-200 px-1 font-mono text-[10px] dark:bg-zinc-800">/start</code>
            {" "}<strong>once.</strong> Telegram blocks bots from messaging users
            who haven&apos;t initiated contact.
          </li>
          <li>
            Fill out the form, then click <strong>Send now</strong> on the
            saved entry to verify before tomorrow&apos;s scheduled brief.
          </li>
        </ol>
      </details>

      <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-zinc-600 dark:text-zinc-400">
            Bot token
          </span>
          <Input
            type="password"
            value={botToken}
            onChange={(e) => setBotToken(e.target.value)}
            placeholder="123456:ABC-..."
            className="font-mono text-xs"
            autoComplete="off"
            required
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-zinc-600 dark:text-zinc-400">
            Chat ID
          </span>
          <Input
            value={chatId}
            onChange={(e) => setChatId(e.target.value)}
            placeholder="987654321 or @yourchannel"
            className="font-mono text-xs"
            autoComplete="off"
            required
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-zinc-600 dark:text-zinc-400">
            Repository
          </span>
          <Input
            value={repo}
            onChange={(e) => setRepo(e.target.value)}
            placeholder="owner/repo"
            className="font-mono text-xs"
            autoComplete="off"
            required
          />
        </label>
        <div className="grid grid-cols-[auto_1fr] gap-3">
          <label className="flex flex-col gap-1">
            <span className="text-xs font-medium text-zinc-600 dark:text-zinc-400">
              Time
            </span>
            <Input
              type="time"
              value={time}
              onChange={(e) => setTime(e.target.value)}
              className="font-mono text-xs"
              required
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs font-medium text-zinc-600 dark:text-zinc-400">
              Timezone (IANA)
            </span>
            <Input
              value={tz}
              onChange={(e) => setTz(e.target.value)}
              placeholder="Asia/Karachi"
              className="font-mono text-xs"
              required
            />
          </label>
        </div>
        <div className="sm:col-span-2">
          <Button
            type="submit"
            disabled={submitting}
            className="h-10 w-full px-5 font-medium sm:w-auto"
          >
            {submitting ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Scheduling…
              </>
            ) : (
              "Schedule brief"
            )}
          </Button>
        </div>
      </form>

      {error && (
        <p className="mt-3 text-xs text-rose-600 dark:text-rose-400">{error}</p>
      )}
      {success && (
        <p className="mt-3 text-xs text-emerald-600 dark:text-emerald-400">
          {success}
        </p>
      )}

      <div className="mt-6 border-t border-zinc-200 pt-5 dark:border-zinc-800">
        <h3 className="mb-3 text-xs font-medium uppercase tracking-wider text-zinc-500 dark:text-zinc-500">
          Scheduled briefs
        </h3>
        {loading ? (
          <p className="text-xs text-zinc-500 dark:text-zinc-500">Loading…</p>
        ) : subs.length === 0 ? (
          <p className="text-xs text-zinc-500 dark:text-zinc-500">
            No briefs scheduled yet.
          </p>
        ) : (
          <ul className="flex flex-col gap-2">
            {subs.map((sub) => (
              <li
                key={sub.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs dark:border-zinc-800 dark:bg-zinc-900"
              >
                <div className="flex flex-col gap-0.5 font-mono text-zinc-700 dark:text-zinc-300">
                  <span>
                    <span className="text-zinc-400 dark:text-zinc-600">
                      repo
                    </span>{" "}
                    {sub.repo}
                  </span>
                  <span className="text-zinc-500 dark:text-zinc-500">
                    {formatTime(sub.hour, sub.minute)} {sub.timezone} · chat{" "}
                    {sub.chat_id} · token {sub.bot_token_masked}
                  </span>
                </div>
                <div className="flex gap-1.5">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => handleTrigger(sub.id)}
                    className="h-7 gap-1 px-2 text-[11px]"
                  >
                    <Send className="size-3" />
                    Send now
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => handleDelete(sub.id)}
                    className="h-7 gap-1 px-2 text-[11px] text-rose-600 hover:text-rose-700 dark:text-rose-400 dark:hover:text-rose-300"
                  >
                    <Trash2 className="size-3" />
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
