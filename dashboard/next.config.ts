import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable standalone output so the Docker image can ship just the files it needs.
  output: "standalone",
};

export default nextConfig;
