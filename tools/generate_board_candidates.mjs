#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { generateBoardDesignSpace } from "../builder/platform_engine.mjs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..");

function readJson(relative) {
  return JSON.parse(fs.readFileSync(path.join(ROOT, relative), "utf8"));
}

const profilePath = process.argv[2];
if (!profilePath) {
  console.error("usage: node tools/generate_board_candidates.mjs <profile.json>");
  process.exit(2);
}

const absoluteProfile = path.resolve(process.cwd(), profilePath);
const profile = JSON.parse(fs.readFileSync(absoluteProfile, "utf8"));
const bundle = {
  questionnaire: readJson("configurator/questionnaire.v1.json"),
  rules: readJson("configurator/rules.v1.json"),
  catalog: readJson("catalog/board_components.v1.json"),
  architectures: readJson("configurator/architectures.v1.json"),
  compatibility: readJson("configurator/compatibility_rules.v1.json"),
  swapSlots: readJson("configurator/swap_slots.v1.json"),
  geometry: readJson("catalog/board_geometry.v1.json"),
  composer: readJson("configurator/composer.v1.json"),
};

process.stdout.write(JSON.stringify(generateBoardDesignSpace(profile, bundle), null, 2) + "\n");
