import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactCompiler: true,
  // Self-contained server in .next/standalone for the Docker image (frontend/Dockerfile).
  output: "standalone",
};

export default nextConfig;
