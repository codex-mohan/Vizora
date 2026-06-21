import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  turbopack: {
    root: process.cwd(),
  },
  allowedDevOrigins: [
    "vizora.localhost",
    "*.vizora.localhost",
    "frontend.localhost",
    "*.frontend.localhost",
    "api.localhost",
  ],
};

export default nextConfig;
