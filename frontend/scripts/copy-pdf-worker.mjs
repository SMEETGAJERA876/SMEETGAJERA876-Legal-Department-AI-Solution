// Copies the PDF.js worker next to the app so the viewer can load it as a static file.
import { copyFileSync, mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";

const require = createRequire(import.meta.url);
const source = join(dirname(require.resolve("pdfjs-dist/package.json")), "build", "pdf.worker.min.mjs");
mkdirSync("public", { recursive: true });
copyFileSync(source, join("public", "pdf.worker.min.mjs"));
console.log("Copied PDF.js worker to public/pdf.worker.min.mjs");
