import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {generateBoardDesignSpace} from "../builder/platform_engine.mjs";
import {buildBuildPassport} from "../builder/build_passport.mjs";
import {emptyEvidenceNotebook,recordEvidence,evaluateEvidenceNotebook} from "../builder/evidence_notebook.mjs";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"..");
const read=x=>JSON.parse(fs.readFileSync(path.join(root,x),"utf8"));
const id=process.argv[2];
if(!id)throw new Error("Pass a candidate ID");
const bundle={
 questionnaire:read("configurator/questionnaire.v1.json"),
 rules:read("configurator/rules.v1.json"),
 architectures:read("configurator/architectures.v1.json"),
 catalog:read("catalog/board_components.v1.json"),
 catalogHealth:read("catalog/catalog_health.v1.json"),
 compatibility:read("configurator/compatibility_rules.v1.json"),
 swapSlots:read("configurator/swap_slots.v1.json"),
 geometry:read("catalog/board_geometry.v1.json"),
 composer:read("configurator/composer.v1.json")
};
const candidates=generateBoardDesignSpace(read("configurator/examples/trail_rider_profile.json"),bundle).candidates;
const chosen=candidates.find(c=>c.id===id);
if(!chosen)throw new Error("Unknown candidate");
const passport=buildBuildPassport(chosen,bundle);
let book=emptyEvidenceNotebook(passport);
const first=passport.parts[0];
book=recordEvidence(book,passport,{kind:"SOURCE_REFERENCE",component_id:first.component_id,
 evidence_url:"https://example.org/catalog/source-record",as_of:"2026-10-10"});
book=recordEvidence(book,passport,{kind:"RECEIVING_OBSERVATION",component_id:first.component_id,
 observed_revision:"Test Rev A",quantity_received:1,as_of:"2026-10-10",note:"Synthetic first-piece receiving note"});
const manual=passport.parts.find(p=>p.component_id==="BRAKE-V5") || first;
book=recordEvidence(book,passport,{kind:"MANUFACTURER_INSTRUCTIONS_CANDIDATE",
 component_id:manual.component_id,observed_revision:"Test Rev A",
 evidence_url:"https://example.org/not-verified/manual",as_of:"2026-10-10"});
const claim=passport.interface_claims.find(c=>c.component_ids.includes(first.component_id));
if(claim)book=recordEvidence(book,passport,{kind:"INTERFACE_MEASUREMENT_NOTE",
 component_id:first.component_id,interface_id:claim.id,note:"Missing actual tolerance stack measurements"});
console.log(JSON.stringify({notebook:book,review:evaluateEvidenceNotebook(passport,book)}));
