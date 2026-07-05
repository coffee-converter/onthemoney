import { Test } from '@nestjs/testing';
import { ScoreboardController } from './scoreboard.controller';
import { ScoreboardService } from './scoreboard.service';

describe('ScoreboardController', () => {
  let controller: ScoreboardController;

  beforeEach(async () => {
    const mod = await Test.createTestingModule({
      controllers: [ScoreboardController],
      providers: [ScoreboardService],
    }).compile();
    controller = mod.get(ScoreboardController);
  });

  it('serves the eval scoreboard artifact', () => {
    const sb: any = controller.get();
    expect(sb.item_count).toBe(5);
    expect(sb.accuracy).toBe(1.0);
    expect(Array.isArray(sb.items)).toBe(true);
  });
});
