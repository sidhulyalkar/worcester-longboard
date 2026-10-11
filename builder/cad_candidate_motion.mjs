// Discrete candidate motion screening. AABB overlap is not contact;
// separation on samples is NOT continuous steering/wheelbite clearance.
import {evaluateMetricFixture,compareCandidateAabbs} from "./cad_metric_workbench.mjs";
const chk=(ok,msg)=>{if(!ok)throw Error("CAD motion candidate: "+msg);};
const scalar=n=>typeof n==="number"&&Number.isFinite(n)&&Math.abs(n)<1e6;
const vec=v=>Array.isArray(v)&&v.length===3&&v.every(scalar);
const dot=(a,b)=>a.reduce((s,x,i)=>s+x*b[i],0);
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const add=(a,b)=>a.map((x,i)=>x+b[i]);
const sub=(a,b)=>a.map((x,i)=>x-b[i]);
const mul=(a,s)=>a.map(x=>x*s);
const norm=a=>Math.hypot(...a);
const corners=b=>{
 const out=[];
 for(const x of [b.min_mm[0],b.max_mm[0]])
  for(const y of [b.min_mm[1],b.max_mm[1]])
   for(const z of [b.min_mm[2],b.max_mm[2]])out.push([x,y,z]);
 return out;
};
const bounds=pts=>({min_mm:[0,1,2].map(i=>Math.min(...pts.map(p=>p[i]))),
 max_mm:[0,1,2].map(i=>Math.max(...pts.map(p=>p[i])))});
const transform=(p,pose)=>add(pose.rotation_rows.map(row=>dot(row,p)),pose.translation_mm);
const rotate=(p,origin,k,r)=>{
 const a=sub(p,origin),c=Math.cos(r),s=Math.sin(r);
 return add(origin,add(add(mul(a,c),mul(cross(k,a),s)),mul(k,dot(k,a)*(1-c))));
};
export function sampleCandidateMotionSweep(fixture,{expected_variant_id=null}={}){
 const base=evaluateMetricFixture(fixture,{expected_variant_id});
 const motion=fixture.motion;
 chk(motion?.scope==="CANDIDATE_MOTION_RESEARCH_ONLY"&&
  motion.kinematics_physically_verified===false&&
  motion.dynamic_clearance_qualified===false&&motion.contact_verified===false,
  "candidate motion requires explicit no-authority scope");
 chk(vec(motion.axis_point_assembly_mm)&&vec(motion.axis_direction_assembly)&&
  norm(motion.axis_direction_assembly)>=0.01,"invalid sample rotation axis");
 chk(Array.isArray(motion.angle_range_deg)&&motion.angle_range_deg.length===2&&
  motion.angle_range_deg.every(scalar)&&motion.angle_range_deg[0]>=-45&&
  motion.angle_range_deg[1]<=45&&
  motion.angle_range_deg[1]>motion.angle_range_deg[0],
  "angle range must lie within -45 to +45 degrees");
 chk(scalar(motion.sample_step_deg)&&motion.sample_step_deg>=1&&
  motion.sample_step_deg<=15,"sample step outside 1 to 15 degrees");
 chk(scalar(motion.uncertainty_mm)&&motion.uncertainty_mm>=0&&
  motion.uncertainty_mm<=10,"invalid uncertainty");
 const parts=new Map(base.parts.map(p=>[p.id,p]));
 chk(parts.has(motion.moving_part_id)&&
  Array.isArray(motion.stationary_part_ids)&&
  motion.stationary_part_ids.length>0&&motion.stationary_part_ids.length<=13&&
  new Set(motion.stationary_part_ids).size===motion.stationary_part_ids.length&&
  motion.stationary_part_ids.every(id=>id!==motion.moving_part_id&&parts.has(id)),
  "candidate part identities invalid");
 const moving=fixture.parts.find(p=>p.id===motion.moving_part_id);
 const pose=parts.get(motion.moving_part_id).candidate_pose;
 const pts=corners(moving.local_bounds_mm).map(p=>transform(p,pose));
 const k=mul(motion.axis_direction_assembly,1/norm(motion.axis_direction_assembly));
 const [lo,hi]=motion.angle_range_deg,angles=[];
 for(let i=0;i<=120;i++){
  const a=lo+i*motion.sample_step_deg;
  if(a>=hi-1e-9)break;
  angles.push(Number(a.toFixed(7)));
 }
 angles.push(hi);
 chk(angles.length>=2&&angles.length<=121,"sample limit exceeded");
 const pairs=motion.stationary_part_ids.map(id=>{
  const stationary=parts.get(id).assembled_broad_phase_bounds_mm;
  const samples=angles.map(angle_deg=>{
   const rotated=bounds(pts.map(p=>rotate(p,motion.axis_point_assembly_mm,k,
    angle_deg*Math.PI/180)));
   const candidate=compareCandidateAabbs(rotated,stationary,
    {uncertainty_mm:motion.uncertainty_mm});
   return {angle_deg,classification:candidate.classification,
    conservative_axis_gap_mm:candidate.conservative_axis_gap_mm,
    physical_clearance_qualified:false};
  });
  return {moving_part_id:motion.moving_part_id,stationary_part_id:id,
   samples,possible_overlap_samples:samples.filter(s=>
    s.classification==="POSSIBLE_OVERLAP_REQUIRES_NARROW_PHASE").length};
 });
 return {scope:"SAMPLED_CANDIDATE_AABB_SWEEP_NO_PHYSICAL_CLEARANCE",
  kit_variant_id:fixture.kit_variant_id,
  angle_range_deg:[lo,hi],sample_step_deg:motion.sample_step_deg,
  uncertainty_mm:motion.uncertainty_mm,sample_count:angles.length,
  tested_angles_deg:angles,pairs,pair_count:pairs.length,
  possible_overlap_pairs:pairs.filter(p=>p.possible_overlap_samples>0).length,
  motion_kinematics_verified:false,between_samples_checked:false,
  geometry_contacts_confirmed:0,physical_clearances_verified:0,
  steering_revision_verified:false,loaded_deck_deflection_checked:false,
  physical_fit_qualified:false,procurement_authorized:false,fabrication_authorized:false,
  interpretation:"Sampled boxes with unverified kinematics, not validated geometry or continuous clearance."};
}
export function renderCandidateMotionSvg(sweep){
 chk(sweep?.scope==="SAMPLED_CANDIDATE_AABB_SWEEP_NO_PHYSICAL_CLEARANCE"&&
  sweep.physical_clearances_verified===0&&
  Array.isArray(sweep.pairs)&&sweep.pairs.length===sweep.pair_count,
  "candidate-only motion plot required");
 const [lo,hi]=sweep.angle_range_deg;
 const x=a=>(40+682*(a-lo)/(hi-lo)).toFixed(2);
 const rows=sweep.pairs.map((pair,i)=>{
  const y=57+(i+.5)*140/sweep.pairs.length;
  return '<text x="40" y="'+(y-12).toFixed(2)+'" fill="#e8f2f7" font-size="11">'+
   'Candidate pair '+(i+1)+': '+pair.possible_overlap_samples+
   ' possible overlap samples</text>'+pair.samples.map(s=>
   '<circle cx="'+x(s.angle_deg)+'" cy="'+y.toFixed(2)+
   '" r="'+(s.classification==="POSSIBLE_OVERLAP_REQUIRES_NARROW_PHASE"?6:4)+
   '" fill="'+(s.classification==="POSSIBLE_OVERLAP_REQUIRES_NARROW_PHASE"?
    "#e9ac7b":"#88c2bc")+'"/>').join("");
 }).join("");
 return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 260" role="img" '+
  'aria-label="Unverified candidate motion sweep. Orange dots represent possible box overlaps; there is no confirmed clearance or contact." style="display:block;width:100%;height:auto">'+
  '<rect width="760" height="260" rx="9" fill="#10232c"/>'+
  '<text x="35" y="26" font-size="13" fill="#e9f4f7">CANDIDATE SWEEP · NOT VERIFIED STEERING CLEARANCE</text>'+
  rows+'<line x1="40" y1="215" x2="722" y2="215" stroke="#95afbd"/>'+
  '<text x="40" y="235" font-size="11" fill="#bdd7e0">'+lo+'°</text>'+
  '<text x="722" y="235" font-size="11" text-anchor="end" fill="#bdd7e0">'+hi+'°</text>'+
  '<text x="380" y="251" font-size="10" text-anchor="middle" fill="#bdd7e0">Discrete samples only; unsampled angles UNKNOWN</text></svg>';
}
