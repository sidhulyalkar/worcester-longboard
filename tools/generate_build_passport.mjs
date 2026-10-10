#!/usr/bin/env node
// Print the same on-demand Build Passport consumed by the browser.
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {generateBoardDesignSpace} from "../builder/platform_engine.mjs";
import {buildBuildPassport} from "../builder/build_passport.mjs";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"..");
const args=process.argv.slice(2);
if(args.length!==2){console.error("Usage: node tools/generate_build_passport.mjs <profile.json> <candidate_id>");process.exit(2);}
const read=p=>JSON.parse(fs.readFileSync(p,"utf8"));
const rel=p=>read(path.join(root,p));
const bundle={
  questionnaire:rel("configurator/questionnaire.v1.json"),
  rules:rel("configurator/rules.v1.json"),
  catalog:rel("catalog/board_components.v1.json"),
  architectures:rel("configurator/architectures.v1.json"),
  compatibility:rel("configurator/compatibility_rules.v1.json"),
  swapSlots:rel("configurator/swap_slots.v1.json"),
  geometry:rel("catalog/board_geometry.v1.json"),
  composer:rel("configurator/composer.v1.json"),
  catalogHealth:rel("catalog/catalog_health.v1.json")
};
const result=generateBoardDesignSpace(read(path.resolve(args[0])),bundle);
const selected=result.candidates.find(c=>c.id===args[1]);
if(!selected){console.error("Unknown design candidate "+args[1]);process.exit(2);}
process.stdout.write(JSON.stringify(buildBuildPassport(selected,bundle),null,2)+"\n");
