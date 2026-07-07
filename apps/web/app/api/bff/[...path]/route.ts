export const dynamic = 'force-dynamic';

export async function GET(req: Request, ctx: { params: { path: string[] } }) {
  const BFF = process.env.BFF_INTERNAL_URL || 'http://localhost:3001';
  const qs = new URL(req.url).search;
  const target = `${BFF}/${ctx.params.path.join('/')}${qs}`;
  const headers: Record<string, string> = {};
  if (process.env.OTM_PROXY_SECRET) headers['x-otm-proxy-secret'] = process.env.OTM_PROXY_SECRET;
  const fwd = req.headers.get('x-forwarded-for');
  if (fwd) headers['x-forwarded-for'] = fwd;

  const upstream = await fetch(target, { headers });
  return new Response(upstream.body, {
    status: upstream.status,
    headers: { 'content-type': upstream.headers.get('content-type') || 'application/json' },
  });
}
