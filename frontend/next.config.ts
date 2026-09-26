import type { NextConfig } from "next";
import { initOpenNextCloudflareForDev } from "@opennextjs/cloudflare";

const nextConfig: NextConfig = {
  reactCompiler: true,
  // Self-contained server in .next/standalone for the Docker image (frontend/Dockerfile).
  // OpenNext's Cloudflare build does its own output tracing and cannot use this mode, so
  // skip it there (scripts/cf:* set OPEN_NEXT_CLOUDFLARE; Cloudflare's git build sets it too).
  ...(process.env.OPEN_NEXT_CLOUDFLARE ? {} : { output: "standalone" as const }),
};

// Makes `next dev` under `wrangler dev` / `opennextjs-cloudflare preview` see Cloudflare
// bindings. A no-op outside that context.
initOpenNextCloudflareForDev();

export default nextConfig;
