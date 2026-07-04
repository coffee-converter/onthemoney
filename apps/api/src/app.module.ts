import { Module } from '@nestjs/common';
import { AgentController } from './agent/agent.controller';
import { AgentService } from './agent/agent.service';
import { ScoreboardController } from './scoreboard/scoreboard.controller';
import { ScoreboardService } from './scoreboard/scoreboard.service';

@Module({
  controllers: [AgentController, ScoreboardController],
  providers: [AgentService, ScoreboardService],
})
export class AppModule {}
