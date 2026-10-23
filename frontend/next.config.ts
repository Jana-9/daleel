import type { NextConfig } from "next";

// Where the FastAPI backend runs. The browser never calls it directly: Next.js forwards
// /api/* to it, so the session cookie stays same-origin and no CORS setup is needed.
// 127.0.0.1 rather than "localhost": on Windows, localhost can resolve to IPv6 (::1)
// while the backend listens on IPv4, which makes the proxy fail to connect.
const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  agentRules: false,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/api/:path*` }];
  },
};

export default nextConfig;
