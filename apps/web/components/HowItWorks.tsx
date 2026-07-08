'use client';
import { useEffect, useState } from 'react';
import { fetchScoreboard } from '../lib/api';
import type { ScoreboardData } from '../lib/types';
import { pct } from '../lib/format';
import regression from '../lib/regression.json';

export function HowItWorks() {
  const [board, setBoard] = useState<ScoreboardData | null>(null);
  useEffect(() => {
    fetchScoreboard().then(setBoard).catch(() => setBoard(null));
  }, []);
  const r = regression as typeof regression;

  return (
    <div className="how">
      <h1>Under the hood</h1>
      <p className="subtle">How On The Money answers a question, and how we know the answer is trustworthy.</p>

      <section>
        <h2>1 · Grounded by construction</h2>
        <p>The agent never invents a number or a coordinate. It states only what a tool
        returned, and it draws maps by naming semantic ids (a district, a value, a color);
        the backend resolves those to real geometry. A map is provably correct or it does
        not render.</p>
      </section>

      <section>
        <h2>2 · Verify &amp; calibrate</h2>
        <p>Before an answer ships, a verify step re-derives the district's true total from
        the ground-truth store and compares it to what the model claimed. If it cannot be
        verified, confidence is downgraded to <em>insufficient evidence</em> rather than
        guessing. That is why answers carry an honest High / Partial / Insufficient signal.</p>
      </section>

      <section>
        <h2>3 · Evaluated &amp; gated</h2>
        {board && (
          <div className="how-metrics">
            <span>answer accuracy {pct(board.accuracy)}</span>
            <span>trajectory {pct(board.trajectory_accuracy)}</span>
            <span>neutrality {pct(board.neutrality_accuracy)}</span>
            <span>Brier {board.brier.toFixed(3)}</span>
          </div>
        )}
        <p className="subtle">
          These are the <strong>deterministic recorded baseline</strong>: the reference
          replay the CI gate grades against ground truth. Real-model accuracy comes from the
          live eval run (<code>run_live</code>).
        </p>
        <div className="how-regression">
          <h3>A caught regression</h3>
          <p>Seed a units bug that drifts every high-confidence total 10% low
          (e.g. case <code>{r.case}</code>: {r.clean_total} → {r.broken_total}, across
          {' '}{r.cases_affected} cases), still reported confidently, and the gate flips
          from pass to fail:</p>
          <table>
            <thead><tr><th></th><th>accuracy</th><th>Brier</th><th>gate</th></tr></thead>
            <tbody>
              <tr><td>clean</td><td>{pct(r.before.accuracy)}</td><td>{r.before.brier}</td>
                <td>{r.before.passes ? 'pass' : 'fail'}</td></tr>
              <tr><td>with bug</td><td>{pct(r.after.accuracy)}</td><td>{r.after.brier}</td>
                <td className="run-stats-warn">{r.after.passes ? 'pass' : 'fail'}</td></tr>
            </tbody>
          </table>
          <p className="subtle">Reproduce with <code>make regression-demo</code>.</p>
        </div>
      </section>

      <section>
        <h2>4 · Operated, not just built</h2>
        <p>Every answer carries a live read-out: how many tools ran, wall-clock latency, the
        tokens spent, an estimated cost, and how many tool calls failed and recovered. A tool
        error is caught and counted, never a dead stream. Open the run-stats line under any
        answer to see it.</p>
      </section>
    </div>
  );
}
