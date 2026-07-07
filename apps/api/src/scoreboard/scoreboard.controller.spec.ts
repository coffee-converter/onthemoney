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
    // Shape-based so regenerating the artifact (case count changes) doesn't break it.
    expect(Array.isArray(sb.items)).toBe(true);
    expect(sb.item_count).toBeGreaterThan(0);
    expect(sb.item_count).toBe(sb.items.length);
    expect(typeof sb.accuracy).toBe('number');
    expect(sb.accuracy).toBeGreaterThanOrEqual(0);
    expect(sb.accuracy).toBeLessThanOrEqual(1);
  });
});
