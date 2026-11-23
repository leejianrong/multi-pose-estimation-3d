import fs from "node:fs";
import path from "node:path";
import { defineConfig } from "vite";

// Dev only: serve the repo's config/, calibration/ and assets/ under /repo/ so the sim reads the
// same files the Python services read.
const repoRoot = path.resolve(__dirname, "..");
const allowed = ["config", "calibration", "assets"];

export default defineConfig({
  plugins: [
    {
      name: "serve-repo-data",
      configureServer(server) {
        server.middlewares.use("/repo", (req, res, next) => {
          const rel = decodeURIComponent((req.url ?? "").split("?")[0]).replace(/^\/+/, "");
          const top = rel.split("/")[0];
          const file = path.resolve(repoRoot, rel);
          if (!allowed.includes(top) || !file.startsWith(repoRoot) || !fs.existsSync(file)) return next();
          res.setHeader("Content-Type", file.endsWith(".json") ? "application/json" : "application/octet-stream");
          fs.createReadStream(file).pipe(res);
        });
      },
    },
  ],
});
