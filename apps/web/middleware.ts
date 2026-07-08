import { NextRequest, NextResponse } from 'next/server';

// Proxy /api/bff/* to the BFF, and stamp each request with the true end-user IP.
//
// The BFF sits behind this Vercel edge, so at the BFF the TCP peer is Vercel,
// not the user - its Fly-Client-IP is a rotating Vercel edge address, useless
// for per-user rate limiting. Vercel, however, knows the real client. We resolve
// it here and forward it as x-otm-real-ip, stamped with a shared secret so the
// BFF can trust it came from our edge (see clientIp() in apps/api). We strip any
// client-supplied stamp first so a caller cannot smuggle a forged IP through.
//
// This does the rewrite itself (rather than next.config `rewrites`) so the stamp
// is guaranteed to reach the destination. A rewrite is an edge passthrough, so
// the agent's SSE trace still streams (a Vercel *function* would buffer it).
export const config = { matcher: '/api/bff/:path*' };

export function middleware(req: NextRequest): NextResponse {
  const bff = process.env.BFF_INTERNAL_URL || 'http://localhost:3001';
  const url = new URL(req.url);
  const dest = new URL(bff + url.pathname.replace(/^\/api\/bff/, '') + url.search);

  const clientIp =
    req.headers.get('x-real-ip')?.trim() ||
    req.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ||
    '';

  const headers = new Headers(req.headers);
  headers.delete('x-otm-real-ip');
  headers.delete('x-otm-edge-secret');
  const secret = process.env.OTM_EDGE_SECRET;
  if (secret && clientIp) {
    headers.set('x-otm-real-ip', clientIp);
    headers.set('x-otm-edge-secret', secret);
  }

  return NextResponse.rewrite(dest, { request: { headers } });
}
