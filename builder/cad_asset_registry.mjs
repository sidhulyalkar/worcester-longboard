// Candidate CAD references, NOT measured mates or a checkout / manufacturing release.
// A GLB here is an immutable, revision-specific geometry candidate. The complete kit
// still has exactly one parent purchase line. No visual placement becomes a datum.
const fail=message=>{throw Error("CAD asset registry: "+message);};
const check=(ok,message)=>{if(!ok)fail(message);};
const roles=["deck","zee_brackets","trucks","wheels","bearings",
 "deck_hardware","truck_hardware"];
const id=x=>typeof x==="string"&&/^[a-z0-9][a-z0-9._-]{1,119}$/.test(x);
const https=x=>{try{const u=new URL(x);return u.protocol==="https:"&&!u.username&&!u.password;}catch{return false;}};
const sha=x=>typeof x==="string"&&/^[a-f0-9]{64}$/.test(x);
const locks=["procurement_authorized","fabrication_authorized",
 "charging_authorized","powered_operation_authorized",
 "generic_builder_may_promote_x1_authority"];
export function validateCadAssetRegistry(registry){
 check(registry?.schema_version===1&&registry.scope===
  "CANDIDATE_PART_CAD_ASSETS_NOT_ENGINEERING_APPROVAL","unknown scope");
 check(registry.coordinate_policy?.native_file_units==="EXPLICIT_PER_ASSET"&&
  registry.coordinate_policy.unmeasured_display_frame==="ARBITRARY_VISUAL_UNITS"&&
  registry.coordinate_policy.allow_automatic_visual_to_metric_alignment===false&&
  registry.coordinate_policy.allow_unverified_collision_clearance===false,
  "cannot silently align actual CAD and illustrative visual frames");
 check(locks.every(k=>registry.authority?.[k]===false),"authority must remain locked");
 check(Array.isArray(registry.assets)&&registry.assets.length<=128,"asset list invalid");
 const ids=new Set(),slots=new Set();
 for(const a of registry.assets){
  check(id(a.asset_id)&&!ids.has(a.asset_id),"duplicate or invalid asset ID");
  ids.add(a.asset_id);
  check(id(a.kit_variant_id)&&roles.includes(a.role)&&
   id(a.part_number)&&id(a.revision),"exact kit/part revision and role required");
  const key=a.kit_variant_id+":"+a.role;
  check(!slots.has(key),"ambiguous assets for a kit role");
  slots.add(key);
  check(["MANUFACTURER_PUBLISHED","INDEPENDENTLY_MEASURED"].includes(a.origin)&&
   https(a.source_url)&&typeof a.license==="string"&&a.license.trim().length>2&&
   /^\d{4}-\d{2}-\d{2}$/.test(a.evidence_date??""),
   "source, dated evidence and reuse rights required");
  check(a.format==="glb"&&a.units==="mm"&&sha(a.sha256)&&
   a.path==="/assets/cad/"+a.sha256+".glb",
   "only locally pinned, digest-addressed GLB with declared mm units");
  check(a.byte_length>20&&Number.isSafeInteger(a.byte_length)&&
   a.byte_length<=25000000,"asset exceeds per-file browser budget");
  check(a.asset_revision_confirmed===true||a.asset_revision_confirmed===false,
   "asset revision confidence must be explicit");
  check(a.verified_mount_datums===false&&a.clearance_qualified===false&&
   a.physical_fit_qualified===false&&a.preview_pose_authority==="NONE"&&
   a.actual_received_units===null&&a.separate_order_lines===0,
   "candidate CAD cannot claim mechanical/receiving/order approval");
  check(a.metric_assembly_transform===null&&a.mount_datums_mm===null,
   "an unverified asset cannot invent mating transforms or datums");
 }
 return {asset_candidates:ids.size,physically_qualified:0};
}
export function planCadAssetReadiness(cad,registry){
 validateCadAssetRegistry(registry);
 if(!cad)return {scope:"NO_SELECTED_COMPLETE_KIT",rows:[],asset_candidates:0,
  missing_geometry:0,verified_mount_datums:0,clearance_status:"NOT_EVALUATED",
  physical_fit_qualified:false,additional_purchase_lines:0};
 check(cad.scope==="BROWSER_PARAMETRIC_CAD_DISPLAY_UNQUALIFIED"&&
  cad.children?.length===7&&cad.child_count===7&&
  cad.physical_mates_verified===0&&cad.additional_purchase_lines===0&&
  Object.values(cad.authority??{}).length===locks.length&&
  locks.every(k=>cad.authority[k]===false),"invalid selected kit CAD display");
 const rows=cad.children.map(c=>{
  const a=registry.assets.find(a=>a.kit_variant_id===cad.selected_variant_id&&
   a.role===c.role);
  return {component_id:c.component_id,role:c.role,
   geometry_status:a?"GLB_CANDIDATE_UNALIGNED":"PARAMETRIC_PROXY_ONLY",
   asset_id:a?.asset_id??null,revision:a?.revision??null,
   origin:a?.origin??null,source_url:a?.source_url??null,
   verified_mount_datums:0,physical_clearance_status:"NOT_EVALUATED",
   order_lines_added:0};
 });
 return {scope:"CAD_GEOMETRY_COVERAGE_RESEARCH_ONLY",kit_id:cad.kit_id,
  selected_variant_id:cad.selected_variant_id,rows,
  asset_candidates:rows.filter(x=>x.asset_id).length,
  missing_geometry:rows.filter(x=>!x.asset_id).length,
  verified_mount_datums:0,clearance_status:"NOT_EVALUATED",
  physical_fit_qualified:false,additional_purchase_lines:0};
}
