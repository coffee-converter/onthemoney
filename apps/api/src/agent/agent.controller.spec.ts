import { Test } from '@nestjs/testing';
import { of } from 'rxjs';
import { AgentController } from './agent.controller';
import { AgentService } from './agent.service';

describe('AgentController', () => {
  let controller: AgentController;
  const mock = {
    ask: jest.fn().mockResolvedValue({
      answer: { confidence: 'high', total: '500.00' },
      trace: [],
    }),
    stream: jest.fn().mockReturnValue(of({ type: 'tool_use', data: '{}' })),
  };

  beforeEach(async () => {
    const mod = await Test.createTestingModule({
      controllers: [AgentController],
      providers: [{ provide: AgentService, useValue: mock }],
    }).compile();
    controller = mod.get(AgentController);
  });

  it('proxies ask to the agent service', async () => {
    const res: any = await controller.ask({ query: 'Who funds AZ-06?' });
    expect(res.answer.total).toBe('500.00');
    expect(mock.ask).toHaveBeenCalledWith('Who funds AZ-06?');
  });

  it('relays a stream observable', (done) => {
    controller.stream('Who funds AZ-06?', { headers: {} }).subscribe((e) => {
      expect(e.type).toBe('tool_use');
      done();
    });
  });
});

describe('AgentService.stream telemetry relay', () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('relays a telemetry SSE frame unchanged', (done) => {
    const telemetry = {
      type: 'telemetry',
      model: 'claude-sonnet-4-5',
      turns: 3,
      tool_calls: 2,
      tool_failures: 0,
      input_tokens: 1000,
      output_tokens: 200,
      elapsed_ms: 1500,
      per_tool: [{ name: 'find_candidate', ms: 120, ok: true }],
      est_cost_usd: 0.01,
    };
    const sse = `event: telemetry\ndata: ${JSON.stringify(telemetry)}\n\n`;

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      body: new ReadableStream({
        start(streamController) {
          streamController.enqueue(new TextEncoder().encode(sse));
          streamController.close();
        },
      }),
    }) as unknown as typeof fetch;

    const service = new AgentService();
    service.stream('Who funds AZ-06?').subscribe((msg) => {
      expect(msg.type).toBe('telemetry');
      expect(JSON.parse(msg.data)).toEqual(telemetry);
      done();
    });
  });

  it('forwards proxy secret and client IP to the agent', async () => {
    process.env.OTM_PROXY_SECRET = 'shh';
    const calls: RequestInit[] = [];
    const fake = ((_url: string, init: RequestInit) => {
      calls.push(init);
      return Promise.resolve(new Response('event: answer\ndata: {}\n\n',
        { headers: { 'content-type': 'text/event-stream' } }));
    }) as typeof fetch;
    global.fetch = fake;
    const svc = new AgentService();
    // stream() returns an Observable; subscribe to trigger the fetch.
    await new Promise<void>((res) => svc.stream('hi', '9.9.9.9').subscribe({ complete: res }));
    const headers = new Headers(calls[0].headers);
    expect(headers.get('x-otm-proxy-secret')).toBe('shh');
    expect(headers.get('x-forwarded-for')).toBe('9.9.9.9');
  });
});
