import test from "node:test";
import assert from "node:assert/strict";
import {sampleCandidateMotionSweep,renderCandidateMotionSvg}
 from "../../builder/cad_candidate_motion.mjs";

const part=(id,tx=0,box={min_mm:[-1,-1,-1],max_mm:[1,1,1]})=>({
 id,source_url:"https://example.com/synthetic-not-manufacturer-cad",
 revision:"test-only",geometry_evidence:"UNVERIFIED_CANDIDATE_BOUNDS",
 mating_datums_physically_verified:false,exact_revision_received:false,
 survey_tolerance_mm:0.25,local_bounds_mm:box,
 correspondences:[[0,0,0],[5,0,0],[0,5,0],[0,0,5]].map(p=>({
  local_mm:p,assembly_mm:[p[0]+tx,p[1],p[2]]
 }))
});
const make=(fixedPosition=4)=>({
 schema_version:1,scope:"METRIC_CAD_SURVEY_FIXTURE_RESEARCH_ONLY",
 kit_variant_id:"loaded-tangent-complete-105 mm Dad Bod 77a",units:"mm",
 authority:{procurement_authorized:false,fabrication_authorized:false,
  physical_fit_qualified:false},
 parts:[part("synthetic_wheel",0,{min_mm:[3,-1,-1],max_mm:[5,1,1]}),
  part("synthetic_deck",fixedPosition)],
 motion:{scope:"CANDIDATE_MOTION_RESEARCH_ONLY",
  moving_part_id:"synthetic_wheel",stationary_part_ids:["synthetic_deck"],
  axis_point_assembly_mm:[0,0,0],axis_direction_assembly:[0,0,1],
  angle_range_deg:[-45,45],sample_step_deg:15,uncertainty_mm:0.25,
  kinematics_physically_verified:false,dynamic_clearance_qualified:false,
  contact_verified:false}
});
test("discrete candidate steering sweep flags overlaps but never reports physical contact",()=>{
 const fixture=make();
 const report=sampleCandidateMotionSweep(fixture,
  {expected_variant_id:fixture.kit_variant_id});
 assert.equal(report.scope,"SAMPLED_CANDIDATE_AABB_SWEEP_NO_PHYSICAL_CLEARANCE");
 assert.equal(report.sample_count,7);
 assert.equal(report.pair_count,1);
 assert.equal(report.pairs[0].samples[3].angle_deg,0);
 assert.equal(report.pairs[0].samples[3].classification,
  "POSSIBLE_OVERLAP_REQUIRES_NARROW_PHASE");
 assert.equal(report.pairs[0].samples[0].classification,
  "CANDIDATE_AABBS_SEPARATED");
 assert.equal(report.pairs[0].samples.at(-1).classification,
  "CANDIDATE_AABBS_SEPARATED");
 assert.equal(report.physical_clearances_verified,0);
 assert.equal(report.geometry_contacts_confirmed,0);
 assert.equal(report.motion_kinematics_verified,false);
 assert.equal(report.between_samples_checked,false);
 assert.equal(report.procurement_authorized,false);
 assert.equal(report.fabrication_authorized,false);
 const svg=renderCandidateMotionSvg(report);
 assert.match(svg,/NOT VERIFIED STEERING CLEARANCE/);
 assert.match(svg,/Orange dots represent possible box overlaps/);
 assert.match(svg,/viewBox="0 0 760 260"/);
});
test("candidate motion is exact-kit-scoped with bounded angles, uncertainty, and part IDs",()=>{
 const base=make();
 const cases=[
  x=>x.motion.dynamic_clearance_qualified=true,
  x=>x.motion.contact_verified=true,
  x=>x.motion.kinematics_physically_verified=true,
  x=>x.motion.axis_direction_assembly=[0,0,0],
  x=>x.motion.axis_point_assembly_mm=[NaN,0,0],
  x=>x.motion.angle_range_deg=[-90,10],
  x=>x.motion.angle_range_deg=[10,10],
  x=>x.motion.sample_step_deg=0,
  x=>x.motion.sample_step_deg=16,
  x=>x.motion.uncertainty_mm=-1,
  x=>x.motion.stationary_part_ids=["synthetic_deck","synthetic_deck"],
  x=>x.motion.stationary_part_ids=["synthetic_wheel"],
  x=>x.motion.stationary_part_ids=["unknown"],
  x=>x.authority.fabrication_authorized=true,
  x=>x.motion.scope="PHYSICAL_STEERING_CLEARED"
 ];
 for(const mutate of cases){
  const bad=structuredClone(base);mutate(bad);
  assert.throws(()=>sampleCandidateMotionSweep(bad),/(CAD motion candidate:|Metric CAD workbench:)/);
 }
 assert.throws(()=>sampleCandidateMotionSweep(base,{expected_variant_id:"wrong-kit"}),
  /match selected exact kit variant/);
});
test("sampling remains bounded and rotation axis is normalized",()=>{
 const sample=make(20);
 sample.motion.axis_direction_assembly=[0,0,10];
 sample.motion.angle_range_deg=[-44.7,44.8];
 sample.motion.sample_step_deg=1;
 const report=sampleCandidateMotionSweep(sample);
 assert.equal(report.sample_count,91);
 assert.deepEqual(report.tested_angles_deg.slice(0,2),[-44.7,-43.7]);
 assert.equal(report.tested_angles_deg.at(-1),44.8);
 assert.equal(report.possible_overlap_pairs,0);
 assert.ok(report.pairs[0].samples.every(s=>s.physical_clearance_qualified===false));
});
test("motion export renderer refuses false physical clearance fields",()=>{
 const report=sampleCandidateMotionSweep(make());
 report.physical_clearances_verified=1;
 assert.throws(()=>renderCandidateMotionSvg(report),/CAD motion candidate:/);
});
