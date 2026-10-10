import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {generateBoardDesignSpace} from "../../builder/platform_engine.mjs";
import {buildBuildPassport,proposePassportRevisionChange} from "../../builder/build_passport.mjs";
import {emptyEvidenceNotebook,recordEvidence,restoreEvidenceNotebook,evaluateEvidenceNotebook} from "../../builder/evidence_notebook.mjs";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../..");
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
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
const generated=generateBoardDesignSpace(read("configurator/examples/trail_rider_profile.json"),bundle);
const passport=id=>buildBuildPassport(generated.candidates.find(c=>c.id===id),bundle);
const manual=()=>passport("brake_first_trail_core");
const receiving={kind:"RECEIVING_OBSERVATION",component_id:"DONOR-COMP95",observed_revision:"Rev B - label",quantity_received:1,as_of:"2026-10-10",note:"Photo of carton retained locally"};
const locked=p=>assert.deepEqual(Object.values(p.authority),[false,false,false,false,false]);

test("receiving observations produce records without elevating quantities or physical clearance",()=>{
 const p=manual(),empty=emptyEvidenceNotebook(p);
 const book=recordEvidence(empty,p,receiving);
 const review=evaluateEvidenceNotebook(p,book);
 assert.equal(book.records[0].quantity_received,1);
 assert.equal(book.records[0].review_status,"USER_RECORDED_NOT_INDEPENDENTLY_VERIFIED");
 assert.equal(book.records[0].usable_for_qualification,false);
 assert.equal(p.parts[0].price.assembly_required_qty,null);
 assert.equal(review.assembly_quantities_authorized,0);
 assert.equal(review.physical_qualification,"NOT_QUALIFIED");
 assert.equal(review.invalidated_interface_ids.length,p.interface_claims.length);
 assert.equal(review.stock_confirmed,0);
 locked(book);locked(review);
});
test("source and manual URLs become candidate evidence, never approved manuals or stock",()=>{
 const p=manual();let book=emptyEvidenceNotebook(p);
 book=recordEvidence(book,p,{kind:"SOURCE_REFERENCE",component_id:"BRAKE-V5",
   evidence_url:"https://www.mbs.com/shop/parts/brakes",as_of:"2026-10-10"});
 book=recordEvidence(book,p,{kind:"MANUFACTURER_INSTRUCTIONS_CANDIDATE",component_id:"BRAKE-V5",
   observed_revision:"v5-marked",evidence_url:"https://www.mbs.com/manual.pdf",as_of:"2026-10-10"});
 const review=evaluateEvidenceNotebook(p,book);
 assert.deepEqual(review.instruction_candidates_part_ids,["BRAKE-V5"]);
 assert.deepEqual(review.source_reference_part_ids,["BRAKE-V5"]);
 assert.equal(review.manufacturer_manuals_independently_verified,0);
 assert.equal(review.stock_confirmed,0);
 assert.equal(p.parts.find(x=>x.component_id==="BRAKE-V5").manufacturer_instructions_url,null);
 assert.ok(book.records.every(x=>!x.usable_for_qualification));
});
test("measured interface notes only annotate, never resolve UNKNOWN or MEASURE_FIRST",()=>{
 const p=passport("x1_compact_electric_study");
 const claim=p.interface_claims.find(x=>["UNKNOWN","MEASURE_FIRST"].includes(x.reference_state));
 assert.ok(claim,"electric case should have unresolved interfaces");
 const book=recordEvidence(emptyEvidenceNotebook(p),p,{
  kind:"INTERFACE_MEASUREMENT_NOTE",component_id:claim.component_ids.find(id=>p.parts.some(part=>part.component_id===id)),
  interface_id:claim.id,note:"Still need calibrated axle offset measurement"});
 const review=evaluateEvidenceNotebook(p,book);
 assert.ok(review.noted_interface_ids.includes(claim.id));
 assert.ok(review.unresolved_interface_ids.includes(claim.id));
 assert.equal(review.physical_qualification,"NOT_QUALIFIED");
});
test("invalid links, dates, quantities, kinds, and cross-part interface claims fail closed",()=>{
 const p=manual(),book=emptyEvidenceNotebook(p);
 const bad=(delta)=>assert.throws(()=>recordEvidence(book,p,{...receiving,...delta}));
 bad({quantity_received:0});bad({quantity_received:1.5});
 bad({quantity_received:501});bad({as_of:"2026-02-31"});
 bad({component_id:"FAKE"});bad({kind:"PROMOTE_AUTHORITY"});
 bad({evidence_url:"javascript:alert(1)"});
 bad({evidence_url:"https://user:pass@example.com/file"});
 bad({observed_revision:"x\n<script>alert(1)</script>"});
 assert.throws(()=>recordEvidence(book,p,{kind:"MANUFACTURER_INSTRUCTIONS_CANDIDATE",
 component_id:"BRAKE-V5",observed_revision:"rev 2",evidence_url:"http://example.org/manual",as_of:"2026-10-10"}));
 assert.throws(()=>recordEvidence(book,p,{kind:"INTERFACE_MEASUREMENT_NOTE",component_id:"BRAKE-V5",
 interface_id:"unknown-rule",note:"Inspect later"}));
});
test("restoring a forged or stale notebook cannot assert evidence approval",()=>{
 const p=manual(),book=recordEvidence(emptyEvidenceNotebook(p),p,receiving);
 const forged=JSON.parse(JSON.stringify(book));
 forged.records[0].review_status="VERIFIED";
 forged.records[0].usable_for_qualification=true;
 forged.authority.procurement_authorized=true;
 const restored=restoreEvidenceNotebook(p,forged);
 assert.equal(restored.records[0].review_status,"USER_RECORDED_NOT_INDEPENDENTLY_VERIFIED");
 assert.equal(restored.records[0].usable_for_qualification,false);
 locked(restored);
 const stale=structuredClone(book);stale.study_identity_key="other snapshot";
 assert.equal(restoreEvidenceNotebook(p,stale).records.length,0);
 const changed=proposePassportRevisionChange(p,"BRAKE-V5","revision-C");
 assert.equal(restoreEvidenceNotebook(changed,book).records.length,0);
 const tampered=structuredClone(book);tampered.records[0].target_variant_identity_key="old";
 assert.equal(restoreEvidenceNotebook(p,tampered).records.length,0);
});
test("restore validates each historical record and preserves input order",()=>{
 const p=manual();let book=emptyEvidenceNotebook(p);
 book=recordEvidence(book,p,{kind:"SOURCE_REFERENCE",component_id:"DONOR-COMP95",
   evidence_url:"https://www.mbs.com/shop/p/example",as_of:"2026-10-10"});
 book=recordEvidence(book,p,receiving);
 assert.deepEqual(restoreEvidenceNotebook(p,JSON.stringify(book)),book);
 assert.equal(evaluateEvidenceNotebook(p,book).evidence_count,2);
});
