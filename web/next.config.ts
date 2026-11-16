import type { NextConfig } from "next";
import { PUBLIC_HOSTS } from "./src/lib/allowed-origins";

const nextConfig: NextConfig = {
  cacheComponents: true,
  experimental: {
    serverActions: { allowedOrigins: [...PUBLIC_HOSTS] },
  },
  allowedDevOrigins: ["127.0.0.1"],
  partialPrefetching: true,
  serverExternalPackages: ["@electric-sql/pglite"],
  // The lead snapshot is read from disk at runtime; make sure it ships with the server build.
  outputFileTracingIncludes: {
    "/**": ["./data/snapshot.json", "./migrations/*.sql"],
  },
  turbopack: {
    // cursor/identity.ts imports its dev sibling with a .js extension (NodeNext style).
    resolveAlias: {
      "./identity.dev.js": "./cursor/identity.dev.ts",
    },
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
