import 'reflect-metadata';
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

async function bootstrap(): Promise<void> {
  const app = await NestFactory.create(AppModule);
  // The web app reaches the BFF same-origin through Vercel's `/api/bff` rewrite,
  // so no cross-origin access is needed by default. Only enable CORS (pinned to
  // an explicit origin) if WEB_ORIGIN is set — never the wildcard `*`, which
  // would let any site script this public, unauthenticated proxy.
  if (process.env.WEB_ORIGIN) {
    app.enableCors({ origin: process.env.WEB_ORIGIN });
  }
  const port = process.env.PORT ? Number(process.env.PORT) : 3001;
  await app.listen(port);
}

void bootstrap();
