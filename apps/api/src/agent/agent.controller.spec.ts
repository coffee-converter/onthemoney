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
    controller.stream('Who funds AZ-06?').subscribe((e) => {
      expect(e.type).toBe('tool_use');
      done();
    });
  });
});
