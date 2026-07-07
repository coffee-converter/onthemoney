import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RunStats } from './RunStats';
import type { Telemetry } from '../lib/types';

const base: Telemetry = {
  model: 'claude-sonnet-5', turns: 3, tool_calls: 4, tool_failures: 0,
  input_tokens: 18000, output_tokens: 400, elapsed_ms: 3200,
  per_tool: [{ name: 'funding_summary', ms: 120, ok: true }], est_cost_usd: 0.04,
};

describe('RunStats', () => {
  it('summarizes tools, latency, tokens, cost', () => {
    render(<RunStats telemetry={base} />);
    expect(screen.getByText(/4 tools/)).toBeTruthy();
    expect(screen.getByText(/3\.2s/)).toBeTruthy();
    expect(screen.getByText(/\$0\.04/)).toBeTruthy();
    expect(screen.getByText(/0 failures/)).toBeTruthy();
  });

  it('flags recovered failures', () => {
    render(<RunStats telemetry={{ ...base, tool_failures: 1 }} />);
    expect(screen.getByText(/1 tool failed/)).toBeTruthy();
  });
});
