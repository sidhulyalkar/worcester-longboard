#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { generateBoardDesignSpace } from "../builder/platform_engine.mjs";
import { renderBoardPreviewSvg } from "../builder/preview_renderer.mjs";
import { visualStateFromCandidate } from "../builder/visual_state.mjs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..");

function repoJson(relative) {
  return JSON.parse(fs.readFileSync(path.join(ROOT, relative), "utf8"));
}

function readJson(filePath) {
  const absolute = path.isAbsolute(filePath) ? filePath : path.resolve(process.cwd(), filePath);
  return JSON.parse(fs.readFileSync(absolute, "utf8"));
}

const profilePath = process.argv[2];
const outFlag = process.argv.indexOf("--out-dir");
if (!profilePath || outFlag < 0 || !process.argv[outFlag + 1]) {
  console.error("usage: node tools/render_board_candidate_previews.mjs <profile.json> --out-dir <directory>");
  process.exit(2);
}

const outDir = path.resolve(process.cwd(), process.argv[outFlag + 1]);
fs.mkdirSync(outDir, { recursive: true });

const bundle = {
  questionnaire: repoJson("configurator/questionnaire.v1.json"),
  rules: repoJson("configurator/rules.v1.json"),
  catalog: repoJson("catalog/board_components.v1.json"),
  architectures: repoJson("configurator/architectures.v1.json"),
  compatibility: repoJson("configurator/compatibility_rules.v1.json"),
  swapSlots: repoJson("configurator/swap_slots.v1.json"),
  geometry: repoJson("catalog/board_geometry.v1.json"),
  composer: repoJson("configurator/composer.v1.json"),
};
const geometry = repoJson("catalog/board_geometry.v1.json");
const generated = generateBoardDesignSpace(readJson(profilePath), bundle);
const manifest = {
  schema_version: 1,
  visualization_only: true,
  files: [],
};

for (const candidate of generated.candidates) {
  const state = visualStateFromCandidate(candidate, geometry, bundle.catalog);
  for (const view of state.views) {
    const filename = candidate.id + "-" + view + ".svg";
    fs.writeFileSync(
      path.join(outDir, filename),
      renderBoardPreviewSvg(state, view, { width: 720, height: 360, compact: false }),
      "utf8"
    );
    manifest.files.push({
      candidate_id: candidate.id,
      view,
      filename,
      readiness: candidate.readiness,
    });
  }
}

fs.writeFileSync(
  path.join(outDir, "manifest.json"),
  JSON.stringify(manifest, null, 2) + "\n",
  "utf8"
);
process.stdout.write(
  "Rendered " + manifest.files.length + " deterministic board preview SVGs to " + outDir + "\n"
);
