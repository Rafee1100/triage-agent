import type { Subscription, SubscriptionCreate } from "./types";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function listSubscriptions(): Promise<Subscription[]> {
  const res = await fetch(`${API_URL}/subscriptions`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`listSubscriptions failed: ${res.status}`);
  }
  const data = await res.json();
  return data.subscriptions ?? [];
}

export async function createSubscription(
  payload: SubscriptionCreate,
): Promise<Subscription> {
  const res = await fetch(`${API_URL}/subscriptions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail ?? `createSubscription failed: ${res.status}`);
  }
  return res.json();
}

export async function deleteSubscription(id: string): Promise<void> {
  const res = await fetch(`${API_URL}/subscriptions/${id}`, {
    method: "DELETE",
  });
  if (!res.ok && res.status !== 204) {
    throw new Error(`deleteSubscription failed: ${res.status}`);
  }
}

export async function triggerSubscription(id: string): Promise<void> {
  const res = await fetch(`${API_URL}/subscriptions/${id}/trigger`, {
    method: "POST",
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail ?? `triggerSubscription failed: ${res.status}`);
  }
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
    "pipeline_failed",
  ] as const;

  let sawServerError = false;
  let pipelineDone = false;

  for (const type of eventTypes) {
    source.addEventListener(type, (ev: MessageEvent) => {
      if (type === "pipeline_failed") sawServerError = true;
      if (type === "pipeline_done") pipelineDone = true;
      try {
        const parsed = JSON.parse(ev.data);
        onEvent(type, parsed);
      } catch {
        onEvent(type, ev.data);
      }
    });
  }

  source.onerror = () => {
    if (!sawServerError && !pipelineDone) {
      onEvent("pipeline_failed", { error: "stream connection lost" });
    }
    source.close();
  };

  return {
    close: () => source.close(),
  };
}
