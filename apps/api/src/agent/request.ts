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
 *  In production the request path is user -> Vercel edge -> this BFF, so the
 *  BFF's real TCP peer is Vercel, not the user: `Fly-Client-IP` is a rotating
 *  Vercel edge address, useless for per-user limiting. Vercel does know the true
 *  client, and our edge middleware forwards it as `x-otm-real-ip`, stamped with
 *  a shared `OTM_EDGE_SECRET` so we can tell it came from our own edge. We trust
 *  that IP only when the stamp matches; a direct caller to the public BFF has no
 *  secret, so it can never forge an IP this way.
 *
 *  Without a valid stamp we fall back to `Fly-Client-IP`, the real TCP peer that
 *  Fly injects and a caller cannot forge. The raw `X-Forwarded-For` is
 *  client-settable, so it is only a last-resort fallback for local dev / other
 *  hosts where no Fly header exists. */
export function clientIp(
  headers: Record<string, string | undefined>,
  edgeSecret: string | undefined = process.env.OTM_EDGE_SECRET,
): string | undefined {
  const stamp = headers['x-otm-edge-secret'];
  const realIp = headers['x-otm-real-ip'];
  if (edgeSecret && stamp === edgeSecret && realIp) return realIp.trim();
  const fly = headers['fly-client-ip'];
  if (fly) return fly.trim();
  const fwd = headers['x-forwarded-for'];
  if (fwd) return fwd.split(',')[0]?.trim() || undefined;
  return undefined;
}
