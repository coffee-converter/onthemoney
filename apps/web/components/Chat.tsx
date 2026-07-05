'use client';
import { useState, type FormEvent, type ReactNode } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { streamAsk } from '../lib/api';
import type { Answer, Candidate, Scene, Step } from '../lib/types';
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

export function Chat({
  onScene,
  onCandidate,
  onReset,
  roster,
}: {
  onScene: (s: Scene) => void;
  onCandidate: (c: Candidate | null) => void;
  onReset?: () => void;
  roster?: ReactNode;
}) {
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
    onReset?.();
    let sceneRendered = false;
    let cand: Candidate | null = null;
    let districtKey: string | undefined;
    streamAsk(query, (step) => {
      if (step.type === 'answer') {
        const a = step as unknown as Answer;
        setAnswer(a);
        // Only render here if emit_scene didn't already - avoids re-running the
        // draw-in animation when the final answer arrives.
        if (a.scene && !sceneRendered) onScene(a.scene);
        setBusy(false);
        return;
      }
      // As soon as the district is identified, render it (pulsing) while the
      // rest of the answer is still being fetched.
      if (step.type === 'tool_use' && step.name === 'resolve_entity' && step.input) {
        const st = String(step.input.state ?? '').toUpperCase();
        const rawDi = step.input.district;
        if (st.length === 2 && rawDi != null && rawDi !== '') {
          districtKey = `${st}-${String(rawDi).padStart(2, '0')}`;
          onCandidate(null); // swap out the old card only once a new district is understood
          onScene({
            highlight: { state: st, district: String(rawDi).padStart(2, '0') },
            camera: { type: 'flyTo', lon: 0, lat: 0, zoom: 7 },
            flows: [],
            loading: true,
          });
        }
      }
      setSteps((prev) => [...prev, step]);
      // Candidate name/party as soon as the district resolves.
      if (step.type === 'tool_result' && step.name === 'resolve_entity' && step.payload?.found) {
        const c = step.payload.candidate as
          | { name?: string; party?: string; cand_id?: string }
          | undefined;
        cand = { cand_id: c?.cand_id, name: c?.name ?? '', party: c?.party, district: districtKey };
        onCandidate(cand);
      }
      // Totals once funding returns.
      if (step.type === 'tool_result' && step.name === 'funding_summary' && cand) {
        cand = {
          ...cand,
          receipts: (step.payload?.receipts as string) ?? cand.receipts,
          individualTotal: (step.payload?.individual_total as string) ?? cand.individualTotal,
        };
        onCandidate(cand);
      }
      if (
        step.type === 'tool_result' &&
        step.name === 'emit_scene' &&
        step.payload &&
        'highlight' in step.payload
      ) {
        onScene(step.payload as unknown as Scene);
        sceneRendered = true;
      }
    });
  }

  const acts = activities(steps);
  const mapDone = steps.some((s) => s.type === 'tool_result' && s.name === 'emit_scene');

  return (
    <div className="chat">
      <div className="chat-top">
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
      {roster}
      </div>

      <div className="chat-results">
      <ol className="trace">
        {busy && acts.length === 0 && (
          <li className="trace-active">
            <span className="trace-spinner" />
            <span>Understanding your question</span>
            <span className="dots" />
          </li>
        )}
        {acts.map((a, i) => (
          <li key={i} className={a.done ? 'trace-done' : 'trace-active'}>
            {a.done ? <span className="trace-icon">✓</span> : <span className="trace-spinner" />}
            <span>{friendly(a.name, a.done)}</span>
            {!a.done && <span className="dots" />}
          </li>
        ))}
        {busy && !answer && mapDone && (
          <li className="trace-active">
            <span className="trace-spinner" />
            <span>Compiling the donor breakdown</span>
            <span className="dots" />
          </li>
        )}
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
    </div>
  );
}
