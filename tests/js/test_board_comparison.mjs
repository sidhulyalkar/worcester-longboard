import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import {fileURLToPath} from "node:url";
import {questionnaireDefaults} from "../../builder/engine.mjs";
import {generateBoardDesignSpace} from "../../builder/platform_engine.mjs";
import {validateExampleRides,profileForExample} from "../../builder/example_rides.mjs";
import {assemblyGuide} from "../../builder/assembly_guide.mjs";
import {compareCandidates,defaultComparisonIds} from "../../builder/comparison.mjs";
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../..");
const read=p=>JSON.parse(fs.readFileSync(path.join(ROOT,p),"utf8"));
const b={
  questionnaire:read("configurator/questionnaire.v1.json"),
  rules:read("configurator/rules.v1.json"),
  catalog:read("catalog/board_components.v1.json"),
  architectures:read("configurator/architectures.v1.json"),
  compatibility:read("configurator/compatibility_rules.v1.json"),
  swapSlots:read("configurator/swap_slots.v1.json"),
  geometry:read("catalog/board_geometry.v1.json"),
  composer:read("configurator/composer.v1.json"),
  catalogHealth:read("catalog/catalog_health.v1.json"),
};
const scenarios=read("configurator/example_rides.v1.json");
const defaults=questionnaireDefaults(b.questionnaire);
const result=generateBoardDesignSpace(defaults,b);
const get=id=>result.candidates.find(c=>c.id===id);
test("six terrain, rider and budget goals match the existing questionnaire and curated references",()=>{
  assert.equal(validateExampleRides(scenarios,b.questionnaire,b.architectures).length,6);
  assert.equal(new Set(scenarios.scenarios.map(x=>x.id)).size,6);
  assert.ok(scenarios.scenarios.some(x=>x.overrides.electric_propulsion==="yes"));
  assert.ok(scenarios.scenarios.some(x=>x.overrides.electric_propulsion==="no"));
  assert.ok(new Set(scenarios.scenarios.map(x=>x.budget_usd)).size>=5);
  for(const s of scenarios.scenarios){
    const p=profileForExample(s,defaults);
    assert.equal(p.budget_usd,s.budget_usd);
    assert.equal(["terrain_pavement","terrain_packed_dirt","terrain_loose_gravel","terrain_roots_rocks","terrain_grass_brush"].reduce((n,k)=>n+p[k],0),100);
    assert.ok(get(s.reference_candidate_id),s.reference_candidate_id);
  }
});
test("malformed examples fail closed",()=>{
  let bad=structuredClone(scenarios);
  bad.scenarios[1].id=bad.scenarios[0].id;
  assert.throws(()=>validateExampleRides(bad,b.questionnaire,b.architectures),/Duplicate/);
  bad=structuredClone(scenarios);bad.scenarios[0].overrides.weight_lb=999;
  assert.throws(()=>validateExampleRides(bad,b.questionnaire,b.architectures),/Out-of-bounds/);
  bad=structuredClone(scenarios);bad.scenarios[0].overrides.unknown_field=1;
  assert.throws(()=>validateExampleRides(bad,b.questionnaire,b.architectures),/Unknown example profile field/);
  bad=structuredClone(scenarios);bad.scenarios[0].overrides.board_experience="unlisted";
  assert.throws(()=>validateExampleRides(bad,b.questionnaire,b.architectures),/Unsupported example selection/);
});
test("comparison defaults to two mechanically different nonauthoritative designs",()=>{
  const ids=defaultComparisonIds(result.candidates);
  assert.deepEqual(ids,["brake_first_trail_core","trampa_hydraulic_freeride"]);
  const before=JSON.stringify(result.candidates);
  const x=compareCandidates(...ids.map(get),b.geometry,b.catalog);
  assert.equal(x.mechanically_distinct,true);
  assert.ok(x.differentiators.geometry_fields_changed.includes("deck_id"));
  assert.ok(x.candidates.every(c=>Object.values(c.authority).every(v=>v===false)));
  assert.ok(Object.values(x.authority).every(v=>v===false));
  assert.equal(JSON.stringify(result.candidates),before);
});
test("comparison retains original price incompleteness, sources, unknown measurements",()=>{
  const tr=generateBoardDesignSpace(read("configurator/examples/trail_rider_profile.json"),b);
  const a=tr.candidates.find(c=>c.id==="trampa_boardnamics_coexistence");
  const c=tr.candidates.find(c=>c.id==="trampa_hydraulic_freeride");
  const x=compareCandidates(a,c,b.geometry,b.catalog);
  assert.equal(x.candidates[0].evidence.open_interfaces,a.evidence.summary.open_interfaces);
  assert.ok(x.candidates[0].evidence.worklist.some(t=>t.category_pair==="drive:truck"));
  assert.ok(x.candidates[0].evidence.sources.length);
  assert.deepEqual(x.candidates[0].cost.unpriced_component_ids,[...new Set(a.cost.unpriced_component_ids)].sort());
  assert.ok(x.candidates[0].cost.excluded.includes("Tools, safety gear and validation"));
  assert.equal(x.candidates[0].assembly.authority.powered_operation_authorized,false);
  assert.equal(x.authority.fabrication_authorized,false);
});
test("powered assembly is professional/gated and manual roadmaps are still unreleased",()=>{
  const manual=assemblyGuide(get("brake_first_trail_core"));
  const electric=assemblyGuide(get("x1_compact_electric_study"));
  assert.equal(manual.powered,false);
  assert.equal(electric.powered,true);
  assert.equal(manual.stages.find(s=>s.id==="electrical").status,"NOT_APPLICABLE");
  assert.equal(electric.stages.find(s=>s.id==="electrical").status,"POWER_GATED");
  assert.equal(electric.stages.find(s=>s.id==="commission").status,"POWER_GATED");
  assert.ok(electric.stages.find(s=>s.id==="electrical").description.includes("Do not build a loose-cell battery pack"));
  assert.ok(Object.values(manual.authority).every(v=>v===false));
  assert.ok(Object.values(electric.authority).every(v=>v===false));
});
test("same physical configuration cannot masquerade as distinct comparison",()=>{
  const a=get("brake_first_trail_core");
  assert.throws(()=>compareCandidates(a,a,b.geometry,b.catalog),/two distinct/);
  const duplicate=structuredClone(a);duplicate.id="duplicate";
  const x=compareCandidates(a,duplicate,b.geometry,b.catalog);
  assert.equal(x.mechanically_distinct,false);
  assert.deepEqual(x.differentiators.geometry_fields_changed,[]);
});
