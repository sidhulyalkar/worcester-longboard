// Separate candidate envelope viewer. Not the board's integrated CAD renderer.
// Native keyboard-accessible angle controls live in parts_picker_app.mjs.
export async function createCandidateMetricViewer(host){
 const local=await fetch("/node_modules/three/build/three.module.js",{method:"HEAD"})
  .then(r=>r.ok).catch(()=>false);
 const [THREE,controlsMod]=await Promise.all(local?[
  import("/node_modules/three/build/three.module.js"),
  import("/node_modules/three/examples/jsm/controls/OrbitControls.js")
 ]:[
  import("https://esm.sh/three@0.180.0"),
  import("https://esm.sh/three@0.180.0/examples/jsm/controls/OrbitControls.js")
 ]);
 const renderer=new THREE.WebGLRenderer({antialias:true,powerPreference:"low-power"});
 renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,2));
 renderer.setClearColor(0x0d202a);
 renderer.outputColorSpace=THREE.SRGBColorSpace;
 renderer.domElement.setAttribute("role","img");
 renderer.domElement.setAttribute("aria-label",
  "Isolated 3D candidate boxes, not a verified manufacturer CAD assembly or clearance test");
 renderer.domElement.dataset.scope="CANDIDATE_METRIC_BOXES_UNVERIFIED";
 host.replaceChildren(renderer.domElement);
 const scene=new THREE.Scene(),root=new THREE.Group();
 scene.add(root);
 scene.add(new THREE.HemisphereLight(0xe5f8ff,0x405060,2.1));
 const keyLight=new THREE.DirectionalLight(0xffffff,2.2);
 keyLight.position.set(20,-30,35);scene.add(keyLight);
 const camera=new THREE.PerspectiveCamera(45,1,0.01,100000);
 const controls=new controlsMod.OrbitControls(camera,renderer.domElement);
 controls.enableDamping=true;controls.enablePan=true;
 const baseGeometry=new THREE.BoxGeometry(1,1,1);
 const edgeGeometry=new THREE.EdgesGeometry(baseGeometry);
 const edges=new THREE.LineBasicMaterial({color:0xc1dce5,transparent:true,opacity:0.85});
 const nodes=new Map();
 let frame=null,settle=0,disposed=false,geometryKey=null,viewKey=null,axis=null;
 function schedule(){
  if(disposed)return;
  settle=18;
  if(frame===null)frame=requestAnimationFrame(render);
 }
 function render(){
  frame=null;
  if(disposed||document.visibilityState==="hidden")return;
  controls.update();renderer.render(scene,camera);
  if(--settle>0&&frame===null)frame=requestAnimationFrame(render);
 }
 controls.addEventListener("change",schedule);
 function resize(){
  if(disposed)return;
  const w=Math.max(1,host.clientWidth),h=Math.max(180,host.clientHeight);
  renderer.setSize(w,h,false);
  camera.aspect=w/h;camera.updateProjectionMatrix();schedule();
 }
 const observer=new ResizeObserver(resize);observer.observe(host);
 function releaseAxis(){
  if(!axis)return;
  root.remove(axis);
  axis.traverse(obj=>{
   obj.geometry?.dispose?.();
   if(Array.isArray(obj.material))for(const mat of obj.material)mat?.dispose?.();
   else obj.material?.dispose?.();
  });
  axis=null;
 }
 function clear(){
  for(const object of nodes.values())object.userData.fill.dispose();
  nodes.clear();
  releaseAxis();
  root.clear();
  geometryKey=null;
 }
 function update(model){
  if(disposed)throw Error("Candidate viewer was disposed");
  if(model?.scope!=="ISOLATED_CANDIDATE_ENVELOPES_NOT_VERIFIED_CAD"||
     model.physical_clearances_verified!==0||
     model.physically_qualified_mates!==0||
     model.actual_manufacturer_geometry_loaded!==false||
     model.approved_for_purchase!==false||
     model.approved_for_fabrication!==false||
     !Array.isArray(model.parts)||model.parts.length<2||model.parts.length>14)
   throw Error("Candidate viewer refuses qualified or malformed geometry");
  const newKey=JSON.stringify([model.kit_variant_id,
   model.parts.map(x=>[x.id,x.dimensions_mm])]);
  if(newKey!==geometryKey){
   clear();geometryKey=newKey;
   for(const p of model.parts){
    const group=new THREE.Group();
    const material=new THREE.MeshStandardMaterial({
     color:p.is_moving?0x83c8db:0xa4b5c6,transparent:true,
     opacity:0.69,roughness:0.72,metalness:0.12,depthWrite:false
    });
    const mesh=new THREE.Mesh(baseGeometry,material);
    mesh.scale.set(...p.dimensions_mm);
    const outline=new THREE.LineSegments(edgeGeometry,edges);
    outline.scale.set(...p.dimensions_mm);
    group.add(mesh,outline);
    group.userData.fill=material;group.userData.partId=p.id;
    nodes.set(p.id,group);root.add(group);
   }
  }
  const b=model.view_bounds_mm;
  if(!b||b.min_mm?.length!==3||b.max_mm?.length!==3||
     ![...b.min_mm,...b.max_mm].every(Number.isFinite))
   throw Error("Candidate 3D requires bounded survey view coordinates");
  const fitKey=JSON.stringify([model.kit_variant_id,newKey,b]);
  if(viewKey!==fitKey){
   viewKey=fitKey;
   const center=new THREE.Vector3(...b.min_mm.map((v,i)=>(v+b.max_mm[i])/2));
   const radius=Math.max(new THREE.Vector3(...b.min_mm.map((v,i)=>
    b.max_mm[i]-v)).length(),8);
   controls.target.copy(center);
   camera.position.copy(center).add(new THREE.Vector3(radius*1.2,radius*1.3,radius*1.5));
   camera.near=Math.max(radius/10000,0.001);
   camera.far=Math.max(radius*50,100);
   camera.updateProjectionMatrix();controls.update();
  }
  for(const p of model.parts){
   const node=nodes.get(p.id);
   node.position.set(...p.center_mm);
   const r=p.rotation_rows;
   const matrix=new THREE.Matrix4().set(
    r[0][0],r[0][1],r[0][2],0,
    r[1][0],r[1][1],r[1][2],0,
    r[2][0],r[2][1],r[2][2],0,
    0,0,0,1);
   node.quaternion.setFromRotationMatrix(matrix);
   node.userData.fill.color.setHex(
    p.potential_overlap_at_sample?0xe8a176:
    p.is_moving?0x83c8db:0xa4b5c6);
  }
  releaseAxis();
  if(model.axis_point_mm&&model.axis_direction){
   const direction=new THREE.Vector3(...model.axis_direction).normalize();
   const radius=Math.max(4,...model.parts.flatMap(p=>p.dimensions_mm));
   const pivot=new THREE.Vector3(...model.axis_point_mm);
   const points=[
    pivot.clone().addScaledVector(direction,-radius*.6),
    pivot.clone().addScaledVector(direction,radius*.6)];
   axis=new THREE.Line(new THREE.BufferGeometry().setFromPoints(points),
    new THREE.LineBasicMaterial({color:0xf1d39c}));
   root.add(axis);
  }
  renderer.domElement.dataset.kitVariantId=model.kit_variant_id;
  renderer.domElement.dataset.sampleIndex=String(model.sample_index);
  renderer.domElement.dataset.sampleAngleDeg=String(model.angle_deg);
  renderer.domElement.dataset.candidatePartCount=String(nodes.size);
  renderer.domElement.dataset.possibleOverlapPairs=String(model.possible_overlap_pairs);
  renderer.domElement.dataset.physicalClearancesVerified="0";
  renderer.domElement.dataset.manufacturerCadLoaded="false";
  resize();
 }
 resize();
 return {update,dispose(){
  if(disposed)return;
  disposed=true;observer.disconnect();controls.dispose();
  if(frame!==null)cancelAnimationFrame(frame);
  clear();baseGeometry.dispose();edgeGeometry.dispose();edges.dispose();
  renderer.dispose();host.replaceChildren();
 }};
}
