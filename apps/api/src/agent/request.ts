import { BadRequestException } from '@nestjs/common';

// Matches the agent's own OTM_DEMO_MAX_QUERY_CHARS default. Capping here is
// defense-in-depth: it stops a multi-megabyte `query` from being proxied into
// the LLM prompt (inflating token cost) before it ever reaches the agent.
export const MAX_QUERY_CHARS = 500;

/** Validate + bound the user's question. Rejects empty/non-string input and
 *  trims to the length cap so an oversized body can't drive up cost. */
export function sanitizeQuery(query: unknown): string {
  if (typeof query !== 'string') {
    throw new BadRequestException('query must be a string');
  }
  const trimmed = query.trim();
  if (!trimmed) {
    throw new BadRequestException('query must not be empty');
  }
  return trimmed.slice(0, MAX_QUERY_CHARS);
}

/** Resolve the client IP the demo rate-limiter should key on.
 *
 *  Prefers `Fly-Client-IP`, which Fly's edge injects from the real TCP peer and
 *  a caller cannot forge. The raw `X-Forwarded-For` is client-settable, so
 *  keying on it lets an attacker hitting the public BFF directly rotate the
 *  header to mint unlimited rate-limit buckets. Falls back to the first
 *  forwarded hop only when there is no Fly header (local dev / other hosts). */
export function clientIp(headers: Record<string, string | undefined>): string | undefined {
  const fly = headers['fly-client-ip'];
  if (fly) return fly.trim();
  const fwd = headers['x-forwarded-for'];
  if (fwd) return fwd.split(',')[0]?.trim() || undefined;
  return undefined;
}
