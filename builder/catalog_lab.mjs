import {buildOutdoorCatalogGraph} from "./outdoor_catalog_graph.mjs";
const byId=id=>document.getElementById(id);
const esc=x=>String(x??"").replaceAll("&","&amp;").replaceAll("<","&lt;")
  .replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#039;");
const sourceLink=x=>{
 if(typeof x!=="string")return "";
 try{const url=new URL(x);if(url.protocol!=="https:"||url.username||url.password)return "";}catch{return "";}
 return '<a href="'+esc(x)+'" target="_blank" rel="noopener noreferrer">Supplier reference <span aria-hidden="true">↗</span></a>';
};
async function loadJson(path) {
 const response=await fetch(path,{cache:"no-store"});
 if(!response.ok)throw new Error("Could not load "+path);
 return response.json();
}
function renderDomains(registry){
 const labels={mountainboard:"🛹",skateboard_longboard:"🛹",snowboard:"🏂",alpine_ski:"🎿",touring_ski:"⛰️",splitboard:"🏔️",surfboard:"🏄",bicycle:"🚵",camping_shelter:"⛺"};
 byId("catalog-domains").innerHTML=registry.domains.map(domain=>{
  const current=domain.stage==="CURRENT_LEGACY_ADAPTER";
  return '<div class="domain'+(current?' current':'')+'"><div class="domain-top"><span aria-hidden="true">'+
   esc(labels[domain.id]??"⚙️")+'</span><small>'+esc(current?"Catalog references loaded":"Planned domain")+'</small></div>'+
   '<strong>'+esc(domain.label)+'</strong><p>'+esc(domain.required_roles.slice(0,4).join(" · "))+
   '</p><small>'+esc(domain.interface_type_ids.length)+' typed compatibility interfaces</small></div>';
 }).join("");
}
function render(graph){
 const offers=new Map(graph.supplier_offer_references.map(x=>[x.variant_id,x]));
 const snapshots=new Map(graph.source_snapshots.map(x=>[x.id,x]));
 const packages=new Map(graph.sellable_package_hypotheses.map(x=>[x.container_variant_id,x]));
 const roles=[...new Set(graph.variants.map(x=>x.component_role))].sort();
 byId("catalog-role").innerHTML='<option value="">All roles</option>'+roles.map(role=>
  '<option value="'+esc(role)+'">'+esc(role.replaceAll("_"," "))+'</option>').join("");
 const summary=graph.summary;
 byId("catalog-stats").innerHTML=[
  [summary.provisional_variants,"Provisional part references"],
  [summary.dated_supplier_references,"Dated seller references"],
  [summary.catalog_interface_claims,"Raw interface claims"],
  [summary.orderable_kits,"Verified orderable kits"],
 ].map(([number,label])=>'<div class="stat"><strong>'+esc(number)+'</strong><span>'+esc(label)+'</span></div>').join("");
 const search=()=>{
  const q=byId("catalog-query").value.trim().toLowerCase();
  const role=byId("catalog-role").value;
  const source=byId("catalog-source").value;
  const visible=graph.variants.filter(v=>{
   const family=graph.families.find(x=>x.id===v.family_id);
   const offer=offers.get(v.id);
   const haystack=[v.legacy_component_id,v.legacy_category,v.component_role,
     v.sku_text,family?.name,family?.manufacturer].join(" ").toLowerCase();
   return (!q||haystack.includes(q))&&(!role||role===v.component_role)&&
    (!source||(source==="dated"&&!!offer)||(source==="planning"&&!offer));
  });
  byId("catalog-filter-status").textContent=visible.length+" of "+graph.variants.length+
    " provisional catalog references shown. None are revision-qualified or orderable.";
  byId("catalog-results").innerHTML=visible.map(v=>{
   const family=graph.families.find(x=>x.id===v.family_id);
   const offer=offers.get(v.id),snapshot=snapshots.get(v.source_snapshot_id);
   const pkg=packages.get(v.id);
   const claims=graph.engineering_claims.filter(x=>x.variant_id===v.id);
   const details='<details><summary>View '+claims.length+' source fields and open questions</summary>'+
     '<dl>'+claims.slice(0,12).map(c=>'<div><dt>'+esc(c.interface_field)+'</dt><dd>'+
       esc(JSON.stringify(c.raw_catalog_value))+
       (c.raw_value_units?' '+esc(c.raw_value_units):'')+'</dd></div>').join("")+
     '</dl>'+(claims.length>12?'<p>More source fields available in the raw catalog.</p>':'')+
     (pkg?'<p class="hold">Donor content claims ('+pkg.items.length+
       ') are not verified inventory: '+esc(pkg.items.map(x=>x.inclusion_token).join(", "))+'</p>':'')+
     '<p>Engineering fields are reference claims, not physical fit qualification.</p></details>';
   return '<article class="component"><div class="component-head"><div><small>'+
     esc(v.component_role.replaceAll("_"," "))+'</small><h3>'+esc(family?.name)+'</h3></div>'+
     '<span class="status">'+esc(offer?"Dated seller reference":"Source only")+'</span></div>'+
     '<p class="subtitle">'+esc(family?.manufacturer??"Manufacturer not established")+
     ' · '+esc(v.legacy_component_id)+'</p>'+
     '<p><strong>SKU:</strong> '+esc(v.sku_text??"Not established")+
     ' <small>('+esc(v.sku_resolution.replaceAll("_"," ").toLowerCase())+')</small></p>'+
     '<p><strong>Offer:</strong> '+(offer?'Snapshot '+esc(offer.dated_as_of)+
       ' · Price reference factor '+esc(offer.catalog_price_qty_factor??"unknown"):
       'No qualifying seller snapshot')+
     '</p><p><strong>Actual order unit:</strong> Unknown · <strong>Revision:</strong> Unverified</p>'+
     (snapshot?.source_url?'<p>'+sourceLink(snapshot.source_url)+'</p>':'')+
     details+'</article>';
  }).join("")||'<p class="empty">No catalog references match these filters.</p>';
 };
 for(const name of ["catalog-query","catalog-role","catalog-source"])
  byId(name).addEventListener(name==="catalog-query"?"input":"change",search);
 byId("catalog-filters").addEventListener("submit",e=>e.preventDefault());
 search();
}
async function main(){
 try{
  const [catalog,domains,packages]=await Promise.all([
    loadJson("../catalog/board_components.v1.json"),
    loadJson("../catalog/outdoor_equipment_domains.v0.json"),
    loadJson("../catalog/board_package_inclusions.v1.json")
  ]);
  const graph=buildOutdoorCatalogGraph(catalog,domains,packages);
  renderDomains(domains);render(graph);
 }catch(error){
  byId("catalog-filter-status").textContent="Catalog explorer unavailable: "+error.message;
  byId("catalog-stats").textContent="Unable to verify local catalog references.";
 }
}
main();
