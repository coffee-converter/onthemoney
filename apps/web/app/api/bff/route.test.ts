import { describe, it, expect, vi } from 'vitest';
import { GET } from './[...path]/route';

describe('BFF proxy route', () => {
  it('injects secret + forwarded IP and preserves the upstream body/type', async () => {
    process.env.OTM_PROXY_SECRET = 'shh';
    process.env.BFF_INTERNAL_URL = 'http://bff.internal';
    const seen: { url: string; init: RequestInit } = { url: '', init: {} };
    vi.stubGlobal('fetch', (url: string, init: RequestInit) => {
      seen.url = url; seen.init = init;
      return Promise.resolve(new Response('event: answer\ndata: {}\n\n',
        { headers: { 'content-type': 'text/event-stream' } }));
    });
    const req = new Request('http://x/api/bff/ask/stream?query=hi', {
      headers: { 'x-forwarded-for': '7.7.7.7' },
    });
    const res = await GET(req, { params: { path: ['ask', 'stream'] } });
    expect(seen.url).toBe('http://bff.internal/ask/stream?query=hi');
    expect(new Headers(seen.init.headers).get('x-otm-proxy-secret')).toBe('shh');
    expect(new Headers(seen.init.headers).get('x-forwarded-for')).toBe('7.7.7.7');
    expect(res.headers.get('content-type')).toBe('text/event-stream');
  });
});
