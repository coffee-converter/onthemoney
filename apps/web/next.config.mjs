/** @type {import('next').NextConfig} */
const nextConfig = {
  // MapLibre initializes a WebGL map in a useEffect; React 18 StrictMode's
  // dev-only mount/unmount/mount double-invoke tears the map down and leaves a
  // blank canvas. Production builds do not double-invoke.
  reactStrictMode: false,
  // The /api/bff/* proxy lives in middleware.ts (not a `rewrites()` entry here):
  // it rewrites the same edge-passthrough way that streams the SSE trace, and
  // additionally stamps each request with the true client IP for the demo rate
  // limiter. See middleware.ts for why the stamp is needed.
};

export default nextConfig;
