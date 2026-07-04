import { Controller, Get } from '@nestjs/common';
import { ScoreboardService } from './scoreboard.service';

@Controller('scoreboard')
export class ScoreboardController {
  constructor(private readonly svc: ScoreboardService) {}

  @Get()
  get(): unknown {
    return this.svc.get();
  }
}
