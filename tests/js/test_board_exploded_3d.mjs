import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {buildAssemblyGraph} from "../../builder/assembly_graph.mjs";
import {planExplodedScene,SCENE_SCOPE} from "../../builder/exploded_scene_model.mjs";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../..");
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
const recipes=read("catalog/outdoor_assembly_recipes.v1.json");
const refs=read("catalog/board_sport_reference_studies.v1.json");
const graphs=[
 ...recipes.examples.map(x=>buildAssemblyGraph(x,recipes)),
 ...refs.studies.map(x=>buildAssemblyGraph(x,recipes,null,null,refs))
];
test("3D model follows the exact graph component identities across every sport",()=>{
 for(const graph of graphs){
  for(const separation of [0,25,50,78,100]){
   const plan=planExplodedScene(graph,{separation,selectedId:graph.components[0].component_id});
   assert.equal(plan.scope,SCENE_SCOPE);
   assert.deepEqual(plan.parts.map(x=>x.component_id),graph.components.map(x=>x.component_id));
   assert.equal(plan.separation_percent,separation);
   assert.equal(plan.parts.filter(x=>x.selected).length,1);
   assert.ok(plan.parts.every(x=>x.position.length===3&&x.position.every(Number.isFinite)));
   assert.equal(plan.units,"ARBITRARY_VISUAL_UNITS");
   assert.equal(plan.physical_fit_verified,false);
   assert.equal(plan.physical_release_authorized,false);
   assert.equal(plan.quantity_verified,false);
   assert.ok(plan.parts.every(x=>x.metric_dimensions_mm===null&&
     x.physical_mount_point_mm===null&&!x.exact_geometry_verified));
  }
 }
});
test("exploding moves proxy parts, not immutable graph or physical authority",()=>{
 const graph=graphs.find(x=>x.domain_id==="snowboard");
 const baseline=structuredClone(graph);
 const assembled=planExplodedScene(graph,{separation:0});
 const exploded=planExplodedScene(graph,{separation:100});
 assert.deepEqual(graph,baseline);
 assert.ok(exploded.parts.some((p,i)=>p.position.some((c,j)=>c!==assembled.parts[i].position[j])));
 assert.ok(Object.values(graph.authority).every(v=>v===false));
});
test("unknown geometry, forged authority and duplicate parts fail closed",()=>{
 const graph=structuredClone(graphs[0]);
 assert.throws(()=>planExplodedScene({...graph,scope:"PHYSICAL_CAD"}),/unqualified/);
 assert.throws(()=>planExplodedScene({...graph,authority:{procurement_authorized:true}}),/unqualified/);
 assert.throws(()=>planExplodedScene({...graph,safety:{physical_qualification:"QUALIFIED"}}),/unqualified/);
 graph.components.push({...graph.components[0]});
 assert.throws(()=>planExplodedScene(graph),/duplicate/);
 graph.components.pop();
 graph.components[0].exact_variant_verified=true;
 assert.throws(()=>planExplodedScene(graph),/claimed-qualified/);
});
test("separation clamps and unsupported groups are rejected",()=>{
 const graph=graphs[0];
 assert.equal(planExplodedScene(graph,{separation:500}).separation_percent,100);
 assert.equal(planExplodedScene(graph,{separation:-5}).separation_percent,0);
 assert.equal(planExplodedScene(graph,{separation:NaN}).separation_percent,78);
 const broken=structuredClone(graph);
 broken.groups.push({...broken.groups[0],id:"unregistered"});
 assert.throws(()=>planExplodedScene(broken),/group/);
});
