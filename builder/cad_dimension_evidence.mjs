// Published marketing and printable DIY drawing dimensions stay evidence, not CAD datums.
// They must never be consumed as automatic GLB transforms, mounting or clearance claims.
const allowedKinds=new Set(["MAKER_PRODUCT_SPECIFICATION","MAKER_DIY_TEMPLATE"]);
const roles=new Set(["deck","zee_brackets","trucks","wheels","bearings",
 "deck_hardware","truck_hardware"]);
const meanings=new Set(["PUBLISHED_OVERALL_ENVELOPE",
 "PUBLISHED_COMPLETE_WHEELBASE_NOT_AXLE_DATUM",
 "PUBLISHED_BARE_DECK_WHEELBASE_NOT_HOLE_POSITION",
 "PUBLISHED_APPROXIMATE_PART_ENVELOPE",
 "PUBLISHED_SYSTEM_RELATION_NOT_ASSEMBLY_DATUM",
 "PUBLISHED_APPROXIMATE_SYSTEM_EFFECT",
 "DIY_TEMPLATE_NOMINAL_HOLE_SPACING",
 "PUBLISHED_NOMINAL_WHEEL_DIAMETER",
 "PUBLISHED_PRODUCT_DIMENSION_NOT_MATING_DATUM"]);
const check=(ok,msg)=>{if(!ok)throw Error("CAD dimensional evidence: "+msg);};
const keys=(obj,arr)=>obj&&typeof obj==="object"&&!Array.isArray(obj)&&
 Object.keys(obj).sort().join("|")===arr.slice().sort().join("|");
const validUrl=s=>{
 try{const u=new URL(s);return u.protocol==="https:"&&!u.username&&!u.password&&
 ["www.loadedboards.com","cdn.shopify.com","www.paristruckco.com",
  "www.orangatangwheels.com"].includes(u.hostname);}
 catch{return false;}
};
export function validateCadDimensionalEvidence(data){
 check(data?.schema_version===1&&data.scope===
  "MAKER_PUBLISHED_DIMENSIONS_NOT_MEASURED_ASSEMBLY_CAD"&&
  /^\d{4}-\d{2}-\d{2}$/.test(data.reviewed_on??""),
  "invalid dimensional source document");
 const a=data.authority;
 check(a&&Object.keys(a).length===4&&a.metric_mates_verified===false&&
  a.physical_clearances_verified===false&&a.procurement_authorized===false&&
  a.fabrication_authorized===false,"evidence cannot promote approvals");
 check(Array.isArray(data.references)&&data.references.length>0&&
  data.references.length<=50,"source references missing or oversized");
 const ids=new Set();
 for(const r of data.references){
  check(keys(r,["id","roles","applies_to","source_url","source_type","note","claims"])&&
   /^[a-z0-9][a-z0-9-]{4,100}$/.test(r.id)&&!ids.has(r.id),
   "source record shape, id or duplicate invalid");
  ids.add(r.id);
  check(allowedKinds.has(r.source_type)&&validUrl(r.source_url)&&
   typeof r.note==="string"&&r.note.length>=12,
   "manufacturer record requires a published source and caution");
  check(Array.isArray(r.applies_to)&&r.applies_to.length>=1&&
   r.applies_to.length<=20&&new Set(r.applies_to).size===r.applies_to.length&&
   r.applies_to.every(x=>typeof x==="string"&&x.length>=6&&x.length<200),
   "exact, distinct kit variants required");
  check(Array.isArray(r.roles)&&r.roles.length>=1&&r.roles.length<=7&&
   new Set(r.roles).size===r.roles.length&&r.roles.every(x=>roles.has(x)),
   "valid distinct assembly roles required");
  check(Array.isArray(r.claims)&&r.claims.length>=1&&r.claims.length<=24,
   "published dimensions required");
  for(const c of r.claims){
   check(keys(c,["name","value_mm","meaning"])&&
    /^[a-z_]{4,80}$/.test(c.name)&&
    typeof c.value_mm==="number"&&Number.isFinite(c.value_mm)&&
    c.value_mm>0&&c.value_mm<=10000&&meanings.has(c.meaning),
    "dimension cannot be promoted to mounting/clearance/fit");
   check((r.source_type==="MAKER_DIY_TEMPLATE")===(c.meaning===
    "DIY_TEMPLATE_NOMINAL_HOLE_SPACING"),
    "DIY stencil is not an assembly datum or manufacturer full 3D model");
  }
 }
 return {published_records:ids.size,metric_datums_qualified:0,
  physically_qualified_mates:0};
}
export function planCadPublishedDimensions(cad,evidence){
 validateCadDimensionalEvidence(evidence);
 if(!cad)return {scope:"NO_COMPLETE_KIT",sources:[],claims:[],
  qualified_mates:0,physical_clearances_qualified:false};
 check(cad.scope==="BROWSER_PARAMETRIC_CAD_DISPLAY_UNQUALIFIED"&&
  cad.children?.length===7&&cad.additional_purchase_lines===0&&
  cad.physical_mates_verified===0&&
  cad.selected_variant_id?.length>0,
  "source dimensions require the same unqualified parent kit");
 const sources=evidence.references.filter(r=>r.applies_to.includes(
  cad.selected_variant_id));
 const claims=sources.flatMap(s=>s.claims.map(c=>({
  evidence_id:s.id,role:s.roles.join(", "),label:c.name,
  value_mm:c.value_mm,meaning:c.meaning,source_url:s.source_url,
  source_note:s.note,revision_verified:false,
  usable_as_mounting_datum:false
 })));
 check(sources.length>0,"no maker data for this selected reference kit");
 return {scope:"PUBLISHED_DIMENSIONS_READ_ONLY_NOT_CAD",kit_id:cad.kit_id,
  variant_id:cad.selected_variant_id,
  sources:sources.map(s=>({id:s.id,source_url:s.source_url,
   source_type:s.source_type,note:s.note})),
  claims,qualified_mates:0,physical_clearances_qualified:false,
  independent_received_item_measurements:0,
  additional_purchase_lines:0};
}
