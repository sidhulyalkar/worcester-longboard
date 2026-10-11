// Standalone deterministic SVG renderer for semantic exploded assemblies.
// Geometry, offsets, and silhouettes are intentional schematic proxies, never CAD.
const esc=value=>String(value??"").replaceAll("&","&amp;").replaceAll("<","&lt;")
 .replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;");
const clamped=n=>Math.max(0,Math.min(100,Number.isFinite(Number(n))?Number(n):0));
const colors={
 platform:"#75b8d4",mount:"#efb77a",ground:"#96c9a6",
 rider:"#b4a2e4",control:"#e69c98",power:"#9bb2f3",utility:"#c8c5a0"
};
function hull(domain){
 if(domain==="alpine_ski")
  return '<path d="M-27 -84Q-33 -98-36-84L-36 87Q-36 102-30 86L-25-83Z M25 -84Q31-98 34-84L34 87Q34 102 28 86L23-83Z" fill="#34556c" stroke="#9bd0e9" stroke-width="2"/>';
 if(domain==="splitboard")
  return '<path d="M-4 -88Q-65 -98-55-60L-55 62Q-60 93-4 86Z M4 -88Q65-98 55-60L55 62Q60 93 4 86Z" fill="#35556d" stroke="#9bd0e9" stroke-width="2"/>';
 if(domain==="surfboard")
  return '<path d="M0 -102C-68-36-68 43 0 101C68 43 68-36 0-102Z" fill="#34566c" stroke="#9bd0e9" stroke-width="2"/>';
 const narrow=domain==="skateboard_longboard";
 return '<path d="M'+(narrow?-34:-54)+' -89Q0 -115 '+(narrow?34:54)+' -89L'+
  (narrow?34:54)+' 70Q0 112 '+(narrow?-34:-54)+' 70Z" fill="#34566c" stroke="#9bd0e9" stroke-width="2"/>';
}
function symbol(node,domain){
 const role=node.role,grp=node.group_id,col=colors[grp]||"#a7ced7";
 const style='fill="none" stroke="'+col+'" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"';
 if(grp==="platform")return hull(domain);
 if(grp==="mount"){
  if(["puck_or_mounting_kit","mounting_disc","touring_pivot"].includes(role))
   return '<circle r="30" '+style+'/><circle r="12" '+style+'/><path d="M-30 0H30M0-30V30" '+style+'/>';
  return '<path d="M-56 0H56M-38-22L-18 0 0 12 18 0 38-22M-43 16H43" '+style+
    '/><circle cx="-47" r="8" '+style+'/><circle cx="47" r="8" '+style+'/>';
 }
 if(grp==="ground"){
  if(role==="fin_set")
   return '<path d="M-33 29Q-29-12 29-38L36 29Z" fill="'+col+'" fill-opacity=".24" '+style+'/>';
  if(role==="skin_pair")
   return '<path d="M-20-43V43M20-43V43" '+style+'/><path d="M-26-35H-14M14-35H26M-26 35H-14M14 35H26" '+style+'/>';
  return '<circle r="38" '+style+'/><circle r="25" '+style+'/><circle r="12" '+style+
    '/><path d="M-28-28L28 28M-28 28L28-28" '+style+'/>';
 }
 if(grp==="rider"){
  if(["griptape","traction_pad"].includes(role))
   return '<rect x="-44" y="-60" width="88" height="120" rx="23" '+style+
    '/><path d="M-31-34H31M-31-16H31M-31 4H31M-31 24H31M-31 42H31" stroke="'+col+'" opacity=".45"/>';
  return '<path d="M-45 30L-33-29Q-30-50-12-47L21-40Q51-32 47 5L25 35Q-7 51-45 30Z" '+style+
    '/><path d="M-33-11L38-2M-28 10L29 17" '+style+'/>';
 }
 if(grp==="control")
  return '<circle cx="-18" cy="0" r="29" '+style+'/><circle cx="-18" cy="0" r="13" '+style+
   '/><path d="M15-40L46-20V22L15 40M15-40V40M18-24H42M18 22H42" '+style+'/>';
 if(grp==="power")
  return '<rect x="-47" y="-32" width="94" height="64" rx="10" '+style+
   '/><path d="M-27-10H27M-27 10H27M0-30V-43M-14-43H14" '+style+'/>';
 return '<path d="M-30 -32H30L42 0 30 32H-30L-42 0Z" '+style+
  '/><path d="M-15 0H15M0-14V14" '+style+'/>';
}
const SVG_WIDTH=1060,SVG_HEIGHT=620;
const positions=(graph,explode)=>{
 const t=clamped(explode)/100;
 const active=graph.groups;
 const map=new Map(active.map(g=>[g.id,g]));
 return graph.components.map((node,i)=>{
  const group=map.get(node.group_id);
  const members=graph.components.filter(x=>x.group_id===group.id);
  const index=members.findIndex(x=>x.component_id===node.component_id);
  const spreading=(index-(members.length-1)/2);
  const y=310+group.vector[1]*173*t+spreading*58*t+
    (group.id==="platform"?0:group.vector[1]*26*(1-t));
  const x=530+group.vector[0]*205*t+
    (members.length>1?spreading*28*t:0)+
    (group.id==="platform"?0:group.vector[0]*35*(1-t));
  return {...node,x,y,group};
 });
};
export function renderExplodedAssemblySvg(graph,{explode=75,selectedId=null}={}){
 if(graph?.scope!=="UNQUALIFIED_SEMANTIC_ASSEMBLY_EXPLODED_VIEW" ||
   !Array.isArray(graph.components))throw new Error("Expected semantic assembly graph");
 const t=clamped(explode),nodes=positions(graph,t);
 const nodelist=nodes.map(node=>{
  const active=node.component_id===selectedId;
  const col=colors[node.group_id]||"#b5d6e2";
  const label=node.label.length>31?node.label.slice(0,28)+"…":node.label;
  const scale=node.group_id==="platform" ? 1 : .67;
  return '<g data-exploded-part="'+esc(node.component_id)+'"'+
   (active?' class="exploded-active-part"':'')+'>'+
    (active?'<circle cx="'+node.x+'" cy="'+node.y+'" r="91" fill="'+col+'" fill-opacity=".12" stroke="'+col+'" stroke-dasharray="5 6"/>':'')+
    '<g transform="translate('+node.x.toFixed(2)+' '+node.y.toFixed(2)+') scale('+scale+')">'+
      symbol(node,graph.domain_id)+'</g>'+
    (t>14?'<g font-family="system-ui,sans-serif"><rect x="'+(node.x-93).toFixed(1)+'" y="'+(node.y+(node.group_id==="platform"?99:49)).toFixed(1)+
     '" width="186" height="26" rx="7" fill="#142632" stroke="'+col+'" stroke-opacity=".55"/>'+
     '<text x="'+node.x.toFixed(1)+'" y="'+(node.y+(node.group_id==="platform"?116:66)).toFixed(1)+
     '" text-anchor="middle" font-size="10.5" font-weight="'+(active?700:500)+
     '" fill="#eaf4f8">'+esc(label)+'</text></g>':'')+
    '</g>';
 });
 const lines=nodes.filter(x=>x.group_id!=="platform").map(n=>
  '<path d="M530 310L'+n.x.toFixed(2)+' '+n.y.toFixed(2)+
  '" stroke="'+colors[n.group_id]+'" stroke-dasharray="4 7" stroke-opacity=".28" fill="none"/>').join("");
 const grid=Array.from({length:14},(_,i)=>'<path d="M'+(50+i*74)+' 0V620" stroke="#ffffff" stroke-opacity=".035"/>').join("")+
  Array.from({length:9},(_,i)=>'<path d="M0 '+(44+i*70)+'H1060" stroke="#ffffff" stroke-opacity=".035"/>').join("");
 const stat=graph.origin==="ILLUSTRATIVE_DOMAIN_RECIPE"?"UNSOURCED SPORT CONCEPT":"SOURCE-BOUND BOARD STUDY";
 const legend=graph.groups.map((g,i)=>'<g transform="translate('+(30+i%4*252)+' '+(558+Math.floor(i/4)*20)+')">'+
  '<circle r="4" fill="'+colors[g.id]+'"/><text x="11" y="4" font-size="11" fill="#b9cbd7">'+
  esc(g.label)+'</text></g>').join("");
 return '<svg class="exploded-assembly-svg" viewBox="0 0 '+SVG_WIDTH+' '+SVG_HEIGHT+
  '" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="'+esc(graph.label)+
  ' conceptual assembly diagram at '+t+' percent separation, with '+nodes.length+
  ' unverified component references">'+
  '<rect width="1060" height="620" rx="18" fill="#0e1b25"/>'+grid+
  '<text x="30" y="31" font-size="17" font-family="system-ui" font-weight="650" fill="#e7f3f7">'+
  esc(graph.label)+'</text>'+
  '<text x="30" y="52" font-size="11" fill="#9cafbc" font-family="system-ui">'+
  esc(stat)+' · '+t+'% separated · NOT ASSEMBLY GEOMETRY</text>'+
  '<rect x="818" y="17" width="214" height="27" rx="8" fill="#3d3030" stroke="#ad8080"/>'+
  '<text x="925" y="35" text-anchor="middle" font-size="11" fill="#f2c1b6" font-family="system-ui">PHYSICAL FIT UNVERIFIED</text>'+
  '<g opacity=".19" transform="translate(530 310) scale(.72)">'+hull(graph.domain_id)+'</g>'+
  lines+nodelist.join("")+
  '<path d="M25 539H1035" stroke="#507082" stroke-opacity=".45"/>'+legend+
  '<text x="1028" y="610" font-family="system-ui" font-size="10" fill="#9cafbc" text-anchor="end">Visual proxies · No quantity or installation approval</text>'+
  '</svg>';
}
