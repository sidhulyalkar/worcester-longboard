import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.180.0/build/three.module.js";
import { OrbitControls } from "https://cdn.jsdelivr.net/npm/three@0.180.0/examples/jsm/controls/OrbitControls.js";

const STATE = {
  QUALIFIED: 0x59d499,
  REFERENCE: 0x6ea8fe,
  ASSUMED: 0xf2c56b,
  BLOCKED: 0xf46d75,
  NOT_PRESENT: 0x606773,
};

const sceneEl = document.getElementById("scene");
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
sceneEl.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 5000);
camera.position.set(1050, 720, 980);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.target.set(0, 0, 90);

scene.add(new THREE.HemisphereLight(0xdce8ff, 0x171922, 2.0));
const key = new THREE.DirectionalLight(0xffffff, 4.0);
key.position.set(600, -300, 1000);
key.castShadow = true;
scene.add(key);

const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(1800, 1200),
  new THREE.MeshStandardMaterial({ color: 0x10141c, roughness: 0.96 })
);
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
scene.add(ground);

const root = new THREE.Group();
root.rotation.x = -0.04;
scene.add(root);

function mat(state, opacity) {
  const color = STATE[state] || STATE.ASSUMED;
  return new THREE.MeshStandardMaterial({
    color,
    roughness: 0.58,
    metalness: 0.1,
    transparent: opacity < 1,
    opacity,
    wireframe: state === "BLOCKED",
  });
}

function box(name, size, pos, state, opacity = 1) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(...size), mat(state, opacity));
  mesh.name = name;
  mesh.position.set(...pos);
  mesh.castShadow = true;
  root.add(mesh);
  return mesh;
}

function wheel(name, x, y, state) {
  const mesh = new THREE.Mesh(
    new THREE.CylinderGeometry(97, 97, 51, 48),
    new THREE.MeshStandardMaterial({ color: STATE[state], roughness: .92 })
  );
  mesh.name = name;
  mesh.rotation.x = Math.PI / 2;
  mesh.position.set(x, y, 97);
  mesh.castShadow = true;
  root.add(mesh);
}

function proceduralBoard(manifest) {
  const byKind = {};
  manifest.components.forEach(c => { byKind[c.render.kind] = c; });
  const s = kind => (byKind[kind] || {}).evidence_state || "ASSUMED";

  box("deck", [950, 251, 18], [0, 0, 155], s("deck"));
  box("front-truck", [32, 400, 22], [470, 0, 115], s("trucks"));
  box("rear-truck", [32, 400, 22], [-470, 0, 115], s("trucks"));
  [-470, 470].forEach(x => [-175, 175].forEach(y => wheel("wheel", x, y, s("wheels"))));

  box("pack-envelope", [330, 188, 58], [20, 0, 194], s("pack"), .38);
  box("left-fit-plate", [235, 115, 8], [-180, 0, 184], s("rider_interface"), .82);
  box("right-fit-plate", [235, 115, 8], [180, 0, 184], s("rider_interface"), .82);

  box("rear-drive-ghost", [95, 330, 80], [-450, 0, 90], s("drive"), .28);
  box("brake-ghost", [30, 330, 150], [-470, 0, 102], s("brake"), .24);
}

function fillUI(manifest) {
  document.getElementById("notice").textContent = manifest.viewer_notice;
  const legend = document.getElementById("legend");
  Object.keys(STATE).forEach(state => {
    const el = document.createElement("span");
    el.textContent = state;
    el.style.borderColor = "#" + STATE[state].toString(16).padStart(6, "0");
    legend.appendChild(el);
  });

  const list = document.getElementById("components");
  manifest.components.forEach(component => {
    const row = document.createElement("div");
    row.className = "component";
    const color = "#" + STATE[component.evidence_state].toString(16).padStart(6, "0");
    row.innerHTML =
      '<span class="dot" style="--state:' + color + '"></span>' +
      '<div><strong>' + component.label + '</strong><small>' +
      (component.authority_gate || "concept-only") + '</small></div>' +
      '<span class="state">' + component.evidence_state + '</span>';
    list.appendChild(row);
  });
}

function setView(view) {
  const views = {
    hero: [[1050, 720, 980], [0, 0, 90]],
    fit: [[120, 1100, 850], [0, 0, 150]],
    clearance: [[980, 250, 420], [0, 0, 80]],
    topology: [[1250, 520, 80], [0, 0, 95]],
  };
  const v = views[view] || views.hero;
  camera.position.set(...v[0]);
  controls.target.set(...v[1]);
  controls.update();
}

document.querySelectorAll("[data-view]").forEach(btn => {
  btn.addEventListener("click", () => setView(btn.dataset.view));
});

function resize() {
  const w = sceneEl.clientWidth;
  const h = sceneEl.clientHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
window.addEventListener("resize", resize);

fetch("./x1_runtime_manifest.json")
  .then(r => {
    if (!r.ok) throw new Error("Run tools/build_showcase_manifest.py first");
    return r.json();
  })
  .then(manifest => {
    fillUI(manifest);
    proceduralBoard(manifest);
    resize();
  })
  .catch(err => {
    document.getElementById("notice").textContent = err.message;
    fetch("./x1_rev_c.json").then(r => r.json()).then(seed => {
      seed.viewer_notice = "Seed preview only. Build the runtime manifest for authority status.";
      fillUI(seed);
      proceduralBoard(seed);
      resize();
    });
  });

function tick() {
  controls.update();
  renderer.render(scene, camera);
  requestAnimationFrame(tick);
}
tick();
