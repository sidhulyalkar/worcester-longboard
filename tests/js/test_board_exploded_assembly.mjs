import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {generateBoardDesignSpace} from "../../builder/platform_engine.mjs";
import {buildAssemblyGraph} from "../../builder/assembly_graph.mjs";
import {renderExplodedAssemblySvg} from "../../builder/exploded_renderer.mjs";
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../..");
const read=p=>JSON.parse(fs.readFileSync(path.join(ROOT,p),"utf8"));
const recipes=read("catalog/outdoor_assembly_recipes.v1.json");
const bundle={
 questionnaire:read("configurator/questionnaire.v1.json"),
 rules:read("configurator/rules.v1.json"),
 catalog:read("catalog/board_components.v1.json"),
 architectures:read("configurator/architectures.v1.json"),
 compatibility:read("configurator/compatibility_rules.v1.json"),
 swapSlots:read("configurator/swap_slots.v1.json"),
 geometry:read("catalog/board_geometry.v1.json"),
 composer:read("configurator/composer.v1.json"),
 catalogHealth:read("catalog/catalog_health.v1.json"),
 packageInclusions:read("catalog/board_package_inclusions.v1.json")
};
const candidates=generateBoardDesignSpace(read("configurator/examples/trail_rider_profile.json"),bundle).candidates;
const build=s=>buildAssemblyGraph(s,recipes,bundle.catalog,bundle.packageInclusions);
const selected=name=>candidates.find(x=>x.id===name);
test("every generated board preserves exact BOM IDs, with no source-quantity promotion",()=>{
 assert.ok(candidates.length>=10);
 for(const c of candidates){
  const graph=build(c);
  assert.equal(graph.scope,"UNQUALIFIED_SEMANTIC_ASSEMBLY_EXPLODED_VIEW");
  assert.deepEqual(graph.components.map(x=>x.component_id),c.bom.map(x=>x.component_id));
  assert.equal(graph.completeness.catalog_components_included,c.bom.length);
  assert.equal(graph.completeness.unique_bom_component_ids,c.bom.length);
  assert.ok(graph.components.every(x=>x.assembly_required_quantity===null &&
    x.supplier_order_quantity===null && !x.exact_variant_verified &&
    !x.approval_status.includes("APPROVED")));
  assert.ok(Object.values(graph.authority).every(x=>x===false));
  assert.equal(graph.safety.physical_qualification,"NOT_QUALIFIED");
  assert.ok(graph.groups.every(g=>g.exact_assembly_geometry_verified===false));
 }
});
test("donor contents and duplicate part references are separate from actual assembled quantities",()=>{
 const original=build(selected("brake_first_trail_core"));
 const donor=original.package_inclusion_hypotheses.find(x=>x.container_component_id==="DONOR-COMP95");
 assert.ok(donor);
 assert.equal(donor.source_registry_binding,"BOUND_REFERENCE_ONLY");
 assert.equal(donor.actual_contents_verified,false);
 assert.ok(donor.content_tokens.some(x=>x.token==="rockstar_ii_hubs" &&
   x.possible_component_ids.includes("HUB-RSII")));
 assert.ok(donor.content_tokens.every(x=>x.included_quantity===null &&
   !x.exact_part_match_verified));
 const broken=structuredClone(bundle.packageInclusions);
 broken.packages[0].catalog_snapshot_id="unrelated";
 const stale=buildAssemblyGraph(selected("brake_first_trail_core"),recipes,bundle.catalog,broken);
 assert.equal(stale.package_inclusion_hypotheses[0].source_registry_binding,"UNBOUND_OR_STALE_HOLD");
 assert.ok(stale.package_inclusion_hypotheses[0].content_tokens.every(x=>x.possible_component_ids.length===0));
});
test("all cross-sport concepts are unsourced and do not suggest physical acceptance",()=>{
 assert.equal(recipes.examples.length,5);
 for(const concept of recipes.examples){
  const graph=build(concept);
  assert.equal(graph.domain_id,concept.domain_id);
  assert.equal(graph.origin,"ILLUSTRATIVE_DOMAIN_RECIPE");
  assert.equal(graph.source_snapshot_as_of,null);
  assert.equal(graph.package_inclusion_hypotheses.length,0);
  assert.ok(graph.components.every(x=>x.source_kind==="illustrative_concept" &&
    x.source_url===null && x.assembly_required_quantity===null));
  assert.ok(!graph.safety.usable_for_mounting && !graph.safety.usable_for_binding_release);
  for(const p of [0,55,100]){
   const svg=renderExplodedAssemblySvg(graph,{explode:p,selectedId:graph.components[0].component_id});
   assert.match(svg,/<svg /);
   assert.match(svg,/NOT ASSEMBLY GEOMETRY/);
   assert.match(svg,/PHYSICAL FIT UNVERIFIED/);
   assert.match(svg,/Visual proxies/);
   assert.match(svg,/data-exploded-part=/);
   assert.ok(!svg.includes("viewBox=\"0 0 0"));
  }
 }
});
test("alpine ski and snowboard views preserve domain-specific safety holds",()=>{
 const ski=build(recipes.examples.find(x=>x.domain_id==="alpine_ski"));
 assert.ok(ski.unresolved_system_checks.some(x=>/release testing/.test(x)));
 const snowboard=build(recipes.examples.find(x=>x.domain_id==="snowboard"));
 assert.ok(snowboard.unresolved_system_checks.some(x=>/binding discs|adapter/.test(x)));
 assert.ok(snowboard.components.some(x=>x.role==="mounting_disc"));
 assert.ok(ski.components.some(x=>x.role==="ski_brake"));
});
test("unsupported parts, mutated sample SKUs and duplicate BOM fail closed",()=>{
 const c=structuredClone(selected("brake_first_trail_core"));
 c.bom.push({...c.bom[0]});
 assert.throws(()=>build(c),/Duplicate or invalid/);
 c.bom.pop();
 c.bom[0].component_id="FAKE-CATALOG";
 assert.throws(()=>build(c),/Unknown catalog/);
 const concept=structuredClone(recipes.examples[0]);
 concept.components[0].sku="fraudulent";
 assert.throws(()=>build(concept),/exact reviewed registry/);
 const unrecognized=structuredClone(recipes);
 unrecognized.groups[0].roles.push("truck");
 assert.throws(()=>buildAssemblyGraph(selected("brake_first_trail_core"),unrecognized,bundle.catalog,bundle.packageInclusions),/Ambiguous assembly role/);
});
test("svg text is escaped and explosion is clamped",()=>{
 const g=build(selected("brake_first_trail_core"));
 const poisoned=structuredClone(g);
 poisoned.label='<script>alert("x")</script>';
 poisoned.components[0].label="<img onerror=evil()>";
 const svg=renderExplodedAssemblySvg(poisoned,{explode:10000,selectedId:poisoned.components[0].component_id});
 assert.ok(!svg.includes("<script>"));
 assert.ok(!svg.includes("<img"));
 assert.ok(svg.includes("&lt;script&gt;"));
 assert.ok(svg.includes("100% separated"));
 assert.ok(svg.includes("exploded-active-part"));
});
