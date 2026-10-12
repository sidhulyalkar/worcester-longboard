// Candidate-only metric 3D scene encoder. Never composited with procedural board,
// file-backed OEM GLBs, purchasing state or fabrication permissions.
// All coordinates here are research fixture millimeters, not measured manufacturer CAD.
import {evaluateMetricFixture} from "./cad_metric_workbench.mjs";
import {sampleCandidateMotionSweep} from "./cad_candidate_motion.mjs";
const check=(ok,msg)=>{if(!ok)throw Error("Candidate scene: "+msg);};
const add=(a,b)=>a.map((n,i)=>n+b[i]);
const sub=(a,b)=>a.map((n,i)=>n-b[i]);
const mul=(a,n)=>a.map(v=>v*n);
const dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0);
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const length=a=>Math.hypot(...a);
const transform=(rotation,position,p)=>add(rotation.map(row=>dot(row,p)),position);
const axisRotation=(axis,angle)=>{
 const [x,y,z]=mul(axis,1/length(axis)),c=Math.cos(angle),s=Math.sin(angle),q=1-c;
 return [[c+x*x*q,x*y*q-z*s,x*z*q+y*s],
  [y*x*q+z*s,c+y*y*q,y*z*q-x*s],
  [z*x*q-y*s,z*y*q+x*s,c+z*z*q]];
};
const matMul=(a,b)=>a.map(row=>
 [0,1,2].map(i=>dot(row,[b[0][i],b[1][i],b[2][i]])));
const boxCenter=b=>[0,1,2].map(i=>(b.min_mm[i]+b.max_mm[i])/2);
const boxSize=b=>[0,1,2].map(i=>b.max_mm[i]-b.min_mm[i]);
const axisAlignedBounds=items=>({
 min_mm:[0,1,2].map(i=>Math.min(...items.map(p=>p[i]))),
 max_mm:[0,1,2].map(i=>Math.max(...items.map(p=>p[i])))
});
const corners=b=>{
 const out=[];
 for(const x of [b.min_mm[0],b.max_mm[0]])
  for(const y of [b.min_mm[1],b.max_mm[1]])
   for(const z of [b.min_mm[2],b.max_mm[2]])out.push([x,y,z]);
 return out;
};
export function compileCandidateMetricScene(fixture,{
 expected_variant_id=null,sample_index=0}={}){
 const base=evaluateMetricFixture(fixture,{expected_variant_id});
 const sweep=fixture.motion?sampleCandidateMotionSweep(fixture,{expected_variant_id}):null;
 const max=sweep?sweep.sample_count:1;
 check(Number.isInteger(sample_index)&&sample_index>=0&&sample_index<max,
  "sample index outside validated sweep");
 const angle_deg=sweep?sweep.tested_angles_deg[sample_index]:0;
 const axis=sweep?fixture.motion.axis_direction_assembly:null;
 const axisRot=sweep?axisRotation(axis,angle_deg*Math.PI/180):null;
 const pivot=sweep?fixture.motion.axis_point_assembly_mm:null;
 const parts=base.parts.map((b,i)=>{
  const p=fixture.parts[i];
  check(p.id===b.id,"candidate part identity mismatch");
  const centerLocal=boxCenter(p.local_bounds_mm);
  const localSize=boxSize(p.local_bounds_mm);
  const posed=b.candidate_pose;
  let position_mm=transform(posed.rotation_rows,posed.translation_mm,centerLocal);
  let rotation_rows=posed.rotation_rows;
  const moving=!!sweep&&p.id===fixture.motion.moving_part_id;
  if(moving){
   position_mm=add(pivot,axisRot.map(row=>dot(row,sub(position_mm,pivot))));
   rotation_rows=matMul(axisRot,posed.rotation_rows);
  }
  const points=corners({min_mm:mul(localSize,-.5),max_mm:mul(localSize,.5)})
   .map(local=>transform(rotation_rows,position_mm,local));
  const aabb_mm=axisAlignedBounds(points);
  return {id:p.id,label:p.id.replaceAll("_"," "),revision:p.revision,
   center_mm:position_mm,dimensions_mm:localSize,rotation_rows,
   sampled_world_bounds_mm:aabb_mm,is_moving:moving,
   geometry_status:"UNVERIFIED_FIXTURE_BOUNDS_NOT_OEM_MESH"};
 });
 const pairStatuses=sweep?sweep.pairs.map(p=>({
  a:p.moving_part_id,b:p.stationary_part_id,
  classification:p.samples[sample_index].classification,
  possible_overlap:p.samples[sample_index].classification===
   "POSSIBLE_OVERLAP_REQUIRES_NARROW_PHASE",
  tested_angle_deg:p.samples[sample_index].angle_deg
 })):base.pairs.map(p=>({
  a:p.a,b:p.b,classification:p.classification,
  possible_overlap:p.classification==="POSSIBLE_OVERLAP_REQUIRES_NARROW_PHASE",
  tested_angle_deg:null
 }));
 const suspect=new Set(pairStatuses.filter(p=>p.possible_overlap)
  .flatMap(p=>[p.a,p.b]));
 return {scope:"ISOLATED_CANDIDATE_ENVELOPES_NOT_VERIFIED_CAD",
  kit_variant_id:fixture.kit_variant_id,
  fixture_type:fixture.fixture_type??"UNVERIFIED_SURVEY_INPUT",
  coordinate_units:"mm",angle_deg,sample_index,sample_count:max,
  moving_part_id:sweep?.pairs[0]?.moving_part_id??null,
  axis_point_mm:pivot,axis_direction:axis,
  parts:parts.map(p=>({...p,potential_overlap_at_sample:suspect.has(p.id)})),
  pair_statuses:pairStatuses,
  possible_overlap_pairs:pairStatuses.filter(p=>p.possible_overlap).length,
  physically_qualified_mates:0,physical_clearances_verified:0,
  actual_manufacturer_geometry_loaded:false,
  approved_for_fabrication:false,approved_for_purchase:false,
  unsampled_motion_checked:false};
}
