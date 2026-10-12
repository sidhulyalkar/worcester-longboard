// Manufacturer source leads are research navigation only, not sourced CAD.
const check=(ok,msg)=>{if(!ok)throw Error("CAD source leadbook: "+msg);};
const roles=["deck","zee_brackets","trucks","wheels","bearings",
 "deck_hardware","truck_hardware"];
const classifications=["DIY_DRAWING_NOT_3D_SOLID",
 "OPTIONAL_ACCESSORY_NOT_SEVEN_PART_ASSEMBLY"];
const https=x=>{try{const u=new URL(x);return u.protocol==="https:"&&
 !u.username&&!u.password&&u.hostname.length>=5;}
 catch{return false;}};
const text=x=>typeof x==="string"&&x.trim()===x&&
 x.length>=4&&x.length<=800&&![...x].some(ch=>ch.charCodeAt(0)<32);
const id=x=>typeof x==="string"&&/^[a-z][a-z0-9-]{5,99}$/.test(x);
const officialHost=(url,manufacturer)=>{
 try{
  const host=new URL(url).hostname;
  const suffix=manufacturer==="Loaded Boards"?"loadedboards.com":
   manufacturer==="Paris Truck Co"?"paristruckco.com":
   manufacturer==="Orangatang Wheels"?"orangatangwheels.com":null;
  return !!suffix&&(host===suffix||host==="www."+suffix);
 }catch{return false;}
};
const digest=x=>typeof x==="string"&&/^[a-f0-9]{64}$/.test(x);
export function validateCadSourceLeadbook(book){
 check(book?.schema_version===1&&book.scope==="SOURCE_LEADS_NOT_VERIFIED_COMPONENT_CAD"&&
  /^\d{4}-\d{2}-\d{2}$/.test(book.reviewed_on??""),
  "missing revision-labeled source catalog");
 check(Array.isArray(book.kit_variant_ids)&&book.kit_variant_ids.length===2&&
  book.kit_variant_ids.every(text)&&
  new Set(book.kit_variant_ids).size===book.kit_variant_ids.length,
  "two unique complete-kit variants required");
 check(book.authority?.cad_geometry_authenticated===false&&
  book.authority?.physical_fit_qualified===false&&
  book.authority?.procurement_authorized===false&&
  book.authority?.fabrication_authorized===false&&
  book.authority?.additional_purchase_lines===0&&
  Object.keys(book.authority).length===5,
  "source leads may not unlock fabrication or checkout");
 check(Array.isArray(book.roles)&&book.roles.length===roles.length,
  "exact seven assembly categories required");
 for(let i=0;i<roles.length;i++){
  const r=book.roles[i];
  check(r?.role===roles[i]&&text(r.manufacturer)&&
   https(r.manufacturer_url)&&officialHost(r.manufacturer_url,r.manufacturer)&&
   text(r.requested_geometry)&&
   r.requested_geometry.length>=40&&
   Array.isArray(r.requested_cad_formats)&&
   r.requested_cad_formats.join("|")==="STEP|GLB"&&
   r.source_geometry_verified===false&&
   r.exact_revision_confirmed===false&&
   r.redistribution_rights==="NOT_GRANTED_OR_DOCUMENTED"&&
   r.approved_mounting_datums===0&&r.extra_order_lines===0,
   "manufacturer roles may not assert CAD coverage or rights");
  check(Array.isArray(r.source_pages)&&r.source_pages.length>=1&&
   r.source_pages.length<=2,"source pages required");
  const seen=new Set();
  for(const page of r.source_pages){
   check(https(page.url)&&officialHost(page.url,r.manufacturer)&&
    Array.isArray(page.variants)&&
    page.variants.length>=1&&page.variants.length<=2,
    "need exact variants and legitimate HTTPS source URL");
   for(const variant of page.variants){
    check(book.kit_variant_ids.includes(variant)&&!seen.has(variant),
     "variant must be uniquely linked to source within each role");
    seen.add(variant);
   }
  }
  check(seen.size===book.kit_variant_ids.length,
   "every role must have a known research lead for each kit");
 }
 check(Array.isArray(book.related_public_artifacts)&&
  book.related_public_artifacts.length===2,
  "DIY/optional-artifact exclusion declarations required");
 const ids=new Set();
 for(const a of book.related_public_artifacts){
  check(id(a.id)&&!ids.has(a.id)&&text(a.label)&&
   classifications.includes(a.classification)&&
   https(a.source_url)&&roles.includes(a.related_role)&&
   text(a.note)&&a.exact_structural_part_cad===false&&
   a.redistribution_authorized===false,
   "accessory/drawing cannot become approved structural CAD");
  ids.add(a.id);
 }
 check(new Set(book.related_public_artifacts.map(a=>a.classification)).size===2,
  "distinguish DIY drawing and optional printable accessory");
 return {research_roles:7,kit_variants:2,
  related_artifacts_excluded:2,qualified_structural_geometry:0,
  additional_purchase_lines:0};
}
export function buildCadSourceAcquisition(cad,book,assetRegistry){
 validateCadSourceLeadbook(book);
 if(!cad)return {scope:"NO_SELECTED_COMPLETE_KIT_SOURCE_LEADS",rows:[],
  excluded_artifacts:[],manufacturer_request_packets:[],qualified_models:0};
 check(cad.scope==="BROWSER_PARAMETRIC_CAD_DISPLAY_UNQUALIFIED"&&
  cad.children?.length===7&&cad.physical_mates_verified===0&&
  cad.additional_purchase_lines===0&&
  book.kit_variant_ids.includes(cad.selected_variant_id),
  "source leads are restricted to the known unqualified Tangent kit");
 check(cad.children.every((r,i)=>r.role===roles[i]),
  "source lead roles differ from selected maker contents");
 check(Array.isArray(assetRegistry?.assets),"require separately validated geometry registry");
 const variant=cad.selected_variant_id;
 const rows=book.roles.map(r=>{
  const page=r.source_pages.find(p=>p.variants.includes(variant));
  const candidate=assetRegistry.assets.find(a=>a.kit_variant_id===variant&&a.role===r.role);
  return {role:r.role,manufacturer:r.manufacturer,
   manufacturer_url:r.manufacturer_url,source_url:page.url,
   required_geometry:r.requested_geometry,
   requested_formats:r.requested_cad_formats,
   lead_classification:"OFFICIAL_PRODUCT_SPECIFICATION_NOT_CAD",
   asset_candidate_id:candidate?.asset_id??null,
   cad_status:candidate?"PINNED_CANDIDATE_NOT_ALIGNED":"NO_VERIFIED_3D_SOURCE",
   exact_revision_confirmed:false,permission_to_redistribute:false,
   physically_verified_mounting_datums:0,
   separate_purchase_lines:0};
 });
 const grouped=new Map();
 for(const r of rows){
  const group=grouped.get(r.manufacturer)??[];
  group.push(r);grouped.set(r.manufacturer,group);
 }
 const manufacturer_request_packets=[...grouped.entries()].map(([manufacturer,entries])=>({
  manufacturer,roles:entries.map(r=>r.role),
  source_pages:entries.map(r=>r.source_url),
  subject:"Request: revision-specific CAD and display permission for "+entries.map(r=>
   r.role.replaceAll("_"," ")).join(", "),
  message:"Hello "+manufacturer+" team,\n\n"+
   "I am developing a research-only web assembly visualization for the Loaded Tangent complete board "+
   "("+variant+"). Can you share exact part revision-specific STEP or GLB geometry, or advise whether "+
   "independent metrology is required? Requested details:\n\n"+
   entries.map(r=>"- "+r.role.replaceAll("_"," ")+": "+r.required_geometry).join("\n")+
   "\n\nCould you also specify the exact model revision, native units/coordinate frame, "+
   "mounting datum or hole center definitions, whether the model represents the currently "+
   "shipped complete kit, and express written permissions for storing and publicly displaying "+
   "a derived browser GLB? No engineering safety or commercial redistribution rights will "+
   "be presumed from an emailed file. Thank you."
 }));
 const excluded_artifacts=book.related_public_artifacts.map(a=>({
  ...a,qualifies_seven_component_models:false,
  purchase_line_created:false,usable_as_structural_mounting_datum:false
 }));
 return {scope:"SOURCE_ACQUISITION_RESEARCH_NOT_ASSEMBLY_FIT",
  kit_variant_id:variant,rows,excluded_artifacts,manufacturer_request_packets,
  source_leads:rows.length,qualified_models:0,
  pending_structural_geometry:rows.length,
  file_backed_unqualified_candidates:rows.filter(r=>r.asset_candidate_id).length,
  physical_mates_verified:0,physical_clearances_verified:0,
  fabrication_authorized:false,procurement_authorized:false,
  additional_purchase_lines:0};
}
