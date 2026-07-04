import { Body, Controller, Post, Query, Sse } from '@nestjs/common';
import { Observable } from 'rxjs';
import { AgentService } from './agent.service';
import { AskDto, StreamMessage } from './dto';

@Controller()
export class AgentController {
  constructor(private readonly agent: AgentService) {}

  @Post('ask')
  ask(@Body() dto: AskDto): Promise<unknown> {
    return this.agent.ask(dto.query);
  }

  @Sse('ask/stream')
  stream(@Query('query') query: string): Observable<StreamMessage> {
    return this.agent.stream(query);
  }
}
