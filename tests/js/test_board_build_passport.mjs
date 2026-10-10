import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {generateBoardDesignSpace} from "../../builder/platform_engine.mjs";
import {buildBuildPassport,proposePassportRevisionChange} from "../../builder/build_passport.mjs";
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
const profile=read("configurator/examples/trail_rider_profile.json");
const generated=generateBoardDesignSpace(profile,bundle);
const sample=id=>generated.candidates.find(x=>x.id===id);
const get=id=>buildBuildPassport(sample(id),bundle);
const locked=packet=>assert.ok(Object.values(packet.authority).every(value=>value===false));

test("dated sourced part preserves SKU text, not fabricated revision or stock",()=>{
  const p=get("brake_first_trail_core");
  const donor=p.parts.find(x=>x.component_id==="DONOR-COMP95");
  assert.equal(donor.sku_text,"10303");
  assert.equal(donor.catalog_revision,null);
  assert.equal(donor.revision_status,"EXACT_VARIANT_REVISION_UNVERIFIED");
  assert.equal(donor.supplier.snapshot_id,"mbs_comp95_2026_09_11");
  assert.equal(donor.supplier.verified_current_stock,false);
  assert.equal(donor.price.availability,"UNKNOWN_NOT_LIVE");
  assert.equal(donor.manufacturer_instructions_url,null);
  assert.equal(donor.supplier.source_health,"REFRESH_DUE");
  assert.equal(donor.price.assembly_required_qty,null);
  locked(p);
});

test("source USD reference separated from planning placeholder and missing prices",()=>{
  const p=get("x1_compact_electric_study");
  const battery=p.parts.find(x=>x.category==="battery");
  assert.ok(battery,"the electric planning study should include a battery-class placeholder");
  assert.equal(battery.price.price_basis,"UNSOURCED_PLANNING_ESTIMATE_USD");
  assert.equal(battery.price.pricing_reference_qty,1);
  assert.equal(battery.price.assembly_required_qty,null);
  assert.ok(p.sourcing.unsourced_planning_usd_estimate.min>0);
  assert.ok(p.sourcing.sourced_usd_snapshot.min>0);
  assert.ok(p.sourcing.unpriced_ids.length>0);
  assert.equal(p.sourcing.all_in_total_usd,null);
  assert.equal(p.sourcing.all_in_status,"UNKNOWN_INCOMPLETE_COST_AND_QUANTITY");
  assert.equal(p.assembly.powered,true);
  assert.equal(p.assembly.stages.find(x=>x.id==="electrical").status,"POWER_GATED");
  assert.equal(p.assembly.electrical_integration_authorized,false);
  locked(p);
});

test("reference interface state never becomes physical clearance",()=>{
  const p=get("brake_first_trail_core");
  assert.ok(p.interface_claims.length);
  assert.ok(p.interface_claims.every(x=>x.valid_for_physical_build===false));
  assert.ok(p.interface_claims.every(x=>x.revision_evidence_state==="EXACT_VARIANT_CONFIRMATION_REQUIRED"));
  assert.equal(p.physical_qualification,"NOT_QUALIFIED");
  assert.equal(p.assembly.receiving_inspection_complete,false);
  assert.ok(p.unresolved.unverified_revision_part_ids.includes("BRAKE-V5"));
});

test("proposed revision change invalidates dependent claims without mutating catalog",()=>{
  const baseline=get("brake_first_trail_core");
  const before=JSON.stringify(baseline);
  const changed=proposePassportRevisionChange(baseline,"BRAKE-V5","new-2026-RevB");
  assert.notEqual(changed.study_identity_key,baseline.study_identity_key);
  assert.deepEqual(changed.change_receipt.invalidated_interface_ids,
    baseline.interface_claims.filter(x=>x.component_ids.includes("BRAKE-V5"))
      .map(x=>x.id).sort());
  assert.ok(changed.change_receipt.invalidated_interface_ids.length>0);
  assert.ok(changed.interface_claims.filter(x=>x.component_ids.includes("BRAKE-V5"))
    .every(x=>x.revision_evidence_state==="INVALIDATED_BY_REVISION_CHANGE"));
  assert.ok(changed.interface_claims.every(x=>!x.valid_for_physical_build));
  assert.equal(changed.parts.find(x=>x.component_id==="BRAKE-V5").supplier.verified_current_stock,false);
  assert.equal(JSON.stringify(baseline),before);
  locked(changed);
});

test("unknown revisions, missing components and untrusted change inputs fail closed",()=>{
  const p=get("x1_compact_electric_study");
  assert.throws(()=>proposePassportRevisionChange(p,"FAKE","revA"),/Choose a component/);
  assert.throws(()=>proposePassportRevisionChange(p,"DONOR-COMP95",""),/bounded/);
  assert.throws(()=>proposePassportRevisionChange(p,"DONOR-COMP95","z".repeat(121)),/bounded/);
  assert.throws(()=>buildBuildPassport({...sample("brake_first_trail_core"),
    bom:[{component_id:"NO-SUCH-PART"}]},bundle),/Missing catalog part/);
  assert.throws(()=>buildBuildPassport(null,bundle),/requires a scored candidate/);
});

test("donor includes are an inclusion audit, not automatic independent purchase counts",()=>{
  const p=get("brake_first_trail_core");
  const donor=p.parts.find(x=>x.component_id==="DONOR-COMP95");
  assert.ok(donor.included_by_donor.includes("deck"));
  assert.ok(p.unresolved.donor_inclusion_review_ids.includes("DONOR-COMP95"));
  assert.ok(p.parts.every(x=>x.price.assembly_required_qty===null));
  assert.equal(p.sourcing.purchase_quantities_confirmed,false);
});
