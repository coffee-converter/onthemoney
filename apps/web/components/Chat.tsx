'use client';
import { useState, type FormEvent } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { streamAsk } from '../lib/api';
import type { Answer, Scene, Step } from '../lib/types';
import { ConfidenceChip } from './ConfidenceChip';
import { Citations } from './Citations';

const SAMPLE = 'Who funds the representative in IL-5?';

function money(x: string | null | undefined): string | null {
  if (!x) return null;
  const n = parseFloat(x);
  if (!isFinite(n)) return null;
  return `$${Math.round(n).toLocaleString()}`;
}

// Human-facing narration for each tool, instead of leaking raw function names.
const FRIENDLY: Record<string, { active: string; done: string }> = {
  resolve_entity: { active: 'Identifying the candidate', done: 'Candidate identified' },
  resolve_candidate: { active: 'Identifying the candidate', done: 'Candidate identified' },
  funding_summary: { active: 'Pulling FEC funding totals', done: 'Funding totals retrieved' },
  top_donors: { active: 'Ranking the largest donors', done: 'Top donors ranked' },
  emit_scene: { active: 'Mapping the money by state', done: 'Map rendered' },
};

function friendly(name: string, done: boolean): string {
  const f = FRIENDLY[name];
  if (f) return done ? f.done : f.active;
  const h = name.replace(/_/g, ' ');
  return done ? `${h} complete` : h;
}

type Activity = { name: string; done: boolean };

// Collapse the tool_use/tool_result stream into one activity per tool call,
// flipping to done when its result arrives.
function activities(steps: Step[]): Activity[] {
  const acts: Activity[] = [];
  for (const s of steps) {
    const name = s.name;
    if (!name) continue;
    if (s.type === 'tool_use') acts.push({ name, done: false });
    else if (s.type === 'tool_result') {
      for (let i = acts.length - 1; i >= 0; i--) {
        if (acts[i].name === name && !acts[i].done) {
          acts[i].done = true;
          break;
        }
      }
    }
  }
  return acts;
}

export function Chat({ onScene }: { onScene: (s: Scene) => void }) {
  const [query, setQuery] = useState(SAMPLE);
  const [steps, setSteps] = useState<Step[]>([]);
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [busy, setBusy] = useState(false);

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!query.trim() || busy) return;
    setSteps([]);
    setAnswer(null);
    setBusy(true);
    streamAsk(query, (step) => {
      if (step.type === 'answer') {
        const a = step as unknown as Answer;
        setAnswer(a);
        if (a.scene) onScene(a.scene);
        setBusy(false);
        return;
      }
      setSteps((prev) => [...prev, step]);
      if (
        step.type === 'tool_result' &&
        step.name === 'emit_scene' &&
        step.payload &&
        'highlight' in step.payload
      ) {
        onScene(step.payload as unknown as Scene);
      }
    });
  }

  return (
    <div className="chat">
      <h1>On The Money</h1>
      <p className="subtle">Ask how House campaign money flows. 2024 cycle.</p>
      <form onSubmit={submit}>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="question"
        />
        <button type="submit" disabled={busy}>
          {busy ? 'Working' : 'Ask'}
        </button>
      </form>

      <ol className="trace">
        {activities(steps).map((a, i) => (
          <li key={i} className={a.done ? 'trace-done' : 'trace-active'}>
            <span className="trace-icon">{a.done ? '✓' : '○'}</span>
            {friendly(a.name, a.done)}
          </li>
        ))}
      </ol>

      {answer && (
        <div className="answer">
          <ConfidenceChip level={answer.confidence} />
          {(money(answer.receipts) || money(answer.individual_total)) && (
            <div className="stat-row">
              {money(answer.receipts) && (
                <div className="stat">
                  <span className="stat-value">{money(answer.receipts)}</span>
                  <span className="stat-label">total raised</span>
                </div>
              )}
              {money(answer.individual_total) && (
                <div className="stat">
                  <span className="stat-value">{money(answer.individual_total)}</span>
                  <span className="stat-label">from individuals</span>
                </div>
              )}
            </div>
          )}
          <div className="answer-body">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{answer.text}</ReactMarkdown>
          </div>
          <Citations items={answer.citations} />
        </div>
      )}
    </div>
  );
}
