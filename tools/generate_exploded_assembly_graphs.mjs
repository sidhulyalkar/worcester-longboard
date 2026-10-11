#!/usr/bin/env node
// Full deterministic source-bound assembly graphs. No physical instructions.
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {generateBoardDesignSpace} from "../builder/platform_engine.mjs";
import {buildAssemblyGraph} from "../builder/assembly_graph.mjs";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"..");
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
const bundle={
 questionnaire:read("configurator/questionnaire.v1.json"),
 rules:read("configurator/rules.v1.json"),
 catalog:read("catalog/board_components.v1.json"),
 architectures:read("configurator/architectures.v1.json"),
 compatibility:read("configurator/compatibility_rules.v1.json"),
 geometry:read("catalog/board_geometry.v1.json"),
 swapSlots:read("configurator/swap_slots.v1.json"),
 composer:read("configurator/composer.v1.json"),
 catalogHealth:read("catalog/catalog_health.v1.json"),
 packageInclusions:read("catalog/board_package_inclusions.v1.json")
};
const recipes=read("catalog/outdoor_assembly_recipes.v1.json");
const profile=read("configurator/examples/trail_rider_profile.json");
const subjects=[...generateBoardDesignSpace(profile,bundle).candidates,...recipes.examples];
const graphs=subjects.map(s=>buildAssemblyGraph(s,recipes,bundle.catalog,bundle.packageInclusions));
console.log(JSON.stringify(graphs));
