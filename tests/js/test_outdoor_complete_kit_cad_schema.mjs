import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {buildPickerStudy} from "../../builder/parts_picker_engine.mjs";
import {auditCompleteKitClaim} from "../../builder/complete_kit_closure.mjs";
import {buildCompleteKitVisualGraph} from "../../builder/complete_kit_visual_graph.mjs";
import {compileCompleteKitCadDisplay,planCadDisplay,validateKitCadRecipe}
 from "../../builder/complete_kit_cad_schema.mjs";
import {renderCompleteKitCadSvg} from "../../builder/complete_kit_cad_svg.mjs";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../..");
const load=n=>JSON.parse(fs.readFileSync(path.join(root,"catalog",n),"utf8"));
const catalog=load("outdoor_parts_picker.v1.json");
const kits=load("outdoor_complete_kit_claims.v1.json");
const retail=load("outdoor_retail_comparisons.v1.json");
const recipe=load("outdoor_complete_kit_cad_recipes.v1.json");
function model(product){
 const id=catalog.products.find(p=>p.id===product).variants[0].id;
 const study=buildPickerStudy(catalog,{domain_id:"skateboard_longboard",
  selections:{long_complete:id}});
 const audit=auditCompleteKitClaim(study,kits,catalog,retail);
 const graph=buildCompleteKitVisualGraph(study,audit);
 const cad=compileCompleteKitCadDisplay(study,audit,kits,recipe);
 return {study,audit,graph,cad};
}
test("compact kit recipe has seven typed roles and prohibits metric mount claims",()=>{
 assert.equal(validateKitCadRecipe(recipe).validated_roles,7);
 assert.equal(recipe.coordinate_frame.units,"ARBITRARY_VISUAL_UNITS");
 assert.equal(recipe.dimensional_evidence_policy.actual_mates_verified,false);
 assert.equal(recipe.dimensional_evidence_policy.published_dimensions_are_not_mating_datums,true);
 assert.equal(recipe.layout.reference_wheel_diameter_mm,105);
 for(const role of ["deck","zee_brackets","trucks","wheels","bearings",
  "deck_hardware","truck_hardware"]){
  assert.ok(recipe.primitives.some(p=>p.role===role));
  assert.ok(recipe.layout.parts_explode_offsets_u[role]);
 }
});
test("assembled loaded complete board is a coherent seven-category visual, not seven orders",()=>{
 const {study,audit,graph,cad}=model("loaded-tangent-complete");
 assert.equal(study.graph.components.length,1);
 assert.equal(graph.components.length,7);
 assert.equal(cad.scope,"BROWSER_PARAMETRIC_CAD_DISPLAY_UNQUALIFIED");
 assert.equal(cad.children.length,7);
 assert.equal(cad.published_dimensions_mm.complete_length,914);
 assert.equal(cad.published_dimensions_mm.complete_width,248);
 assert.equal(cad.published_dimensions_mm.wheel_diameter,105);
 assert.equal(cad.additional_purchase_lines,0);
 assert.equal(cad.delivered_contents_verified,0);
 assert.equal(cad.physical_mates_verified,0);
 assert.equal(cad.total_order_price,null);
 assert.deepEqual(Object.values(cad.authority),Array(5).fill(false));
 assert.equal(audit.independent_additional_item_orders,0);
 assert.deepEqual(cad.children.map(x=>x.component_id),
  graph.components.map(x=>x.component_id));
 assert.equal(cad.children.find(x=>x.role==="wheels").instances.length,4);
 assert.equal(cad.children.find(x=>x.role==="bearings").instances.length,8);
 assert.ok(cad.children.filter(x=>x.role.endsWith("hardware"))
  .every(x=>x.instances.length===1&&x.instances[0].symbol_only&&
  x.instances[0].actual_location_known===false));
 for(const n of cad.children){
  assert.equal(n.true_mount_datum_mm,null);
  assert.equal(n.true_clearance_mm,null);
  assert.equal(n.actual_received_units,undefined);
  assert.ok(n.instances.every(item=>item.at.length===3));
 }
 const assembled=planCadDisplay(cad,0);
 assert.ok(assembled.parts.every(p=>p.position.every(n=>n===0)));
 assert.ok(assembled.parts.filter(p=>p.visible).length===5);
 assert.equal(assembled.mechanical_clearances_checked,false);
 assert.equal(assembled.physical_assembly_qualified,false);
 const exploded=planCadDisplay(cad,100,graph.components[3].component_id);
 assert.ok(exploded.parts.some(p=>p.position.some(n=>n!==0)));
 assert.equal(exploded.parts.filter(p=>p.visible).length,7);
 assert.equal(exploded.parts.filter(p=>p.selected).length,1);
 const svg=renderCompleteKitCadSvg(cad,{explode:0});
 assert.match(svg,/INTEGRATED BOARD/);
 assert.match(svg,/mounting coordinates not measured/);
 assert.equal((svg.match(/data-exploded-part=/g)||[]).length,7);
 for(const c of cad.children)assert.ok(svg.includes(c.component_id));
 assert.match(renderCompleteKitCadSvg(cad,{explode:100}),/EXPLODED COMPONENTS/);
});
test("85 vs 105 mm source-linked models change the normalized wheel radius, not mounts",()=>{
 const large=model("loaded-tangent-complete").cad;
 const small=model("loaded-tangent-caguama").cad;
 assert.notEqual(large.kit_id,small.kit_id);
 assert.equal(small.published_dimensions_mm.wheel_diameter,85);
 assert.equal(large.published_dimensions_mm.wheel_diameter,105);
 const radius=cad=>cad.children.find(x=>x.role==="wheels").instances[0].radius;
 assert.equal(Number((radius(small)/radius(large)).toFixed(6)),
  Number((85/105).toFixed(6)));
 assert.ok(small.children.every(x=>!large.children.some(y=>y.component_id===x.component_id)));
 assert.equal(small.physical_mates_verified,0);
 assert.equal(small.additional_purchase_lines,0);
});
test("forged source geometry, invalid authority or altered kit identity fails closed",()=>{
 const mutate=fn=>{const r=structuredClone(recipe);fn(r);return r;};
 const cases=[
  x=>x.authority.fabrication_authorized=true,
  x=>x.coordinate_frame.units="mm",
  x=>x.coordinate_frame.origin_physically_measured=true,
  x=>x.dimensional_evidence_policy.actual_mates_verified=true,
  x=>x.dimensional_evidence_policy.fastener_locations_verified=true,
  x=>x.primitives[3].pattern="EIGHT_CORNERS",
  x=>x.layout.parts_explode_offsets_u.deck=[999,0,0],
  x=>x.layout.reference_wheel_diameter_mm=88
 ];
 for(const fn of cases)
  assert.throws(()=>validateKitCadRecipe(mutate(fn)),/CAD display schema:/);
 const {study,audit}=model("loaded-tangent-complete");
 const bad=structuredClone(audit);bad.variant_id="another-kit";
 assert.throws(()=>compileCompleteKitCadDisplay(study,bad,kits,recipe),
  /Kit visual study:/);
 const cad=model("loaded-tangent-complete").cad;
 cad.authority.procurement_authorized=true;
 assert.throws(()=>planCadDisplay(cad,0),/CAD display schema:/);
});
test("no complete kit emits no false parametric board CAD",()=>{
 const study=buildPickerStudy(catalog,{domain_id:"skateboard_longboard",selections:{}});
 const audit=auditCompleteKitClaim(study,kits,catalog,retail);
 assert.equal(compileCompleteKitCadDisplay(study,audit,kits,recipe),null);
});
