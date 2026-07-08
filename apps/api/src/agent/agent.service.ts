import { Injectable } from '@nestjs/common';
import { Observable } from 'rxjs';
import { StreamMessage } from './dto';

@Injectable()
export class AgentService {
  private readonly base = process.env.AGENT_URL || 'http://localhost:8000';

  // Forward the resolved client IP on the secret-gated proxy hop as a dedicated
  // trusted header, rather than passing through the client-settable
  // X-Forwarded-For. The agent keys its rate limiter on x-otm-client-ip.
  private agentHeaders(clientIp?: string): Record<string, string> {
    const h: Record<string, string> = {};
    if (process.env.OTM_PROXY_SECRET) h['x-otm-proxy-secret'] = process.env.OTM_PROXY_SECRET;
    if (clientIp) h['x-otm-client-ip'] = clientIp;
    return h;
  }

  async ask(query: string, clientIp?: string): Promise<unknown> {
    const res = await fetch(`${this.base}/ask`, {
      method: 'POST',
      headers: { 'content-type': 'application/json', ...this.agentHeaders(clientIp) },
      body: JSON.stringify({ query }),
    });
    if (!res.ok) {
      throw new Error(`agent service responded ${res.status}`);
    }
    return res.json();
  }

  async roster(state: string, district: string): Promise<unknown> {
    const res = await fetch(`${this.base}/district/${state}/${district}/candidates`, {
      headers: this.agentHeaders(),
    });
    if (!res.ok) {
      throw new Error(`agent service responded ${res.status}`);
    }
    return res.json();
  }

  async candidateScene(candId: string, state: string, district: string): Promise<unknown> {
    const url = `${this.base}/candidate/${encodeURIComponent(candId)}/scene?state=${encodeURIComponent(
      state,
    )}&district=${encodeURIComponent(district)}`;
    const res = await fetch(url, { headers: this.agentHeaders() });
    if (!res.ok) {
      throw new Error(`agent service responded ${res.status}`);
    }
    return res.json();
  }

  stream(query: string, clientIp?: string): Observable<StreamMessage> {
    const url = `${this.base}/ask/stream?query=${encodeURIComponent(query)}`;
    return new Observable<StreamMessage>((subscriber) => {
      const controller = new AbortController();
      (async () => {
        const res = await fetch(url, {
          signal: controller.signal,
          headers: this.agentHeaders(clientIp),
        });
        if (!res.ok || !res.body) {
          throw new Error(`agent stream responded ${res.status}`);
        }
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n');
          let idx = buffer.indexOf('\n\n');
          while (idx >= 0) {
            const frame = buffer.slice(0, idx);
            buffer = buffer.slice(idx + 2);
            let event = 'message';
            let data = '';
            for (const line of frame.split('\n')) {
              if (line.startsWith('event:')) event = line.slice(6).trim();
              else if (line.startsWith('data:')) data += line.slice(5).trim();
            }
            if (data) subscriber.next({ type: event, data });
            idx = buffer.indexOf('\n\n');
          }
        }
        subscriber.complete();
      })().catch((err) => subscriber.error(err));
      return () => controller.abort();
    });
  }
}
