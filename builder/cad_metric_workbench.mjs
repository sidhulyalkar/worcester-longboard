// Deterministic candidate metric frame alignment and AABB broad-phase only.
// This deliberately cannot qualify a physical fit, clearance, safety or purchase.
const check=(ok,msg)=>{if(!ok)throw Error("Metric CAD workbench: "+msg);};
const finite=n=>typeof n==="number"&&Number.isFinite(n)&&Math.abs(n)<=1e7;
const vec=p=>Array.isArray(p)&&p.length===3&&p.every(finite);
const sub=(a,b)=>a.map((x,i)=>x-b[i]);
const add=(a,b)=>a.map((x,i)=>x+b[i]);
const mul=(p,s)=>p.map(x=>x*s);
const dot=(a,b)=>a.reduce((sum,x,i)=>sum+x*b[i],0);
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],
 a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const length=p=>Math.hypot(...p);
function unit(p){
 const mag=length(p);
 check(mag>=0.01,"degenerate or coincident fiducial points");
 return mul(p,1/mag);
}
function frame(anchors){
 const x=unit(sub(anchors[1],anchors[0]));
 const third=sub(anchors[2],anchors[0]);
 const z=unit(cross(x,third));
 const y=cross(z,x);
 return [x,y,z];
}
function apply(rotation,translation,p){
 return add(rotation.map(row=>dot(row,p)),translation);
}
const rotations=([x,y,z],[a,b,c])=>{
 // R = [a b c] [x y z]^T. Store 3 rows in world XYZ order.
 const out=[];
 for(let i=0;i<3;i++)out.push([
  a[i]*x[0]+b[i]*y[0]+c[i]*z[0],
  a[i]*x[1]+b[i]*y[1]+c[i]*z[1],
  a[i]*x[2]+b[i]*y[2]+c[i]*z[2]
 ]);
 return out;
};
const det=r=>dot(r[0],cross(r[1],r[2]));
export function solveThreePointDatumFrame(pairs,{max_residual_mm=0.25}={}){
 check(Array.isArray(pairs)&&pairs.length>=3&&pairs.length<=16,
  "3 to 16 ordered point correspondences required");
 check(finite(max_residual_mm)&&max_residual_mm>0&&max_residual_mm<=2,
  "residual tolerance must be explicitly bounded between 0 and 2 mm");
 const local=pairs.map(p=>p.local_mm),world=pairs.map(p=>p.assembly_mm);
 check(local.every(vec)&&world.every(vec),"point coordinates must be finite mm triples");
 const R=rotations(frame(local),frame(world));
 const origin=world[0],translation=sub(origin,R.map(row=>dot(row,local[0])));
 const residuals=pairs.map((p,i)=>length(sub(
  apply(R,translation,local[i]),world[i])));
 const worst=Math.max(...residuals);
 check(Math.abs(det(R)-1)<1e-6,"a reflection or nonrigid frame was inferred");
 check(worst<=max_residual_mm,
  "mismatched fiducials: residual "+worst.toFixed(5)+
  " mm exceeds stated "+max_residual_mm+" mm survey tolerance");
 return {rotation_rows:R,translation_mm:translation,
  max_residual_mm:worst,residuals_mm:residuals,
  mathematical_frame_only:true,mounting_verified:false};
}
function boundedAabb(box){
 check(box&&vec(box.min_mm)&&vec(box.max_mm)&&
  box.min_mm.every((x,i)=>x<box.max_mm[i]),
  "each local bounding box requires strict min/max triples in mm");
 check(box.max_mm.every((x,i)=>x-box.min_mm[i]<=10000),
  "bounding envelope exceeds workbench range");
 return box;
}
export function transformedBounds(box,pose){
 boundedAabb(box);
 check(pose?.rotation_rows?.length===3&&pose.rotation_rows.every(vec)&&
  vec(pose.translation_mm),"invalid candidate metric frame");
 const pts=[];
 for(const x of [box.min_mm[0],box.max_mm[0]])
  for(const y of [box.min_mm[1],box.max_mm[1]])
   for(const z of [box.min_mm[2],box.max_mm[2]])
    pts.push(apply(pose.rotation_rows,pose.translation_mm,[x,y,z]));
 return {min_mm:[0,1,2].map(i=>Math.min(...pts.map(p=>p[i]))),
  max_mm:[0,1,2].map(i=>Math.max(...pts.map(p=>p[i])))};
}
export function compareCandidateAabbs(a,b,{uncertainty_mm=0}={}){
 boundedAabb(a);boundedAabb(b);
 check(finite(uncertainty_mm)&&uncertainty_mm>=0&&uncertainty_mm<=20,
  "bounded nonnegative uncertainty required");
 const gaps=[0,1,2].map(i=>Math.max(
  a.min_mm[i]-b.max_mm[i],b.min_mm[i]-a.max_mm[i])-
  2*uncertainty_mm);
 const axis=Math.max(...gaps);
 return {classification:axis>0?"CANDIDATE_AABBS_SEPARATED":
  "POSSIBLE_OVERLAP_REQUIRES_NARROW_PHASE",
  conservative_axis_gap_mm:axis>0?axis:0,
  uncertainty_mm,method:"ROTATED_AABB_BROAD_PHASE_ONLY",
  physical_clearance_qualified:false,contact_confirmed:false,
  structural_or_motion_analysis_performed:false};
}
export function evaluateMetricFixture(fixture,{expected_variant_id=null}={}){
 check(fixture?.schema_version===1&&fixture.scope===
  "METRIC_CAD_SURVEY_FIXTURE_RESEARCH_ONLY"&&fixture.units==="mm"&&
  fixture.authority?.procurement_authorized===false&&
  fixture.authority?.fabrication_authorized===false&&
  fixture.authority?.physical_fit_qualified===false,
  "unqualified research scope / safety locks required");
 check(typeof fixture.kit_variant_id==="string"&&fixture.kit_variant_id.length>3&&
  (!expected_variant_id||fixture.kit_variant_id===expected_variant_id),
  "survey must match selected exact kit variant");
 check(Array.isArray(fixture.parts)&&fixture.parts.length>=2&&
  fixture.parts.length<=14,"need 2 to 14 candidate shapes");
 const seen=new Set();
 const parts=fixture.parts.map(p=>{
  check(typeof p.id==="string"&&/^[a-z0-9_-]{2,80}$/.test(p.id)&&
   !seen.has(p.id),"unique lowercase part instance ID required");
  seen.add(p.id);
  check(typeof p.source_url==="string"&&p.source_url.startsWith("https://")&&
   typeof p.revision==="string"&&p.revision.trim().length>0&&
   p.geometry_evidence==="UNVERIFIED_CANDIDATE_BOUNDS"&&
   p.mating_datums_physically_verified===false&&
   p.exact_revision_received===false,
   "candidate identity and explicit unverified geometry required");
  const frame=solveThreePointDatumFrame(p.correspondences,{
   max_residual_mm:p.survey_tolerance_mm});
  const bounds=transformedBounds(p.local_bounds_mm,frame);
  return {id:p.id,revision:p.revision,source_url:p.source_url,
   candidate_pose:frame,assembled_broad_phase_bounds_mm:bounds,
   physical_mates_verified:0,source_file_verified:false};
 });
 const pairs=[];
 for(let i=0;i<parts.length;i++)for(let j=i+1;j<parts.length;j++){
  const test=compareCandidateAabbs(
   parts[i].assembled_broad_phase_bounds_mm,
   parts[j].assembled_broad_phase_bounds_mm,{
    uncertainty_mm:Math.max(fixture.parts[i].survey_tolerance_mm,
     fixture.parts[j].survey_tolerance_mm)});
  pairs.push({a:parts[i].id,b:parts[j].id,...test});
 }
 return {scope:"CANDIDATE_BROAD_PHASE_NOT_PHYSICAL_CLEARANCE",
  kit_variant_id:fixture.kit_variant_id,parts,pairs,
  candidate_pairs_checked:pairs.length,
  possible_overlap_pairs:pairs.filter(p=>
   p.classification==="POSSIBLE_OVERLAP_REQUIRES_NARROW_PHASE").length,
  physical_mates_verified:0,physical_clearances_verified:0,
  fabrication_authorized:false,procurement_authorized:false,
  assessment:"SYNTHETIC_OR_UNVERIFIED_SURVEY_NOT_ENGINEERING_VALIDATION"};
}
