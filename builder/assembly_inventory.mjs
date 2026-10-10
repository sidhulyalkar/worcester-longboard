// Read-only purchase-unit / donor-content audit. Never resolves stock, quantities,
// source manuals, charging, physical fit or procurement by inference.
const AUTHORITY=Object.freeze({
 procurement_authorized:false,fabrication_authorized:false,
 charging_authorized:false,powered_operation_authorized:false,
 generic_builder_may_promote_x1_authority:false
});
const sorted=x=>[...new Set(x)].sort();
const invalid=msg=>{throw new Error("Package inclusion registry: "+msg)};
export function auditAssemblyInventory(passport,registry){
 if(!passport || passport.scope!=="NON_AUTHORITATIVE_BUILD_PASSPORT" ||
  !Array.isArray(passport.parts)||!passport.study_identity_key)
  throw new Error("Assembly inventory requires exact Build Passport snapshot");
 if(!registry || registry.schema_version!==1 ||
    registry.scope!=="CATALOG_INCLUSION_HYPOTHESES_NOT_PACKAGE_CERTIFICATION" ||
    !Array.isArray(registry.packages))invalid("unexpected schema");
 const parts=new Map(passport.parts.map(p=>[p.component_id,p]));
 if(parts.size!==passport.parts.length)throw new Error("Duplicate BOM component ID cannot be treated as a resolved order");
 const packages=[],overlap=[],retrofit=[],unknownTokens=[];
 const seen=new Set();
 for(const pkg of registry.packages){
   if(!pkg || typeof pkg.component_id!=="string" ||seen.has(pkg.component_id))
     invalid("missing or duplicate donor package id");
   seen.add(pkg.component_id);
   if(!Array.isArray(pkg.inclusions)||!Array.isArray(pkg.retrofit_warnings))
     invalid("missing inclusion/retrofit lists");
   const part=parts.get(pkg.component_id);
   if(!part)continue;
   const allTokens=part.included_by_donor||[];
   const declared=pkg.inclusions.map(x=>x.token);
   if(new Set(declared).size!==declared.length ||
     allTokens.length!==declared.length || !declared.every(t=>allTokens.includes(t)))
     invalid("included token mismatch for "+pkg.component_id);
   const snapshotMatches=part.supplier?.snapshot_id===pkg.catalog_snapshot_id &&
     part.sku_text===pkg.catalog_sku_text && !part.proposed_revision;
   packages.push({
     package_id:pkg.component_id,reference_source_snapshot_id:pkg.catalog_snapshot_id,
     snapshot_binding_status:snapshotMatches?"BOUND_TO_REFERENCE_SNAPSHOT":"STALE_OR_CHANGED_SOURCE_HOLD",
     exact_received_contents_verified:false,order_unit_quantity:null,
     source_document_status:"PACKAGE_CONTENTS_UNVERIFIED"
   });
   for(const entry of pkg.inclusions){
     if(!entry || typeof entry.token!=="string" ||
       !Array.isArray(entry.possible_catalog_reference_ids) ||
       typeof entry.review_question!=="string" || !entry.review_question.trim())
       invalid("invalid inclusion token entry");
     for(const relatedId of entry.possible_catalog_reference_ids){
       if(typeof relatedId!=="string" || relatedId===pkg.component_id)
         invalid("invalid possible included catalog reference");
     }
     const selected=entry.possible_catalog_reference_ids.filter(id=>parts.has(id));
     // This is a possible catalog-family overlap, never exact inclusion.
     for(const id of selected)overlap.push({
       package_id:pkg.component_id,component_id:id,inclusion_token:entry.token,
       classification:snapshotMatches?"POSSIBLE_DOUBLE_COUNT":"MAPPING_STALE_CONSERVATIVE_HOLD",
       source_snapshot_verified_for_exact_revision:false,possible_included_quantity:null,
       review_question:entry.review_question,
       action:"Check actual received contents and vendor assembly/order units before pricing or buying"
     });
     if(!entry.possible_catalog_reference_ids.length || !snapshotMatches)
       unknownTokens.push({
         package_id:pkg.component_id,inclusion_token:entry.token,
         reason:!snapshotMatches?"STALE_OR_CHANGED_SOURCE_HOLD":"NO_EXACT_CATALOG_COUNTERPART",
         review_question:entry.review_question
       });
   }
   const knownTokens=new Set(declared);
   for(const warn of pkg.retrofit_warnings){
     if(!warn || typeof warn.when_component_id!=="string" || typeof warn.included_token!=="string" ||
       !knownTokens.has(warn.included_token) || !warn.question)
       invalid("invalid retrofit reference");
     if(parts.has(warn.when_component_id))retrofit.push({
       package_id:pkg.component_id,component_id:warn.when_component_id,
       related_inclusion_token:warn.included_token,
       status:"MEASURE_AND_VERIFY_RETROFIT_BEFORE_PHYSICAL_USE",
       question:warn.question
     });
   }
 }
 // A generic donor with no mapped registry must not have its inclusion claims ignored.
 for(const part of passport.parts){
   if((part.included_by_donor||[]).length && !seen.has(part.component_id)){
     packages.push({package_id:part.component_id,reference_source_snapshot_id:null,
       snapshot_binding_status:"UNMAPPED_BUNDLE_HOLD",exact_received_contents_verified:false,
       order_unit_quantity:null,source_document_status:"PACKAGE_CONTENTS_UNVERIFIED"});
     for(const token of part.included_by_donor)unknownTokens.push({
       package_id:part.component_id,inclusion_token:token,
       reason:"NO_REVIEWED_BUNDLE_MAPPING",review_question:"Determine exact received contents, variants and quantities"
     });
   }
 }
 const overlapByPart=new Map();
 for(const row of overlap){
   if(!overlapByPart.has(row.component_id))overlapByPart.set(row.component_id,[]);
   overlapByPart.get(row.component_id).push(row.package_id);
 }
 const orderLines=passport.parts.map(p=>({
   component_id:p.component_id,variant_identity_key:p.variant_identity_key,
   catalog_price_reference_multiplier:p.price?.pricing_reference_qty??null,
   actual_assembly_quantity:null,actual_supplier_order_quantity:null,
   vendor_package_unit_description:null,
   donor_overlap_candidate_ids:sorted(overlapByPart.get(p.component_id)||[]),
   current_availability:"UNKNOWN_NOT_LIVE",quote_verified:false,
   state:"HOLD_RECEIVING_AND_ORDER_UNIT_AUDIT"
 }));
 const sourceWorklist=passport.parts.map(p=>({
   component_id:p.component_id,missing:[
     ...(!p.supplier?.source_url?["VENDOR_SOURCE_URL"]:[]),
     ...(!p.supplier?.snapshot_id?["SOURCE_SNAPSHOT"]:[]),
     ...(!p.sku_text?["EXACT_SKU_OR_VARIANT"]:[]),
     "EXACT_PHYSICAL_REVISION",
     "REVISION_MATCHED_MANUFACTURER_INSTRUCTIONS",
     "CURRENT_STOCK_CHECK",
     "VERIFIED_ASSEMBLY_QUANTITY",
     "VERIFIED_VENDOR_ORDER_UNIT",
     "CONFIRMED_CURRENT_QUOTE"
   ],source_health:p.supplier?.source_health||"HEALTH_UNAVAILABLE"
 }));
 const sortedRows=(arr,keys)=>arr.sort((a,b)=>{
   const aa=keys.map(k=>a[k]||"").join(":"),bb=keys.map(k=>b[k]||"").join(":");
   return aa<bb?-1:aa>bb?1:0;
 });
 sortedRows(packages,["package_id"]);sortedRows(overlap,["package_id","component_id"]);
 sortedRows(retrofit,["package_id","component_id"]);
 sortedRows(unknownTokens,["package_id","inclusion_token"]);
 return {
   schema_version:1,scope:"NON_AUTHORITATIVE_ASSEMBLY_INCLUSION_AUDIT",
   candidate_id:passport.candidate_id,study_identity_key:passport.study_identity_key,
   source_note:"Bundle inclusion labels describe vendor/catalog reference claims only. Similar part families do not establish equal revisions, included quantities, fit, or a buyable kit.",
   package_claims:packages,overlap_worklist:overlap,retrofit_worklist:retrofit,
   unmapped_inclusion_worklist:unknownTokens,order_lines:orderLines,
   source_worklist:sourceWorklist,
   costs:{existing_bom_subtotal_has_possible_double_count:overlap.length>0,
     overlap_adjusted_total_usd:null,confirmed_quote_total_usd:null,
     all_in_assembly_total_usd:null,
     warning:"Never subtract bundled items from the existing BOM by guess. Source values are not assembly quotes."},
   eligibility:{parts_quantities_qualified:false,bundle_contents_qualified:false,
     manual_instructions_qualified:false,mechanical_interfaces_qualified:false,
     electrical_integration_qualified:false},
   authority:{...AUTHORITY}
 };
}
