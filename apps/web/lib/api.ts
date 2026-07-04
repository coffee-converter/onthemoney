import type { ScoreboardData, Step } from './types';

const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001';

const STREAM_EVENTS = ['tool_use', 'tool_result', 'text', 'result', 'answer'];

// Opens the BFF server-sent-events stream and calls onStep for each event.
// Returns a cleanup function that closes the stream.
export function streamAsk(query: string, onStep: (step: Step) => void): () => void {
  const url = `${BASE}/ask/stream?query=${encodeURIComponent(query)}`;
  const source = new EventSource(url);
  for (const name of STREAM_EVENTS) {
    source.addEventListener(name, (ev) => {
      try {
        onStep(JSON.parse((ev as MessageEvent).data) as Step);
      } catch {
        // ignore malformed frames
      }
      if (name === 'answer') source.close();
    });
  }
  source.onerror = () => source.close();
  return () => source.close();
}

export async function fetchScoreboard(): Promise<ScoreboardData> {
  const res = await fetch(`${BASE}/scoreboard`);
  if (!res.ok) throw new Error(`scoreboard responded ${res.status}`);
  return (await res.json()) as ScoreboardData;
}
