#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { generateCandidates } from "../builder/engine.mjs";
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
if (!profilePath) {
  console.error("usage: node tools/build_board_visual_states.mjs <profile.json>");
  process.exit(2);
}

const bundle = {
  questionnaire: repoJson("configurator/questionnaire.v1.json"),
  rules: repoJson("configurator/rules.v1.json"),
  catalog: repoJson("catalog/board_components.v1.json"),
  architectures: repoJson("configurator/architectures.v1.json"),
  compatibility: repoJson("configurator/compatibility_rules.v1.json"),
};
const geometry = repoJson("catalog/board_geometry.v1.json");
const generated = generateCandidates(readJson(profilePath), bundle);
const payload = {
  schema_version: 1,
  winner_selected: false,
  visualization_only: true,
  states: generated.candidates.map(candidate =>
    visualStateFromCandidate(candidate, geometry, bundle.catalog)
  ),
};
process.stdout.write(JSON.stringify(payload, null, 2) + "\n");
