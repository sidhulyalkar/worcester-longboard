import {validatePartsRegistry,buildPickerStudy} from "./parts_picker_engine.mjs";
import {renderExplodedAssemblySvg} from "./exploded_renderer.mjs";
import {validateSupplierObservations,auditMakerOrderUnits} from "./offer_qualification.mjs";
import {validateRetailRegistry,validateBuildStudies,compareRetailOffers,
 researchRelatedSellerListings,composeResearchAlternatives} from "./retail_build_comparison.mjs";
import {validateMakerKitClaims,auditCompleteKitClaim} from "./complete_kit_closure.mjs";
import {buildCompleteKitVisualGraph} from "./complete_kit_visual_graph.mjs";
import {validateKitCadRecipe,compileCompleteKitCadDisplay} from "./complete_kit_cad_schema.mjs";
import {renderCompleteKitCadSvg} from "./complete_kit_cad_svg.mjs";
import {validateCadAssetRegistry,planCadAssetReadiness} from "./cad_asset_registry.mjs";
import {inspectGlbBytes} from "./cad_glb_contract.mjs";
import {validateCadDimensionalEvidence,planCadPublishedDimensions}
 from "./cad_dimension_evidence.mjs";
import {evaluateMetricFixture} from "./cad_metric_workbench.mjs";
import {sampleCandidateMotionSweep,renderCandidateMotionSvg}
 from "./cad_candidate_motion.mjs";
import {makeSyntheticCandidateMotionFixture} from "./cad_demo_fixture.mjs";
import {compileCandidateMetricScene} from "./cad_candidate_scene.mjs";
import {validateCadCaptureRequirements,planCadCaptureCampaign,
 blankCadFieldObservations,validateCadFieldObservations}
 from "./cad_capture_campaign.mjs";
import {validateCadSourceLeadbook,buildCadSourceAcquisition}
 from "./cad_source_acquisition.mjs";
const $=selector=>document.querySelector(selector);
const esc=x=>String(x??"").replaceAll("&","&amp;").replaceAll("<","&lt;")
 .replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;");
const cleanUrl=value=>{
 try{const u=new URL(value);return u.protocol==="https:"&&!u.username&&!u.password?u.href:null;}
 catch{return null;}
};
const state={catalog:null,offerObservations:null,offerAudit:null,
 retailCatalog:null,studyCatalog:null,alternatives:null,kitClaims:null,kitAudit:null,visualGraph:null,
 cadRecipe:null,cadModel:null,cadRegistry:null,cadReadiness:null,
 cadInspector:null,inspectedKit:null,dimensionalEvidence:null,publishedCad:null,metricResult:null,motionResult:null,sceneFixture:null,sceneEpoch:0,sceneViewer:null,sceneViewerPromise:null,captureRequirements:null,captureObservations:null,captureReport:null,captureVariant:null,sourceLeadbook:null,sourceAcquisition:null,
 domain:"skateboard_longboard",selections:{},study:null,
 mode:"2d",separation:0,selectedId:null,viewer:null,viewerPromise:null,
 search:""};
const sourceFor=id=>state.catalog.sources.find(s=>s.id===id);
const currentGraph=()=>state.visualGraph??state.study?.graph;
const productsFor=slot=>state.catalog.products.filter(p=>p.domain_id===state.domain&&p.slot===slot);
function slotOptions(slot){
 let html='<option value="">Unselected / check exact variant</option>';
 for(const p of productsFor(slot)){
  const all=p.variants.filter(v=>(p.brand+" "+p.name+" "+v.label).toLowerCase().includes(state.search)||
   state.selections[slot]===v.id);
  if(!all.length)continue;
  html+='<optgroup label="'+esc(p.brand+" · "+p.name)+'">';
  for(const variant of all)html+='<option value="'+esc(variant.id)+'"'+
   (state.selections[slot]===variant.id?' selected':'')+'>'+esc(variant.label)+'</option>';
  html+='</optgroup>';
 }
 return html;
}
function selectedVariant(slot){
 const id=state.selections[slot];
 const p=productsFor(slot).find(p=>p.variants.some(v=>v.id===id));
 return p?{product:p,variant:p.variants.find(v=>v.id===id)}:null;
}
function renderSlots(){
 const template=state.catalog.assembly_templates.find(x=>x.domain_id===state.domain);
 $("#picker-slots").innerHTML=template.slots.map(slot=>{
  const entry=selectedVariant(slot);
  const source=entry?sourceFor(entry.product.source_id):null;
  const url=cleanUrl(source?.url);
  const parts=entry?.product.inclusion_claim||[];
  const price=entry?state.catalog.observed_listing_prices.find(x=>x.product_id===entry.product.id):null;
  return '<article class="slot-card"><div class="slot-head"><strong>'+esc(slot.label)+
   '</strong><span class="slot-status">'+esc(slot.status.replaceAll("_"," "))+'</span></div>'+
   '<small>'+esc(slot.needed)+'</small>'+
   '<label for="picker-choice-'+esc(slot.id)+'">Maker / variant study</label>'+
   '<select id="picker-choice-'+esc(slot.id)+'" data-picker-slot="'+esc(slot.id)+'">'+slotOptions(slot)+'</select>'+
   (entry?'<div class="slot-product-evidence">'+
    esc(entry.product.brand+" · "+entry.variant.label)+
    '<br>Specific manufacturer SKU, revision and pack quantities: unverified. '+
    (url?'<a href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">Read manufacturer evidence ↗</a>':'')+
    (parts.length?'<br>'+esc(parts[0]):'')+
     (price?'<br><strong>Maker listing reference USD '+
      price.displayed_maker_listing_usd.toFixed(2)+' ('+esc(price.observed_on)+
      ')</strong> · Not an exact-size quote or cart total.':'')+'</div>':
    '<div class="slot-product-evidence">No maker product selected. An unselected or unqualified component cannot be silently added to the cart.</div>')+
   '</article>';
 }).join("");
}
function renderTree(){
 const graph=currentGraph();
 $("#picker-part-tree").innerHTML=graph.groups.map(g=>{
  const items=graph.components.filter(c=>c.group_id===g.id);
  return '<div><strong>'+esc(g.label)+'</strong><div>'+
   items.map(c=>'<button type="button" data-picker-part="'+esc(c.component_id)+'" aria-pressed="'+
    (c.component_id===state.selectedId?'true':'false')+'">'+esc(c.label)+'</button>').join("")+
   '</div></div>';
 }).join("");
}
function selectPart(id){
 const graph=currentGraph();
 if(!graph?.components.some(x=>x.component_id===id))return;
 state.selectedId=id;
 $("#picker-part-tree").querySelectorAll("[data-picker-part]").forEach(b=>{
  b.setAttribute("aria-pressed",String(b.dataset.pickerPart===id));
 });
 const c=graph.components.find(x=>x.component_id===id);
 const selected=state.study.selected_variants.find(x=>x.variant_id===id);
 const link=cleanUrl(c.source_url);
 const dims=selected?.dimensions_mm?
  Object.entries(selected.dimensions_mm).map(([k,v])=>esc(k.replaceAll("_"," "))+": "+esc(v)+" mm").join(" · "):
  "Exact dimensions not supplied";
 const kitPart=c.role?.startsWith("kit_child_");
 const kitNote=kitPart?
  '<p><strong>One included-kit research component, not a standalone seller order line.</strong> '+
  'Expected assembly units: '+esc(c.expected_assembly_units??"UNKNOWN")+
  ' · manufacturer-advertised claim: '+esc(c.maker_advertised_child_claim)+
  '. <strong>Actual contents, mounting geometry and fit NOT VERIFIED.</strong></p>':'';
 $("#picker-component-detail").innerHTML='<p><strong>'+esc(c.label)+'</strong></p>'+
  '<p>System: '+esc(c.group_id)+'. Maker: '+esc(c.manufacturer||"Not selected")+
  '. Variant revision / physical interface: <strong>NOT QUALIFIED</strong>.</p>'+
  '<p>Published product envelope (not CAD): '+dims+'</p>'+kitNote+
  (selected?.inclusion_claim?.length?'<p>Package evidence: '+esc(selected.inclusion_claim.join("; "))+
   '. Contents as received are still unverified.</p>':'')+
  (link?'<p><a href="'+esc(link)+'" target="_blank" rel="noopener noreferrer">View original maker reference ↗</a></p>':
    '<p>This missing reference has no supplier page.</p>');
 redrawVisual();
}
function redrawVisual(){
 const graph=currentGraph();
 if(!graph)return;
 const kit=graph.kit_parent_variant_id!==undefined;
 $("#picker-rendered-scene-status").textContent=kit&&state.cadModel?
  "Integrated parametric board · "+graph.components.length+
  " source-named categories · maker board "+
  state.cadModel.published_dimensions_mm.complete_length+" × "+
  state.cadModel.published_dimensions_mm.complete_width+" mm, wheels "+
  state.cadModel.published_dimensions_mm.wheel_diameter+
  " mm · 0 measured mounts or received pieces":
  graph.components.length+" source-family component reference(s) · unmeasured visual proxies";
 $("#picker-cad-export").disabled=!state.cadModel;
 $("#picker-cad-status").textContent=state.cadModel?
  "Schema: "+state.cadModel.recipe_id+" · "+
  (state.separation===0?"integrated assembled view":"exploded view")+
  " · normalized schematic poses only. Not manufacturer CAD.":
  "No source-matched parametric complete-board model for this selection.";
 $("#picker-assemble").setAttribute("aria-pressed",String(state.separation===0));
 $("#picker-separate").setAttribute("aria-pressed",String(state.separation===100));
 const host=$("#picker-visual-svg");
 host.innerHTML=state.cadModel?
  renderCompleteKitCadSvg(state.cadModel,{explode:state.separation,
   selectedId:state.selectedId}):
  renderExplodedAssemblySvg(graph,{explode:state.separation,
   selectedId:state.selectedId});
 host.querySelectorAll("[data-exploded-part]").forEach(part=>
  part.addEventListener("click",()=>selectPart(part.getAttribute("data-exploded-part"))));
 $("#picker-explode-output").textContent=state.separation+"%";
 if(state.mode==="3d"&&state.viewer){
  try{state.viewer.update(graph,state.separation,state.selectedId,null,state.study.selected_variants,state.cadModel);}
  catch(error){fallbackTo2D("3D study could not render this selection. SVG fallback remains available.");}
 }
}
function renderCadMakerDimensions(){
 const report=state.publishedCad=planCadPublishedDimensions(
  state.cadModel,state.dimensionalEvidence);
 $("#picker-cad-maker-export").disabled=!state.cadModel;
 $("#picker-cad-maker-dimensions").innerHTML=report.claims.map(c=>{
  const url=cleanUrl(c.source_url);
  return '<tr><td>'+esc(c.role.replaceAll("_"," "))+'</td><td>'+
   esc(c.label.replaceAll("_"," "))+
   '<small>'+esc(c.meaning.replaceAll("_"," "))+'</small></td><td>'+
   esc(c.value_mm)+' mm</td><td>'+
   (url?'<a href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">Maker original ↗</a>':"")+
   '<small>'+esc(c.source_note)+'</small></td></tr>';
 }).join("");
}
function renderCadSourceAcquisition(){
 const report=state.sourceAcquisition=buildCadSourceAcquisition(
  state.cadModel,state.sourceLeadbook,state.cadRegistry);
 const active=!!state.cadModel;
 $("#picker-cad-source-export").disabled=!active;
 $("#picker-cad-source-requests").disabled=!active;
 $("#picker-cad-source-status").textContent=active?
  report.pending_structural_geometry+"/7 part categories still need licensed CAD · "+
  report.manufacturer_request_packets.length+" manufacturer inquiry packets · "+
  "0 verified mechanical mates or purchases":
  "No complete kit selected. Manufacturer sourcing does not qualify geometry.";
 $("#picker-cad-source-roles").innerHTML=report.rows.map(r=>{
  const url=cleanUrl(r.source_url);
  return '<div class="cad-source-role"><strong>'+
   esc(r.role.replaceAll("_"," "))+'</strong> · '+esc(r.manufacturer)+
   '<p>'+esc(r.cad_status.replaceAll("_"," "))+
   ' · revision UNCONFIRMED · publication rights NOT GRANTED</p>'+
   (url?'<a href="'+esc(url)+'" rel="noopener noreferrer" target="_blank">Manufacturer source ↗</a>':"")+
   '<p>'+esc(r.required_geometry)+'</p></div>';
 }).join("");
 $("#picker-cad-source-exclusions").innerHTML=report.excluded_artifacts.length?
  '<p><strong>Published files excluded from the seven structural CAD parts</strong></p>'+
  report.excluded_artifacts.map(a=>{
   const url=cleanUrl(a.source_url);
   return '<div><strong>'+esc(a.label)+'</strong> · '+
    esc(a.classification.replaceAll("_"," "))+
    ' · not the structural part model. '+
    (url?'<a href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">Original ↗</a>':"")+
    '<p>'+esc(a.note)+'</p></div>';
  }).join(""):"";
}
function renderCadCaptureCampaign(){
 const variant=state.cadModel?.selected_variant_id??null;
 if(state.captureVariant!==variant){
  state.captureObservations=null;state.captureVariant=variant;
  $("#picker-cad-capture-upload").value="";
 }
 const report=state.captureReport=planCadCaptureCampaign(
  state.cadModel,state.captureRequirements,state.dimensionalEvidence,
  state.cadRegistry,{observations:state.captureObservations,kitAudit:state.kitAudit});
 const active=!!state.cadModel;
 for(const id of ["picker-cad-capture-template","picker-cad-capture-upload",
  "picker-cad-capture-export"])$("#"+id).disabled=!active;
 const status=$("#picker-cad-capture-status");
 status.textContent=active?
  report.missing_evidence+"/"+report.task_count+" evidence tasks open · "+
  report.reported_unreviewed+" field-reported (NOT reviewed) · "+
  report.interfaces.length+" interface reviews blocked · "+
  "0 independently verified datums · 0 physical fit approvals":
  "No selected complete kit. No manufacturer geometry or physical approvals inferred.";
 const taskGroups=report.roles.map(r=>{
  const tasks=report.tasks.filter(t=>t.role===r.role);
  const links=r.source_reference_urls.map(url=>{
   const safe=cleanUrl(url);
   return safe?'<a target="_blank" rel="noopener noreferrer" href="'+
    esc(safe)+'">Maker source ↗</a>':"";
  }).join(" ");
  return '<details class="cad-capture-role"><summary>'+
   esc(r.role.replaceAll("_"," "))+" · "+
   r.tasks_missing+" open / "+tasks.length+" tasks"+
   (r.tasks_reported_unreviewed?" · "+r.tasks_reported_unreviewed+" reported":"")+
   '</summary><p>'+links+'</p><ol>'+
   tasks.map(t=>'<li><strong>'+esc(t.task_id.replaceAll("-"," "))+
    '</strong> · '+esc(t.required_method.replaceAll("_"," "))+
    ' · '+esc(t.status.replaceAll("_"," "))+
    '<p>'+esc(t.instruction)+'</p></li>').join("")+
   '</ol></details>';
 });
 $("#picker-cad-capture-tasks").innerHTML=taskGroups.join("");
 $("#picker-cad-capture-interfaces").innerHTML=report.interfaces.length?
  '<p><strong>Physical interface checks requiring independent review</strong></p><ol>'+
  report.interfaces.map(i=>'<li><strong>'+esc(i.id.replaceAll("-"," "))+
   '</strong>: '+esc(i.check)+' · NOT VERIFIED</li>').join("")+'</ol>':"";
}
function renderCadAssetReadiness(){
 const report=state.cadReadiness=planCadAssetReadiness(state.cadModel,state.cadRegistry);
 $("#picker-cad-evidence-export").disabled=!state.cadModel;
 $("#picker-cad-upload").disabled=!state.cadModel;
 $("#picker-cad-coverage-rows").innerHTML=report.rows.map(r=>
  '<tr><td>'+esc(r.role.replaceAll("_"," "))+'</td><td>'+
  esc(r.geometry_status==="PARAMETRIC_PROXY_ONLY"?
   "Procedural proxy only":"Dated GLB candidate, not aligned")+
  (r.revision?" · "+esc(r.revision):"")+
  (r.asset_id?' <button type="button" data-cad-asset="'+esc(r.asset_id)+'">Inspect pinned GLB</button>':"")+
  '</td><td>UNKNOWN · not verified</td></tr>').join("");
 $("#picker-cad-readiness").textContent=state.cadModel?
  report.asset_candidates+"/7 file-backed candidates · "+report.missing_geometry+
  " procedural categories · 0 verified mounting datums · clearance NOT EVALUATED · 0 extra orders":
  "No complete-kit geometry coverage for this selection. No physical approval.";
}
function download(name,data,mime){
 const blob=new Blob([data],{type:mime}),url=URL.createObjectURL(blob);
 const a=document.createElement("a");a.href=url;a.download=name;document.body.append(a);
 a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
const quoteCsv=value=>{
 const raw=String(value??"");
 const escaped=/^[=+\-@\t\r]/.test(raw)?"'"+raw:raw;
 return '"'+escaped.replaceAll('"','""')+'"';
};
function exportWorklist(format){
 if(!state.study)return;
 if(format==="json")return download("worcester-parts-research-"+state.domain+".json",
  JSON.stringify({report:state.study.report,source_bound_variants:state.study.selected_variants,
    display_graph:currentGraph(),
    parametric_cad_display:state.cadModel,
    maker_published_dimensions_not_mount_datums:state.publishedCad,
    maker_unit_observations:state.offerAudit,
    complete_kit_claim_audit:state.kitAudit,
   visual_geometry:"UNSCALED_PROXY_NOT_MEASURED_CAD"},null,2)+"\n","application/json");
 const headers=["Sport","Slot","Variant ID","Requirement","Status",
  "Actual supplier order units","Historical maker pack examples","Maker code","Notes"];
 const bySlot=new Map(state.offerAudit?.rows.map(x=>[x.slot,x])||[]);
 const rows=[headers,...state.study.report.rows.map(r=>{
  const maker=bySlot.get(r.slot);
  return [state.domain,r.label,r.variant_id??"",r.needed,r.status,
   "UNKNOWN",maker?.reference_pack_count===null||maker?.reference_pack_count===undefined?
    "HOLD":String(maker.reference_pack_count)+" (historical only)",
   maker?.maker_product_code||"",
   "Confirm source revision, received contents, physical fit and current stock"];
 })];
 download("worcester-parts-worklist-"+state.domain+".csv",
  rows.map(row=>row.map(quoteCsv).join(",")).join("\n")+"\n","text/csv;charset=utf-8");
}
function renderCompleteKitClosure(){
 const host=$("#picker-kit-summary"),body=$("#picker-kit-rows"),unknowns=$("#picker-kit-unknowns");
 if(!state.kitClaims||!state.study){host.textContent="No complete-kit maker claims loaded.";return;}
 const asOf=new Date().toISOString().slice(0,10);
 const result=auditCompleteKitClaim(state.study,state.kitClaims,state.catalog,
   state.retailCatalog,{as_of:asOf});
 state.kitAudit=result;
 state.visualGraph=buildCompleteKitVisualGraph(state.study,result);
 state.cadModel=compileCompleteKitCadDisplay(
  state.study,result,state.kitClaims,state.cadRecipe);
 const kit=state.cadModel?.kit_id??null;
 if(state.inspectedKit!==kit){
  state.cadInspector?.dispose();
  state.cadInspector=null;state.inspectedKit=kit;
  $("#picker-cad-file-inspector").hidden=true;
  $("#picker-cad-inspect-status").textContent=
   "No local GLB inspected for this kit. The integrated board uses procedural geometry.";
  $("#picker-cad-upload").value="";
 }
 renderCadAssetReadiness();
 renderCadMakerDimensions();
 renderCadSourceAcquisition();
 renderCadCaptureCampaign();
 state.metricResult=null;state.motionResult=null;state.sceneFixture=null;
 state.sceneEpoch++;
 $("#picker-cad-scene-panel").hidden=true;
 $("#picker-cad-scene-angle").disabled=true;
 $("#picker-cad-scene-angle").value="0";
 $("#picker-cad-metric-export").disabled=true;
 $("#picker-cad-motion-export").disabled=true;
 $("#picker-cad-motion-plot").replaceChildren();
 $("#picker-cad-motion-status").textContent=
  "No optional motion fixture loaded · steering and wheel-bite clearance UNKNOWN.";
 $("#picker-cad-metric-upload").disabled=!state.cadModel;
 $("#picker-cad-motion-demo").disabled=!state.cadModel;
 $("#picker-cad-metric-results").replaceChildren();
 $("#picker-cad-metric-status").textContent=
  "No independent candidate survey loaded for this kit · 0 physical clearances verified.";
 const exportButton=$("#picker-export-kit");
 exportButton.disabled=result.rows.length===0;
 if(!result.rows.length){
  host.textContent="This is a modular or other-sport study; no maker complete-package child list is asserted.";
  body.replaceChildren();unknowns.replaceChildren();return;
 }
 host.innerHTML='<strong>'+esc(result.status.replaceAll("_"," "))+'</strong>'+
  ' · '+result.children_source_claimed+' advertised component categories in ONE maker kit'+
  ' · 0 verified received components · 0 separate child purchases · exact seller kit contents UNKNOWN'+
  (result.inclusion_conflict?'<p class="kit-conflict"><strong>Physical package mismatch!</strong> '+
    esc(result.inclusion_conflict.explanation)+'</p>':'')+
  '<p><small>Kit reference '+esc(result.kit_id)+'. Source revision and individual fastener counts require inspection.</small></p>';
 body.innerHTML=result.rows.map(r=>{
  const url=cleanUrl(r.source_url);
  return '<tr><td><strong>'+esc(r.label)+'</strong><small>'+esc(r.child_id)+'</small>'+
    '<button type="button" class="kit-inspect-button" data-kit-inspect="'+esc(r.child_id)+
    '">Highlight in assembly</button></td>'+
   '<td>'+esc(r.expected_assembly_units??"UNKNOWN")+
   '<small>'+esc(r.expectation_basis.replaceAll("_"," "))+'</small></td>'+
   '<td>'+esc(r.source_claim)+'</td>'+
   '<td><strong>UNKNOWN</strong><small>Not physically received</small></td>'+
   '<td>'+esc(r.status.replaceAll("_"," "))+
   (url?'<small><a href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">Manufacturer kit contents ↗</a></small>':'')+
   '</td></tr>';
 }).join("");
 unknowns.innerHTML='<h3>Receiving and assembly unknowns</h3><ul>'+
   result.known_unknowns.map(s=>'<li>'+esc(s)+'</li>').join("")+'</ul>'+
   '<p>The assembled and exploded board are generated from one compact parametric display schema. Deck and wheel size references are published; every mount offset, axle spacing, clearance and fastener location is illustrative, not measured manufacturer CAD. Source-linked child IDs are preserved.</p>';
}
function renderOrder(){
 const report=state.study.report;
 $("#picker-study-status").textContent=report.status.replaceAll("_"," ");
 $("#picker-quantity-status").textContent=report.qualified_supplier_order_lines+
  " verified order lines";
 $("#picker-order-status").textContent=report.rows.filter(x=>x.variant_id).length+
  " selected maker families · "+report.missing_required_count+" missing required references · "+
  report.review_required_count+" selected family reviews · "+report.conflicts.length+
  " declared compatibility conflicts. No live basket total or shipping promises.";
 const entries=new Map(state.study.selected_variants.map(x=>[x.slot,x]));
 $("#picker-order-rows").innerHTML=report.rows.map(r=>{
  const entry=entries.get(r.slot),url=cleanUrl(entry?.source_url);
  return '<tr><td><strong>'+esc(r.label)+'</strong></td><td>'+
   (entry?esc(entry.label):'Not selected')+
   (url?'<small><a href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">Original manufacturer listing ↗</a></small>':'')+
   (entry?.indicative_family_price?'<small>Maker reference USD '+
     entry.indicative_family_price.displayed_maker_listing_usd.toFixed(2)+
     ' · indicative family-level price only</small>':'')+
   '</td><td>'+esc(r.needed)+'</td><td><strong>UNKNOWN</strong>'+
   '<small>SKU, package size and included hardware need inspection</small></td>'+
   '<td class="'+(r.status==="MISSING_REQUIRED_REFERENCE"?"status-missing":"status-hold")+'">'+
   esc(r.status.replaceAll("_"," "))+'</td></tr>';
 }).join("");
 $("#picker-findings").innerHTML='<h3>Mechanical compatibility and professional handoff</h3>'+
  (report.findings.length?'<ul>'+report.findings.map(x=>'<li><strong>'+esc(x.kind)+
   '</strong> · '+esc(x.message)+'</li>').join("")+'</ul>':
   '<p>No declared conflict established. Missing manufacturer evidence can still prevent safe assembly.</p>')+
  '<p>No print-to-ski mounting templates, automatic release settings, electrical assembly permission, or inferred seller pack quantities are generated.</p>';
}

function renderMakerUnitAudit(){
 const host=$("#maker-audit-summary"),body=$("#maker-audit-rows");
 if(!state.offerObservations||!state.study){
  host.textContent="No manufacturer unit observations loaded.";
  body.replaceChildren();return;
 }
 const today=new Date().toISOString().slice(0,10);
 state.offerAudit=auditMakerOrderUnits(state.study,state.offerObservations,state.catalog,{as_of:today});
 const audit=state.offerAudit;
 const sum=Object.entries(audit.historical_partial_subtotals_by_currency)
  .map(([currency,value])=>esc(currency)+" "+value.toFixed(2)).join(" · ")||"No matched lines";
 host.innerHTML='<span><strong>'+audit.matched_historical_unit_lines+
  '</strong> dated maker pack line(s)</span>'+
  '<span>Partial historical reference: '+sum+'</span>'+
  '<span><strong>0</strong> purchase-authorized lines</span>'+
  '<span>Audit date: '+esc(today)+' UTC · No live stock</span>';
 body.innerHTML=audit.rows.map(x=>{
  const link=cleanUrl(x.source_url);
  const amount=x.reference_extended_amount!==null?
   '<small>Maker price example '+esc(x.reference_currency)+' '+
   x.reference_extended_amount.toFixed(2)+' (dated, partial)</small>':'';
  return '<tr><td>'+esc(x.label)+'</td>'+
   '<td><span class="source-part-code">'+esc(x.maker_product_code??"Unknown option code")+'</span>'+
   (link?'<small><a href="'+esc(link)+'" target="_blank" rel="noopener noreferrer">Original maker listing ↗</a></small>':'')+
   '<small>'+esc(x.observed_on??"No reviewed listing")+'</small></td>'+
   '<td>'+esc(x.required_item_count??"Unknown")+'</td>'+
   '<td>'+esc(x.seller_unit_items??"Unknown")+
   (x.item_kind?'<small>'+esc(x.item_kind.replaceAll("_"," "))+'/pack</small>':'')+'</td>'+
   '<td>'+(x.reference_pack_count===null?'<span class="unit-hold">HOLD</span>':
    '<span class="unit-reference">'+x.reference_pack_count+' reference pack(s)</span>')+
   amount+'</td>'+
   '<td class="'+(x.reference_pack_count===null?"unit-hold":"unit-reference")+'">'+
   esc(x.status.replaceAll("_"," "))+
   '<small>'+esc(x.review_actions?.[0]??"Stock, taxes, shipping and fit unverified")+'</small></td></tr>';
 }).join("");
}

function renderThreeStudies(){
 const host=$("#picker-study-cards"),details=$("#picker-study-differences");
 if(!state.studyCatalog||!state.retailCatalog||!state.study){
  host.textContent="Build studies are not yet available.";details.textContent="";return;
 }
 const entered=$("#picker-mass").value.trim();
 const amount=entered===""?null:Number(entered);
 const validMass=amount===null||Number.isFinite(amount)&&amount>=15&&amount<=250;
 $("#picker-mass-validation").textContent=validMass?"": 
  "Rider mass is outside the supported 15–250 kg research range. This input is ignored until corrected.";
 const mass=validMass?amount:null;
 state.alternatives=composeResearchAlternatives(state.catalog,state.studyCatalog,
  state.offerObservations,state.retailCatalog,state.domain,{
   as_of:new Date().toISOString().slice(0,10),
   profile:{left_mondo_mm:$("#picker-left").value||null,
    right_mondo_mm:$("#picker-right").value||null,mass_kg:mass}
  });
 host.innerHTML=state.alternatives.cards.map((card,i)=>{
  const active=Object.keys(state.selections).length===Object.keys(card.selection).length&&
   Object.entries(card.selection).every(([k,v])=>state.selections[k]===v);
  const pct=card.indicative_published_dimensions.map(d=>
   Object.entries(d.dimensions_mm).map(([key,val])=>esc(key.replaceAll("_"," "))+
   ": "+esc(val)+" mm").join(" · ")).join(" / ");
  const historical=Object.entries(card.historical_maker_subtotals).map(([currency,value])=>
   esc(currency)+" "+value.toFixed(2)).join(", ")||"No eligible manufacturer price units";
  return '<article class="study-card'+(active?' current-study':'')+'">'+
   '<span class="study-number">RESEARCH '+(i+1)+' / 3</span>'+
   '<h3>'+esc(card.title)+'</h3><p>'+esc(card.intent)+'</p>'+
   (pct?'<p class="study-measure">'+pct+' (published dimensions, not CAD)</p>':'')+
   '<div class="study-stats"><span>'+esc(card.variant_count)+' selected reference(s)</span>'+
   '<span>'+esc(card.missing_required)+' missing required slot(s)</span>'+
   '<span>'+esc(card.findings.length)+' compatibility/review findings</span></div>'+
   '<p class="study-historical">Partial historic maker subtotal: '+historical+
   ' · NOT build total</p>'+
   '<p class="study-note">'+esc(card.notes.join("; "))+'</p>'+
   (card.findings.length?'<details class="study-review"><summary>Inspect '+
     card.findings.length+' unresolved compatibility / professional checks</summary>'+
     '<ul>'+card.findings.map(f=>'<li data-warning-code="'+esc(f.code??f.kind)+'">'+
     '<strong>'+esc(f.kind)+'</strong>: '+esc(f.message)+'</li>').join("")+'</ul></details>':
     '<p class="study-review-none">No declared conflict; physical fit remains unqualified.</p>')+
   '<button type="button" data-load-study="'+esc(card.id)+
   '"'+(active?' aria-pressed="true"':' aria-pressed="false"')+'>'+
   (active?'Currently inspecting':'Inspect this configuration')+'</button>'+
   '</article>';
 }).join("");
 details.innerHTML='<strong>Source-aware differences:</strong> '+
  state.alternatives.differences.map(d=>{
   const a=state.alternatives.cards.find(x=>x.id===d.left)?.title;
   const b=state.alternatives.cards.find(x=>x.id===d.right)?.title;
   return '<span>'+esc(a)+' vs '+esc(b)+': '+esc(d.changed_slots.join(", "))+'</span>';
  }).join("");
}
function renderRetailMatches(){
 const host=$("#picker-retail-results");
 if(!state.retailCatalog||!state.study){host.textContent="No seller references loaded.";return;}
 const today=new Date().toISOString().slice(0,10);
 const comparisons=state.study.selected_variants.map(s=>
  compareRetailOffers(state.retailCatalog,state.catalog,s.variant_id,{as_of:today}))
  .filter(x=>x.rows.length);
 const loose=state.domain==="alpine_ski"?
  state.study.selected_variants.filter(x=>x.slot==="ski_pair")
   .flatMap(x=>researchRelatedSellerListings(
    state.retailCatalog,state.catalog,x.product_id,{as_of:today}).rows):[];
 const sections=comparisons.map(x=>{
  const count=x.compared_merchants;
  return '<article class="retail-match"><h3>'+esc(x.product_name)+'</h3>'+
   '<p class="'+(x.conflict?"unit-hold":count>=2?"unit-reference":"unit-hold")+'">'+
   esc(x.status.replaceAll("_"," "))+
   '. Named wheel setup only; included hardware must also match. NOT verified exact checkout SKU.</p>'+
   (x.conflict?'<p class="retail-conflict" role="status"><strong>Do not treat these as identical seller kits.</strong> '+
    esc(x.conflict.explanation)+'</p>':'')+
   '<div class="retail-offer-grid">'+x.rows.map(offer=>{
    const url=cleanUrl(offer.source_url);
    return '<div class="retail-offer">'+
      '<strong>'+esc(offer.merchant_name)+'</strong>'+
      '<p>'+esc(offer.setup)+'</p>'+
      '<p><strong>Declared trucks: '+esc(offer.advertised_truck_revision_claim?.replaceAll("_"," ")??"UNKNOWN")+
       '</strong> · original package contents not physically received</p>'+
      '<p class="retail-price">USD '+offer.displayed_amount_usd.toFixed(2)+
      '<small> · observed '+esc(offer.observed_on)+'</small></p>'+
      '<small>'+esc(offer.status.replaceAll("_"," "))+
       ' · stock, delivery and order SKU not verified</small>'+
      (url?'<p><a href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">View seller listing ↗</a></p>':'')+
     '</div>';
   }).join("")+'</div>'+
   (x.historical_listing_price_span_usd?
    '<p class="retail-footnote">Published setup price gap USD '+
     x.historical_listing_price_span_usd.gap.toFixed(2)+
    '. The complete landed cost remains unknown.</p>':'')+
   '</article>';
 });
 if(loose.length)sections.push('<article class="retail-match">'+
  '<h3>Related listings that must NOT be compared as an exact variant</h3>'+
  '<p>These related family listings do not confirm the selected ski length, boot/binding revision or sellable package. Different ski-only and binding-bundle contents must NEVER be compared as the same offer.</p>'+
  loose.map(o=>{const url=cleanUrl(o.source_url);return '<p><strong>'+
   esc(o.description)+'</strong> · USD '+o.historical_page_amount_usd.toFixed(2)+
   ' historical page listing · <strong>'+esc(o.state.replaceAll("_"," "))+'</strong>'+
   (url?' · <a href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">Inspect source ↗</a>':'')+
   '</p>';}).join("")+'</article>');
 host.innerHTML=sections.length?sections.join(""):
  '<p class="retail-none">No distinct seller sources with source-bounded option identifiers are available for this selection. No comparable offer or current cart total can be inferred.</p>';
}
function renderVendorDirectory(){
 const vendors=state.catalog.vendors.filter(x=>x.domains.includes(state.domain));
 $("#picker-vendors").innerHTML=vendors.map(v=>{
  const url=cleanUrl(v.url);
  return '<article class="vendor-card"><strong>'+esc(v.name)+
   ' · '+esc(v.kind.replaceAll("_"," "))+'</strong>'+
   '<p>'+esc(v.notes)+'</p>'+
   (url?'<a href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">Visit '+esc(v.name)+' ↗</a>':'')+
   '<small>Stock, applicable shipping/returns and exact product availability: not checked.</small></article>';
 }).join("");
}
function renderPrint(){
 $("#picker-print").innerHTML=state.catalog.print_guidance.map(x=>
  '<article class="print-item"><strong>'+esc(x.label)+'</strong>'+
  '<small>'+esc(x.classification.replaceAll("_"," "))+'</small>'+
  '<p>'+esc(x.notes)+'</p></article>').join("");
}
function refresh(){
 try{
  state.study=buildPickerStudy(state.catalog,{
   domain_id:state.domain,selections:state.selections,profile:{
    left_mondo_mm:$("#picker-left").value||null,
    right_mondo_mm:$("#picker-right").value||null
   }});
  renderSlots();renderOrder();renderMakerUnitAudit();renderThreeStudies();
  renderRetailMatches();renderCompleteKitClosure();renderVendorDirectory();
  const active=currentGraph();
  if(!active.components.some(x=>x.component_id===state.selectedId))
   state.selectedId=active.components[0]?.component_id??null;
  renderTree();
  if(state.selectedId)selectPart(state.selectedId);
  else $("#picker-component-detail").textContent="No part families selected.";
  redrawVisual();
 }catch(error){
  $("#picker-order-status").textContent="Selection held: "+error.message;
  console.error(error);
 }
}
function fallbackTo2D(message){
 state.mode="2d";
 $("#picker-visual-svg").hidden=false;
 $("#picker-visual-3d").hidden=true;
 $("#picker-camera-controls").hidden=true;
 $("#picker-3d").setAttribute("aria-pressed","false");
 $("#picker-2d").setAttribute("aria-pressed","true");
 if(message)$("#picker-view-note").textContent=message;
}
async function use3D(){
 state.mode="3d";
 $("#picker-visual-svg").hidden=true;
 $("#picker-visual-3d").hidden=false;
 $("#picker-camera-controls").hidden=false;
 $("#picker-3d").setAttribute("aria-pressed","true");
 $("#picker-2d").setAttribute("aria-pressed","false");
 $("#picker-view-note").textContent="3D shows independently explodable source-named categories, not measured parts or mounting geometry. Rotate with mouse/touch, select a component or choose a camera preset.";
 try{
  if(!state.viewerPromise){
   state.viewerPromise=import("./exploded_3d_viewer.mjs")
    .then(x=>x.createExploded3DViewer($("#picker-visual-3d"),{
     onSelect:selectPart
    }));
  }
  state.viewer=await state.viewerPromise;
  if(state.mode==="3d")redrawVisual();
 }catch(error){
  state.viewerPromise=null;
  fallbackTo2D("WebGL or CDN unavailable. The source-linked SVG and ordering worklist remain available.");
 }
}
function loadDemo(){
 const get=(slot,prefix,label)=>{
  const p=productsFor(slot).find(x=>x.id===prefix);
  return p?.variants.find(v=>!label||v.label===label)?.id??null;
 };
 state.selections={};
 if(state.domain==="alpine_ski"){
  state.selections.ski_pair=get("ski_pair","atomic-bent90","157 cm");
  state.selections.ski_binding=get("ski_binding","tyrolia-gw-ref");
  state.selections.ski_boot=get("ski_boot","salomon-alpha130");
 }else if(state.domain==="snowboard"){
  state.selections.snowboard=get("snowboard","burton-goodcompany","145 cm");
  state.selections.snow_binding=get("snow_binding","burton-stepon","S");
  state.selections.snow_boot=get("snow_boot","burton-stepon-boot-ref");
 }else if(state.domain==="skateboard_longboard"){
  state.selections.long_complete=get("long_complete","loaded-tangent-complete");
  state.separation=0;$("#picker-explode").value="0";
 }else{
  state.selections.mt_deck=get("mt_deck","mbs-comp95");
  state.selections.mt_trucks=get("mt_trucks","mbs-matrix3");
  state.selections.mt_wheels=get("mt_wheels","mbs-rockstar");
  state.selections.mt_bindings=get("mt_bindings","mbs-f5");
 }
 refresh();
}
function initEvents(){
 $("#picker-domain").addEventListener("change",e=>{
  state.domain=e.target.value;state.selections={};state.selectedId=null;refresh();
 });
 $("#picker-search").addEventListener("input",e=>{state.search=e.target.value.trim().toLowerCase();renderSlots();});
 $("#picker-slots").addEventListener("change",e=>{
  const slot=e.target?.dataset?.pickerSlot;
  if(!slot)return;
  const value=e.target.value;
  if(value)state.selections[slot]=value;else delete state.selections[slot];
  if(state.domain==="skateboard_longboard"&&slot==="long_complete"&&value){
   state.separation=0;$("#picker-explode").value="0";
  }
  if(state.domain==="skateboard_longboard"&&value){
   if(slot==="long_complete")for(const key of ["long_deck","long_trucks","long_wheels","long_hardware"])delete state.selections[key];
   else delete state.selections.long_complete;
  }
  refresh();
 });
 $("#picker-left").addEventListener("input",refresh);
 $("#picker-right").addEventListener("input",refresh);
 $("#picker-mass").addEventListener("input",refresh);
 $("#picker-study-cards").addEventListener("click",event=>{
  const choice=event.target.closest("[data-load-study]");
  if(!choice)return;
  const entry=state.studyCatalog.studies.find(x=>x.id===choice.dataset.loadStudy&&
   x.domain_id===state.domain);
  if(!entry)return;
  state.selections={...entry.selections};
  if(state.domain==="skateboard_longboard"&&state.selections.long_complete){
   state.separation=0;$("#picker-explode").value="0";
  }
  state.selectedId=null;
  state.search="";
  $("#picker-search").value="";
  refresh();
 });
 $("#picker-explode").addEventListener("input",e=>{state.separation=Number(e.target.value);redrawVisual();});
 $("#picker-assemble").addEventListener("click",()=>{
  state.separation=0;$("#picker-explode").value="0";redrawVisual();
 });
 $("#picker-separate").addEventListener("click",()=>{
  state.separation=100;$("#picker-explode").value="100";redrawVisual();
 });
 $("#picker-cad-source-export").addEventListener("click",()=>{
  if(state.sourceAcquisition)download("worcester-cad-official-source-leads-"+state.domain+".json",
   JSON.stringify(state.sourceAcquisition,null,2)+"\n","application/json");
 });
 $("#picker-cad-source-requests").addEventListener("click",()=>{
  const packets=state.sourceAcquisition?.manufacturer_request_packets;
  if(!packets?.length)return;
  const content=packets.map(x=>
   "## "+x.manufacturer+"\nSubject: "+x.subject+"\n\n"+x.message).join("\n\n---\n\n");
  download("worcester-cad-manufacturer-requests-"+state.domain+".md",
   "# CAD file inquiry drafts · UNVERIFIED source research\n\n"+content+"\n",
   "text/markdown");
 });
 $("#picker-cad-capture-template").addEventListener("click",()=>{
  if(!state.cadModel)return;
  download("worcester-cad-field-template-"+state.domain+".json",
   JSON.stringify(blankCadFieldObservations(state.cadModel.selected_variant_id),
    null,2)+"\n","application/json");
 });
 $("#picker-cad-capture-export").addEventListener("click",()=>{
  if(state.captureReport)download("worcester-cad-metrology-gaps-"+state.domain+".json",
   JSON.stringify(state.captureReport,null,2)+"\n","application/json");
 });
 $("#picker-cad-capture-upload").addEventListener("change",async event=>{
  const file=event.target.files?.[0];if(!file)return;
  const variant=state.cadModel?.selected_variant_id;
  state.captureObservations=null;
  try{
   if(!variant||file.size>65536||file.size<20)
    throw Error("Exact kit and observation JSON of up to 64 KB required");
   const input=JSON.parse(await file.text());
   validateCadFieldObservations(input,state.captureRequirements,variant);
   if(variant!==state.cadModel?.selected_variant_id)
    throw Error("The selected kit changed during observation import");
   state.captureObservations=input;
   renderCadCaptureCampaign();
  }catch(err){
   if(variant===state.cadModel?.selected_variant_id){
    renderCadCaptureCampaign();
    $("#picker-cad-capture-status").textContent=
     "Observation packet held: "+err.message+
     " · all physical approvals remain blocked.";
   }
  }finally{event.target.value="";}
 });
 $("#picker-cad-maker-export").addEventListener("click",()=>{
  if(state.publishedCad)download("worcester-maker-dimensions-"+state.domain+".json",
   JSON.stringify(state.publishedCad,null,2)+"\n","application/json");
 });
 $("#picker-cad-motion-export").addEventListener("click",()=>{
  if(state.motionResult)download("worcester-candidate-motion-"+state.domain+".json",
   JSON.stringify(state.motionResult,null,2)+"\n","application/json");
 });
 $("#picker-cad-metric-export").addEventListener("click",()=>{
  if(state.metricResult)download("worcester-metric-candidate-"+state.domain+".json",
   JSON.stringify(state.metricResult,null,2)+"\n","application/json");
 });
 async function redrawCandidate3D(){
  const fixture=state.sceneFixture,kit=state.cadModel;
  if(!fixture||!kit)return;
  const version=state.sceneEpoch;
  const slider=$("#picker-cad-scene-angle");
  const selected=Math.min(Number(slider.value)||0,
   (state.motionResult?.sample_count??1)-1);
  let snapshot;
  try{snapshot=compileCandidateMetricScene(fixture,{
   expected_variant_id:kit.selected_variant_id,sample_index:selected});
  }catch(error){
   $("#picker-cad-scene-status").textContent="Candidate visualization held: "+error.message;
   return;
  }
  $("#picker-cad-scene-panel").hidden=false;
  slider.max=String(snapshot.sample_count-1);
  slider.disabled=snapshot.sample_count<=1;
  $("#picker-cad-scene-angle-output").textContent=snapshot.angle_deg+"°";
  if(state.motionResult)
   $("#picker-cad-motion-plot").innerHTML=renderCandidateMotionSvg(state.motionResult,
    {selectedIndex:selected});
  $("#picker-cad-scene-status").textContent=
   (snapshot.fixture_type==="SYNTHETIC_NUMERICAL_DEMO_NOT_REAL_ASSEMBLY"?
    "SYNTHETIC numerical example · ":"Unverified candidate survey · ")+
   snapshot.possible_overlap_pairs+" possible box-overlap pair(s) at "+
   snapshot.angle_deg+"° · physical clearance UNKNOWN";
  try{
   if(!state.sceneViewerPromise)
    state.sceneViewerPromise=import("./cad_candidate_viewer.mjs")
     .then(module=>module.createCandidateMetricViewer($("#picker-cad-scene-view")));
   const viewer=await state.sceneViewerPromise;
   if(version!==state.sceneEpoch||kit!==state.cadModel)return;
   state.sceneViewer=viewer;
   viewer.update(snapshot);
  }catch(error){
   if(version!==state.sceneEpoch)return;
   state.sceneViewerPromise=null;state.sceneViewer=null;
   $("#picker-cad-scene-status").textContent=
    "3D WebGL unavailable: "+error.message+
    ". The source data, SVG sample chart and export remain available.";
  }
 }
 $("#picker-cad-scene-angle").addEventListener("input",()=>{void redrawCandidate3D();});
 const clearCandidate=()=>{
  state.metricResult=null;state.motionResult=null;state.sceneFixture=null;
  state.sceneEpoch++;
  $("#picker-cad-scene-panel").hidden=true;
  $("#picker-cad-scene-angle").value="0";
  $("#picker-cad-scene-angle").disabled=true;
  $("#picker-cad-metric-export").disabled=true;
  $("#picker-cad-motion-export").disabled=true;
  $("#picker-cad-metric-results").replaceChildren();
  $("#picker-cad-motion-plot").replaceChildren();
 };
 function showCandidateFixture(input,{kitId,variant,synthetic=false}){
  const status=$("#picker-cad-metric-status");
  clearCandidate();
  try{
   const result=evaluateMetricFixture(input,{expected_variant_id:variant});
   const motion=input.motion?sampleCandidateMotionSweep(input,
    {expected_variant_id:variant}):null;
   if(kitId!==state.cadModel?.kit_id||variant!==state.cadModel?.selected_variant_id)
    throw Error("kit selection changed during calculation");
   state.metricResult=result;state.motionResult=motion;
   state.sceneFixture=input;
   $("#picker-cad-scene-angle").value="0";
   $("#picker-cad-metric-export").disabled=false;
   $("#picker-cad-motion-export").disabled=!motion;
   $("#picker-cad-motion-status").textContent=motion?
    (synthetic?"SYNTHETIC ALGORITHM EXAMPLE ONLY · ":"Candidate motion: ")+
    motion.sample_count+" sampled angles · "+
    motion.possible_overlap_pairs+" of "+motion.pair_count+
    " pairs show possible AABB overlap · physical clearance UNKNOWN":
    "No optional motion block in survey JSON · steering and wheel-bite clearance UNKNOWN.";
   $("#picker-cad-motion-plot").innerHTML=motion?renderCandidateMotionSvg(motion):"";
   void redrawCandidate3D();
   status.textContent=(synthetic?"SYNTHETIC, NOT MANUFACTURER GEOMETRY · ":"")+
    result.candidate_pairs_checked+" candidate pair(s) · "+
    result.possible_overlap_pairs+" potential AABB overlap(s) · "+
    "0 physical clearances verified, 0 engineering approvals";
   $("#picker-cad-metric-results").innerHTML='<div class="table-scroll"><table class="cad-coverage-table">'+
    '<thead><tr><th>Candidate pair</th><th>AABB broad-phase</th><th>Decision</th></tr></thead><tbody>'+
    result.pairs.map(p=>'<tr><td>'+esc(p.a)+" / "+esc(p.b)+
     '</td><td>'+esc(p.classification.replaceAll("_"," "))+
     '</td><td>Physical clearance UNKNOWN</td></tr>').join("")+
    '</tbody></table></div>';
  }catch(error){
   clearCandidate();
   $("#picker-cad-motion-status").textContent=
    "Motion study unavailable. No physical clearance or contact decision.";
   status.textContent="Metric survey held: "+error.message+
    ". No changes to the assembled board or safety readiness.";
  }
 }
 $("#picker-cad-motion-demo").addEventListener("click",()=>{
  const kitId=state.cadModel?.kit_id,variant=state.cadModel?.selected_variant_id;
  if(!kitId||!variant)return;
  showCandidateFixture(makeSyntheticCandidateMotionFixture(variant),
   {kitId,variant,synthetic:true});
 });
 $("#picker-cad-metric-upload").addEventListener("change",async event=>{
  const file=event.target.files?.[0];
  if(!file)return;
  const kitId=state.cadModel?.kit_id,variant=state.cadModel?.selected_variant_id;
  try{
   if(!kitId||file.size>65536||file.size<10)
    throw Error("Choose a survey JSON under 64 KB with a complete kit selected");
   const input=JSON.parse(await file.text());
   showCandidateFixture(input,{kitId,variant});
  }catch(error){
   clearCandidate();
   $("#picker-cad-metric-status").textContent="Metric survey held: "+error.message+
    ". No changes to the assembled board or safety readiness.";
   $("#picker-cad-motion-status").textContent=
    "Motion study unavailable. No physical clearance or contact decision.";
  }finally{event.target.value="";}
 });
 $("#picker-cad-evidence-export").addEventListener("click",()=>{
  if(state.cadModel)download("worcester-cad-evidence-"+state.domain+".json",
   JSON.stringify(state.cadReadiness,null,2)+"\n","application/json");
 });
 $("#picker-cad-coverage-rows").addEventListener("click",async event=>{
  const button=event.target.closest("[data-cad-asset]");
  if(!button)return;
  const candidate=state.cadRegistry.assets.find(
   a=>a.asset_id===button.dataset.cadAsset&&
   a.kit_variant_id===state.cadModel?.selected_variant_id);
  if(!candidate)return;
  const currentKit=state.cadModel.kit_id,status=$("#picker-cad-inspect-status");
  try{
   status.textContent="Verifying pinned geometry digest for "+candidate.asset_id+"…";
   const response=await fetch(candidate.path,{cache:"no-store"});
   if(!response.ok)throw Error("pinned file is unavailable");
   const blob=await response.blob();
   if(blob.size!==candidate.byte_length||blob.size>25000000)
    throw Error("pinned file size mismatch");
   const bytes=await blob.arrayBuffer();
   const hash=Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",bytes)))
    .map(x=>x.toString(16).padStart(2,"0")).join("");
   if(hash!==candidate.sha256)throw Error("SHA-256 mismatch; source asset not displayed");
   inspectGlbBytes(bytes);
   const host=$("#picker-cad-file-inspector");
   if(!state.cadInspector)
    state.cadInspector=await import("./cad_glb_inspector.mjs")
     .then(x=>x.createLocalCadInspector(host));
   if(currentKit!==state.cadModel?.kit_id)
    throw Error("kit changed during loading");
   const result=await state.cadInspector.load(bytes);
   if(!result)return;
   host.hidden=false;
   status.textContent="Pinned, digest-verified "+candidate.origin+" candidate "+
    candidate.part_number+" · "+candidate.revision+": "+
    result.mesh_count+" mesh(es), glTF scene meters; physical source scale NOT VERIFIED. "+
    "No verified datums, assembly mating, clearances or purchasing approval.";
  }catch(error){
   status.textContent="Candidate CAD held: "+error.message+
    ". The assembled schematic remains available.";
  }
 });
 $("#picker-cad-upload").addEventListener("change",async event=>{
  const file=event.target.files?.[0],status=$("#picker-cad-inspect-status");
  if(!file)return;
  const kit=state.cadModel?.kit_id,part=state.selectedId;
  try{
   if(!kit||!part||file.size>25000000||file.size<28)
    throw Error("Select a file under 25 MB while viewing a complete-kit part");
   const data=await file.arrayBuffer();
   inspectGlbBytes(data);
   status.textContent="Inspecting isolated unverified geometry from "+file.name+"…";
   const host=$("#picker-cad-file-inspector");
   if(!state.cadInspector)
    state.cadInspector=await import("./cad_glb_inspector.mjs")
     .then(x=>x.createLocalCadInspector(host));
   if(kit!==state.cadModel?.kit_id)
    throw Error("Kit changed during import. Re-select the file.");
   const result=await state.cadInspector.load(data);
   if(!result)return;
   host.hidden=false;
   status.textContent="Local-only GLB attached to "+part+" for inspection: "+
    result.mesh_count+" mesh(es), "+result.vertex_reference_count+
    " referenced vertices; native-file bounds "+
    [result.bounds_in_file_units.x,result.bounds_in_file_units.y,
     result.bounds_in_file_units.z].map(x=>x.toPrecision(4)).join(" × ")+
    " (UNITS UNKNOWN). No assembly mating, clearance test or new order lines.";
  }catch(error){
   status.textContent="Local CAD file held: "+error.message+
    ". The integrated schematic above remains available.";
  }finally{event.target.value="";}
 });
 $("#picker-cad-export").addEventListener("click",()=>{
  if(state.cadModel)download("worcester-parametric-cad-research-"+state.domain+".json",
   JSON.stringify(state.cadModel,null,2)+"\n","application/json");
 });
 $("#picker-3d").addEventListener("click",use3D);
 $("#picker-2d").addEventListener("click",()=>{fallbackTo2D();redrawVisual();});
 $("#picker-camera-controls").addEventListener("click",e=>{
  const camera=e.target.dataset?.camera;
  if(camera)state.viewer?.view(camera);
 });
 $("#picker-part-tree").addEventListener("click",e=>{
  const el=e.target.closest("[data-picker-part]");
  if(el)selectPart(el.dataset.pickerPart);
 });
 $("#picker-kit-rows").addEventListener("click",e=>{
  const el=e.target.closest("[data-kit-inspect]");
  if(!el)return;
  selectPart(el.dataset.kitInspect);
  $(".preview").scrollIntoView({behavior:"smooth",block:"start"});
  $("#picker-part-tree [data-picker-part='"+CSS.escape(el.dataset.kitInspect)+"']")
    ?.focus({preventScroll:true});
 });
 $("#picker-demo").addEventListener("click",loadDemo);
 $("#picker-export-json").addEventListener("click",()=>exportWorklist("json"));
 $("#picker-export-csv").addEventListener("click",()=>exportWorklist("csv"));
 $("#picker-export-kit").addEventListener("click",()=>{
  if(state.kitAudit?.rows?.length)download("worcester-kit-inclusion-"+state.domain+".json",
   JSON.stringify(state.kitAudit,null,2)+"\n","application/json");
 });
 $("#picker-export-maker-audit").addEventListener("click",()=>{
  if(state.offerAudit)download("worcester-maker-unit-evidence-"+state.domain+".json",
   JSON.stringify(state.offerAudit,null,2)+"\n","application/json");
 });
}
async function main(){
 try{
  const [res,obsRes,retailRes,studyRes,kitRes,cadRes,assetsRes,dimsRes,captureRes,sourceRes]=await Promise.all([
   fetch("../catalog/outdoor_parts_picker.v1.json",{cache:"no-store"}),
   fetch("../catalog/outdoor_supplier_observations.v1.json",{cache:"no-store"}),
   fetch("../catalog/outdoor_retail_comparisons.v1.json",{cache:"no-store"}),
   fetch("../catalog/outdoor_build_studies.v1.json",{cache:"no-store"}),
   fetch("../catalog/outdoor_complete_kit_claims.v1.json",{cache:"no-store"}),
   fetch("../catalog/outdoor_complete_kit_cad_recipes.v1.json",{cache:"no-store"}),
   fetch("../catalog/outdoor_cad_asset_registry.v1.json",{cache:"no-store"}),
   fetch("../catalog/outdoor_cad_dimensional_evidence.v1.json",{cache:"no-store"}),
   fetch("../catalog/outdoor_cad_capture_requirements.v1.json",{cache:"no-store"}),
   fetch("../catalog/outdoor_cad_source_leads.v1.json",{cache:"no-store"})
  ]);
  if(!res.ok||!obsRes.ok||!retailRes.ok||!studyRes.ok||!kitRes.ok||!cadRes.ok||!assetsRes.ok||!dimsRes.ok||!captureRes.ok||!sourceRes.ok)
   throw Error("Cannot load all four source-bound parts, retailer and study registries");
  state.catalog=await res.json();
  state.offerObservations=await obsRes.json();
  state.retailCatalog=await retailRes.json();
  state.studyCatalog=await studyRes.json();
  state.kitClaims=await kitRes.json();
  state.cadRecipe=await cadRes.json();
  state.cadRegistry=await assetsRes.json();
  state.dimensionalEvidence=await dimsRes.json();
  state.captureRequirements=await captureRes.json();
  state.sourceLeadbook=await sourceRes.json();
  validateKitCadRecipe(state.cadRecipe);
  validateCadAssetRegistry(state.cadRegistry);
  validateCadDimensionalEvidence(state.dimensionalEvidence);
  validateCadCaptureRequirements(state.captureRequirements);
  validateCadSourceLeadbook(state.sourceLeadbook);
  const coverage=validatePartsRegistry(state.catalog);
  validateSupplierObservations(state.offerObservations,state.catalog);
  validateRetailRegistry(state.retailCatalog,state.catalog);
  validateBuildStudies(state.studyCatalog,state.catalog);
  validateMakerKitClaims(state.kitClaims,state.catalog);
  $("#picker-coverage").innerHTML='<strong>'+coverage.product_families+' product families</strong> / '+
   coverage.variant_choices+' referenced choices<br>'+
   coverage.suppliers+' supplier directories · '+coverage.source_documents+' maker pages<br>'+
   '<small>Four active sport assembly workflows; no checkout-ready SKU combinations.</small>';
  // Lead with the fully integrated, unqualified Loaded kit research view.
  // Choose by canonical catalog identity, never a hard-coded seller SKU.
  const pilot=state.catalog.products.find(p=>p.id==="loaded-tangent-complete");
  const preset=pilot?.variants?.[0]?.id;
  if(preset)state.selections.long_complete=preset;
  initEvents();renderPrint();refresh();
 }catch(err){
  $("#picker-coverage").textContent="Catalog unavailable: "+err.message;
  $("#picker-order-status").textContent="Unable to create assembly research. No unverified product lists were substituted.";
 }
}
main();
