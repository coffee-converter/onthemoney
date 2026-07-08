/** @type {import('next').NextConfig} */
const nextConfig = {
  // MapLibre initializes a WebGL map in a useEffect; React 18 StrictMode's
  // dev-only mount/unmount/mount double-invoke tears the map down and leaves a
  // blank canvas. Production builds do not double-invoke.
  reactStrictMode: false,
  // Proxy the BFF as a rewrite (Vercel edge-proxy passthrough), not a route
  // handler. A Vercel *function* buffers the SSE response and flushes it in one
  // batch at close, killing the live agent trace; a rewrite streams it through.
  // The BFF is public (its secret is verified by the private agent, which the
  // BFF calls with its own OTM_PROXY_SECRET), so no auth header is needed here.
  async rewrites() {
    const bff = process.env.BFF_INTERNAL_URL || 'http://localhost:3001';
    return [{ source: '/api/bff/:path*', destination: `${bff}/:path*` }];
  },
};

export default nextConfig;
