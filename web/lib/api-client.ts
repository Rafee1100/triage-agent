import type { Ranking } from "./types";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function fetchRanking(repoSlug: string): Promise<Ranking> {
  const res = await fetch(`${API_URL}/rank/${repoSlug}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`fetchRanking failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export function streamRanking(
  repoSlug: string,
  onEvent: (type: string, data: unknown) => void,
): { close: () => void } {
  const source = new EventSource(`${API_URL}/rank/${repoSlug}/stream`);

  const eventTypes = [
    "pipeline_started",
    "agent_completed",
    "synthesizer_completed",
    "critic_completed",
    "pipeline_done",
    "error",
  ] as const;

  for (const type of eventTypes) {
    source.addEventListener(type, (ev: MessageEvent) => {
      try {
        const parsed = JSON.parse(ev.data);
        onEvent(type, parsed);
      } catch {
        onEvent(type, ev.data);
      }
    });
  }

  source.onerror = () => {
    onEvent("error", { error: "stream connection lost" });
    source.close();
  };

  return {
    close: () => source.close(),
  };
}
