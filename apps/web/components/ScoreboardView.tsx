import type { ScoreboardData } from '../lib/types';

function pct(x: number): string {
  return `${(x * 100).toFixed(0)}%`;
}

function yn(b: boolean): string {
  return b ? 'pass' : 'fail';
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span className="metric-value">{value}</span>
      <span className="metric-label">{label}</span>
    </div>
  );
}

export function ScoreboardView({ data }: { data: ScoreboardData }) {
  return (
    <div className="scoreboard">
      <h2>Eval scoreboard</h2>
      <p className="subtle">
        Graded against provable FEC ground truth. {data.item_count} cases.
      </p>
      {data.coverage && (
        <p className="subtle coverage">
          Dataset: {data.coverage.districts.toLocaleString()} House districts ·{' '}
          {data.coverage.candidates.toLocaleString()} candidates ·{' '}
          {data.coverage.contributions.toLocaleString()} individual contributions ·{' '}
          {data.coverage.cycle} cycle
        </p>
      )}
      <div className="metrics">
        <Metric label="Accuracy" value={pct(data.accuracy)} />
        <Metric label="Trajectory" value={pct(data.trajectory_accuracy)} />
        <Metric label="Scene" value={pct(data.scene_accuracy)} />
        <Metric label="Neutrality" value={pct(data.neutrality_accuracy)} />
        <Metric label="Brier" value={data.brier.toFixed(3)} />
      </div>
      <table>
        <thead>
          <tr>
            <th>Item</th>
            <th>Correct</th>
            <th>Trajectory</th>
            <th>Scene</th>
            <th>Neutral</th>
            <th>Confidence</th>
          </tr>
        </thead>
        <tbody>
          {data.items.map((it) => (
            <tr key={it.id}>
              <td>{it.id}</td>
              <td>{yn(it.correct)}</td>
              <td>{yn(it.trajectory_ok)}</td>
              <td>{yn(it.scene_ok)}</td>
              <td>{yn(it.neutral_ok)}</td>
              <td>{it.confidence}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
