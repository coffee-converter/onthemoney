import type { ScoreboardData, Step, RosterCandidate, Scene } from './types';

const BASE = process.env.NEXT_PUBLIC_API_URL || '/api/bff';

export const STREAM_EVENTS = ['tool_use', 'tool_result', 'text', 'result', 'telemetry', 'answer'];

// Opens the BFF server-sent-events stream and calls onStep for each event.
// `onError` fires once if the connection drops before the terminal `answer`
// event arrives (BFF down, agent 5xx, network blip) — the caller uses it to
// clear the busy state and show a retry, instead of spinning forever.
// Returns a cleanup function that closes the stream.
export function streamAsk(
  query: string,
  onStep: (step: Step) => void,
  onError?: () => void,
): () => void {
  const url = `${BASE}/ask/stream?query=${encodeURIComponent(query)}`;
  const source = new EventSource(url);
  // Once we've seen the terminal `answer` (or the caller tore us down), a
  // subsequent onerror is just the normal post-close and must not be surfaced.
  let settled = false;
  for (const name of STREAM_EVENTS) {
    source.addEventListener(name, (ev) => {
      try {
        const parsed = JSON.parse((ev as MessageEvent).data) as Record<string, unknown>;
        // the answer event's payload has no `type` field; tag it from the event name
        onStep({ ...parsed, type: (parsed.type as string) ?? name } as Step);
      } catch {
        // ignore malformed frames
      }
      if (name === 'answer') {
        settled = true;
        source.close();
      }
    });
  }
  source.onerror = () => {
    source.close();
    if (!settled) {
      settled = true;
      onError?.();
    }
  };
  return () => {
    settled = true;
    source.close();
  };
}

export async function fetchScoreboard(): Promise<ScoreboardData> {
  const res = await fetch(`${BASE}/scoreboard`);
  if (!res.ok) throw new Error(`scoreboard responded ${res.status}`);
  return (await res.json()) as ScoreboardData;
}

export async function fetchRoster(state: string, district: string): Promise<RosterCandidate[]> {
  const res = await fetch(`${BASE}/district/${state}/${district}/candidates`);
  if (!res.ok) throw new Error(`roster responded ${res.status}`);
  const data = (await res.json()) as { candidates?: RosterCandidate[] };
  return data.candidates ?? [];
}

export async function fetchCandidateScene(
  candId: string,
  state: string,
  district: string,
): Promise<{ scene: Scene | null; receipts: string | null; individual_total: string | null }> {
  const url = `${BASE}/candidate/${encodeURIComponent(candId)}/scene?state=${encodeURIComponent(
    state,
  )}&district=${encodeURIComponent(district)}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`candidate scene responded ${res.status}`);
  return res.json();
}
