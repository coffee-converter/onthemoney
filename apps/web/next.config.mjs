/** @type {import('next').NextConfig} */
const nextConfig = {
  // MapLibre initializes a WebGL map in a useEffect; React 18 StrictMode's
  // dev-only mount/unmount/mount double-invoke tears the map down and leaves a
  // blank canvas. Production builds do not double-invoke.
  reactStrictMode: false,
};

export default nextConfig;
