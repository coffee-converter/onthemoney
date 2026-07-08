'use client';
import { useEffect, useRef, useState, type FormEvent } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { track } from '@vercel/analytics';
import { streamAsk } from '../lib/api';
import type { Answer, Candidate, Scene, Step, Telemetry } from '../lib/types';
import { ConfidenceChip } from './ConfidenceChip';
import { Citations } from './Citations';
import { RunStats } from './RunStats';

const SAMPLE = 'Who funds the representative in IL-5?';

// Shown on the empty state to teach the range of questions and let a first-time
// visitor start with one click.
const EXAMPLES = [
  'Who funds the representative in NY-14?',
  "Where does Marjorie Taylor Greene's money come from?",
  'What industries fund NY-14?',
  'Show House funding by state as a heat map',
  'Who are the 10 best-funded House candidates?',
  'How competitive is the race in TX-15?',
];

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
  find_candidate: { active: 'Looking up the candidate', done: 'Candidate found' },
  funding_summary: { active: 'Pulling FEC funding totals', done: 'Funding totals retrieved' },
  top_donors: { active: 'Ranking the largest donors', done: 'Top donors ranked' },
  industry_breakdown: { active: 'Breaking donations down by industry', done: 'Industry breakdown ready' },
  top_employers: { active: 'Ranking the top employers', done: 'Top employers ranked' },
  donor_geography: { active: 'Mapping where donors are', done: 'Donor geography ready' },
  funding_timeline: { active: 'Tracing the money over time', done: 'Timeline ready' },
  donor_size_breakdown: { active: 'Splitting small vs large donors', done: 'Donor sizes ready' },
  top_candidates: { active: 'Ranking candidates nationwide', done: 'Nationwide ranking ready' },
  race_summary: { active: 'Sizing up the race', done: 'Race summary ready' },
  state_field: { active: 'Gathering the statewide field', done: 'Statewide field ready' },
  map_state: { active: 'Mapping the state', done: 'State map ready' },
  map_nation: { active: 'Mapping the whole country', done: 'National map ready' },
  map_candidates: { active: 'Mapping the top candidates', done: 'Candidate map ready' },
  render_map: { active: 'Drawing the map', done: 'Map drawn' },
  highlight_district: { active: 'Locating the district', done: 'District located' },
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
}: {
  onScene: (s: Scene) => void;
  onCandidate: (c: Candidate | null) => void;
  onReset?: () => void;
}) {
  const [query, setQuery] = useState(SAMPLE);
  const [steps, setSteps] = useState<Step[]>([]);
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [telemetry, setTelemetry] = useState<Telemetry | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Holds the active stream's cleanup so we can cancel it on unmount (and before
  // starting a new one), so a navigated-away stream can't keep firing callbacks.
  const streamCleanup = useRef<(() => void) | null>(null);
  useEffect(() => () => streamCleanup.current?.(), []);

  function runQuery(q: string) {
    if (!q.trim() || busy) return;
    track('ask', { queryLength: q.length });
    streamCleanup.current?.();
    setQuery(q);
    setSteps([]);
    setAnswer(null);
    setTelemetry(null);
    setError(null);
    setBusy(true);
    onReset?.();
    let sceneRendered = false;
    let loadingScenePending = false;
    let cand: Candidate | null = null;
    let districtKey: string | undefined;
    let pulsedKey = '';
    let fundingCandId = '';
    streamCleanup.current = streamAsk(q, (step) => {
      if (step.type === 'answer') {
        const a = step as unknown as Answer;
        setAnswer(a);
        // Only render here if emit_scene didn't already - avoids re-running the
        // draw-in animation when the final answer arrives.
        if (a.scene && !sceneRendered) {
          onScene(a.scene);
        } else if (!sceneRendered && loadingScenePending && districtKey) {
          // We pulsed a district while the answer streamed, but no map ever
          // arrived (the scene tool errored, or the answer was text-only). Settle
          // the pulse on the seat rather than leaving it spinning forever. The
          // (0,0) camera tells the map to frame the district from its geometry.
          const [st, di] = districtKey.split('-');
          onScene({
            highlight: { state: st, district: di },
            camera: { type: 'flyTo', lon: 0, lat: 0, zoom: 7 },
            flows: [],
          });
        }
        setBusy(false);
        return;
      }
      if (step.type === 'telemetry') {
        setTelemetry(step as unknown as Telemetry);
        return;
      }
      // As soon as the district is identified, render it (pulsing) while the
      // rest of the answer is still being fetched.
      if (step.type === 'tool_use' && step.name === 'resolve_entity' && step.input) {
        const st = String(step.input.state ?? '').toUpperCase();
        const rawDi = step.input.district;
        if (st.length === 2 && rawDi != null && rawDi !== '') {
          districtKey = `${st}-${String(rawDi).padStart(2, '0')}`;
          // The agent can call resolve_entity more than once in a run; only pulse
          // and zoom to a given district the first time, so the map doesn't
          // re-zoom to the same seat twice.
          if (districtKey !== pulsedKey) {
            pulsedKey = districtKey;
            onCandidate(null); // swap out the old card only once a new district is understood
            onScene({
              highlight: { state: st, district: String(rawDi).padStart(2, '0') },
              camera: { type: 'flyTo', lon: 0, lat: 0, zoom: 7 },
              flows: [],
              loading: true,
            });
            loadingScenePending = true;
          }
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
      // Name-based lookups resolve through find_candidate, not resolve_entity, so
      // pick the top match as the active candidate too.
      if (
        step.type === 'tool_result' &&
        step.name === 'find_candidate' &&
        !step.payload?.insufficient
      ) {
        const m = (step.payload?.matches as
          | { cand_id?: string; name?: string; party?: string; state?: string; district?: string }[]
          | undefined)?.[0];
        if (m?.cand_id) {
          districtKey = `${String(m.state ?? '').toUpperCase()}-${String(m.district ?? '').padStart(2, '0')}`;
          cand = { cand_id: m.cand_id, name: m.name ?? '', party: m.party, district: districtKey };
          onCandidate(cand);
        }
      }
      if (step.type === 'tool_use' && step.name === 'funding_summary') {
        fundingCandId = String(step.input?.cand_id ?? '');
      }
      // Totals once funding returns - only for the resolved (primary) candidate,
      // so a comparison's other candidate cannot overwrite the card.
      if (
        step.type === 'tool_result' &&
        step.name === 'funding_summary' &&
        cand &&
        fundingCandId === cand.cand_id
      ) {
        cand = {
          ...cand,
          receipts: (step.payload?.receipts as string) ?? cand.receipts,
          individualTotal: (step.payload?.individual_total as string) ?? cand.individualTotal,
        };
        onCandidate(cand);
      }
      if (
        step.type === 'tool_result' &&
        ['emit_scene', 'render_map', 'map_state', 'map_nation', 'map_candidates',
          'highlight_district'].includes(step.name ?? '') &&
        step.payload &&
        !('insufficient' in step.payload) &&
        !('error' in step.payload)
      ) {
        onScene(step.payload as unknown as Scene);
        sceneRendered = true;
      }
    }, () => {
      // The stream dropped before an answer arrived. Clear the spinner and let
      // the user retry rather than leaving "Working…" hanging forever.
      setBusy(false);
      setError('The connection dropped before the answer finished. Please try again.');
    });
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    runQuery(query);
  }

  const acts = activities(steps);
  const idle = !busy && !answer && steps.length === 0;

  return (
    <div className="chat">
      <div className="chat-top">
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
      </div>

      <div className="chat-results">
      {idle && (
        <div className="intro">
          <p className="intro-lead">
            On The Money traces where U.S. House campaign money comes from. Ask in plain
            English and the agent pulls the 2024 FEC filings, works through the data, and
            draws the answer on the map. Every figure is sourced and confidence-scored.
          </p>
          <p className="intro-label">Try one of these</p>
          <div className="intro-chips">
            {EXAMPLES.map((q) => (
              <button key={q} type="button" className="chip" onClick={() => runQuery(q)}>
                {q}
              </button>
            ))}
          </div>
        </div>
      )}
      <ol className="trace">
        {acts.map((a, i) => (
          <li key={i} className={a.done ? 'trace-done' : 'trace-active'}>
            {a.done ? <span className="trace-icon">✓</span> : <span className="trace-spinner" />}
            <span>{friendly(a.name, a.done)}</span>
            {!a.done && <span className="dots" />}
          </li>
        ))}
        {busy && !answer && !acts.some((a) => !a.done) && (
          <li className="trace-active">
            <span className="trace-spinner" />
            <span>{acts.length === 0 ? 'Understanding your question' : 'Composing the answer'}</span>
            <span className="dots" />
          </li>
        )}
      </ol>

      {error && (
        <div className="chat-error" role="alert">
          <span>{error}</span>
          <button type="button" className="chat-retry" onClick={() => runQuery(query)}>
            Retry
          </button>
        </div>
      )}

      {answer && (
        <div className="answer">
          <ConfidenceChip level={answer.confidence} />
          {telemetry && <RunStats telemetry={telemetry} />}
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
            {/* singleTilde:false so the model's "~$80k" (approximately) isn't parsed
                as GFM strikethrough — only real ~~strike~~ is. */}
            <ReactMarkdown remarkPlugins={[[remarkGfm, { singleTilde: false }]]}>
              {answer.text}
            </ReactMarkdown>
          </div>
          <Citations items={answer.citations} />
        </div>
      )}
      </div>
    </div>
  );
}
