import type { Telemetry } from '../lib/types';

function tokens(n: number): string {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k tok` : `${n} tok`;
}

export function RunStats({ telemetry }: { telemetry: Telemetry }) {
  const t = telemetry;
  const secs = (t.elapsed_ms / 1000).toFixed(1);
  const failed = t.tool_failures > 0;
  return (
    <details className="run-stats">
      <summary>
        {t.tool_calls} tools · {secs}s · {tokens(t.input_tokens + t.output_tokens)} ·{' '}
        ~${t.est_cost_usd.toFixed(2)} ·{' '}
        <span className={failed ? 'run-stats-warn' : ''}>
          {failed ? `${t.tool_failures} tool${t.tool_failures === 1 ? '' : 's'} failed — recovered` : '0 failures'}
        </span>
        {' '}<a href="/how-it-works">how this works ▸</a>
      </summary>
      <ul className="run-stats-detail">
        <li>model {t.model} · {t.turns} turns</li>
        <li>{t.input_tokens.toLocaleString()} in / {t.output_tokens.toLocaleString()} out tokens</li>
        {t.per_tool.map((p, i) => (
          <li key={i} className={p.ok ? '' : 'run-stats-warn'}>
            {p.name} · {p.ms}ms{p.ok ? '' : ' · failed'}
          </li>
        ))}
      </ul>
    </details>
  );
}
