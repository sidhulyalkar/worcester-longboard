import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {buildAssemblyGraph} from "../../builder/assembly_graph.mjs";
import {evaluateSnowboardMountReference} from "../../builder/snowboard_mount_reference.mjs";
import {renderExplodedAssemblySvg} from "../../builder/exploded_renderer.mjs";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../..");
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
const refs=read("catalog/board_sport_reference_studies.v1.json");
const recipes=read("catalog/outdoor_assembly_recipes.v1.json");
const catalog=read("catalog/board_components.v1.json");
const packs=read("catalog/board_package_inclusions.v1.json");
const build=(s,reg=refs)=>buildAssemblyGraph(s,recipes,catalog,packs,reg);
test("all manufacturer reference studies show sourced roles without implied fit or units",()=>{
 assert.ok(refs.studies.length>=5);
 for(const study of refs.studies){
  const graph=build(study);
  assert.equal(graph.origin,"MANUFACTURER_REFERENCED_INTEGRATION_STUDY");
  assert.equal(graph.source_snapshot_as_of,refs.reviewed_as_of);
  assert.deepEqual(graph.components.map(x=>x.component_id),study.components.map(x=>x.component_id));
  assert.equal(graph.completeness.physical_connections_qualified,0);
  assert.ok(graph.components.every(x=>x.assembly_required_quantity===null &&
   x.supplier_order_quantity===null && !x.exact_variant_verified));
  assert.ok(Object.values(graph.authority).every(v=>v===false));
  assert.equal(graph.manufacturer_advertised_contents.length,study.advertised_contents.length);
  assert.ok(graph.manufacturer_advertised_contents.every(x=>x.source_listed&&!x.physically_received_and_counted&&x.shipped_quantity===null));
  assert.ok(renderExplodedAssemblySvg(graph,{explode:75}).includes("PHYSICAL FIT UNVERIFIED"));
 }
});
test("maker-loaded kit references reflect only the documented complete-board option",()=>{
 const tangent=refs.studies.find(x=>x.id==="source-loaded-tangent-complete"),graph=build(tangent);
 assert.ok(graph.components.some(x=>x.role==="bracket_set"&&x.source_url.includes("loadedboards.com")));
 assert.ok(graph.components.some(x=>x.role==="wheelset"&&x.label.includes("105mm")));
 assert.ok(graph.components.some(x=>x.role==="bearing_set"));
 assert.ok(!graph.components.some(x=>x.role==="esc"));
 assert.equal(graph.manufacturer_mount_reference,null);
 const omakase=refs.studies.find(x=>x.id==="source-loaded-omakase-complete");
 assert.ok(build(omakase).components.some(x=>x.role==="bushing_set"));
 assert.ok(build(omakase).components.some(x=>x.role==="riser_set"));
});
test("Burton Channel and Re:Flex reference path is a hold, not verified fit",()=>{
 const study=refs.studies.find(x=>x.id==="source-burton-custom-mission");
 const report=build(study);
 const check=evaluateSnowboardMountReference(report.manufacturer_mount_reference);
 assert.equal(check.verdict,"MAKER_FAMILY_REFERENCE_MATCH_REVIEW_REQUIRED");
 assert.equal(check.physical_fit_verified,false);
 assert.equal(check.install_authorized,false);
 assert.equal(check.boot_fit,"BOOT_BINDING_FIT_NOT_VERIFIED");
 assert.ok(Object.values(check.authority).every(v=>v===false));
 assert.ok(report.components.some(x=>x.role==="boot_pair" && x.source_url===null));
 assert.ok(report.components.some(x=>x.role==="mounting_disc" && x.source_url?.includes("burton.com")));
});
test("EST non-Channel incompatible; Re:Flex 3D needs special disc; Step On boot must match",()=>{
 let a=evaluateSnowboardMountReference({
 board_mount:"2X4_REFERENCE",binding_mount:"EST",disc_family:null});
 assert.equal(a.verdict,"MANUFACTURER_REFERENCE_INCOMPATIBLE");
 a=evaluateSnowboardMountReference({
 board_mount:"3D_LEGACY_REFERENCE",binding_mount:"REFLEX",disc_family:"BURTON_REFLEX_COMBO"});
 assert.equal(a.verdict,"REQUIRED_SPECIAL_DISC_MISSING");
 a=evaluateSnowboardMountReference({
 board_mount:"CHANNEL_M6_REFERENCE",binding_mount:"REFLEX",
 disc_family:"BURTON_REFLEX_COMBO",boot_retention:"STEP_ON_ONLY"});
 assert.equal(a.verdict,"MAKER_FAMILY_REFERENCE_MATCH_REVIEW_REQUIRED");
 assert.equal(a.boot_fit,"STEP_ON_BOOT_MODEL_SIZE_REQUIRED");
 a=evaluateSnowboardMountReference({
 board_mount:"UNRECOGNIZED",binding_mount:"REFLEX",disc_family:"BURTON_REFLEX_COMBO"});
 assert.equal(a.verdict,"UNKNOWN_REFERENCE");
 assert.ok(Object.values(a.authority).every(x=>x===false));
});
test("forged source URL or study content cannot be passed directly",()=>{
 const study=structuredClone(refs.studies[0]);
 study.components[0].source_url="https://some-unrelated-shop.example";
 assert.throws(()=>build(study),/exact reviewed registry/);
 const s=structuredClone(refs.studies[0]);
 s.components[0].quantity_verified=500;
 assert.throws(()=>build(s),/exact reviewed registry/);
 const malformed=structuredClone(refs);
 malformed.studies[0].components[0].label="forged variant";
 assert.throws(()=>build(refs.studies[0],malformed),/exact reviewed registry/);
});
