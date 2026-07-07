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
    // Item count is shape-based so regenerating the artifact doesn't break it...
    expect(Array.isArray(sb.items)).toBe(true);
    expect(sb.item_count).toBeGreaterThan(0);
    expect(sb.item_count).toBe(sb.items.length);
    // ...but the baseline is built deterministically from ground truth, so it
    // must ship perfect and well-calibrated. A degraded baseline is a bug, not
    // a case-count change, and should fail here.
    expect(sb.accuracy).toBe(1);
    expect(sb.brier).toBeLessThan(0.1);
    // Every case lands in exactly one regime bucket.
    const regimeTotal = Object.values(sb.by_regime as Record<string, { count: number }>)
      .reduce((n, r) => n + r.count, 0);
    expect(regimeTotal).toBe(sb.item_count);
  });
});
