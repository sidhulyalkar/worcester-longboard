import {validatePartsRegistry,buildPickerStudy} from "./parts_picker_engine.mjs";
import {renderExplodedAssemblySvg} from "./exploded_renderer.mjs";
const $=selector=>document.querySelector(selector);
const esc=x=>String(x??"").replaceAll("&","&amp;").replaceAll("<","&lt;")
 .replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;");
const cleanUrl=value=>{
 try{const u=new URL(value);return u.protocol==="https:"&&!u.username&&!u.password?u.href:null;}
 catch{return null;}
};
const state={catalog:null,domain:"alpine_ski",selections:{},study:null,
 mode:"2d",separation:72,selectedId:null,viewer:null,viewerPromise:null,
 search:""};
const sourceFor=id=>state.catalog.sources.find(s=>s.id===id);
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
 const graph=state.study.graph;
 $("#picker-part-tree").innerHTML=graph.groups.map(g=>{
  const items=graph.components.filter(c=>c.group_id===g.id);
  return '<div><strong>'+esc(g.label)+'</strong><div>'+
   items.map(c=>'<button type="button" data-picker-part="'+esc(c.component_id)+'" aria-pressed="'+
    (c.component_id===state.selectedId?'true':'false')+'">'+esc(c.label)+'</button>').join("")+
   '</div></div>';
 }).join("");
}
function selectPart(id){
 if(!state.study.graph.components.some(x=>x.component_id===id))return;
 state.selectedId=id;
 $("#picker-part-tree").querySelectorAll("[data-picker-part]").forEach(b=>{
  b.setAttribute("aria-pressed",String(b.dataset.pickerPart===id));
 });
 const c=state.study.graph.components.find(x=>x.component_id===id);
 const selected=state.study.selected_variants.find(x=>x.variant_id===id);
 const link=cleanUrl(c.source_url);
 const dims=selected?.dimensions_mm?
  Object.entries(selected.dimensions_mm).map(([k,v])=>esc(k.replaceAll("_"," "))+": "+esc(v)+" mm").join(" · "):
  "Exact dimensions not supplied";
 $("#picker-component-detail").innerHTML='<p><strong>'+esc(c.label)+'</strong></p>'+
  '<p>System: '+esc(c.group_id)+'. Maker: '+esc(c.manufacturer||"Not selected")+
  '. Variant revision / physical interface: <strong>NOT QUALIFIED</strong>.</p>'+
  '<p>Published product envelope (not CAD): '+dims+'</p>'+
  (selected?.inclusion_claim?.length?'<p>Package evidence: '+esc(selected.inclusion_claim.join("; "))+
   '. Contents as received are still unverified.</p>':'')+
  (link?'<p><a href="'+esc(link)+'" target="_blank" rel="noopener noreferrer">View original maker reference ↗</a></p>':
    '<p>This missing reference has no supplier page.</p>');
 redrawVisual();
}
function redrawVisual(){
 const graph=state.study?.graph;
 if(!graph)return;
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
   visual_geometry:"UNSCALED_PROXY_NOT_MEASURED_CAD"},null,2)+"\n","application/json");
 const headers=["Sport","Slot","Variant ID","Requirement","Status","Supplier order units","Notes"];
 const rows=[headers,...state.study.report.rows.map(r=>[
  state.domain,r.label,r.variant_id??"",r.needed,r.status,"UNKNOWN",r.exact_variant_revision_verified?"":"Check exact SKU, package contents and fit"
 ])];
 download("worcester-parts-worklist-"+state.domain+".csv",
  rows.map(row=>row.map(quoteCsv).join(",")).join("\n")+"\n","text/csv;charset=utf-8");
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
  if(!state.study.graph.components.some(x=>x.component_id===state.selectedId))
   state.selectedId=state.study.graph.components[0]?.component_id??null;
  renderSlots();renderOrder();renderVendorDirectory();renderTree();
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
 $("#picker-view-note").textContent="3D is a source-linked size/proportion STUDY, never measured mounting geometry. Rotate with mouse/touch, select parts via the list, or choose a camera preset.";
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
}
async function main(){
 try{
  const res=await fetch("../catalog/outdoor_parts_picker.v1.json",{cache:"no-store"});
  if(!res.ok)throw Error("Cannot load parts registry");
  state.catalog=await res.json();
  const coverage=validatePartsRegistry(state.catalog);
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
+price.displayed_maker_listing_usd.toFixed(2)+
     ' USD ('+esc(price.observed_on)+')</strong> · Not an exact-size quote or cart total.':'')+
    '</div>':
    '<div class="slot-product-evidence">No maker product selected. An unselected or unqualified component cannot be silently added to the cart.</div>')+
   '</article>';
 }).join("");
}
function renderTree(){
 const graph=state.study.graph;
 $("#picker-part-tree").innerHTML=graph.groups.map(g=>{
  const items=graph.components.filter(c=>c.group_id===g.id);
  return '<div><strong>'+esc(g.label)+'</strong><div>'+
   items.map(c=>'<button type="button" data-picker-part="'+esc(c.component_id)+'" aria-pressed="'+
    (c.component_id===state.selectedId?'true':'false')+'">'+esc(c.label)+'</button>').join("")+
   '</div></div>';
 }).join("");
}
function selectPart(id){
 if(!state.study.graph.components.some(x=>x.component_id===id))return;
 state.selectedId=id;
 $("#picker-part-tree").querySelectorAll("[data-picker-part]").forEach(b=>{
  b.setAttribute("aria-pressed",String(b.dataset.pickerPart===id));
 });
 const c=state.study.graph.components.find(x=>x.component_id===id);
 const selected=state.study.selected_variants.find(x=>x.variant_id===id);
 const link=cleanUrl(c.source_url);
 const dims=selected?.dimensions_mm?
  Object.entries(selected.dimensions_mm).map(([k,v])=>esc(k.replaceAll("_"," "))+": "+esc(v)+" mm").join(" · "):
  "Exact dimensions not supplied";
 $("#picker-component-detail").innerHTML='<p><strong>'+esc(c.label)+'</strong></p>'+
  '<p>System: '+esc(c.group_id)+'. Maker: '+esc(c.manufacturer||"Not selected")+
  '. Variant revision / physical interface: <strong>NOT QUALIFIED</strong>.</p>'+
  '<p>Published product envelope (not CAD): '+dims+'</p>'+
  (selected?.inclusion_claim?.length?'<p>Package evidence: '+esc(selected.inclusion_claim.join("; "))+
   '. Contents as received are still unverified.</p>':'')+
  (link?'<p><a href="'+esc(link)+'" target="_blank" rel="noopener noreferrer">View original maker reference ↗</a></p>':
    '<p>This missing reference has no supplier page.</p>');
 redrawVisual();
}
function redrawVisual(){
 const graph=state.study?.graph;
 if(!graph)return;
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
   visual_geometry:"UNSCALED_PROXY_NOT_MEASURED_CAD"},null,2)+"\n","application/json");
 const headers=["Sport","Slot","Variant ID","Requirement","Status","Supplier order units","Notes"];
 const rows=[headers,...state.study.report.rows.map(r=>[
  state.domain,r.label,r.variant_id??"",r.needed,r.status,"UNKNOWN",r.exact_variant_revision_verified?"":"Check exact SKU, package contents and fit"
 ])];
 download("worcester-parts-worklist-"+state.domain+".csv",
  rows.map(row=>row.map(quoteCsv).join(",")).join("\n")+"\n","text/csv;charset=utf-8");
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
  if(!state.study.graph.components.some(x=>x.component_id===state.selectedId))
   state.selectedId=state.study.graph.components[0]?.component_id??null;
  renderSlots();renderOrder();renderVendorDirectory();renderTree();
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
 $("#picker-view-note").textContent="3D is a source-linked size/proportion STUDY, never measured mounting geometry. Rotate with mouse/touch, select parts via the list, or choose a camera preset.";
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
}
async function main(){
 try{
  const res=await fetch("../catalog/outdoor_parts_picker.v1.json",{cache:"no-store"});
  if(!res.ok)throw Error("Cannot load parts registry");
  state.catalog=await res.json();
  const coverage=validatePartsRegistry(state.catalog);
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
+
     entry.indicative_family_price.displayed_maker_listing_usd.toFixed(2)+
     ' USD · reference only</small>':'')+
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
  if(!state.study.graph.components.some(x=>x.component_id===state.selectedId))
   state.selectedId=state.study.graph.components[0]?.component_id??null;
  renderSlots();renderOrder();renderVendorDirectory();renderTree();
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
 $("#picker-view-note").textContent="3D is a source-linked size/proportion STUDY, never measured mounting geometry. Rotate with mouse/touch, select parts via the list, or choose a camera preset.";
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
}
async function main(){
 try{
  const res=await fetch("../catalog/outdoor_parts_picker.v1.json",{cache:"no-store"});
  if(!res.ok)throw Error("Cannot load parts registry");
  state.catalog=await res.json();
  const coverage=validatePartsRegistry(state.catalog);
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
+price.displayed_maker_listing_usd.toFixed(2)+
     ' USD ('+esc(price.observed_on)+')</strong> · Not an exact-size quote or cart total.':'')+
    '</div>':
    '<div class="slot-product-evidence">No maker product selected. An unselected or unqualified component cannot be silently added to the cart.</div>')+
   '</article>';
 }).join("");
}
function renderTree(){
 const graph=state.study.graph;
 $("#picker-part-tree").innerHTML=graph.groups.map(g=>{
  const items=graph.components.filter(c=>c.group_id===g.id);
  return '<div><strong>'+esc(g.label)+'</strong><div>'+
   items.map(c=>'<button type="button" data-picker-part="'+esc(c.component_id)+'" aria-pressed="'+
    (c.component_id===state.selectedId?'true':'false')+'">'+esc(c.label)+'</button>').join("")+
   '</div></div>';
 }).join("");
}
function selectPart(id){
 if(!state.study.graph.components.some(x=>x.component_id===id))return;
 state.selectedId=id;
 $("#picker-part-tree").querySelectorAll("[data-picker-part]").forEach(b=>{
  b.setAttribute("aria-pressed",String(b.dataset.pickerPart===id));
 });
 const c=state.study.graph.components.find(x=>x.component_id===id);
 const selected=state.study.selected_variants.find(x=>x.variant_id===id);
 const link=cleanUrl(c.source_url);
 const dims=selected?.dimensions_mm?
  Object.entries(selected.dimensions_mm).map(([k,v])=>esc(k.replaceAll("_"," "))+": "+esc(v)+" mm").join(" · "):
  "Exact dimensions not supplied";
 $("#picker-component-detail").innerHTML='<p><strong>'+esc(c.label)+'</strong></p>'+
  '<p>System: '+esc(c.group_id)+'. Maker: '+esc(c.manufacturer||"Not selected")+
  '. Variant revision / physical interface: <strong>NOT QUALIFIED</strong>.</p>'+
  '<p>Published product envelope (not CAD): '+dims+'</p>'+
  (selected?.inclusion_claim?.length?'<p>Package evidence: '+esc(selected.inclusion_claim.join("; "))+
   '. Contents as received are still unverified.</p>':'')+
  (link?'<p><a href="'+esc(link)+'" target="_blank" rel="noopener noreferrer">View original maker reference ↗</a></p>':
    '<p>This missing reference has no supplier page.</p>');
 redrawVisual();
}
function redrawVisual(){
 const graph=state.study?.graph;
 if(!graph)return;
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
   visual_geometry:"UNSCALED_PROXY_NOT_MEASURED_CAD"},null,2)+"\n","application/json");
 const headers=["Sport","Slot","Variant ID","Requirement","Status","Supplier order units","Notes"];
 const rows=[headers,...state.study.report.rows.map(r=>[
  state.domain,r.label,r.variant_id??"",r.needed,r.status,"UNKNOWN",r.exact_variant_revision_verified?"":"Check exact SKU, package contents and fit"
 ])];
 download("worcester-parts-worklist-"+state.domain+".csv",
  rows.map(row=>row.map(quoteCsv).join(",")).join("\n")+"\n","text/csv;charset=utf-8");
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
  if(!state.study.graph.components.some(x=>x.component_id===state.selectedId))
   state.selectedId=state.study.graph.components[0]?.component_id??null;
  renderSlots();renderOrder();renderVendorDirectory();renderTree();
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
 $("#picker-view-note").textContent="3D is a source-linked size/proportion STUDY, never measured mounting geometry. Rotate with mouse/touch, select parts via the list, or choose a camera preset.";
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
}
async function main(){
 try{
  const res=await fetch("../catalog/outdoor_parts_picker.v1.json",{cache:"no-store"});
  if(!res.ok)throw Error("Cannot load parts registry");
  state.catalog=await res.json();
  const coverage=validatePartsRegistry(state.catalog);
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
