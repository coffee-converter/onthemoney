import type { Telemetry } from '../lib/types';

function tokens(n: number): string {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k tok` : `${n} tok`;
}

// Never let a nonzero run read as free: a fraction-of-a-cent estimate keeps
// enough precision to stay above $0.00.
function cost(usd: number): string {
  if (usd > 0 && usd < 0.01) return `~$${usd.toFixed(4)}`;
  return `~$${usd.toFixed(2)}`;
}

export function RunStats({ telemetry }: { telemetry: Telemetry }) {
  const t = telemetry;
  const secs = (t.elapsed_ms / 1000).toFixed(1);
  const failed = t.tool_failures > 0;
  return (
    <details className="run-stats">
      <summary>
        {t.tool_calls} tools · {secs}s · {tokens(t.input_tokens + t.output_tokens)} ·{' '}
        {cost(t.est_cost_usd)} ·{' '}
        <span className={failed ? 'run-stats-warn' : ''}>
          {failed ? `${t.tool_failures} tool${t.tool_failures === 1 ? '' : 's'} failed, recovered` : '0 failures'}
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
