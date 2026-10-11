// Read-only v1 mountainboard -> general outdoor equipment graph adapter.
// This does NOT determine product-family equivalence, current stock, exact revisions,
// physical compatibility, seller order quantities, charging or purchasing authority.
const AUTHORITY={
  procurement_authorized:false,fabrication_authorized:false,
  charging_authorized:false,powered_operation_authorized:false,
  generic_builder_may_promote_x1_authority:false
};
const clone=x=>JSON.parse(JSON.stringify(x));
const assert=(valid,message)=>{if(!valid)throw new Error("Outdoor catalog graph: "+message)};
const namespaced=(kind,id)=>kind+":mountainboard:"+id;
const stableBinding=c=>JSON.stringify([
  c.id,c.category,c.label,c.manufacturer??null,c.sku??null,c.source?.kind??null,
  c.source?.snapshot_id??null,c.source?.as_of??null,c.source?.url??null,
  c.source?.seller??null,c.source?.native_price_snapshot??null,
  c.price?.kind??null,c.price?.qty??null,
  c.price?.unit_price_usd??null,c.price?.min_usd??null,c.price?.max_usd??null
]);
const exactTextSku=c=>{
  if(!c.sku)return "ABSENT";
  return /(?:\/|\bfamily\b|\bclass\b)/i.test(c.sku)?"FAMILY_OR_ALTERNATE_SKUS_UNRESOLVED":"CATALOG_SKU_TEXT_NOT_RECEIVED_VARIANT";
};
const trustedListing=s=>{
  if(!["vendor","retailer"].includes(s?.kind) ||
    typeof s.url!=="string" || !s.snapshot_id || !s.as_of || !s.seller ||
    !/^\d{4}-\d{2}-\d{2}$/.test(s.as_of))return false;
  try{
    const parsed=new URL(s.url),date=new Date(s.as_of+"T00:00:00.000Z");
    return parsed.protocol==="https:" && !!parsed.hostname &&
      !parsed.username && !parsed.password && !Number.isNaN(date.valueOf()) &&
      date.toISOString().slice(0,10)===s.as_of;
  }catch{return false;}
};
export function buildOutdoorCatalogGraph(catalog,domains,packageRegistry){
 assert(catalog?.schema_version===1 && Array.isArray(catalog.components),
   "expected existing board components v1");
 assert(domains?.scope==="EXPERIMENTAL_DOMAIN_TAXONOMY_NO_PRODUCT_COMPATIBILITY_OR_PURCHASE_AUTHORITY",
   "unreviewed domain mapping");
 assert(domains.legacy_migration?.source_of_truth==="catalog/board_components.v1.json" &&
   domains.legacy_migration?.policy==="READ_ONLY_MAPPING_NO_RUNTIME_CHANGE",
   "legacy adapter must remain read-only");
 assert(packageRegistry?.scope==="CATALOG_INCLUSION_HYPOTHESES_NOT_PACKAGE_CERTIFICATION" &&
   Array.isArray(packageRegistry.packages),"missing source-bound package registry");
 const mapping=new Map((domains.legacy_migration.mappings||[])
   .map(x=>[x.legacy_category,x]));
 assert(mapping.size===(domains.legacy_migration.mappings||[]).length,
   "duplicate legacy category mapping");
 const seen=new Set(),families=[],variants=[],offers=[],snapshots=[],claims=[],packages=[],holds=[];
 const donorMapping=new Map(packageRegistry.packages.map(x=>[x.component_id,x]));
 assert(donorMapping.size===packageRegistry.packages.length,"duplicate source package");
 for(const comp of catalog.components){
   assert(typeof comp.id==="string"&&comp.id && !seen.has(comp.id),
     "duplicate or invalid legacy component");
   seen.add(comp.id);
   const map=mapping.get(comp.category);
   assert(map,"unmapped category for "+comp.id);
   const source=comp.source||{},binding=stableBinding(comp);
   const familyId=namespaced("family",comp.id);
   const variantId=namespaced("variant",comp.id);
   const sourceId=namespaced("source",comp.id);
   const pkgId=namespaced("package",comp.id);
   const stockId=namespaced("offer",comp.id);
   const sourceTrusted=trustedListing(source);
   const revision=typeof comp.revision==="string" && comp.revision.trim()?comp.revision:null;
   // One provisional family per legacy row. Matching names/brands DO NOT prove
   // that two different legacy rows are variants of the same model.
   families.push({
     id:familyId,domain_id:"mountainboard",name:comp.label,
     manufacturer:comp.manufacturer??null,provisional:true,
     legacy_component_id:comp.id,
     variant_equivalence_verified:false
   });
   variants.push({
     id:variantId,family_id:familyId,component_role:map.new_role,
     legacy_component_id:comp.id,
     legacy_category:comp.category,
     legacy_identity_binding_key:binding,
     sku_text:comp.sku??null,sku_resolution:exactTextSku(comp),
     physical_revision:revision,
     exact_received_variant_verified:false,
     source_evidence_state:comp.evidence_state??"UNKNOWN",
     procurement_state:comp.procurement_state??"UNKNOWN",
     actual_assembly_quantity:null,
     real_seller_order_quantity:null,
     source_snapshot_id:sourceId,
     actual_physical_compatibility_verified:false,
     status:"PROVISIONAL_CATALOG_REFERENCE_NOT_ORDERABLE"
   });
   snapshots.push({
     id:sourceId,component_id:comp.id,
     binding_key:binding,
     source_kind:source.kind??"UNSPECIFIED",
     source_url:source.url??null,
     source_snapshot_id:source.snapshot_id??null,
     source_as_of:source.as_of??null,
     seller:source.seller??null,
     native_price_snapshot:source.native_price_snapshot??null,
     live_stock_verified:false,source_status:"REFERENCE_SNAPSHOT_ONLY"
   });
   for(const [field,value] of Object.entries(comp.interfaces||{}).sort(([a],[b])=>a.localeCompare(b,"en"))){
     claims.push({
       id:namespaced("claim",comp.id+":"+field),variant_id:variantId,
       interface_field:field,raw_catalog_value:clone(value),
       raw_value_units:field.endsWith("_mm")?"mm":
         field.endsWith("_psi")?"psi":field.endsWith("_g")?"g":
         field.endsWith("_wh")?"Wh":null,
       source_snapshot_id:sourceId,
       evidence_state:comp.evidence_state??"UNKNOWN",
       typed_interface_qualified:false,independently_measured:false,
       exact_revision_applicability_verified:false,
       interpretation:"RAW_LEGACY_INTERFACE_CLAIM_NOT_NORMALIZED_FIT_RULE"
     });
   }
   if(sourceTrusted){
     offers.push({
       id:stockId,variant_id:variantId,source_snapshot_id:sourceId,
       supplier_name:source.seller,offer_url:source.url,
       dated_as_of:source.as_of,currency_native_text:source.native_price_snapshot??null,
       legacy_price_reference:comp.price?clone(comp.price):null,
       catalog_price_qty_factor:comp.price?.qty??null,
       // price.qty in v1 may be 4 wheels / 2 axles; never assume the
       // supplier listing is for this many physically orderable units.
       seller_pack_unit_count:null,assembly_units_per_pack:null,
       current_availability:"UNKNOWN_NOT_LIVE",verified_quote:false,
       checkout_authorized:false,status:"DATED_VENDOR_OR_RETAILER_REFERENCE_ONLY"
     });
   }else{
     holds.push({
       component_id:comp.id,variant_id:variantId,
       reason:"NO_ORDERABLE_SOURCE_SNAPSHOT",
       source_kind:source.kind??"UNSPECIFIED"
     });
   }
   const included=Array.isArray(comp.includes)?comp.includes:[];
   if(included.length){
     const record=donorMapping.get(comp.id);
     const bound=Boolean(record && record.catalog_sku_text===(comp.sku??null) &&
       record.catalog_snapshot_id===(source.snapshot_id??null));
     assert(!record || new Set(record.inclusions.map(x=>x.token)).size===record.inclusions.length,
       "duplicate donor inclusion tokens");
     if(record)assert(new Set(included).size===record.inclusions.length &&
       record.inclusions.every(x=>included.includes(x.token)),
       "donor token mismatch "+comp.id);
     packages.push({
       id:pkgId,container_variant_id:variantId,component_id:comp.id,
       source_snapshot_id:sourceId,
       registry_mapping_status:!record?"MISSING_REGISTRY_HOLD":
         bound?"BOUND_REFERENCE_NOT_CONTENTS_PROOF":"STALE_REGISTRY_HOLD",
       contents_verified:false,
       items:included.map(token=>{
         const entry=record?.inclusions.find(x=>x.token===token);
         return {
           inclusion_token:token,
           possible_reference_variant_ids:(entry?.possible_catalog_reference_ids||[])
             .map(id=>namespaced("variant",id)),
           included_quantity:null,
           exact_variant_equivalence_verified:false,
           review_question:entry?.review_question??
             "Determine actual contents, marked revision and included counts."
         };
       })
     });
   }
   // Unmodified complete legacy snapshot for lossless backward conversion.
   // It is not a signed authority record. A source replacement requires a new graph.
 }
 assert(seen.size===catalog.components.length,"missing legacy components");
 for(const donor of packageRegistry.packages)
   assert(seen.has(donor.component_id),"orphan source-bound donor mapping");
 const legacySnap={schema_version:catalog.schema_version,as_of:catalog.as_of,
   currency:catalog.currency,refresh_before_checkout:catalog.refresh_before_checkout,
   note:catalog.note,components:clone(catalog.components)};
 return {
   schema_version:1,scope:"EXPERIMENTAL_READ_ONLY_OUTDOOR_CATALOG_GRAPH",
   domain_registry_version:domains.schema_version,
   migration:"LOSSLESS_V1_MOUNTAINBOARD_ADAPTER_NO_RUNTIME_CHANGE",
   legacy_source_of_truth:"catalog/board_components.v1.json",
   // No manufacturer SKU, exact physical revision or product identity is
   // promoted beyond the catalog's already-uncertain legacy text.
   families,variants,source_snapshots:snapshots,supplier_offer_references:offers,
   engineering_claims:claims,sellable_package_hypotheses:packages,source_holds:holds,
   legacy_catalog_snapshot:legacySnap,
   summary:{
     imported_legacy_components:seen.size,provisional_families:families.length,
     provisional_variants:variants.length,
     catalog_interface_claims:claims.length,dated_supplier_references:offers.length,
     package_content_hypotheses:packages.length,
     confirmed_exact_variants:0,live_offers:0,orderable_kits:0,
     independently_qualified_interfaces:0,physical_release_status:"NOT_QUALIFIED"
   },
   authority:{...AUTHORITY}
 };
}
export function replayLegacyBoardCatalog(graph){
 assert(graph?.scope==="EXPERIMENTAL_READ_ONLY_OUTDOOR_CATALOG_GRAPH" &&
   graph.migration==="LOSSLESS_V1_MOUNTAINBOARD_ADAPTER_NO_RUNTIME_CHANGE",
   "cannot replay non-v1 read-only graph");
 assert(graph.legacy_catalog_snapshot?.schema_version===1 &&
   Array.isArray(graph.legacy_catalog_snapshot.components),"missing legacy snapshot");
 const originals=graph.legacy_catalog_snapshot.components;
 assert(graph.variants.length===originals.length &&
   graph.families.length===originals.length &&
   graph.source_snapshots.length===originals.length,"partial graph cannot be replayed");
 const variantById=new Map(graph.variants.map(x=>[x.legacy_component_id,x]));
 const sourceById=new Map(graph.source_snapshots.map(x=>[x.component_id,x]));
 assert(variantById.size===originals.length&&sourceById.size===originals.length,
   "duplicate graph identity");
 for(const comp of originals){
   const variant=variantById.get(comp.id),src=sourceById.get(comp.id);
   assert(variant?.legacy_identity_binding_key===stableBinding(comp) &&
     src?.binding_key===stableBinding(comp),"stale graph snapshot binding "+comp.id);
   assert(variant.family_id===namespaced("family",comp.id) &&
     src.id===namespaced("source",comp.id),"graph ID mismatch "+comp.id);
 }
 // Explicitly clone the original data. Do not reconstruct from inferred family,
 // a presumed pack quantity, measured fit or normalized geometry.
 return clone(graph.legacy_catalog_snapshot);
}
