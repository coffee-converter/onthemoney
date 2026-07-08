import { Body, Controller, Get, Param, Post, Query, Req, Sse } from '@nestjs/common';
import { Observable } from 'rxjs';
import { AgentService } from './agent.service';
import { AskDto, StreamMessage } from './dto';
import { clientIp, sanitizeQuery } from './request';

@Controller()
export class AgentController {
  constructor(private readonly agent: AgentService) {}

  @Post('ask')
  ask(
    @Body() dto: AskDto,
    @Req() req: { headers: Record<string, string | undefined> },
  ): Promise<unknown> {
    return this.agent.ask(sanitizeQuery(dto.query), clientIp(req.headers));
  }

  @Sse('ask/stream')
  stream(
    @Query('query') query: string,
    @Req() req: { headers: Record<string, string | undefined> },
  ): Observable<StreamMessage> {
    return this.agent.stream(sanitizeQuery(query), clientIp(req.headers));
  }

  @Get('district/:state/:district/candidates')
  roster(
    @Param('state') state: string,
    @Param('district') district: string,
  ): Promise<unknown> {
    return this.agent.roster(state, district);
  }

  @Get('candidate/:candId/scene')
  candidateScene(
    @Param('candId') candId: string,
    @Query('state') state: string,
    @Query('district') district: string,
  ): Promise<unknown> {
    return this.agent.candidateScene(candId, state, district);
  }
}
