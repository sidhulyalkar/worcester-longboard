import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {generateBoardDesignSpace} from "../../builder/platform_engine.mjs";
import {buildBuildPassport,proposePassportRevisionChange} from "../../builder/build_passport.mjs";
import {auditAssemblyInventory} from "../../builder/assembly_inventory.mjs";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../..");
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
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
const candidates=generateBoardDesignSpace(read("configurator/examples/trail_rider_profile.json"),bundle).candidates;
const choice=id=>candidates.find(c=>c.id===id);
const p=id=>buildBuildPassport(choice(id),bundle);
const donor=()=>p("brake_first_trail_core");
const synthetic=(ids)=>buildBuildPassport({...choice("brake_first_trail_core"),
  bom:ids.map(component_id=>({component_id}))},bundle);

test("donor included tokens are audited without inventing counts or order approval",()=>{
 const passport=donor(),report=passport.assembly_inventory_audit;
 const pkg=report.package_claims.find(x=>x.package_id==="DONOR-COMP95");
 assert.ok(pkg);
 assert.equal(pkg.snapshot_binding_status,"BOUND_TO_REFERENCE_SNAPSHOT");
 assert.equal(pkg.exact_received_contents_verified,false);
 assert.equal(pkg.order_unit_quantity,null);
 assert.ok(report.unmapped_inclusion_worklist.some(x=>x.inclusion_token==="f5_bindings"));
 assert.ok(report.order_lines.every(x=>x.actual_supplier_order_quantity===null));
 assert.ok(report.order_lines.every(x=>x.actual_assembly_quantity===null));
 assert.equal(report.costs.overlap_adjusted_total_usd,null);
 assert.ok(Object.values(report.authority).every(x=>x===false));
});
test("possible donor/standalone hub and truck overlaps never auto subtract USD",()=>{
 const packet=synthetic(["DONOR-COMP95","HUB-RSII","TRUCK-M3-400","BRAKE-V5"]);
 const a=packet.assembly_inventory_audit;
 assert.deepEqual(a.overlap_worklist.map(x=>x.component_id),["HUB-RSII","TRUCK-M3-400"]);
 assert.ok(a.overlap_worklist.every(x=>x.classification==="POSSIBLE_DOUBLE_COUNT"));
 assert.equal(a.costs.existing_bom_subtotal_has_possible_double_count,true);
 assert.ok(packet.sourcing.sourced_usd_snapshot.min>0);
 assert.equal(a.costs.confirmed_quote_total_usd,null);
 assert.equal(a.order_lines.find(x=>x.component_id==="HUB-RSII").actual_supplier_order_quantity,null);
});
test("70mm axles and powered drive on donor are retrofit questions not fit declarations",()=>{
 const packet=synthetic(["DONOR-COMP95","AXLE-M3-70","DRIVE-G1-DUAL"]);
 const a=packet.assembly_inventory_audit;
 assert.deepEqual(a.retrofit_worklist.map(x=>x.component_id),["AXLE-M3-70","DRIVE-G1-DUAL"]);
 assert.ok(a.retrofit_worklist.every(x=>x.status==="MEASURE_AND_VERIFY_RETROFIT_BEFORE_PHYSICAL_USE"));
 assert.equal(a.eligibility.mechanical_interfaces_qualified,false);
 assert.equal(a.eligibility.electrical_integration_qualified,false);
});
test("the registry is source-revision bound; supplier snapshot changes trigger hold",()=>{
 const packet=donor();
 const changed=structuredClone(packet);
 changed.parts.find(x=>x.component_id==="DONOR-COMP95").supplier.snapshot_id="new-listing";
 const report=auditAssemblyInventory(changed,bundle.packageInclusions);
 assert.equal(report.package_claims[0].snapshot_binding_status,"STALE_OR_CHANGED_SOURCE_HOLD");
 assert.ok(report.unmapped_inclusion_worklist.some(x=>x.reason==="STALE_OR_CHANGED_SOURCE_HOLD"));
 const revision=proposePassportRevisionChange(packet,"DONOR-COMP95","rev-new");
 assert.equal(revision.assembly_inventory_audit,null);
 assert.equal(revision.physical_qualification,"NOT_QUALIFIED");
});
test("mismatched inclusion declarations and duplicate BOM references fail closed",()=>{
 const packet=donor();
 const reg=structuredClone(bundle.packageInclusions);
 reg.packages[0].inclusions.pop();
 assert.throws(()=>auditAssemblyInventory(packet,reg),/included token mismatch/);
 const duplicated=structuredClone(packet);
 duplicated.parts.push(structuredClone(duplicated.parts[0]));
 assert.throws(()=>auditAssemblyInventory(duplicated,bundle.packageInclusions),/Duplicate BOM/);
});
test("a new unmapped bundled donor does not silently become a complete package",()=>{
 const packet=structuredClone(donor());
 packet.parts[0].component_id="DONOR-UNKNOWN-REF";
 const audit=auditAssemblyInventory(packet,bundle.packageInclusions);
 assert.equal(audit.package_claims[0].snapshot_binding_status,"UNMAPPED_BUNDLE_HOLD");
 assert.ok(audit.unmapped_inclusion_worklist.length>=5);
 assert.equal(audit.costs.all_in_assembly_total_usd,null);
});
