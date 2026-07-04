import { Injectable } from '@nestjs/common';
import { Observable } from 'rxjs';
import { StreamMessage } from './dto';

@Injectable()
export class AgentService {
  private readonly base = process.env.AGENT_URL || 'http://localhost:8000';

  async ask(query: string): Promise<unknown> {
    const res = await fetch(`${this.base}/ask`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ query }),
    });
    if (!res.ok) {
      throw new Error(`agent service responded ${res.status}`);
    }
    return res.json();
  }

  stream(query: string): Observable<StreamMessage> {
    const url = `${this.base}/ask/stream?query=${encodeURIComponent(query)}`;
    return new Observable<StreamMessage>((subscriber) => {
      const controller = new AbortController();
      (async () => {
        const res = await fetch(url, { signal: controller.signal });
        if (!res.ok || !res.body) {
          throw new Error(`agent stream responded ${res.status}`);
        }
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
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
