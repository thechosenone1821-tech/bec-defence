import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const out = path.join(root, "out");
const target = path.resolve(root, "..", "packages", "frontend", "static");

if (!fs.existsSync(path.join(out, "index.html"))) {
  throw new Error(`Next.js static export is missing ${path.join(out, "index.html")}`);
}

fs.rmSync(target, { recursive: true, force: true });
fs.mkdirSync(path.dirname(target), { recursive: true });
fs.cpSync(out, target, { recursive: true });
const files = fs.readdirSync(target, { recursive: true }).filter((entry) => {
  return fs.statSync(path.join(target, entry)).isFile();
});
console.log(`OK: copied ${files.length} static frontend files to packages/frontend/static`);
