// STEP->glTF conversion receipt is a reproducible *tool* report.
// Hash matching establishes byte integrity, never source authenticity or physical fit.
const fail=m=>{throw Error("CAD conversion receipt: "+m);};
const hash=s=>typeof s==="string"&&/^[a-f0-9]{64}$/.test(s);
const number=n=>typeof n==="number"&&Number.isFinite(n);
const triple=x=>Array.isArray(x)&&x.length===3&&x.every(number);
export function validateCadConversionReceipt(r,{output_sha256,output_bytes}={}){
 if(!r||r.schema_version!==1||r.scope!==
  "STEP_TO_GLTF_CONVERSION_RECEIPT_NOT_MEASURED_FIT")
  fail("unknown conversion scope");
 if(!hash(r.source_step_sha256)||!hash(r.output_glb_sha256)||
    (output_sha256!==undefined&&r.output_glb_sha256!==output_sha256))
  fail("source or output digest invalid");
 if(r.source_cad_units!=="mm"||r.gltf_scene_units!=="m"||
    r.mm_to_gltf_m_scale!==0.001)
  fail("glTF 2.0 must contain meters from source millimeters");
 if(!Number.isSafeInteger(r.source_step_bytes)||r.source_step_bytes<64||
    r.source_step_bytes>100000000||
    !Number.isSafeInteger(r.output_glb_bytes)||r.output_glb_bytes<28||
    r.output_glb_bytes>25000000||
    (output_bytes!==undefined&&r.output_glb_bytes!==output_bytes))
  fail("size limit or receipt byte identity invalid");
 if(!Array.isArray(r.source_bounds_mm)||r.source_bounds_mm.length!==2||
    !r.source_bounds_mm.every(triple)||!triple(r.source_extents_mm)||
    !triple(r.gltf_sorted_extents_m)||
    !r.source_extents_mm.every(v=>v>0&&v<=10000)||
    !r.gltf_sorted_extents_m.every(v=>v>0&&v<=10)||
    !number(r.tessellation_tolerance_mm)||
    r.tessellation_tolerance_mm<0.05||r.tessellation_tolerance_mm>1.0||
    !number(r.angular_tolerance_rad)||
    r.angular_tolerance_rad<0.05||r.angular_tolerance_rad>0.8||
    !number(r.max_sorted_extent_error_mm)||
    r.max_sorted_extent_error_mm<0||
    r.max_sorted_extent_error_mm>Math.max(r.tessellation_tolerance_mm*0.1,0.02))
  fail("invalid or unverified source geometry conversion envelope");
 const expected=r.source_bounds_mm[1].map((v,i)=>v-r.source_bounds_mm[0][i]);
 if(expected.some((v,i)=>v<=0||Math.abs(v-r.source_extents_mm[i])>1e-6)||
    [...r.source_extents_mm].sort((a,b)=>a-b).some((v,i)=>
     Math.abs(v-1000*r.gltf_sorted_extents_m[i])>
      Math.max(r.tessellation_tolerance_mm*0.1,0.02)))
  fail("source and exported extents do not reconcile");
 for(const key of ["geometry_revision_confirmed","mounting_datums_verified",
  "physical_clearance_qualified","procurement_authorized","fabrication_authorized"])
  if(r[key]!==false)fail("physical/revision authority cannot be granted");
 return {source_step_sha256:r.source_step_sha256,
  output_glb_sha256:r.output_glb_sha256,
  scale_m_per_source_mm:0.001,geometric_extent_error_mm:r.max_sorted_extent_error_mm,
  manufacturer_authenticity_qualified:false,mounting_datums_qualified:false};
}
