import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Built as plain static files so it can be hosted for free as a Render Static Site.
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
};

export default nextConfig;
