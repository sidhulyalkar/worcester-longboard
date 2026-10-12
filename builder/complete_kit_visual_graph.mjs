// Presentation-only decomposition of a maker-advertised complete board.
// This overlay does NOT alter the underlying BOM, parent SKU, package counts
// or physical qualification. Every identity is tied to the selected kit claim.
import {planExplodedScene} from "./exploded_scene_model.mjs";

const requireCondition=(v,msg)=>{if(!v)throw Error("Kit visual study: "+msg);};
const groups=[
 {id:"platform",label:"Deck shell (illustrative)",shape:"platform",vector:[0,0]},
 {id:"mount",label:"Brackets, trucks and hardware (unmeasured)",shape:"mount",vector:[-1.18,0.92]},
 {id:"ground",label:"Rolling elements (unmeasured)",shape:"wheel",vector:[1.18,0.95]}
];
const safe=(v)=>typeof v==="string"&&v.length>=5&&v.length<220;
export function buildCompleteKitVisualGraph(study,kitAudit){
 requireCondition(study?.graph?.scope==="UNQUALIFIED_SEMANTIC_ASSEMBLY_EXPLODED_VIEW"&&
  study.graph.safety?.physical_qualification==="NOT_QUALIFIED"&&
  Object.values(study.graph.authority??{}).every(x=>x===false),
  "requires an unqualified maker graph with all authority disabled");
 requireCondition(kitAudit?.scope==="PUBLISHED_KIT_CLOSURE_NO_CART"&&
  kitAudit?.authority&&Object.values(kitAudit.authority).every(x=>x===false),
  "kit audit is absent or contains physical/ordering authority");
 const rows=kitAudit.rows??[];
 if(kitAudit.status==="NO_COMPLETE_KIT_SELECTED"&&rows.length===0)
  return study.graph;
 requireCondition(study.graph.domain_id==="skateboard_longboard"&&
  kitAudit.status==="SELLER_PACKAGE_REVISION_CONFLICT_HOLD"&&
  rows.length===7&&
  kitAudit.verified_kit_count===0&&
  kitAudit.independent_additional_item_orders===0&&
  kitAudit.physical_connections_qualified===0&&
  kitAudit.actual_seller_unit_count===null&&
  kitAudit.current_cart_total===null,
  "complete kit not in a reviewed, physically unqualified study");
 const selected=study.selected_variants.filter(x=>x.slot==="long_complete");
 requireCondition(selected.length===1&&selected[0].variant_id===kitAudit.variant_id&&
  study.graph.components.length===1&&
  study.graph.components[0].component_id===selected[0].variant_id,
  "kit claim cannot substitute another graph's physical components");
 const roles=["deck","zee_brackets","trucks","wheels","bearings",
  "deck_hardware","truck_hardware"];
 requireCondition(rows.length===roles.length&&
  rows.every((r,i)=>r.role===roles[i]&&safe(r.child_id)&&
    safe(r.label)&&safe(r.source_claim)&&safe(r.source_url)&&
    r.add_independent_purchase_line===false&&
    r.qualified_mount===false&&r.actual_received_units===null&&
    r.exact_seller_pack_units===null&&r.maker_claimed_included===true),
  "maker child cannot gain receipt, extra purchase or installation status");
 requireCondition(new Set(rows.map(x=>x.child_id)).size===rows.length,
  "duplicate maker kit child identities");
 const map={deck:"platform",zee_brackets:"mount",trucks:"mount",
  wheels:"ground",bearings:"ground",deck_hardware:"mount",truck_hardware:"mount"};
 const components=rows.map((r,i)=>({
  id:"kit-visual:"+r.child_id,component_id:r.child_id,
  group_id:map[r.role],role:"kit_child_"+r.role,
  label:r.label,order_index:i,
  manufacturer:"Loaded (advertised inclusion)",sku_text:null,
  source_kind:"original_maker_kit_claim_unreceived",
  source_url:r.source_url,source_snapshot_id:kitAudit.kit_id,
  parent_kit_id:kitAudit.kit_id,
  parent_package_variant_id:kitAudit.variant_id,
  expected_assembly_units:r.expected_assembly_units,
  supplier_order_quantity:null,actual_received_units:null,
  exact_variant_verified:false,visual_proxy_only:true,
  approval_status:"KIT_CONTENTS_AND_MATES_NOT_QUALIFIED",
  inclusion_status:"MAKER_DECLARED_NOT_INSPECTED",
  maker_advertised_child_claim:r.source_claim,
  physical_mount_point_mm:null,
  unit_basis:"ARBITRARY_3D_VISUAL_UNITS"
 }));
 const active=groups.filter(g=>components.some(c=>c.group_id===g.id)).map(g=>({
  ...g,component_ids:components.filter(x=>x.group_id===g.id).map(x=>x.component_id),
  item_count:components.filter(x=>x.group_id===g.id).length,
  exact_assembly_geometry_verified:false
 }));
 const graph={
  ...study.graph,
  label:"Loaded Tangent maker-kit seven-component illustrated decomposition",
  origin:"MAKER_KIT_ADVERTISED_CHILDREN_UNRECEIVED_VISUALIZATION",
  groups:active,components,connections:[],
  kit_parent_variant_id:kitAudit.variant_id,
  kit_parent_source_id:kitAudit.kit_id,
  package_inclusion_hypotheses:rows.map(r=>({
   child_id:r.child_id,role:r.role,source_claim:r.source_claim,
   received_units:null,order_units:null,
   source_status:"MANUFACTURER_ADVERTISED_NOT_RECEIVED"
  })),
  completeness:{...study.graph.completeness,
   catalog_components_included:components.length,
   unique_bom_component_ids:components.length,
   conceptual_assembly_groups:active.length,
   source_bound_variant_revisions_qualified:0,
   supplier_order_quantities_qualified:0,
   physical_connections_qualified:0
  },
  safety:{...study.graph.safety,
   visual_geometry:"SEVEN_SOURCE_NAMED_CHILD_PROXY_WITH_ARBITRARY_COORDINATES",
   sequence:"ILLUSTRATIVE_EXPLOSION_NOT_INSTALLATION_ORDER",
   physical_qualification:"NOT_QUALIFIED",usable_for_fabrication:false,
   usable_for_mounting:false,usable_for_binding_release:false},
  note:"Seven maker-advertised complete-board categories, not actual received pieces. " +
   "Visual layouts, wheel offset, hardware grouping, mounting and mechanics are schematic only. " +
   "One parent package, zero separately approved child purchases."
 };
 planExplodedScene(graph,{separation:70});
 return graph;
}
