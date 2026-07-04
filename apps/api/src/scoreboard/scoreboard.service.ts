import { Injectable } from '@nestjs/common';
import { readFileSync } from 'fs';
import { join } from 'path';

@Injectable()
export class ScoreboardService {
  private readonly path =
    process.env.SCOREBOARD_PATH || join(__dirname, 'scoreboard.json');

  get(): unknown {
    return JSON.parse(readFileSync(this.path, 'utf-8'));
  }
}
