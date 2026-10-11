// Optional orbitable 3D representation of the SAME source-aware assembly graph.
// Three.js only loads when a user selects 3D; the semantic SVG remains the fallback.
import {planExplodedScene} from "./exploded_scene_model.mjs";
const PALETTE={platform:0x496f89,mount:0xe9b475,ground:0x85bda0,
 rider:0xbca8e8,control:0xe79c94,power:0x9baef0,utility:0xc5c497};

export async function createExploded3DViewer(host,{onSelect=()=>{}}={}) {
  const [THREE, orbitModule]=await Promise.all([
    import("https://esm.sh/three@0.180.0"),
    import("https://esm.sh/three@0.180.0/examples/jsm/controls/OrbitControls.js")
  ]);
  const {OrbitControls}=orbitModule;
  const renderer=new THREE.WebGLRenderer({antialias:true,alpha:true,powerPreference:"low-power"});
  renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,2));
  renderer.outputColorSpace=THREE.SRGBColorSpace;
  renderer.setClearColor(0x0e1b25,1);
  renderer.domElement.setAttribute("tabindex","0");
  renderer.domElement.setAttribute("role","img");
  renderer.domElement.setAttribute("aria-label","Illustrative 3D assembly, orbit with pointer; choose a part from the adjacent keyboard-accessible assembly tree");
  host.replaceChildren(renderer.domElement);
  const scene=new THREE.Scene(),root=new THREE.Group();
  const camera=new THREE.PerspectiveCamera(39,1,0.1,150);
  camera.up.set(0,0,1);
  const orbit=new OrbitControls(camera,renderer.domElement);
  orbit.enableDamping=true;
  orbit.enablePan=false;
  orbit.minDistance=5; orbit.maxDistance=55;
  orbit.target.set(0,0,0.65);
  scene.add(root,new THREE.HemisphereLight(0xd2e6ff,0x273244,2.5));
  const key=new THREE.DirectionalLight(0xffffff,3.2);
  key.position.set(5,-7,14);scene.add(key);
  const fill=new THREE.DirectionalLight(0x9ecde1,1.6);
  fill.position.set(-9,5,5);scene.add(fill);
  const grid=new THREE.GridHelper(20,20,0x3a5967,0x263d4a);
  grid.rotation.x=Math.PI/2;grid.position.z=-2.6;scene.add(grid);
  let graph=null,plan=null,nodes=new Map(),selected=null,disposed=false;
  let frame=null,settle=0,down=null;
  const raycaster=new THREE.Raycaster();
  const pointer=new THREE.Vector2();
  const material=color=>new THREE.MeshStandardMaterial({
    color,roughness:0.68,metalness:0.18,side:THREE.DoubleSide
  });
  function add(group,geometry,mat,pos=[0,0,0],rotation=null) {
    const mesh=new THREE.Mesh(geometry,mat);
    mesh.position.set(...pos);
    if(rotation)mesh.rotation.set(...rotation);
    group.add(mesh);
    return mesh;
  }
  function box(group,w,h,d,mat,x=0,y=0,z=0) {
    return add(group,new THREE.BoxGeometry(w,h,d),mat,[x,y,z]);
  }
  function wheel(group,mat,x,y,rad=0.46) {
    add(group,new THREE.TorusGeometry(rad,0.17,9,24),mat,[x,y,0.02],[0,Math.PI/2,0]);
    add(group,new THREE.CylinderGeometry(rad*0.38,rad*0.38,0.34,16),
        mat,[x,y,0.02],[0,0,Math.PI/2]);
  }
  function boardShape(width,length) {
    const w=width/2,l=length/2,sh=new THREE.Shape();
    sh.moveTo(-w,-l+0.55);
    sh.quadraticCurveTo(-w,-l,-0.28*w,-l);
    sh.quadraticCurveTo(0,-l-0.16,0.28*w,-l);
    sh.quadraticCurveTo(w,-l,w,-l+0.55);
    sh.lineTo(w,l-0.55);
    sh.quadraticCurveTo(w,l,0.28*w,l);
    sh.quadraticCurveTo(0,l+0.16,-0.28*w,l);
    sh.quadraticCurveTo(-w,l,-w,l-0.55);
    sh.closePath();return sh;
  }
  function board(group,mat,w=2.15,l=7.2,originX=0) {
    const geom=new THREE.ExtrudeGeometry(boardShape(w,l),{
      depth:0.13,steps:1,bevelEnabled:true,bevelSize:0.04,
      bevelThickness:0.035,bevelSegments:2,curveSegments:10
    });
    add(group,geom,mat,[originX,0,-0.08]);
  }
  function disc(group,mat,r=0.46,z=0) {
    add(group,new THREE.CylinderGeometry(r,r,0.13,28),mat,[0,0,z],[Math.PI/2,0,0]);
  }
  function createProxy(part,domain) {
    const group=new THREE.Group(),mat=material(PALETTE[part.group_id]||0xaac2c7);
    const role=part.role;
    if(part.group_id==="platform") {
      if(role==="ski_pair"){
        board(group,mat,0.48,8.5,-0.47);board(group,mat,0.48,8.5,0.47);
      }else if(role==="splitboard"){
        board(group,mat,1,7.8,-0.55);board(group,mat,1,7.8,0.55);
      }else if(role==="surfboard")board(group,mat,2.35,8.2);
      else board(group,mat,domain==="skateboard_longboard"?1.7:2.25,
                 domain==="snowboard"?8.0:7.2);
    }else if(part.group_id==="ground") {
      if(role==="fin_set"){
        box(group,0.11,0.55,0.85,mat,-0.5,0,0.25);
        box(group,0.11,0.55,0.85,mat,0.5,0,0.25);
      }else if(role==="ski_brake"){
        box(group,2.4,0.14,0.18,mat);
        box(group,0.1,1,0.16,mat,-1.05,0.15,-0.15);
        box(group,0.1,1,0.16,mat,1.05,0.15,-0.15);
      }else if(role==="skin_pair"){
        box(group,0.46,7.3,0.07,mat,-0.45,0,0);
        box(group,0.46,7.3,0.07,mat,0.45,0,0);
      }else{
        for(const x of [-1.15,1.15])for(const y of [-2.2,2.2])wheel(group,mat,x,y);
      }
    }else if(part.group_id==="mount") {
      if(role==="mounting_disc"||role==="puck_or_mounting_kit"||role==="touring_pivot"){
        for(const y of [-1.4,1.4]){
          add(group,new THREE.CylinderGeometry(0.52,0.52,0.15,30),
              mat,[0,y,0],[Math.PI/2,0,0]);
          box(group,0.85,0.08,0.13,mat,0,y,0.12);
        }
      }else if(role==="bearing_set"||role==="bushing_set"){
        for(const y of [-1.1,1.1])add(group,new THREE.TorusGeometry(0.31,0.13,10,20),
          mat,[0,y,0]);
      }else{
        for(const y of [-2.2,2.2]){
          box(group,3.6,0.12,0.12,mat,0,y,0);
          box(group,0.54,0.48,0.31,mat,0,y,0.22);
        }
      }
    }else if(part.group_id==="rider") {
      if(role==="griptape"||role==="traction_pad")board(group,mat,1.85,6.1);
      else for(const y of [-1.4,1.4]){
        box(group,1.38,0.95,0.17,mat,0,y,0);
        box(group,0.85,0.55,0.84,mat,0,y+0.12,0.42);
        box(group,1.22,0.15,0.22,mat,0,y-0.34,0.35);
      }
    }else if(part.group_id==="power"){
      box(group,2.0,3.1,0.75,mat);
      for(const x of [-0.62,0,0.62])box(group,0.13,2.45,0.08,mat,x,0,0.43);
    }else if(part.group_id==="control"){
      for(const y of [-1.1,1.1]){
        add(group,new THREE.CylinderGeometry(0.48,0.48,0.26,28),mat,
            [0,y,0],[0,Math.PI/2,0]);
        box(group,0.7,1.3,0.2,mat,0,y,0.28);
      }
    }else{
      box(group,1.6,1.3,0.4,mat);
      box(group,1.24,0.18,0.18,mat,0,0,0.32);
    }
    group.userData.partId=part.component_id;
    group.userData.material=mat;
    return group;
  }
  function clearParts() {
    root.traverse(obj=>{if(obj.isMesh){obj.geometry.dispose();}});
    for(const item of nodes.values())item.userData.material.dispose();
    root.clear();nodes.clear();
  }
  function select(id) {
    selected=id;
    for(const [partId,obj] of nodes) {
      const m=obj.userData.material;
      m.emissive.setHex(partId===selected?0x566a82:0x000000);
      m.emissiveIntensity=partId===selected?0.7:0;
    }
    schedule();
  }
  function moveParts(separation) {
    if(!graph)return;
    plan=planExplodedScene(graph,{separation,selectedId:selected});
    for(const part of plan.parts){
      const node=nodes.get(part.component_id);
      if(node)node.position.set(...part.position);
    }
    schedule();
  }
  function update(nextGraph,separation=78,selectedId=null) {
    if(disposed)return;
    if(graph!==nextGraph){
      planExplodedScene(nextGraph);
      clearParts();graph=nextGraph;
      for(const part of nextGraph.components){
        const obj=createProxy(part,nextGraph.domain_id);
        nodes.set(part.component_id,obj);root.add(obj);
      }
    }
    select(selectedId);moveParts(separation);
  }
  function fit() {
    const width=Math.max(1,host.clientWidth),height=Math.max(220,host.clientHeight);
    renderer.setSize(width,height,false);
    camera.aspect=width/height;camera.updateProjectionMatrix();schedule();
  }
  function view(name="hero") {
    const target={hero:[11,-14,11],top:[0,-0.01,21],
      side:[20,0,4],front:[0,-20,5]}[name]||[11,-14,11];
    camera.position.set(...target);orbit.target.set(0,0,0.55);
    orbit.update();schedule();
  }
  function schedule(){
    if(disposed)return;
    settle=20;
    if(frame===null)frame=requestAnimationFrame(render);
  }
  function render(){
    frame=null;
    if(disposed)return;
    if(document.visibilityState==="hidden")return;
    orbit.update();renderer.render(scene,camera);
    if(--settle>0)frame=requestAnimationFrame(render);
  }
  function onPointerDown(e){down=[e.clientX,e.clientY];}
  function onPointerUp(e){
    if(!down || Math.hypot(down[0]-e.clientX,down[1]-e.clientY)>6)return;
    const rect=renderer.domElement.getBoundingClientRect();
    if(!rect.width||!rect.height)return;
    pointer.set(2*(e.clientX-rect.left)/rect.width-1,
                1-2*(e.clientY-rect.top)/rect.height);
    raycaster.setFromCamera(pointer,camera);
    const hits=raycaster.intersectObjects(root.children,true);
    for(const hit of hits){
      let item=hit.object;
      while(item && !item.userData.partId)item=item.parent;
      if(item?.userData.partId){onSelect(item.userData.partId);return;}
    }
  }
  renderer.domElement.addEventListener("pointerdown",onPointerDown);
  renderer.domElement.addEventListener("pointerup",onPointerUp);
  orbit.addEventListener("change",schedule);
  const resize=new ResizeObserver(fit);resize.observe(host);
  view("hero");fit();
  return {
    update,view,plan:()=>plan,
    dispose(){
      disposed=true;
      if(frame!==null)cancelAnimationFrame(frame);
      resize.disconnect();orbit.dispose();clearParts();
      renderer.dispose();host.replaceChildren();
    }
  };
}
