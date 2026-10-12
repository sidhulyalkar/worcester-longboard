import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {buildPickerStudy} from "../../builder/parts_picker_engine.mjs";
import {auditCompleteKitClaim} from "../../builder/complete_kit_closure.mjs";
import {buildCompleteKitVisualGraph} from "../../builder/complete_kit_visual_graph.mjs";
import {planExplodedScene} from "../../builder/exploded_scene_model.mjs";
import {renderExplodedAssemblySvg} from "../../builder/exploded_renderer.mjs";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../..");
const load=name=>JSON.parse(fs.readFileSync(path.join(root,"catalog",name),"utf8"));
const catalog=load("outdoor_parts_picker.v1.json"),retail=load("outdoor_retail_comparisons.v1.json");
const kit=load("outdoor_complete_kit_claims.v1.json");
const byName=name=>catalog.products.find(x=>x.id===name).variants[0].id;
function select(productId){
 const v=byName(productId);
 const s=buildPickerStudy(catalog,{domain_id:"skateboard_longboard",selections:{long_complete:v}});
 const audit=auditCompleteKitClaim(s,kit,catalog,retail);
 return {s,audit,view:buildCompleteKitVisualGraph(s,audit)};
}
test("same parent package, seven separately selectable visually unqualified child identities",()=>{
 const {s,audit,view}=select("loaded-tangent-complete");
 assert.equal(s.graph.components.length,1);
 assert.equal(s.report.qualified_supplier_order_lines,0);
 assert.equal(audit.independent_additional_item_orders,0);
 assert.equal(view.components.length,7);
 assert.equal(view.kit_parent_variant_id,s.selected_variants[0].variant_id);
 assert.equal(new Set(view.components.map(x=>x.component_id)).size,7);
 assert.deepEqual(view.components.map(x=>x.role),[
  "kit_child_deck","kit_child_zee_brackets","kit_child_trucks",
  "kit_child_wheels","kit_child_bearings","kit_child_deck_hardware",
  "kit_child_truck_hardware"]);
 assert.ok(view.components.every(x=>x.parent_package_variant_id===
  view.kit_parent_variant_id&&x.visual_proxy_only&&x.exact_variant_verified===false&&
  x.supplier_order_quantity===null&&x.actual_received_units===null));
 assert.deepEqual(view.connections,[]);
 assert.equal(view.completeness.physical_connections_qualified,0);
 assert.equal(view.safety.physical_qualification,"NOT_QUALIFIED");
 assert.equal(view.safety.usable_for_fabrication,false);
 assert.ok(Object.values(view.authority).every(x=>x===false));
 for(const percent of [0,50,100]){
  const p=planExplodedScene(view,{separation:percent,
   selectedId:view.components[3].component_id});
  assert.equal(p.parts.length,7);
  assert.equal(p.units,"ARBITRARY_VISUAL_UNITS");
  assert.equal(p.quantity_verified,false);
  assert.equal(p.physical_fit_verified,false);
  assert.equal(p.selected_id,view.components[3].component_id);
  const svg=renderExplodedAssemblySvg(view,{explode:percent,
   selectedId:p.selected_id});
  for(const c of view.components)assert.ok(svg.includes('data-exploded-part="'+c.component_id+'"'));
  assert.ok(svg.includes("conceptual assembly")&&svg.includes("unverified component"));
 }
});
test("switch 85 and 105 wheel setup invalidates ALL seven child selection IDs",()=>{
 const large=select("loaded-tangent-complete"),small=select("loaded-tangent-caguama");
 assert.equal(small.view.components.length,7);
 assert.notEqual(small.view.kit_parent_variant_id,large.view.kit_parent_variant_id);
 assert.ok(small.view.components.every(x=>!large.view.components.some(y=>y.component_id===x.component_id)));
 assert.equal(small.view.completeness.supplier_order_quantities_qualified,0);
});
test("modular longboard does not silently create a full maker package",()=>{
 const s=buildPickerStudy(catalog,{domain_id:"skateboard_longboard",selections:{}});
 const audit=auditCompleteKitClaim(s,kit,catalog,retail);
 assert.equal(buildCompleteKitVisualGraph(s,audit),s.graph);
});
test("claimed received child or changed maker variant cannot enter graph",()=>{
 const {s,audit}=select("loaded-tangent-complete");
 const forged=structuredClone(audit);
 forged.rows[0].actual_received_units=1;
 assert.throws(()=>buildCompleteKitVisualGraph(s,forged),/maker child/);
 const forged2=structuredClone(audit);
 forged2.variant_id=byName("loaded-tangent-caguama");
 assert.throws(()=>buildCompleteKitVisualGraph(s,forged2),/cannot substitute/);
 const forged3=structuredClone(audit);
 forged3.independent_additional_item_orders=1;
 assert.throws(()=>buildCompleteKitVisualGraph(s,forged3),/not in a reviewed/);
 const forged4=structuredClone(audit);
 forged4.rows[0].child_id=forged4.rows[1].child_id;
 assert.throws(()=>buildCompleteKitVisualGraph(s,forged4),/duplicate maker kit child/);
});
