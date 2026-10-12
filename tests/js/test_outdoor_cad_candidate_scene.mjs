import test from "node:test";
import assert from "node:assert/strict";
import {compileCandidateMetricScene} from "../../builder/cad_candidate_scene.mjs";
import {makeSyntheticCandidateMotionFixture} from "../../builder/cad_demo_fixture.mjs";

const sourceVariant="loaded-tangent-complete-105 mm Dad Bod 77a";
test("candidate scene enforces exact kit and always stays separate from manufacturer assembly",()=>{
 const fixture=makeSyntheticCandidateMotionFixture(sourceVariant);
 const report=compileCandidateMetricScene(fixture,{
  expected_variant_id:sourceVariant,sample_index:3});
 assert.equal(report.scope,"ISOLATED_CANDIDATE_ENVELOPES_NOT_VERIFIED_CAD");
 assert.equal(report.kit_variant_id,sourceVariant);
 assert.equal(report.fixture_type,"SYNTHETIC_NUMERICAL_DEMO_NOT_REAL_ASSEMBLY");
 assert.equal(report.sample_count,7);
 assert.equal(report.angle_deg,0);
 assert.equal(report.parts.length,2);
 assert.equal(report.moving_part_id,"example_moving_box");
 assert.deepEqual(report.parts[0].center_mm,[4,0,0]);
 assert.deepEqual(report.parts[1].center_mm,[4,0,0]);
 assert.equal(report.possible_overlap_pairs,1);
 assert.ok(report.parts.every(p=>p.potential_overlap_at_sample));
 assert.ok(report.parts.every(p=>p.geometry_status==="UNVERIFIED_FIXTURE_BOUNDS_NOT_OEM_MESH"));
 assert.equal(report.physically_qualified_mates,0);
 assert.equal(report.physical_clearances_verified,0);
 assert.equal(report.actual_manufacturer_geometry_loaded,false);
 assert.equal(report.approved_for_purchase,false);
 assert.equal(report.approved_for_fabrication,false);
 assert.equal(report.unsampled_motion_checked,false);
});
test("angle scrubbing produces transformed world positions without changing input geometry",()=>{
 const fixture=makeSyntheticCandidateMotionFixture(sourceVariant);
 const before=JSON.stringify(fixture);
 const turn0=compileCandidateMetricScene(fixture,{sample_index:0});
 const mid=compileCandidateMetricScene(fixture,{sample_index:3});
 const turn1=compileCandidateMetricScene(fixture,{sample_index:6});
 assert.equal(JSON.stringify(fixture),before,"renderer must never mutate source fixture");
 assert.equal(turn0.angle_deg,-45);
 assert.equal(turn1.angle_deg,45);
 const left=turn0.parts.find(p=>p.is_moving).center_mm;
 const right=turn1.parts.find(p=>p.is_moving).center_mm;
 const center=mid.parts.find(p=>p.is_moving).center_mm;
 const close=(a,b)=>assert.ok(Math.abs(a-b)<1e-9,`${a} vs ${b}`);
 close(left[0],4/Math.sqrt(2));
 close(left[1],-4/Math.sqrt(2));
 close(right[0],4/Math.sqrt(2));
 close(right[1],4/Math.sqrt(2));
 assert.deepEqual(center,[4,0,0]);
 assert.deepEqual(turn0.parts.find(p=>!p.is_moving).center_mm,[4,0,0]);
 assert.equal(turn0.sample_index,0);
 assert.equal(turn1.sample_index,6);
 assert.equal(turn0.possible_overlap_pairs,0);
 assert.equal(turn1.possible_overlap_pairs,0);
});
test("non-motion survey remains inspectable with one disabled angle sample",()=>{
 const fixture=makeSyntheticCandidateMotionFixture(sourceVariant);
 delete fixture.motion;
 const result=compileCandidateMetricScene(fixture,{sample_index:0});
 assert.equal(result.sample_count,1);
 assert.equal(result.angle_deg,0);
 assert.equal(result.axis_direction,null);
 assert.equal(result.moving_part_id,null);
 assert.equal(result.parts.length,2);
 assert.equal(result.physical_clearances_verified,0);
 assert.throws(()=>compileCandidateMetricScene(fixture,{sample_index:1}),/sample index/);
});
test("forged safety claims, wrong kit and invalid indices never compile",()=>{
 const fixture=makeSyntheticCandidateMotionFixture(sourceVariant);
 assert.throws(()=>compileCandidateMetricScene(fixture,{
  expected_variant_id:"loaded-tangent-caguama-85 mm Caguama 80a"
 }),/match selected exact kit variant/);
 for(const invalid of [-1,7,1.5,NaN,Infinity,undefined]){
  if(invalid===undefined)continue;
  assert.throws(()=>compileCandidateMetricScene(fixture,{sample_index:invalid}),
   /sample index/);
 }
 const tampered=structuredClone(fixture);
 tampered.motion.dynamic_clearance_qualified=true;
 assert.throws(()=>compileCandidateMetricScene(tampered),
  /CAD motion candidate:/);
 const tampered2=structuredClone(fixture);
 tampered2.authority.procurement_authorized=true;
 assert.throws(()=>compileCandidateMetricScene(tampered2),
  /Metric CAD workbench:/);
});
