// Opt-in local GLB inspection. This canvas is isolated from the complete-board
// assembly: no automatic mating, metric transforms or replacement of kit proxies.
import {inspectGlbBytes} from "./cad_glb_contract.mjs";
export async function createLocalCadInspector(host){
 const local=await fetch("/node_modules/three/build/three.module.js",
  {method:"HEAD"}).then(r=>r.ok).catch(()=>false);
 const [THREE,controlsMod,loaderMod]=await Promise.all(local?[
  import("/node_modules/three/build/three.module.js"),
  import("/node_modules/three/examples/jsm/controls/OrbitControls.js"),
  import("/node_modules/three/examples/jsm/loaders/GLTFLoader.js")
 ]:[
  import("https://esm.sh/three@0.180.0"),
  import("https://esm.sh/three@0.180.0/examples/jsm/controls/OrbitControls.js"),
  import("https://esm.sh/three@0.180.0/examples/jsm/loaders/GLTFLoader.js")
 ]);
 const renderer=new THREE.WebGLRenderer({antialias:true,powerPreference:"low-power"});
 renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,2));
 renderer.setClearColor(0x0e1b25);
 renderer.outputColorSpace=THREE.SRGBColorSpace;
 renderer.domElement.setAttribute("role","img");
 renderer.domElement.setAttribute("aria-label",
  "Locally loaded unverified GLB geometry, not aligned with the complete board");
 renderer.domElement.setAttribute("data-cad-inspection","ISOLATED_NOT_ASSEMBLED");
 host.replaceChildren(renderer.domElement);
 const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(45,1,.01,10000);
 scene.add(new THREE.HemisphereLight(0xf4f7ff,0x344454,2.5));
 const directional=new THREE.DirectionalLight(0xffffff,2.3);
 directional.position.set(4,8,11);scene.add(directional);
 const controls=new controlsMod.OrbitControls(camera,renderer.domElement);
 controls.enableDamping=true;controls.enablePan=true;
 const loader=new loaderMod.GLTFLoader();
 let model=null,frame=null,disposed=false,generation=0;
 const schedule=()=>{
  if(disposed||frame!==null)return;
  frame=requestAnimationFrame(render);
 };
 function render(){
  frame=null;if(disposed||document.visibilityState==="hidden")return;
  controls.update();renderer.render(scene,camera);
  if(controls.enableDamping)frame=requestAnimationFrame(render);
 }
 const resize=()=>{
  if(disposed)return;
  const w=Math.max(host.clientWidth,1),h=Math.max(host.clientHeight,200);
  renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();
  schedule();
 };
 const observer=new ResizeObserver(resize);observer.observe(host);
 function clear(){
  if(model){
   scene.remove(model);
   model.traverse(o=>{
    if(o.geometry)o.geometry.dispose();
    const mats=Array.isArray(o.material)?o.material:[o.material];
    for(const mat of mats)mat?.dispose?.();
   });
   model=null;
  }
 }
 async function load(data){
  const details=inspectGlbBytes(data);
  const ticket=++generation;
  const result=await loader.parseAsync(data.slice(0),"");
  if(disposed||ticket!==generation){
   result.scene.traverse(o=>{o.geometry?.dispose?.();});
   return null;
  }
  const bounds=new THREE.Box3().setFromObject(result.scene);
  const size=bounds.getSize(new THREE.Vector3());
  const center=bounds.getCenter(new THREE.Vector3());
  if(bounds.isEmpty()||![size.x,size.y,size.z,center.x,center.y,center.z]
     .every(Number.isFinite)||Math.max(size.x,size.y,size.z)>1e7)
   throw Error("GLB inspection: invalid or extreme mesh bounds");
  clear();model=result.scene;scene.add(model);
  const radius=Math.max(size.length()*0.5,0.0001);
  controls.target.copy(center);
  camera.near=Math.max(radius/10000,0.000001);
  camera.far=Math.max(radius*100,10);
  camera.position.copy(center).add(new THREE.Vector3(radius*1.7,radius*1.5,radius*1.8));
  camera.updateProjectionMatrix();controls.update();resize();
  renderer.domElement.dataset.meshCount=String(details.mesh_count);
  renderer.domElement.dataset.fitAuthority="NONE";
  return {...details,bounds_in_file_units:{
   x:size.x,y:size.y,z:size.z,
   label:"Native GLB coordinate units only; no mm conversion"}};
 }
 resize();
 return {load,dispose(){
  generation++;disposed=true;observer.disconnect();controls.dispose();
  if(frame!==null)cancelAnimationFrame(frame);
  clear();renderer.dispose();host.replaceChildren();
 }};
}
