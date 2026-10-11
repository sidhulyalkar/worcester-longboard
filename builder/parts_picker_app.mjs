import {validatePartsRegistry,buildPickerStudy} from "./parts_picker_engine.mjs";
import {renderExplodedAssemblySvg} from "./exploded_renderer.mjs";
import {validateSupplierObservations,auditMakerOrderUnits} from "./offer_qualification.mjs";
import {validateRetailRegistry,validateBuildStudies,compareRetailOffers,
 researchRelatedSellerListings,composeResearchAlternatives} from "./retail_build_comparison.mjs";
import {validateMakerKitClaims,auditCompleteKitClaim} from "./complete_kit_closure.mjs";
import {buildCompleteKitVisualGraph} from "./complete_kit_visual_graph.mjs";
const $=selector=>document.querySelector(selector);
const esc=x=>String(x??"").replaceAll("&","&amp;").replaceAll("<","&lt;")
 .replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;");
const cleanUrl=value=>{
 try{const u=new URL(value);return u.protocol==="https:"&&!u.username&&!u.password?u.href:null;}
 catch{return null;}
};
const state={catalog:null,offerObservations:null,offerAudit:null,
 retailCatalog:null,studyCatalog:null,alternatives:null,kitClaims:null,kitAudit:null,visualGraph:null,
 domain:"alpine_ski",selections:{},study:null,
 mode:"2d",separation:72,selectedId:null,viewer:null,viewerPromise:null,
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
 $("#picker-rendered-scene-status").textContent=kit?
  graph.components.length+" distinct maker-advertised kit component categories · "+
  "0 received/verified pieces · unmeasured 2D/3D visual proxies · one parent package":
  graph.components.length+" source-family component reference(s) · unmeasured visual proxies";
 const host=$("#picker-visual-svg");
 host.innerHTML=renderExplodedAssemblySvg(graph,{explode:state.separation,
  selectedId:state.selectedId});
 host.querySelectorAll("[data-exploded-part]").forEach(part=>
  part.addEventListener("click",()=>selectPart(part.getAttribute("data-exploded-part"))));
 $("#picker-explode-output").textContent=state.separation+"%";
 if(state.mode==="3d"&&state.viewer){
  try{state.viewer.update(graph,state.separation,state.selectedId,null,state.study.selected_variants);}
  catch(error){fallbackTo2D("3D study could not render this selection. SVG fallback remains available.");}
 }
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
  return '<tr><td><strong>'+esc(r.label)+'</strong><small>'+esc(r.child_id)+'</small></td>'+
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
   '<p>Each manufacturer-advertised component category now has its own selectable, explodable 2D/3D visual proxy. No shape, position, mate or fastener pattern is measured CAD. All seven stable child IDs are included in the review JSON export.</p>';
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
  state.selectedId=null;
  state.search="";
  $("#picker-search").value="";
  refresh();
 });
 $("#picker-explode").addEventListener("input",e=>{state.separation=Number(e.target.value);redrawVisual();});
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
  const [res,obsRes,retailRes,studyRes,kitRes]=await Promise.all([
   fetch("../catalog/outdoor_parts_picker.v1.json",{cache:"no-store"}),
   fetch("../catalog/outdoor_supplier_observations.v1.json",{cache:"no-store"}),
   fetch("../catalog/outdoor_retail_comparisons.v1.json",{cache:"no-store"}),
   fetch("../catalog/outdoor_build_studies.v1.json",{cache:"no-store"}),
   fetch("../catalog/outdoor_complete_kit_claims.v1.json",{cache:"no-store"})
  ]);
  if(!res.ok||!obsRes.ok||!retailRes.ok||!studyRes.ok||!kitRes.ok)
   throw Error("Cannot load all four source-bound parts, retailer and study registries");
  state.catalog=await res.json();
  state.offerObservations=await obsRes.json();
  state.retailCatalog=await retailRes.json();
  state.studyCatalog=await studyRes.json();
  state.kitClaims=await kitRes.json();
  const coverage=validatePartsRegistry(state.catalog);
  validateSupplierObservations(state.offerObservations,state.catalog);
  validateRetailRegistry(state.retailCatalog,state.catalog);
  validateBuildStudies(state.studyCatalog,state.catalog);
  validateMakerKitClaims(state.kitClaims,state.catalog);
  $("#picker-coverage").innerHTML='<strong>'+coverage.product_families+' product families</strong> / '+
   coverage.variant_choices+' referenced choices<br>'+
   coverage.suppliers+' supplier directories · '+coverage.source_documents+' maker pages<br>'+
   '<small>Four active sport assembly workflows; no checkout-ready SKU combinations.</small>';
  initEvents();renderPrint();refresh();
 }catch(err){
  $("#picker-coverage").textContent="Catalog unavailable: "+err.message;
  $("#picker-order-status").textContent="Unable to create assembly research. No unverified product lists were substituted.";
 }
}
main();
