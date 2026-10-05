#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { generateCandidates } from "../builder/engine.mjs";
import { evaluateSwap } from "../builder/swap_engine.mjs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..");

function readJson(relativeOrAbsolute) {
  const absolute = path.isAbsolute(relativeOrAbsolute)
    ? relativeOrAbsolute
    : path.resolve(process.cwd(), relativeOrAbsolute);
  return JSON.parse(fs.readFileSync(absolute, "utf8"));
}

function repoJson(relative) {
  return JSON.parse(fs.readFileSync(path.join(ROOT, relative), "utf8"));
}

const profilePath = process.argv[2];
const selectionPath = process.argv[3];
const candidateFlag = process.argv.indexOf("--candidate");
if (!profilePath || !selectionPath || candidateFlag < 0 || !process.argv[candidateFlag + 1]) {
  console.error("usage: node tools/evaluate_board_swap.mjs <profile.json> <selection.json> --candidate <id>");
  process.exit(2);
}

const bundle = {
  questionnaire: repoJson("configurator/questionnaire.v1.json"),
  rules: repoJson("configurator/rules.v1.json"),
  catalog: repoJson("catalog/board_components.v1.json"),
  architectures: repoJson("configurator/architectures.v1.json"),
  compatibility: repoJson("configurator/compatibility_rules.v1.json"),
};
const slots = repoJson("configurator/swap_slots.v1.json");
const generated = generateCandidates(readJson(profilePath), bundle);
const candidateId = process.argv[candidateFlag + 1];
const candidate = generated.candidates.find(row => row.id === candidateId);
if (!candidate) {
  console.error("unknown candidate " + candidateId);
  process.exit(2);
}
const result = evaluateSwap(candidate, generated.requirements, readJson(selectionPath), bundle, slots);
process.stdout.write(JSON.stringify(result, null, 2) + "\n");
