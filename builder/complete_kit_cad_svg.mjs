// Scalable vector fallback for the SAME parametric assembled/exploded visual
// model used by Three.js. Display geometry is unmeasured and non-fabricable.
import {planCadDisplay} from "./complete_kit_cad_schema.mjs";
const esc=x=>String(x??"").replaceAll("&","&amp;").replaceAll("<","&lt;")
 .replaceAll(">","&gt;").replaceAll('"',"&quot;");
const color={
 deck:"#48738a",zee_brackets:"#d1a16b",trucks:"#aabcc2",
 wheels:"#8fbea9",bearings:"#ead7ad",
 deck_hardware:"#e0b17b",truck_hardware:"#bca4d7"
};
export function renderCompleteKitCadSvg(cad,{explode=0,selectedId=null}={}){
 const plan=planCadDisplay(cad,explode,selectedId);
 const t=plan.separation_percent/100,scale=64/(1+0.55*t);
 const at=(instance,offset)=>{
  const x=instance.at[0]+offset[0];
  const y=instance.at[1]+offset[1];
  return [520+(x+0.24*offset[2])*scale,310+(y-0.44*offset[2])*scale];
 };
 const fmt=n=>Number(n).toFixed(1);
 // Wheels, bearings and trucks should be behind the deck when fully joined.
 // The layer order is display-only and never indicates mechanical assembly order.
 const paintOrder=["wheels","bearings","trucks","zee_brackets","deck",
  "deck_hardware","truck_hardware"];
 let shapes="";
 for(const role of paintOrder){
  const part=cad.children.find(x=>x.role===role);
  const pose=plan.parts.find(x=>x.component_id===part.component_id);
  const col=color[role];
  const opacity=pose.visible?1:0;
  let path="";
  for(const el of part.instances){
   const [x,y]=at(el,pose.position);
   const rx=r=>fmt(r*scale);
   const rectangle=(width,height,r=5)=>
    '<rect x="'+fmt(x-width*scale/2)+'" y="'+fmt(y-height*scale/2)+
    '" width="'+fmt(width*scale)+'" height="'+fmt(height*scale)+
    '" rx="'+r+'" fill="'+col+'" stroke="#172935" stroke-width="2"/>';
   switch(role){
    case "deck":{
     const w=el.size[0]*scale,l=el.size[1]*scale;
     path+='<rect x="'+fmt(x-w/2)+'" y="'+fmt(y-l/2)+'" width="'+fmt(w)+
       '" height="'+fmt(l)+'" rx="'+fmt(0.36*scale)+
       '" fill="'+col+'" stroke="#b4d3de" stroke-width="3"/>'+
       '<rect x="'+fmt(x-w*0.40)+'" y="'+fmt(y-l*0.46)+'" width="'+fmt(w*0.8)+
       '" height="'+fmt(l*0.92)+'" rx="'+fmt(0.23*scale)+
       '" fill="#173645" opacity=".78"/>';
     break;
    }
    case "zee_brackets":
     path+=rectangle(1.65,0.32,7)+
      '<rect x="'+fmt(x-0.62*scale)+'" y="'+fmt(y-0.28*scale)+
      '" width="'+fmt(1.24*scale)+'" height="'+fmt(0.56*scale)+
      '" fill="none" stroke="#f1c78a" stroke-width="3" rx="6"/>';
     break;
    case "trucks":
     path+=rectangle(3.02,0.13,4)+rectangle(0.48,0.45,8);break;
    case "wheels":
     path+='<circle cx="'+fmt(x)+'" cy="'+fmt(y)+'" r="'+rx(el.radius)+
      '" fill="'+col+'" stroke="#173d39" stroke-width="5"/>'+
      '<circle cx="'+fmt(x)+'" cy="'+fmt(y)+'" r="'+rx(el.radius*.39)+
      '" fill="#345e5b" stroke="#d4e0cd" stroke-width="2"/>';
     break;
    case "bearings":
     path+='<circle cx="'+fmt(x)+'" cy="'+fmt(y)+'" r="'+rx(el.radius)+
      '" fill="none" stroke="'+col+'" stroke-width="4"/>';
     break;
    default:
     path+='<path d="M'+fmt(x)+' '+fmt(y-22)+'V'+fmt(y+17)+
      '" stroke="'+col+'" stroke-width="7" stroke-linecap="round"/>'+
      '<circle cx="'+fmt(x)+'" cy="'+fmt(y-22)+
      '" r="11" fill="'+col+'" stroke="#273541" stroke-width="3"/>';
   }
  }
  const active=part.component_id===selectedId;
  const primary=part.instances[0];
  const [px,py]=at(primary,pose.position);
  const border=active?
   '<circle cx="'+fmt(px)+'" cy="'+fmt(py)+'" r="'+
   (role==="deck"?60:role==="wheels"?53:43)+
   '" fill="none" stroke="#fcce79" stroke-dasharray="5 6" stroke-width="3"/>':"";
  const label=t>0.22?
   '<g pointer-events="none"><rect x="'+fmt(px-86)+'" y="'+fmt(py+54)+
   '" width="172" height="23" rx="6" fill="#142732" stroke="'+col+'"/>'+
   '<text x="'+fmt(px)+'" y="'+fmt(py+70)+
   '" text-anchor="middle" font-family="system-ui" font-size="11" fill="#f0f8fa">'+
   esc(part.label.slice(0,26))+'</text></g>':"";
  shapes+='<g data-exploded-part="'+esc(part.component_id)+
   '"'+(active?' class="exploded-active-part"':'')+
   ' opacity="'+opacity+'">'+border+path+label+'</g>';
 }
 return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1040 620" '+
  'class="exploded-assembly-svg" role="img" aria-label="Integrated source-listed longboard, '+
  cad.child_count+' unverified assembly categories; '+plan.separation_percent+
  ' percent schematic separation; mounting coordinates not measured">'+
  '<rect width="1040" height="620" rx="18" fill="#0e1b25"/>'+
  '<path d="M110 310H930 M520 38V580" stroke="#426072" stroke-width="1" stroke-dasharray="4 8" opacity=".25"/>'+
  shapes+
  '<rect x="18" y="15" rx="9" width="420" height="54" fill="#152b39" stroke="#3b667a"/>'+
  '<text x="32" y="37" font-family="system-ui" font-size="14" fill="#e5f0f6">'+
   (t===0?"INTEGRATED BOARD · SCHEMATIC":"EXPLODED COMPONENTS · SCHEMATIC")+
  '</text><text x="32" y="54" font-family="system-ui" font-size="10" fill="#c7d4db">'+
  'Model-relative coordinates only · no qualified mounts or clearances</text>'+
  '<text x="30" y="596" font-family="system-ui" font-size="11" fill="#bdcbd4">'+
  esc("Published board envelope "+cad.published_dimensions_mm.complete_length+
  " × "+cad.published_dimensions_mm.complete_width+
  " mm | Wheel "+cad.published_dimensions_mm.wheel_diameter+
  " mm (values are source claims, not CAD datums)")+'</text></svg>';
}
