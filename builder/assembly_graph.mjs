// Semantic assembly graph for explanatory exploded views, not fabrication geometry.
const AUTH={procurement_authorized:false,fabrication_authorized:false,
 charging_authorized:false,powered_operation_authorized:false,
 generic_builder_may_promote_x1_authority:false};
const unique=(rows,label)=>{
 const ids=rows.map(x=>x.id);
 if(new Set(ids).size!==ids.length)throw new Error("Duplicate "+label);
};
export function buildAssemblyGraph(subject,recipes,catalog=null,packageRegistry=null,referenceStudies=null){
 if(recipes?.scope!=="CONCEPTUAL_ASSEMBLY_VISUALIZATION_NOT_PHYSICAL_INSTRUCTIONS" ||
   recipes.schema_version!==1 || !Array.isArray(recipes.groups) || !Array.isArray(recipes.domains))
   throw new Error("Invalid assembly recipe contract");
 unique(recipes.groups,"assembly group");unique(recipes.domains,"assembly domain");
 const domainId=subject?.domain_id||"mountainboard";
 const domain=recipes.domains.find(x=>x.id===domainId);
 if(!domain)throw new Error("Unknown assembly sport "+domainId);
 if(domainId==="mountainboard" && domain.source!=="LIVE_EXISTING_BOARD_CANDIDATE")
   throw new Error("Mountainboard must be sourced from existing design candidate");
 if(domainId!=="mountainboard" && domain.source!=="UNSOURCED_ILLUSTRATIVE_CONCEPT")
   throw new Error("Non-board examples cannot imply a live product");
 const concept=domainId!=="mountainboard";
 const rows=concept?subject?.components:subject?.bom;
 if(!Array.isArray(rows)||!rows.length)throw new Error("Missing assembly parts");
 const sourceParts=new Map((catalog?.components||[]).map(x=>[x.id,x]));
 let referenceBacked=false;
 if(concept){
   const canonical=recipes.examples.find(x=>x.id===subject.id && x.domain_id===domainId);
   const studied=referenceStudies?.scope==="SOURCE_REFERENCED_BOARD_SPORT_STUDIES_NOT_VERIFIED_FIT_OR_CHECKOUT"?
     referenceStudies.studies?.find(x=>x.id===subject.id&&x.domain_id===domainId):null;
   const exactConcept=canonical&&JSON.stringify(canonical)===JSON.stringify(subject);
   const exactStudy=studied&&JSON.stringify(studied)===JSON.stringify(subject);
   if(!exactConcept && !exactStudy)
     throw new Error("Concept or reference study must match exact reviewed registry");
   referenceBacked=Boolean(exactStudy);
 }
 if(!concept && (!catalog || !packageRegistry ||
    packageRegistry.scope!=="CATALOG_INCLUSION_HYPOTHESES_NOT_PACKAGE_CERTIFICATION"))
   throw new Error("Existing board requires full source and donor registers");
 const groupByRole=new Map();
 for(const g of recipes.groups){
   if(!Array.isArray(g.roles) || g.vector?.length!==2 ||
      g.vector.some(x=>!Number.isFinite(x)))throw new Error("Invalid group geometry");
   for(const role of g.roles){
     if(groupByRole.has(role))throw new Error("Ambiguous assembly role "+role);
     groupByRole.set(role,g);
   }
 }
 const seen=new Set();
 const componentNodes=rows.map((row,i)=>{
   const componentId=row.component_id;
   if(typeof componentId!=="string" || !componentId || seen.has(componentId))
     throw new Error("Duplicate or invalid assembly component ID");
   seen.add(componentId);
   const reference=sourceParts.get(componentId);
   if(!concept&&!reference)throw new Error("Unknown catalog reference "+componentId);
   const role=concept?row.role:reference.category;
   const grp=groupByRole.get(role);
   if(!grp)throw new Error("Unknown assembly role "+role);
   const source=reference?.source||{};
   const refKind=concept?(referenceBacked?row.source_kind:"illustrative_concept"):
     source.kind||"repository_reference";
   const url=concept?(referenceBacked?row.source_url:null):source.url??null;
   return {
     id:"part:"+componentId,component_id:componentId,
     group_id:grp.id,role,label:row.label,order_index:i,
     manufacturer:concept?(referenceBacked?row.manufacturer:null):reference.manufacturer??null,
     sku_text:concept?(referenceBacked?row.sku:null):reference.sku??null,
     source_kind:refKind,
     source_url:url,
     source_snapshot_id:concept?(referenceBacked?row.source_id:null):source.snapshot_id??null,
     exact_variant_verified:false,
     assembly_required_quantity:null, supplier_order_quantity:null,
     visual_proxy_only:true,
     inclusion_status:"NOT_INDEPENDENTLY_CONFIRMED",
     approval_status:"HOLD_SOURCE_REVISION_AND_INTERFACE_REVIEW",
     reference_price_factor:concept?null:reference.price?.qty??null
   };
 });
 const activeGroups=recipes.groups.filter(group=>componentNodes.some(x=>x.group_id===group.id))
   .map(group=>({id:group.id,label:group.label,shape:group.shape,
     vector:[...group.vector],
     component_ids:componentNodes.filter(x=>x.group_id===group.id).map(x=>x.component_id),
     item_count:componentNodes.filter(x=>x.group_id===group.id).length,
     exact_assembly_geometry_verified:false}));
 const packageClaims=[],connections=[];
 if(!concept){
   const packs=new Map(packageRegistry.packages.map(x=>[x.component_id,x]));
   for(const node of componentNodes){
     const ref=sourceParts.get(node.component_id);
     if(!ref.includes?.length)continue;
     const pkg=packs.get(node.component_id);
     const valid=Boolean(pkg && pkg.catalog_snapshot_id===ref.source?.snapshot_id &&
       pkg.catalog_sku_text===ref.sku &&
       ref.includes.length===pkg.inclusions.length &&
       ref.includes.every(t=>pkg.inclusions.some(x=>x.token===t)));
     packageClaims.push({container_component_id:node.component_id,
       source_registry_binding:valid?"BOUND_REFERENCE_ONLY":"UNBOUND_OR_STALE_HOLD",
       actual_contents_verified:false,
       content_tokens:ref.includes.map(token=>{
         const finding=valid?pkg.inclusions.find(x=>x.token===token):null;
         const ids=finding?.possible_catalog_reference_ids||[];
         return {token,possible_component_ids:ids,
           included_quantity:null,exact_part_match_verified:false,
           potential_duplicate_bom_component_ids:ids.filter(id=>seen.has(id)),
           review_question:finding?.review_question||"Inspect included variant and count"};
       })});
     connections.push({from:node.component_id,to:"unverified-package-contents:"+node.component_id,
       kind:"POSSIBLE_PACKAGE_CONTENTS_NOT_PHYSICAL_CONNECTION",verified:false});
   }
 }
 return {
   schema_version:1,scope:"UNQUALIFIED_SEMANTIC_ASSEMBLY_EXPLODED_VIEW",
   subject_id:subject.id,domain_id:domainId,label:subject.label,
   origin:referenceBacked?"MANUFACTURER_REFERENCED_INTEGRATION_STUDY":
     concept?"ILLUSTRATIVE_DOMAIN_RECIPE":"EXISTING_BOARD_CANDIDATE",
   source_snapshot_as_of:referenceBacked?referenceStudies.reviewed_as_of:
     concept?null:catalog.as_of,
   groups:activeGroups,components:componentNodes,connections,
   package_inclusion_hypotheses:packageClaims,
   manufacturer_advertised_contents:referenceBacked?
     subject.advertised_contents.map(role=>({role,source_listed:true,
       physically_received_and_counted:false,shipped_quantity:null})):[],
   manufacturer_mount_reference:referenceBacked?subject.known_mount_lookups:null,
   unresolved_system_checks:[...domain.important_checks,
     ...(referenceBacked?subject.additional_checks:[])],
   completeness:{catalog_components_included:componentNodes.length,
     unique_bom_component_ids:seen.size,
     conceptual_assembly_groups:activeGroups.length,
     source_bound_variant_revisions_qualified:0,
     supplier_order_quantities_qualified:0,
     physical_connections_qualified:0},
   safety:{visual_geometry:"ILLUSTRATIVE_SEMANTIC_PROXY_ONLY",
     sequence:"NOT_INSTALLATION_INSTRUCTIONS",
     physical_qualification:"NOT_QUALIFIED",
     usable_for_fabrication:false,usable_for_mounting:false,
     usable_for_binding_release:false},
   authority:{...AUTH},
   note:"Exploded positions and silhouettes explain relationships only. They are not measured geometry, a verified parts inventory, a bill of order quantities or installation instructions."
 };
}
