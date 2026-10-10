#!/usr/bin/env node
// Reproducible synthetic receiving case for exact Python/JS parity, not actual parts.
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {generateBoardDesignSpace} from "../builder/platform_engine.mjs";
import {buildBuildPassport} from "../builder/build_passport.mjs";
import {recordEvidence,emptyEvidenceNotebook} from "../builder/evidence_notebook.mjs";
import {buildReceivingReconciliation} from "../builder/receiving_reconciliation.mjs";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"..");
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
const bundle={
 questionnaire:read("configurator/questionnaire.v1.json"),rules:read("configurator/rules.v1.json"),
 catalog:read("catalog/board_components.v1.json"),architectures:read("configurator/architectures.v1.json"),
 catalogHealth:read("catalog/catalog_health.v1.json"),compatibility:read("configurator/compatibility_rules.v1.json"),
 geometry:read("catalog/board_geometry.v1.json"),swapSlots:read("configurator/swap_slots.v1.json"),
 composer:read("configurator/composer.v1.json"),packageInclusions:read("catalog/board_package_inclusions.v1.json")
};
const name=process.argv[2];
if(!name)throw new Error("Supply candidate ID");
const profile=read("configurator/examples/trail_rider_profile.json");
const candidate=generateBoardDesignSpace(profile,bundle).candidates.find(x=>x.id===name);
if(!candidate)throw new Error("Unknown candidate "+name);
const passport=buildBuildPassport(candidate,bundle);
const id=passport.parts[0].component_id;
let notes=emptyEvidenceNotebook(passport);
notes=recordEvidence(notes,passport,{kind:"RECEIVING_OBSERVATION",component_id:id,
 observed_revision:"Sample A",quantity_received:1,as_of:"2026-10-10"});
notes=recordEvidence(notes,passport,{kind:"SOURCE_REFERENCE",component_id:id,
 evidence_url:"https://example.org/reference",as_of:"2026-10-10"});
notes=recordEvidence(notes,passport,{kind:"RECEIVING_OBSERVATION",component_id:id,
 observed_revision:"Sample B",quantity_received:2,as_of:"2026-10-10"});
console.log(JSON.stringify(buildReceivingReconciliation(
 passport,notes,read("catalog/manufacturer_document_references.v1.json"))));
