import * as THREE from "https://esm.sh/three@0.180.0";
import { OrbitControls } from "https://esm.sh/three@0.180.0/examples/jsm/controls/OrbitControls.js";
import { GLTFLoader } from "https://esm.sh/three@0.180.0/examples/jsm/loaders/GLTFLoader.js";

const STATE = {
  QUALIFIED: 0x59d499,
  REFERENCE: 0x6ea8fe,
  ASSUMED: 0xf2c56b,
  BLOCKED: 0xf46d75,
  NOT_PRESENT: 0x606773,
};

const PHYSICAL = {
  deck: 0x2f3948,
  trucks: 0x9ca8b8,
  wheels: 0x161a20,
  hubs: 0x66758a,
  pack: 0x313a48,
  rider_interface: 0xd5dbe4,
  brake: 0x9e3f49,
  drive: 0x697687,
  armor: 0x566170,
  dock: 0x3e4856,
};

const sceneEl = document.getElementById("scene");
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.outputColorSpace = THREE.SRGBColorSpace;
sceneEl.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 5000);
camera.up.set(0, 0, 1);
camera.position.set(1050, -900, 600);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.target.set(0, 0, 100);

scene.add(new THREE.HemisphereLight(0xdce8ff, 0x171922, 2.0));
const key = new THREE.DirectionalLight(0xffffff, 4.0);
key.position.set(600, -300, 1000);
key.castShadow = true;
scene.add(key);

const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(1800, 1200),
  new THREE.MeshStandardMaterial({ color: 0x10141c, roughness: 0.96 })
);
ground.position.z = 0;
ground.receiveShadow = true;
scene.add(ground);

const root = new THREE.Group();
const clearanceRoot = new THREE.Group();
const armorRoot = new THREE.Group();
const dockRoot = new THREE.Group();
const cadNeutralRoot = new THREE.Group();
const cadSweepRoot = new THREE.Group();
scene.add(root, clearanceRoot, armorRoot, dockRoot, cadNeutralRoot, cadSweepRoot);

const visual = {
  movable: [],
  manifest: null,
  geometry: null,
  axles: {},
  snow: {},
  topologyId: "brake_first_400mm",
  steerDeg: 0,
  autoSweep: false,
  exploded: false,
  cadManifest: null,
  cadCache: new Map(),
  showCad: false,
  showSweep: false,
  deckCandidateId: "comp95",
  layerGroups: {},
  layerVisibility: {},
  snapshots: { A: null, B: null },
};

clearanceRoot.visible = false;
armorRoot.visible = false;
dockRoot.visible = false;
cadNeutralRoot.visible = false;
cadSweepRoot.visible = false;

function componentState(kind) {
  const component = (visual.manifest.components || []).find(c => c.render && c.render.kind === kind);
  return component ? component.evidence_state : "ASSUMED";
}

function materialFor(state, opacity = 1, wireframe = false, physicalKind = null) {
  const authorityColor = STATE[state] || STATE.ASSUMED;
  const color = physicalKind && state !== "BLOCKED"
    ? (PHYSICAL[physicalKind] || authorityColor)
    : authorityColor;
  return new THREE.MeshStandardMaterial({
    color,
    roughness: physicalKind === "wheels" ? 0.92 : 0.58,
    metalness: ["trucks", "hubs", "brake", "drive"].includes(physicalKind) ? 0.48 : 0.08,
    transparent: opacity < 1,
    opacity,
    wireframe: wireframe || state === "BLOCKED",
    depthWrite: opacity >= 0.58,
  });
}

function addEvidenceEdges(mesh, state, opacity = 0.72) {
  if (!mesh.geometry) return mesh;
  const edges = new THREE.LineSegments(
    new THREE.EdgesGeometry(mesh.geometry, 28),
    new THREE.LineBasicMaterial({
      color: STATE[state] || STATE.ASSUMED,
      transparent: true,
      opacity,
    })
  );
  edges.renderOrder = 4;
  mesh.add(edges);
  return mesh;
}

function registerMovable(object, offset) {
  object.userData.basePosition = object.position.clone();
  object.userData.explodeOffset = new THREE.Vector3(...offset);
  object.userData.targetPosition = object.position.clone();
  visual.movable.push(object);
  return object;
}

function box(parent, name, size, pos, state, opacity = 1, physicalKind = null) {
  const mesh = new THREE.Mesh(
    new THREE.BoxGeometry(...size),
    materialFor(state, opacity, false, physicalKind)
  );
  mesh.name = name;
  mesh.position.set(...pos);
  mesh.castShadow = opacity >= 0.5;
  if (physicalKind) addEvidenceEdges(mesh, state, state === "BLOCKED" ? 0.9 : 0.48);
  parent.add(mesh);
  return mesh;
}

function roundedDeck(parent, g, state) {
  const length = g.deck_length_mm;
  const width = g.deck_width_mm;
  const r = Math.min(34, width * 0.14);
  const x = length / 2;
  const y = width / 2;
  const shape = new THREE.Shape();
  shape.moveTo(-x + r, -y);
  shape.lineTo(x - r, -y);
  shape.quadraticCurveTo(x, -y, x, -y + r);
  shape.lineTo(x, y - r);
  shape.quadraticCurveTo(x, y, x - r, y);
  shape.lineTo(-x + r, y);
  shape.quadraticCurveTo(-x, y, -x, y - r);
  shape.lineTo(-x, -y + r);
  shape.quadraticCurveTo(-x, -y, -x + r, -y);
  const geometry = new THREE.ExtrudeGeometry(shape, {
    depth: g.deck_reference_thickness_mm,
    bevelEnabled: true,
    bevelSegments: 2,
    steps: 1,
    bevelSize: 2.5,
    bevelThickness: 1.5,
  });
  const mesh = new THREE.Mesh(geometry, materialFor(state, 1, false, "deck"));
  mesh.name = "deck";
  mesh.position.z = g.static_ground_clearance_mm;
  mesh.castShadow = true;
  addEvidenceEdges(mesh, state, 0.48);
  parent.add(mesh);
  return mesh;
}

function wheel(parent, name, y, radius, width, state) {
  const group = new THREE.Group();
  group.name = name;
  group.position.set(0, y, radius);

  const tire = new THREE.Mesh(
    new THREE.CylinderGeometry(radius, radius, width, 72, 1, false),
    materialFor(state, 1, false, "wheels")
  );
  tire.castShadow = true;
  group.add(tire);

  const hub = new THREE.Mesh(
    new THREE.CylinderGeometry(radius * 0.43, radius * 0.43, width + 4, 48),
    materialFor(state, 1, false, "hubs")
  );
  hub.castShadow = true;
  group.add(hub);

  for (const side of [-1, 1]) {
    const ring = new THREE.Mesh(
      new THREE.RingGeometry(radius * 0.78, radius * 0.9, 64),
      new THREE.MeshBasicMaterial({
        color: STATE[state] || STATE.ASSUMED,
        transparent: true,
        opacity: 0.7,
        side: THREE.DoubleSide,
      })
    );
    ring.rotation.x = Math.PI / 2;
    ring.position.y = side * (width / 2 + 0.8);
    group.add(ring);
  }

  parent.add(group);
  return group;
}

function makeTruck(parent, name, width, deckBottom, state) {
  const group = new THREE.Group();
  group.name = name;
  const z = deckBottom - 16;

  const axle = new THREE.Mesh(
    new THREE.CylinderGeometry(4.2, 4.2, width, 24),
    materialFor(state, 1, false, "trucks")
  );
  axle.position.z = z;
  group.add(axle);

  const hanger = new THREE.Mesh(
    new THREE.CylinderGeometry(8, 8, Math.max(80, width - 92), 28),
    materialFor(state, 1, false, "trucks")
  );
  hanger.position.z = z + 4;
  group.add(hanger);

  box(group, name + "-baseplate", [94, 70, 7], [0, 0, deckBottom - 5], state, 1, "trucks");
  box(group, name + "-pivot", [40, 34, 26], [0, 0, deckBottom - 17], state, 1, "trucks");
  parent.add(group);
  return group;
}

function lineRectangle(width, height, z, color) {
  const x = width / 2;
  const y = height / 2;
  const points = [
    new THREE.Vector3(-x, -y, z),
    new THREE.Vector3(x, -y, z),
    new THREE.Vector3(x, y, z),
    new THREE.Vector3(-x, y, z),
    new THREE.Vector3(-x, -y, z),
  ];
  return new THREE.Line(
    new THREE.BufferGeometry().setFromPoints(points),
    new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.8 })
  );
}

function makeFootAssembly(parent, id, initialX, state, deckTop) {
  const group = new THREE.Group();
  group.name = id;
  group.position.set(initialX, 0, 0);
  group.rotation.order = "ZXY";

  const insert = box(group, id + "-insert", [260, 132, 2], [0, 0, deckTop + 1], "ASSUMED", 0.22);
  const plate = box(group, id + "-plate", [260, 132, 6], [0, 0, deckTop + 5], state, 0.92, "rider_interface");
  const fore = box(group, id + "-fore-zone", [105, 78, 1.5], [60, 0, deckTop + 8.75], state, 0.24);
  const heel = box(group, id + "-heel-zone", [105, 78, 1.5], [-60, 0, deckTop + 8.75], state, 0.24);

  registerMovable(group, [0, 0, 230]);
  visual.snow[id] = { group, plate, insert, fore, heel };
  parent.add(group);
  return group;
}

function makeClearanceOverlay(g) {
  clearanceRoot.clear();
  const outerWidth = (g.estimated_outer_wheel_envelope_width_mm || 401) + 100;
  const keepoutHeight = g.minimum_compressed_clearance_mm || 45;
  const volume = new THREE.Mesh(
    new THREE.BoxGeometry(1320, outerWidth, keepoutHeight),
    new THREE.MeshBasicMaterial({
      color: STATE.ASSUMED,
      transparent: true,
      opacity: 0.055,
      wireframe: false,
      depthWrite: false,
    })
  );
  volume.position.z = keepoutHeight / 2;
  clearanceRoot.add(volume);
  clearanceRoot.add(lineRectangle(1320, outerWidth, keepoutHeight, STATE.ASSUMED));
  clearanceRoot.add(lineRectangle(1320, outerWidth, g.static_ground_clearance_mm || 65, STATE.REFERENCE));
}

function makeArmorStudy(manifest, deckBottom) {
  armorRoot.clear();
  const study = (manifest.design_studies || {}).trail_armor;
  if (!study || !study.provisional_visual_only) return;
  const g = study.provisional_visual_only;
  const state = componentState("armor");
  const z = Math.max(1, deckBottom - g.runner_thickness_mm / 2 - 2);
  for (const side of [-1, 1]) {
    const y = side * g.runner_lateral_offset_mm;
    box(armorRoot, "trail-runner-" + side,
      [g.runner_length_mm, g.runner_width_mm, g.runner_thickness_mm],
      [0, y, z], state, 0.62, "armor");
  }
}

function makeBrakeReference(parent, axleX, g, state) {
  const group = new THREE.Group();
  group.name = "mechanical-brake-reference";
  group.position.x = -axleX;
  const rotorOuter = g.wheel_diameter_mm * 0.31;
  const rotorInner = rotorOuter * 0.72;
  for (const side of [-1, 1]) {
    const y = side * (g.wheel_center_lateral_mm - g.wheel_width_mm / 2 - 3);
    const rotor = new THREE.Mesh(
      new THREE.RingGeometry(rotorInner, rotorOuter, 48),
      materialFor(state, 0.78, false, "brake")
    );
    rotor.rotation.x = Math.PI / 2;
    rotor.position.set(0, y, g.wheel_diameter_mm / 2);
    group.add(rotor);
    box(group, "brake-caliper-" + side, [30, 18, 34],
      [18, y, g.wheel_diameter_mm * 0.63], state, 0.72, "brake");
  }
  const envelope = box(group, "brake-packaging-envelope",
    [40, g.truck_total_width_mm - 34, g.wheel_diameter_mm * 0.78],
    [0, 0, g.wheel_diameter_mm / 2], state, 0.055);
  visual.brakeGhost = envelope;
  registerMovable(group, [-70, -180, 100]);
  parent.add(group);
  return group;
}

function makeDriveReference(parent, axleX, g, state) {
  const group = new THREE.Group();
  group.name = "drive-packaging-reference";
  group.position.x = -axleX + 28;
  for (const side of [-1, 1]) {
    const y = side * (g.wheel_center_lateral_mm - 58);
    const motor = new THREE.Mesh(
      new THREE.CylinderGeometry(28, 28, 48, 36),
      materialFor(state, 0.58, state === "BLOCKED", "drive")
    );
    motor.position.set(36, y, 78);
    motor.castShadow = true;
    group.add(motor);
    const gear = new THREE.Mesh(
      new THREE.CylinderGeometry(34, 34, 7, 40),
      materialFor(state, 0.5, true, "drive")
    );
    gear.position.set(0, side * (g.wheel_center_lateral_mm - g.wheel_width_mm / 2 - 7), g.wheel_diameter_mm / 2);
    group.add(gear);
  }
  const envelope = box(group, "drive-packaging-envelope",
    [122, g.truck_total_width_mm - 48, 92], [24, 0, 74], state, 0.055);
  visual.driveGhost = envelope;
  registerMovable(group, [-70, 180, 100]);
  parent.add(group);
  return group;
}

function makeDockStudy(g) {
  dockRoot.clear();
  const state = componentState("dock");
  const railY = Math.min(120, g.deck_width_mm * 0.42);
  for (const side of [-1, 1]) {
    box(dockRoot, "dock-rail-" + side, [440, 22, 16], [0, side * railY, 8], state, 0.48, "dock");
    box(dockRoot, "dock-guide-" + side, [66, 36, 52], [-80, side * (railY + 4), 26], state, 0.38, "dock");
  }
  box(dockRoot, "dock-center-stop", [36, 120, 24], [150, 0, 12], state, 0.38, "dock");
}

function createLayerGroup(id) {
  const group = new THREE.Group();
  group.name = "layer-" + id;
  root.add(group);
  visual.layerGroups[id] = group;
  return group;
}

function proceduralBoard(manifest) {
  root.clear();
  visual.movable = [];
  visual.axles = {};
  visual.snow = {};
  visual.layerGroups = {};

  const g = manifest.design_studies.chassis_reference;
  visual.geometry = g;
  const deckBottom = g.static_ground_clearance_mm;
  const deckTop = deckBottom + g.deck_reference_thickness_mm;
  const axleX = g.wheelbase_mm / 2;
  const wheelRadius = g.wheel_diameter_mm / 2;

  const deck = roundedDeck(root, g, componentState("deck"));
  visual.deck = registerMovable(deck, [0, 0, 70]);

  for (const axle of [
    { id: "rear", x: -axleX, steerSign: -1, explode: [-120, 0, 80] },
    { id: "front", x: axleX, steerSign: 1, explode: [120, 0, 80] },
  ]) {
    const group = new THREE.Group();
    group.position.set(axle.x, 0, 0);
    group.userData.steerSign = axle.steerSign;
    const truck = makeTruck(group, axle.id + "-truck", g.truck_total_width_mm, deckBottom, componentState("trucks"));
    const leftWheel = wheel(group, axle.id + "-wheel-left", -g.wheel_center_lateral_mm, wheelRadius, g.wheel_width_mm, componentState("wheels"));
    const rightWheel = wheel(group, axle.id + "-wheel-right", g.wheel_center_lateral_mm, wheelRadius, g.wheel_width_mm, componentState("wheels"));
    visual.axles[axle.id] = { group, truck, leftWheel, rightWheel };
    registerMovable(group, axle.explode);
    root.add(group);
  }

  const packLayer = createLayerGroup("pack");
  const packHeight = 58;
  const packCenterZ = Math.max(packHeight / 2 + 3, deckBottom - packHeight / 2 - 4);
  const pack = box(packLayer, "pack-envelope", [330, 188, packHeight], [20, 0, packCenterZ],
    componentState("pack"), 0.42, "pack");
  visual.pack = registerMovable(packLayer, [0, 0, 250]);

  const snowLayer = createLayerGroup("snowdeck");
  makeFootAssembly(snowLayer, "rearFoot", -180, componentState("rider_interface"), deckTop);
  makeFootAssembly(snowLayer, "frontFoot", 180, componentState("rider_interface"), deckTop);

  const brakeLayer = createLayerGroup("brake");
  makeBrakeReference(brakeLayer, axleX, g, componentState("brake"));

  const driveLayer = createLayerGroup("drive");
  makeDriveReference(driveLayer, axleX, g, componentState("drive"));

  makeClearanceOverlay(g);
  makeArmorStudy(manifest, deckBottom);
  makeDockStudy(g);
  applyTopology(visual.topologyId);
  updateSteering(0);
  updateSnowdeck();
}
function updateSteering(angle) {
  const max = visual.geometry ? visual.geometry.max_steer_deg : 22;
  visual.steerDeg = Math.max(-max, Math.min(max, Number(angle)));
  Object.values(visual.axles).forEach(axle => {
    axle.group.rotation.z = THREE.MathUtils.degToRad(
      visual.steerDeg * axle.group.userData.steerSign
    );
  });
  const output = document.getElementById("steer-value");
  if (output) output.textContent = visual.steerDeg.toFixed(1) + "°";
}

function applyTopology(id) {
  const studies = visual.manifest.design_studies || {};
  const branches = studies.topology_branches || [];
  const branch = branches.find(x => x.id === id) || branches[0];
  if (!branch || !visual.geometry) return;

  visual.topologyId = branch.id;
  for (const axle of Object.values(visual.axles)) {
    axle.truck.scale.y = branch.truck_total_width_mm / visual.geometry.truck_total_width_mm;
    axle.leftWheel.position.y = -branch.wheel_center_lateral_mm;
    axle.rightWheel.position.y = branch.wheel_center_lateral_mm;
  }

  if (visual.brakeGhost) {
    visual.brakeGhost.material.opacity =
      branch.brake_reference_compatible === true ? 0.28 :
      branch.brake_reference_compatible === false ? 0.07 : 0.16;
  }
  if (visual.driveGhost) {
    visual.driveGhost.material.opacity =
      branch.drive_reference_compatible === true ? 0.28 : 0.07;
  }

  const note = document.getElementById("topology-note");
  if (note) {
    note.textContent =
      branch.label + ". Brake reference: " + String(branch.brake_reference_compatible) +
      ". Drive reference: " + String(branch.drive_reference_compatible) +
      ". Catalog/reference geometry only until physical qualification.";
  }
  loadCadTopology(branch.id);
}

function updateSnowdeck() {
  if (!visual.snow.frontFoot || !visual.geometry) return;

  const stance = Number(document.getElementById("stance")?.value || 360);
  const frontYaw = Number(document.getElementById("front-yaw")?.value || 0);
  const rearYaw = Number(document.getElementById("rear-yaw")?.value || 0);
  const frontCant = Number(document.getElementById("front-cant")?.value || 0);
  const rearCant = Number(document.getElementById("rear-cant")?.value || 0);
  const insert = Number(document.getElementById("insert-proxy")?.value || 0);

  const deckTop =
    visual.geometry.static_ground_clearance_mm +
    visual.geometry.deck_reference_thickness_mm;

  const setFoot = (foot, x, yaw, cant) => {
    foot.group.userData.basePosition.x = x;
    foot.group.userData.targetPosition
      .copy(foot.group.userData.basePosition)
      .add(visual.exploded ? foot.group.userData.explodeOffset : new THREE.Vector3());
    if (!visual.exploded) foot.group.position.x = x;
    foot.group.rotation.z = THREE.MathUtils.degToRad(yaw);
    foot.group.rotation.x = THREE.MathUtils.degToRad(cant);
    foot.insert.visible = insert > 0;
    foot.insert.scale.z = Math.max(insert, 0.5) / 2;
    foot.insert.position.z = deckTop + Math.max(insert, 0.5) / 2;
    const plateZ = deckTop + insert + 3;
    foot.plate.position.z = plateZ;
    foot.fore.position.z = plateZ + 3.75;
    foot.heel.position.z = plateZ + 3.75;
  };

  setFoot(visual.snow.frontFoot, stance / 2, frontYaw, frontCant);
  setFoot(visual.snow.rearFoot, -stance / 2, rearYaw, rearCant);

  const values = {
    "stance-value": stance.toFixed(0) + " mm",
    "front-yaw-value": frontYaw.toFixed(0) + "°",
    "rear-yaw-value": rearYaw.toFixed(0) + "°",
    "front-cant-value": frontCant.toFixed(1) + "°",
    "rear-cant-value": rearCant.toFixed(1) + "°",
    "insert-proxy-value": insert.toFixed(1) + " mm",
  };
  Object.entries(values).forEach(([id, value]) => {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  });
}

function setExploded(on) {
  visual.exploded = on;
  visual.movable.forEach(object => {
    const base = object.userData.basePosition;
    const offset = object.userData.explodeOffset;
    object.userData.targetPosition.copy(base).add(on ? offset : new THREE.Vector3());
  });
}

function setView(view) {
  setExploded(view === "exploded");
  clearanceRoot.visible = view === "clearance" || view === "risk" || view === "armor";
  armorRoot.visible = view === "armor";

  const views = {
    hero: [[1050, -900, 600], [0, 0, 100]],
    fit: [[0, -40, 1200], [0, 0, 80]],
    clearance: [[920, -900, 300], [0, 0, 70]],
    topology: [[1100, -750, 250], [0, 0, 90]],
    exploded: [[1100, -900, 720], [0, 0, 180]],
    risk: [[1180, -980, 520], [0, 0, 95]],
    armor: [[900, -780, 220], [0, 0, 45]],
  };
  const v = views[view] || views.hero;
  camera.position.set(...v[0]);
  controls.target.set(...v[1]);
  controls.update();
}

function deckStudyUI(manifest) {
  const host = document.getElementById("deck-candidates");
  host.innerHTML = "";
  const candidates = manifest.design_studies.deck_candidates || [];
  const selection = manifest.deck_comparison_selection || null;
  const selectedAuthorityId = selection?.selected_candidate_id || null;
  let defaultButton = null;

  candidates.forEach((candidate, index) => {
    const btn = document.createElement("button");
    const physicallySelected =
      selectedAuthorityId &&
      candidate.authority_candidate_id === selectedAuthorityId;

    btn.textContent =
      candidate.label + (physicallySelected ? " · PHYSICAL PICK" : "");
    if (physicallySelected) btn.classList.add("physical-selected");

    btn.addEventListener("click", () => {
      if (!visual.deck || !visual.geometry) return;
      visual.deck.scale.x = candidate.length_mm / visual.geometry.deck_length_mm;
      visual.deck.scale.y = candidate.width_mm / visual.geometry.deck_width_mm;
      document.querySelectorAll("#deck-candidates button").forEach(x => x.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById("deck-note").textContent =
        candidate.label + ": " + candidate.length_mm + " × " + candidate.width_mm +
        " mm maximum reference envelope. " +
        (physicallySelected
          ? "Selected by a fingerprint-valid full-scale deck comparison; this is not chassis qualification. "
          : "") +
        "Truck/wheel geometry is intentionally unchanged.";
    });

    host.appendChild(btn);
    if (physicallySelected || (!defaultButton && index === 0)) {
      defaultButton = btn;
    }
  });

  if (defaultButton) defaultButton.click();
}

function topologyUI(manifest) {
  const host = document.getElementById("topology-branches");
  host.innerHTML = "";
  const branches = manifest.design_studies.topology_branches || [];
  branches.forEach((branch, index) => {
    const btn = document.createElement("button");
    btn.textContent = branch.short_label;
    if (index === 0) btn.classList.add("active");
    btn.addEventListener("click", () => {
      document.querySelectorAll("#topology-branches button").forEach(x => x.classList.remove("active"));
      btn.classList.add("active");
      applyTopology(branch.id);
    });
    host.appendChild(btn);
  });
}

function fmt(value, digits = 3) {
  return Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : "—";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function snowdeckResponseUI(manifest) {
  const host = document.getElementById("snowdeck-response");
  const signature = manifest.snowdeck_bench_signature;
  const comparison = manifest.snowdeck_bench_comparison;
  if (!signature) return;

  const neutral = signature.neutral || {};
  const transfer = signature.heel_to_toe_forefoot_transfer || {};
  const rejects = signature.mechanical_rejects || [];
  const stateClass = rejects.length ? "response-blocked" : "response-clear";
  const synthetic = signature.synthetic_fixture === true;

  host.innerHTML =
    '<div class="response-head ' + stateClass + '">' +
      '<strong>' + escapeHtml(signature.condition_id || "local condition") +
      (synthetic ? ' <em>SYNTHETIC</em>' : '') + '</strong>' +
      '<span>' + signature.trial_count + ' trials</span>' +
    '</div>' +
    '<div class="metric-grid">' +
      '<div><span>Neutral L load</span><strong>' + fmt(neutral.left_load_fraction?.mean) + '</strong><small>SD ' + fmt(neutral.left_load_fraction?.sd) + '</small></div>' +
      '<div><span>L heel→toe</span><strong>' + fmt(transfer.left?.mean) + '</strong><small>SD ' + fmt(transfer.left?.sd) + '</small></div>' +
      '<div><span>R heel→toe</span><strong>' + fmt(transfer.right?.mean) + '</strong><small>SD ' + fmt(transfer.right?.sd) + '</small></div>' +
      '<div><span>Total-load SD</span><strong>' + fmt(neutral.total_load?.sd, 2) + '</strong><small>force units</small></div>' +
    '</div>' +
    (rejects.length
      ? '<div class="reject-box"><strong>Mechanically blocked</strong><span>' + rejects.map(escapeHtml).join(" · ") + '</span></div>'
      : '<div class="accept-box"><strong>No linked immediate-reject observation</strong><span>Still bench-only and non-authoritative.</span></div>');

  if (comparison) {
    const deltas = comparison.signed_variant_minus_baseline || {};
    const rows = [
      ["Δ neutral L load", deltas.neutral_left_load_mean],
      ["Δ L heel→toe", deltas.left_heel_to_toe_transfer_mean],
      ["Δ R heel→toe", deltas.right_heel_to_toe_transfer_mean],
      ["Δ neutral load SD", deltas.neutral_total_load_sd],
    ];
    host.innerHTML +=
      '<div class="comparison"><strong>Variant − baseline</strong>' +
      rows.map(([label, value]) =>
        '<div><span>' + label + '</span><b>' + (Number(value) >= 0 ? "+" : "") + fmt(value) + '</b></div>'
      ).join("") +
      '<small>No direction is automatically preferred. No winner is selected.</small></div>';
  }
}

function fillUI(manifest) {
  document.getElementById("notice").textContent = manifest.viewer_notice;
  const legend = document.getElementById("legend");
  legend.innerHTML = "";
  Object.keys(STATE).forEach(state => {
    const el = document.createElement("span");
    el.textContent = state;
    el.style.borderColor = "#" + STATE[state].toString(16).padStart(6, "0");
    legend.appendChild(el);
  });

  const list = document.getElementById("components");
  list.innerHTML = "";
  manifest.components.forEach(component => {
    const row = document.createElement("div");
    row.className = "component";
    const color = "#" + STATE[component.evidence_state].toString(16).padStart(6, "0");
    const gates = [component.authority_gate]
      .concat(component.context_gates || [])
      .filter(Boolean)
      .join(" · ");
    row.innerHTML =
      '<span class="dot" style="--state:' + color + '"></span>' +
      '<div><strong>' + component.label + '</strong><small>' +
      (gates || "concept-only") + '</small></div>' +
      '<span class="state">' + component.evidence_state + '</span>';
    list.appendChild(row);
  });

  snowdeckResponseUI(manifest);

  const risks = document.getElementById("risks");
  risks.innerHTML = "";
  (manifest.risk_summary || []).forEach(risk => {
    const row = document.createElement("div");
    row.className = "risk-row";
    row.innerHTML =
      '<span class="risk-id">' + risk.id + '</span>' +
      '<div><strong>' + risk.subsystem.replaceAll("_", " ") + '</strong><small>' +
      risk.failure_mode + '</small></div>' +
      '<span class="risk-score">' + risk.priority_score + '</span>';
    row.title = "Must close before: " + risk.must_close_before;
    risks.appendChild(row);
  });

  const g = manifest.design_studies.chassis_reference;
  document.getElementById("clearance-note").textContent =
    "Provisional reference: static deck clearance " + g.static_ground_clearance_mm +
    " mm; compressed keep-out " + g.minimum_compressed_clearance_mm +
    " mm. These values remain measurement gates.";
}

function assetUrl(record) {
  let path = record.asset || "";
  if (path.startsWith("showcase/")) path = path.slice("showcase/".length);
  return "./" + path;
}

function recolorCad(sceneObject, color, opacity) {
  sceneObject.traverse(child => {
    if (!child.isMesh) return;
    child.material = new THREE.MeshStandardMaterial({
      color,
      transparent: true,
      opacity,
      wireframe: true,
      depthWrite: false,
    });
    child.castShadow = false;
  });
}

async function loadGeneratedAssetManifest() {
  try {
    const response = await fetch("./generated/assets.json", { cache: "no-store" });
    if (!response.ok) throw new Error("asset manifest not generated");
    visual.cadManifest = await response.json();
    document.getElementById("asset-status").textContent =
      visual.cadManifest.assets.length + " generated CAD assets available.";
    document.getElementById("show-cad").disabled = false;
    document.getElementById("show-sweep").disabled = false;
    await loadCadTopology(visual.topologyId);
  } catch (error) {
    document.getElementById("asset-status").textContent =
      "Procedural reference active. Generate local GLB assets to enable exact CAD overlays.";
  }
}

async function loadGlbRecord(record, color, opacity) {
  const cacheKey = record.asset + ":" + color + ":" + opacity;
  if (visual.cadCache.has(cacheKey)) return visual.cadCache.get(cacheKey).clone(true);

  const loader = new GLTFLoader();
  const gltf = await loader.loadAsync(assetUrl(record));
  recolorCad(gltf.scene, color, opacity);
  visual.cadCache.set(cacheKey, gltf.scene);
  return gltf.scene.clone(true);
}

async function loadCadTopology(id) {
  if (!visual.cadManifest) return;

  const neutralStem = "x1_chassis_" + id + "_neutral";
  const sweepStem = "x1_chassis_" + id + "_sweep";
  const assets = visual.cadManifest.assets || [];
  const neutral = assets.find(x => x.asset_id === neutralStem);
  const sweep = assets.find(x => x.asset_id === sweepStem);

  cadNeutralRoot.clear();
  cadSweepRoot.clear();

  try {
    if (neutral) {
      cadNeutralRoot.add(await loadGlbRecord(neutral, 0xf5f7fb, 0.24));
    }
    if (sweep) {
      cadSweepRoot.add(await loadGlbRecord(sweep, STATE.ASSUMED, 0.13));
    }
    cadNeutralRoot.visible = visual.showCad;
    cadSweepRoot.visible = visual.showSweep;
  } catch (error) {
    document.getElementById("asset-status").textContent =
      "CAD manifest found, but one or more GLB overlays could not be loaded.";
  }
}

function connectControls() {
  document.querySelectorAll("[data-view]").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("[data-view]").forEach(x => x.classList.remove("active"));
      btn.classList.add("active");
      setView(btn.dataset.view);
    });
  });

  const steer = document.getElementById("steer");
  steer.addEventListener("input", () => {
    visual.autoSweep = false;
    document.getElementById("auto-sweep").checked = false;
    updateSteering(steer.value);
  });

  document.getElementById("auto-sweep").addEventListener("change", event => {
    visual.autoSweep = event.target.checked;
  });

  document.getElementById("show-cad").addEventListener("change", event => {
    visual.showCad = event.target.checked;
    cadNeutralRoot.visible = visual.showCad;
  });

  document.getElementById("show-sweep").addEventListener("change", event => {
    visual.showSweep = event.target.checked;
    cadSweepRoot.visible = visual.showSweep;
  });

  ["stance", "front-yaw", "rear-yaw", "front-cant", "rear-cant", "insert-proxy"].forEach(id => {
    document.getElementById(id).addEventListener("input", updateSnowdeck);
  });

  document.getElementById("reset-snowdeck").addEventListener("click", () => {
    const defaults = {
      stance: 360,
      "front-yaw": 0,
      "rear-yaw": 0,
      "front-cant": 0,
      "rear-cant": 0,
      "insert-proxy": 0,
    };
    Object.entries(defaults).forEach(([id, value]) => {
      document.getElementById(id).value = value;
    });
    updateSnowdeck();
  });
}

function resize() {
  const w = sceneEl.clientWidth;
  const h = sceneEl.clientHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
window.addEventListener("resize", resize);

async function loadManifest() {
  try {
    const response = await fetch("./x1_runtime_manifest.json", { cache: "no-store" });
    if (!response.ok) throw new Error("runtime manifest unavailable");
    return await response.json();
  } catch (error) {
    const seed = await fetch("./x1_rev_c.json").then(r => r.json());
    seed.viewer_notice =
      "Seed preview only. Run tools/build_showcase_manifest.py for evaluated authority status.";
    return seed;
  }
}

const manifest = await loadManifest();
visual.manifest = manifest;
fillUI(manifest);
proceduralBoard(manifest);
deckStudyUI(manifest);
topologyUI(manifest);
connectControls();
resize();
await loadGeneratedAssetManifest();

const clock = new THREE.Clock();
function tick() {
  const elapsed = clock.getElapsedTime();
  if (visual.autoSweep && visual.geometry) {
    const angle = Math.sin(elapsed * 1.1) * visual.geometry.max_steer_deg;
    document.getElementById("steer").value = angle;
    updateSteering(angle);
  }

  visual.movable.forEach(object => {
    const target = object.userData.targetPosition;
    if (target) object.position.lerp(target, 0.09);
  });

  controls.update();
  renderer.render(scene, camera);
  requestAnimationFrame(tick);
}
tick();
