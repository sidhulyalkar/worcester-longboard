#!/usr/bin/env node
// Emit the same read-only graph as the Python importer, with no live product calls.
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {buildOutdoorCatalogGraph,replayLegacyBoardCatalog} from "../builder/outdoor_catalog_graph.mjs";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"..");
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
const catalog=read("catalog/board_components.v1.json");
const graph=buildOutdoorCatalogGraph(catalog,
  read("catalog/outdoor_equipment_domains.v0.json"),
  read("catalog/board_package_inclusions.v1.json"));
if(JSON.stringify(replayLegacyBoardCatalog(graph))!==JSON.stringify(catalog))
  throw new Error("Lossless v1 replay failed");
process.stdout.write(JSON.stringify(graph)+"\n");
