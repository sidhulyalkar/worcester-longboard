// Compact, source-bound parametric CAD *display* schema compiler.
// This is a deterministic illustration model, NOT exact maker CAD or a
// physical mounting/clearance solution. All poses use arbitrary view units.
import {buildCompleteKitVisualGraph} from "./complete_kit_visual_graph.mjs";
const check=(ok,msg)=>{if(!ok)throw Error("CAD display schema: "+msg);};
const roles=["deck","zee_brackets","trucks","wheels","bearings",
 "deck_hardware","truck_hardware"];
const shapes=["tapered_deck_shell","vee_bracket_symbol","truck_hanger_symbol",
 "wheel_with_hub","bearing_ring","single_fastener_set_symbol",
 "single_fastener_set_symbol"];
const patterns=["SINGLE","STATIONS","STATIONS","FOUR_CORNERS",
 "TWO_PER_WHEEL","SINGLE_NOT_QUANTITY","SINGLE_NOT_QUANTITY"];
const finite=(n,lo,hi)=>typeof n==="number"&&Number.isFinite(n)&&n>=lo&&n<=hi;
const vector=(p)=>Array.isArray(p)&&p.length===3&&p.every(v=>finite(v,-20,20));
const ALL_LOCKS=["procurement_authorized","fabrication_authorized",
 "charging_authorized","powered_operation_authorized",
 "generic_builder_may_promote_x1_authority"];
export function validateKitCadRecipe(recipe){
 check(recipe?.schema_version===1&&
  recipe.scope==="SCHEMATIC_PARAMETRIC_CAD_RECIPE_NOT_MEASURED_MANUFACTURER_CAD"&&
  recipe.recipe_id==="loaded-tangent-complete-reference-assembly-v1",
  "unknown or promoted CAD recipe");
 check(ALL_LOCKS.every(x=>recipe.authority?.[x]===false),
  "recipe cannot grant any physical or seller authority");
 const frame=recipe.coordinate_frame,claims=recipe.dimensional_evidence_policy;
 check(frame?.units==="ARBITRARY_VISUAL_UNITS"&&
  frame.origin_physically_measured===false&&
  claims?.actual_mates_verified===false&&
  claims.physical_clearances_verified===false&&
  claims.fastener_locations_verified===false&&
  claims.structural_strength_verified===false&&
  claims.all_normalized_placements_are_inferred===true&&
  claims.published_dimensions_are_not_mating_datums===true,
  "normalized placement must never be described as measured CAD");
 const l=recipe.layout;
 for(const key of ["deck_length_u","deck_width_u","deck_height_u",
  "deck_thickness_u","hub_center_z_u","bracket_z_u","truck_z_u",
  "reference_wheel_diameter_mm","wheel_radius_at_reference_u"]){
  check(finite(l?.[key],0.01,150),key+" missing or invalid");
 }
 check(l.reference_wheel_diameter_mm===105&&
  l.station_y_u?.length===2&&l.wheel_x_u?.length===2&&
  l.station_y_u.every(v=>finite(v,-5,5))&&
  l.wheel_x_u.every(v=>finite(v,-4,4)),
  "axle station pattern invalid");
 check(Array.isArray(recipe.primitives)&&recipe.primitives.length===7,
  "one CAD recipe per advertised physical category required");
 for(let i=0;i<roles.length;i++){
  const p=recipe.primitives[i];
  check(p.role===roles[i]&&p.shape===shapes[i]&&p.pattern===patterns[i],
    "unexpected geometry prototype or component role: "+roles[i]);
  check(vector(l.parts_explode_offsets_u?.[p.role]),
    "missing unitless explosion vector for "+p.role);
 }
 return {schema_version:1,validated_roles:7,
  physical_dimensions_qualified:0,qualified_mates:0};
}

export function compileCompleteKitCadDisplay(study,kitAudit,kitClaims,recipe){
 validateKitCadRecipe(recipe);
 const graph=buildCompleteKitVisualGraph(study,kitAudit);
 if(!graph.kit_parent_variant_id)return null;
 check(kitClaims?.scope==="MAKER_COMPLETE_KIT_ADVERTISED_CONTENTS_NOT_PHYSICAL_RECEIPT"&&
  Object.values(kitClaims.authority??{}).every(x=>x===false),
  "maker kit claims missing safety gates");
 const kit=kitClaims.kits.find(k=>k.id===kitAudit.kit_id&&
  k.variant_id===graph.kit_parent_variant_id);
 check(kit?.actual_received_kit_verified===false&&
  kit.measured_mechanical_interfaces_qualified===false&&
  kit.seller_checkout_option_verified===false,
  "maker kit identity/receipt not verified");
 const ref=study.selected_variants.find(x=>x.variant_id===graph.kit_parent_variant_id);
 const diam=ref?.visual_reference_claims?.wheel_diameter_mm;
 check([85,105].includes(diam),
  "wheel diameter must originate in selected published reference");
 const overall=kit.published_complete_dimensions_mm;
 check(overall?.length_mm===914&&overall.width_mm===248,
  "published overall envelope changed: new source review required");
 const l=recipe.layout,ys=l.station_y_u,xs=l.wheel_x_u;
 const wheelRadius=l.wheel_radius_at_reference_u*diam/l.reference_wheel_diameter_mm;
 // All objects are in the same assembled view frame (x across, y longitudinal,
 // z above arbitrary ground). These are visual alignments, never maker mounts.
 const placements={
  deck:[{shape:"tapered_deck_shell",at:[0,0,l.deck_height_u],
    size:[l.deck_width_u,l.deck_length_u,l.deck_thickness_u]}],
  zee_brackets:ys.map(y=>({shape:"vee_bracket_symbol",
    at:[0,y,l.bracket_z_u],size:[1.5,0.5,0.32]})),
  trucks:ys.map(y=>({shape:"truck_hanger_symbol",
    at:[0,y,l.truck_z_u],size:[3.0,0.45,0.25]})),
  wheels:ys.flatMap(y=>xs.map(x=>({shape:"wheel_with_hub",
    at:[x,y,l.hub_center_z_u],radius:wheelRadius}))),
  bearings:ys.flatMap(y=>xs.flatMap(x=>[-0.14,0.14].map(dx=>({
    shape:"bearing_ring",at:[x+dx,y,l.hub_center_z_u],radius:0.16
  })))),
  // Symbol-only components deliberately have no fake mount/hole coordinates.
  deck_hardware:[{shape:"single_fastener_set_symbol",
    at:[0,0,0],symbol_only:true,actual_location_known:false}],
  truck_hardware:[{shape:"single_fastener_set_symbol",
    at:[0,0,0],symbol_only:true,actual_location_known:false}]
 };
 const children=graph.components.map((node,i)=>{
  const role=roles[i],part=recipe.primitives[i];
  check(node.role==="kit_child_"+role&&node.component_id===kitAudit.rows[i].child_id,
    "visual CAD child identity diverged from maker kit source");
  const items=placements[role];
  check(items.every(p=>vector(p.at)),"CAD recipe contains bad visual location");
  return {
   component_id:node.component_id,role,label:node.label,
   parent_kit_id:kit.id,parent_package_variant_id:ref.variant_id,
   source_url:kit.source_url,shape:part.shape,
   geometry_class:"GENERATED_PROCEDURAL_SCHEMATIC",
   instances:items,illustrative_offset_u:l.parts_explode_offsets_u[role],
   assembly_position_authority:"NONE",true_mount_datum_mm:null,
   true_clearance_mm:null,fastener_count_verified:false,
   physical_fit_verified:false,received_units:null,order_units:null
  };
 });
 return {
  schema_version:1,scope:"BROWSER_PARAMETRIC_CAD_DISPLAY_UNQUALIFIED",
  recipe_id:recipe.recipe_id,revision:recipe.reviewed_on,
  kit_id:kit.id,selected_variant_id:ref.variant_id,
  published_dimensions_mm:{complete_length:overall.length_mm,
   complete_width:overall.width_mm,wheel_diameter:diam},
  published_dimensions_provenance:kit.source_url,
  visual_frame:structuredClone(recipe.coordinate_frame),
  geometry_basis:"SCHEMATIC_NORMALIZED_VISUAL_UNITS_NOT_MAKER_MOUNT_COORDINATES",
  children,child_count:7,physical_mates_verified:0,
  delivered_contents_verified:0,additional_purchase_lines:0,
  total_order_price:null,
  sample_assembled_configuration_only:true,
  assembly_instruction_authorized:false,
  authority:Object.fromEntries(ALL_LOCKS.map(x=>[x,false]))
 };
}
export function planCadDisplay(cad,separation=0,selectedId=null){
 check(cad?.scope==="BROWSER_PARAMETRIC_CAD_DISPLAY_UNQUALIFIED"&&
  cad.child_count===7&&cad.children?.length===7&&
  cad.physical_mates_verified===0&&
  Object.values(cad.authority??{}).every(x=>x===false),
  "not an unqualified assembled CAD display");
 const n=Number(separation),pct=Number.isFinite(n)?Math.max(0,Math.min(100,n)):0;
 const t=pct/100;
 return {schema_version:1,scope:"ASSEMBLED_AND_EXPLODED_VISUAL_STUDY",
  separation_percent:pct,units:"ARBITRARY_VISUAL_UNITS",
  kit_id:cad.kit_id,
  parts:cad.children.map(c=>({
   component_id:c.component_id,
   position:c.illustrative_offset_u.map(v=>v*t),
   visible:c.instances.some(p=>p.symbol_only!==true)||t>=0.08,
   selected:c.component_id===selectedId
  })),
  mechanical_clearances_checked:false,physical_assembly_qualified:false,
  order_authorized:false};
}
