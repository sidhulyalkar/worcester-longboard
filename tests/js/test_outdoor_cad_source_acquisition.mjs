import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {fileURLToPath} from "node:url";
import path from "node:path";
import {validateCadSourceLeadbook,buildCadSourceAcquisition}
 from "../../builder/cad_source_acquisition.mjs";
import {buildPickerStudy} from "../../builder/parts_picker_engine.mjs";
import {auditCompleteKitClaim} from "../../builder/complete_kit_closure.mjs";
import {compileCompleteKitCadDisplay} from "../../builder/complete_kit_cad_schema.mjs";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../..");
const file=n=>JSON.parse(readFileSync(path.join(root,"catalog",n),"utf8"));
const source=file("outdoor_cad_source_leads.v1.json");
const registry=file("outdoor_cad_asset_registry.v1.json");
const catalog=file("outdoor_parts_picker.v1.json");
const kits=file("outdoor_complete_kit_claims.v1.json");
const retail=file("outdoor_retail_comparisons.v1.json");
const recipe=file("outdoor_complete_kit_cad_recipes.v1.json");
const cad=name=>{
 const variant=catalog.products.find(x=>x.id===name).variants[0].id;
 const study=buildPickerStudy(catalog,{domain_id:"skateboard_longboard",
  selections:{long_complete:variant}});
 return compileCompleteKitCadDisplay(study,
  auditCompleteKitClaim(study,kits,catalog,retail),kits,recipe);
};
test("official seven-role source inquiries exclude unrelated maker-published files",()=>{
 const count=validateCadSourceLeadbook(source);
 assert.deepEqual(count,{research_roles:7,kit_variants:2,
  related_artifacts_excluded:2,qualified_structural_geometry:0,
  additional_purchase_lines:0});
 const research=buildCadSourceAcquisition(cad("loaded-tangent-complete"),source,registry);
 assert.equal(research.source_leads,7);
 assert.equal(research.pending_structural_geometry,7);
 assert.equal(research.rows.length,7);
 assert.equal(research.manufacturer_request_packets.length,3);
 assert.ok(research.manufacturer_request_packets.every(r=>r.message.includes(
  "express written permissions")));
 assert.equal(research.qualified_models,0);
 assert.equal(research.file_backed_unqualified_candidates,0);
 assert.equal(research.physical_mates_verified,0);
 assert.equal(research.additional_purchase_lines,0);
 assert.ok(research.excluded_artifacts.every(r=>
  !r.exact_structural_part_cad&&!r.qualifies_seven_component_models&&
  !r.usable_as_structural_mounting_datum&&!r.purchase_line_created));
 assert.ok(research.excluded_artifacts.some(r=>r.id==="zee-optional-tail-nub-stl"&&
  r.classification==="OPTIONAL_ACCESSORY_NOT_SEVEN_PART_ASSEMBLY"));
 assert.ok(research.excluded_artifacts.some(r=>r.id==="zee-diy-cutting-pdf"&&
  r.classification==="DIY_DRAWING_NOT_3D_SOLID"));
});
test("wheel geometry requests and source links are scoped to the selected diameter",()=>{
 const dad=buildCadSourceAcquisition(cad("loaded-tangent-complete"),source,registry);
 const caguama=buildCadSourceAcquisition(cad("loaded-tangent-caguama"),source,registry);
 assert.match(dad.rows.find(r=>r.role==="wheels").source_url,/dad-bod-105mm/);
 assert.match(caguama.rows.find(r=>r.role==="wheels").source_url,/caguama-85mm/);
 assert.ok(!dad.rows.some(r=>r.source_url.includes("caguama-85mm")));
 assert.ok(!caguama.rows.some(r=>r.source_url.includes("dad-bod-105mm")));
 assert.notEqual(dad.kit_variant_id,caguama.kit_variant_id);
 assert.equal(dad.rows.find(r=>r.role==="trucks").exact_revision_confirmed,false);
 assert.match(dad.rows.find(r=>r.role==="trucks").required_geometry,/V2 versus maker V3/);
 assert.ok(dad.rows.every(r=>!r.permission_to_redistribute&&r.physically_verified_mounting_datums===0));
 assert.deepEqual(buildCadSourceAcquisition(null,source,registry).rows,[]);
});
test("forge-resistant official source references and license policy",()=>{
 const mutants=[
  x=>x.authority.procurement_authorized=true,
  x=>x.authority.cad_geometry_authenticated=true,
  x=>x.roles[0].source_geometry_verified=true,
  x=>x.roles[0].exact_revision_confirmed=true,
  x=>x.roles[0].redistribution_rights="GRANTED",
  x=>x.roles[0].approved_mounting_datums=1,
  x=>x.roles[0].extra_order_lines=1,
  x=>x.roles[0].source_pages[0].url="javascript:alert(1)",
  x=>x.roles[0].source_pages[0].url="https://forged-loadedboards.com/model.step",
  x=>x.roles[2].manufacturer_url="https://phishing.example/steer",
  x=>x.roles[0].source_pages[0].variants=[x.kit_variant_ids[0]],
  x=>x.roles[3].source_pages[0].variants=[x.kit_variant_ids[0],x.kit_variant_ids[1]],
  x=>x.related_public_artifacts[0].exact_structural_part_cad=true,
  x=>x.related_public_artifacts[1].redistribution_authorized=true,
  x=>x.related_public_artifacts[1].classification="STRUCTURAL_OEM_CAD",
  x=>x.roles[6].role="deck"
 ];
 for(const update of mutants){
  const altered=structuredClone(source);
  update(altered);
  assert.throws(()=>validateCadSourceLeadbook(altered),/CAD source leadbook:/);
 }
 const invalidCad=structuredClone(cad("loaded-tangent-complete"));
 invalidCad.physical_mates_verified=1;
 assert.throws(()=>buildCadSourceAcquisition(invalidCad,source,registry),
  /CAD source leadbook:/);
});
