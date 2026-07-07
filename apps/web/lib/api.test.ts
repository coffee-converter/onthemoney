import { describe, it, expect, vi, afterEach } from 'vitest';
import { fetchScoreboard, STREAM_EVENTS } from './api';

describe('stream contract', () => {
  it('subscribes to the telemetry event', () => {
    expect(STREAM_EVENTS).toContain('telemetry');
  });
});

describe('fetchScoreboard', () => {
  afterEach(() => vi.restoreAllMocks());

  it('returns parsed scoreboard json', async () => {
    const payload = { item_count: 3, accuracy: 1 };
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => payload }),
    );
    const data = await fetchScoreboard();
    expect(data.item_count).toBe(3);
  });

  it('throws on a non-ok response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }));
    await expect(fetchScoreboard()).rejects.toThrow();
  });
});
