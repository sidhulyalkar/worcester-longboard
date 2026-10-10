import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {generateBoardDesignSpace} from "../../builder/platform_engine.mjs";
import {buildBuildPassport,proposePassportRevisionChange} from "../../builder/build_passport.mjs";
import {emptyEvidenceNotebook,recordEvidence} from "../../builder/evidence_notebook.mjs";
import {buildReceivingReconciliation} from "../../builder/receiving_reconciliation.mjs";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../..");
const read=x=>JSON.parse(fs.readFileSync(path.join(root,x),"utf8"));
const docs=read("catalog/manufacturer_document_references.v1.json");
const bundle={
 questionnaire:read("configurator/questionnaire.v1.json"),
 rules:read("configurator/rules.v1.json"),
 architectures:read("configurator/architectures.v1.json"),
 catalog:read("catalog/board_components.v1.json"),
 catalogHealth:read("catalog/catalog_health.v1.json"),
 compatibility:read("configurator/compatibility_rules.v1.json"),
 geometry:read("catalog/board_geometry.v1.json"),
 swapSlots:read("configurator/swap_slots.v1.json"),
 composer:read("configurator/composer.v1.json"),
 packageInclusions:read("catalog/board_package_inclusions.v1.json")
};
const generated=generateBoardDesignSpace(read("configurator/examples/trail_rider_profile.json"),bundle);
const get=id=>buildBuildPassport(generated.candidates.find(x=>x.id===id),bundle);
const receipted=(p,n,rev="R1",qty=1)=>recordEvidence(n,p,{
 kind:"RECEIVING_OBSERVATION",component_id:"DONOR-COMP95",
 observed_revision:rev,quantity_received:qty,as_of:"2026-10-10"
});
const locked=obj=>assert.ok(Object.values(obj.authority).every(v=>v===false));

test("no purchases: all receiving and actual order quantities remain missing",()=>{
 const p=get("brake_first_trail_core");
 const report=buildReceivingReconciliation(p,emptyEvidenceNotebook(p),docs);
 assert.equal(report.scope,"UNVERIFIED_RECEIVING_RECONCILIATION");
 assert.equal(report.review_queue.no_receiving_observation_ids.length,p.parts.length);
 const donor=report.rows.find(x=>x.component_id==="DONOR-COMP95");
 assert.equal(donor.donor_content_evidence_status,"UNVERIFIED_DONOR_CONTENTS");
 assert.equal(donor.actual_assembly_quantity,null);
 assert.equal(donor.actual_supplier_order_quantity,null);
 assert.equal(donor.received_inventory_verified,false);
 assert.equal(report.confirmation.physical_qualification,"NOT_QUALIFIED");
 locked(report);
});
test("official MBS references are valid documentation leads but never exact maker manuals",()=>{
 const p=get("brake_first_trail_core");
 const report=buildReceivingReconciliation(p,emptyEvidenceNotebook(p),docs);
 const donor=report.rows.find(x=>x.component_id==="DONOR-COMP95");
 assert.ok(donor.manufacturer_reference_documents.some(x=>x.url==="https://www.mbs.com/manuals"));
 assert.ok(donor.manufacturer_reference_documents.some(x=>x.id==="mbs-comp95-product"));
 assert.ok(donor.manufacturer_reference_documents.every(x=>x.exact_revision_verified===false));
 assert.equal(donor.revision_matched_manufacturer_manual_verified,false);
 assert.equal(p.parts.find(x=>x.component_id==="DONOR-COMP95").manufacturer_instructions_url,null);
});
test("user-reported receiving leaves donor contents, quantities and revision unverified",()=>{
 const p=get("brake_first_trail_core"),n=receipted(p,emptyEvidenceNotebook(p));
 const report=buildReceivingReconciliation(p,n,docs);
 const donor=report.rows.find(x=>x.component_id==="DONOR-COMP95");
 assert.equal(donor.last_observation.quantity_received,1);
 assert.equal(donor.receipt_history_status,"SELF_REPORTED_RECEIPT_NEEDS_INDEPENDENT_REVIEW");
 assert.equal(donor.physical_revision_verified,false);
 assert.equal(donor.donor_content_evidence_status,"UNVERIFIED_DONOR_CONTENTS");
 assert.equal(donor.actual_assembly_quantity,null);
 assert.equal(report.confirmation.received_contents_qualified,0);
 assert.ok(!report.review_queue.no_receiving_observation_ids.includes("DONOR-COMP95"));
 locked(report);
});
test("multiple dissimilar receipts are conflicts, not additive stock",()=>{
 const p=get("brake_first_trail_core");let n=receipted(p,emptyEvidenceNotebook(p));
 n=receipted(p,n,"R2",2);
 const report=buildReceivingReconciliation(p,n,docs);
 const donor=report.rows.find(x=>x.component_id==="DONOR-COMP95");
 assert.equal(donor.last_observation.quantity_received,2);
 assert.equal(donor.recorded_receiving_count,2);
 assert.equal(donor.receipt_history_status,"CONFLICTING_RECEIPT_HISTORY_REVIEW");
 assert.deepEqual(report.review_queue.conflicting_receipt_history_ids,["DONOR-COMP95"]);
 assert.equal(donor.received_inventory_verified,false);
 assert.equal(donor.actual_supplier_order_quantity,null);
});
test("stale, forged and variant-updated evidence does not migrate or authorize",()=>{
 const p=get("brake_first_trail_core");
 const note=receipted(p,emptyEvidenceNotebook(p));
 const forged=structuredClone(note);
 forged.records[0].usable_for_qualification=true;
 forged.authority.procurement_authorized=true;
 const review=buildReceivingReconciliation(p,forged,docs);
 assert.equal(review.evidence_record_count,1);
 locked(review);
 const revised=proposePassportRevisionChange(p,"DONOR-COMP95","R2");
 const stale=buildReceivingReconciliation(revised,note,docs);
 assert.equal(stale.evidence_record_count,0);
 assert.equal(stale.rows.find(x=>x.component_id==="DONOR-COMP95").last_observation,null);
 assert.equal(stale.confirmation.order_lines_qualified,0);
});
test("fake official-document approvals cannot be injected into source index",()=>{
 const p=get("brake_first_trail_core"),n=emptyEvidenceNotebook(p);
 const fake=structuredClone(docs);fake.entries[0].exact_revision_verified=true;
 assert.throws(()=>buildReceivingReconciliation(p,n,fake),/Invalid or duplicate/);
 fake.entries[0].exact_revision_verified=false;
 fake.entries[0].url="javascript:alert(1)";
 assert.throws(()=>buildReceivingReconciliation(p,n,fake),/Invalid or duplicate/);
});
