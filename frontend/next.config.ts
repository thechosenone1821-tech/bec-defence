import type { NextConfig } from "next";

/**
 * Static export, because the Phosphor console is served by the Python apps.
 *
 * `output: "export"` writes a plain `out/` directory that
 * `packages/frontend/gateway.py` serves from `packages/frontend/static`, so
 * no Node process runs in the demo and no Next server has to be reachable.
 * `trailingSlash: true` matches the file-per-route layout (`/console/rings/`
 * → `console/rings/index.html`) that the gateway's SPA fallback resolves.
 *
 * There is deliberately no `eslint` key here: Next 16 dropped it, and this
 * repository gates lint and typecheck in their own scripts
 * (`npm run lint`, `npm run typecheck`) instead of skipping them inside the
 * build.
 */
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  reactStrictMode: false,
  images: {
    // static export cannot use the Next image optimiser; the kit ships one svg
    unoptimized: true,
  },
};

export default nextConfig;
