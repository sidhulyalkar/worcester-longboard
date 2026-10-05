function visualIndices(geometry, catalog) {
  return {
    decks: new Map((geometry.decks || []).map(row => [row.id, row])),
    topologies: new Map((geometry.topologies || []).map(row => [row.id, row])),
    components: new Map((catalog.components || []).map(row => [row.id, row])),
  };
}

function firstInterface(interfaces, keys, fallback = null) {
  for (const key of keys) {
    const value = interfaces?.[key];
    if (value !== undefined && value !== null) return value;
  }
  return fallback;
}

function wheelState(wheelId, components) {
  if (!wheelId) {
    return {
      study_id: "none",
      manufacturer: null,
      wheel_class: "none",
      hub_family: null,
      diameter_mm: 0,
      width_mm: 0,
      visual_geometry_state: null,
      visible: false,
    };
  }

  const component = components.get(wheelId);
  if (!component) throw new Error("Unknown visual wheel component " + wheelId);
  const interfaces = component.interfaces || {};
  const diameter = Number(firstInterface(
    interfaces,
    ["measured_reference_diameter_mm", "published_diameter_mm"],
    0
  ));
  const width = Number(firstInterface(
    interfaces,
    ["measured_reference_width_mm", "published_width_mm", "visual_width_mm"],
    0
  ));
  if (!(diameter > 0) || !(width > 0)) {
    throw new Error("Visual wheel component lacks normalized diameter/width " + wheelId);
  }

  let hubFamily = interfaces.hub_family || null;
  if (!hubFamily && wheelId === "TIRE-T1-8-REF") hubFamily = "rockstar_ii";
  if (!hubFamily && wheelId === "TIRE-T2-9") hubFamily = "multi_hub_measure_first";

  return {
    study_id: wheelId,
    manufacturer: component.manufacturer || null,
    wheel_class: interfaces.wheel_class || "pneumatic",
    hub_family: hubFamily,
    diameter_mm: diameter,
    width_mm: width,
    visual_geometry_state: interfaces.visual_geometry_state || null,
    visible: true,
  };
}

function candidateWheelId(candidate) {
  const wheelRow = (candidate.bom || []).find(row => row.category === "wheel");
  if (wheelRow) return wheelRow.component_id;
  if (candidate.capabilities?.wheel_class === "8in_pneumatic") return "TIRE-T1-8-REF";
  if (candidate.capabilities?.wheel_class === "9in_pneumatic") return "TIRE-T2-9";
  return null;
}

function layersFromBom(rows) {
  const categories = new Set((rows || []).map(row => row.category));
  return {
    brake: categories.has("brake"),
    drive: categories.has("drive"),
    pack: categories.has("battery"),
    snowdeck: categories.has("rider_interface"),
    armor: categories.has("armor"),
    dock: categories.has("dock"),
  };
}

function selectedComponent(rows, category, components) {
  const row = (rows || []).find(item => item.category === category);
  return row ? components.get(row.component_id) || null : null;
}

function visualStyle({ deck, topology, wheel, brake, drive }) {
  let brakeFamily = "none";
  if (brake) {
    brakeFamily =
      brake.interfaces?.brake_family ||
      (brake.id === "BRAKE-V5" ? "mbs_v5_mechanical" : "friction_brake");
  }

  let driveType = "none";
  if (drive) {
    driveType =
      drive.interfaces?.drive_type ||
      (drive.id === "DRIVE-G1-DUAL" ? "gear" : "drive");
  }

  return {
    deck_shape: deck.shape_family || "generic_mountainboard",
    steering_family: topology.steering_family || "generic",
    wheel_family: wheel.hub_family || wheel.wheel_class || "none",
    brake_family: brakeFamily,
    drive_type: driveType,
  };
}

function baseVisualState({
  scope,
  subjectId,
  label,
  vendorFamily,
  deckId,
  topologyId,
  wheelId,
  stanceMm,
  layers,
  brakeComponent,
  driveComponent,
  readiness,
  checkoutState,
  fitScore,
  cost,
  geometry,
  catalog,
}) {
  const { decks, topologies, components } = visualIndices(geometry, catalog);
  const deck = decks.get(deckId);
  const topology = topologies.get(topologyId);
  if (!deck) throw new Error("Unknown visual deck candidate " + deckId);
  if (!topology) throw new Error("Unknown visual topology " + topologyId);

  const stance = stanceMm === null || stanceMm === undefined ? null : Number(stanceMm);
  if (stance !== null && (!Number.isFinite(stance) || stance < 260 || stance > 520)) {
    throw new Error("Visual stance outside 260..520 mm study bounds");
  }

  const wheel = wheelState(wheelId, components);
  const resolveComponent = value => {
    if (!value) return null;
    const id = typeof value === "string"
      ? value
      : (value.component_id || value.id || null);
    return id ? components.get(id) || null : null;
  };
  const brake = resolveComponent(brakeComponent);
  const drive = resolveComponent(driveComponent);

  return {
    schema_version: 1,
    scope,
    subject_id: subjectId,
    vendor_family: vendorFamily || "Custom mix",
    label,
    deck: {
      id: deckId,
      manufacturer: deck.manufacturer || null,
      length_mm: Number(deck.length_mm),
      width_mm: Number(deck.width_mm),
      wheelbase_mm: deck.wheelbase_mm == null ? null : Number(deck.wheelbase_mm),
      tip_angle_deg: deck.tip_angle_deg == null ? null : Number(deck.tip_angle_deg),
      shape_family: deck.shape_family || "generic_mountainboard",
      evidence_state: deck.evidence_state,
    },
    topology: {
      id: topologyId,
      manufacturer: topology.manufacturer || null,
      truck_total_width_mm: Number(topology.truck_total_width_mm),
      wheel_center_lateral_mm: Number(topology.wheel_center_lateral_mm),
      steering_family: topology.steering_family || "generic",
      axle_diameter_mm: topology.axle_diameter_mm == null ? null : Number(topology.axle_diameter_mm),
      evidence_state: topology.evidence_state,
      visual_geometry_state: topology.visual_geometry_state || null,
    },
    wheel,
    stance_mm: stance,
    layers: Object.fromEntries(
      ["brake", "drive", "pack", "snowdeck", "armor", "dock"].map(key => [key, Boolean(layers?.[key])])
    ),
    visual_style: visualStyle({ deck, topology, wheel, brake, drive }),
    readiness,
    checkout_state: checkoutState,
    fit_score: fitScore === null || fitScore === undefined ? null : Number(fitScore),
    cost: structuredClone(cost),
    views: ["hero", "top", "side"],
    authority: {
      visualization_only: true,
      procurement_authorized: false,
      fabrication_authorized: false,
      powered_operation_authorized: false,
    },
  };
}

export function visualStateFromCandidate(candidate, geometry, catalog) {
  const { components } = visualIndices(geometry, catalog);
  const brake = selectedComponent(candidate.bom, "brake", components);
  const drive = selectedComponent(candidate.bom, "drive", components);
  return baseVisualState({
    scope: "candidate_preview",
    subjectId: candidate.id,
    label: candidate.label,
    vendorFamily: candidate.vendor_family || "Unspecified",
    deckId: candidate.deck_candidate_id,
    topologyId: candidate.topology_id,
    wheelId: candidateWheelId(candidate),
    stanceMm: candidate.personalized_spec?.stance_center_mm ?? null,
    layers: layersFromBom(candidate.bom),
    brakeComponent: brake,
    driveComponent: drive,
    readiness: candidate.readiness,
    checkoutState: candidate.checkout_state,
    fitScore: candidate.fit_score,
    cost: candidate.cost,
    geometry,
    catalog,
  });
}

export function visualStateFromSwap(baselineCandidate, swapResult, geometry, catalog) {
  const twin = swapResult.twin_state || {};
  return baseVisualState({
    scope: "custom_swap_preview",
    subjectId: "custom:" + baselineCandidate.id,
    label: baselineCandidate.label + " · Custom",
    vendorFamily: "Custom mix",
    deckId: twin.deck_candidate_id,
    topologyId: twin.topology_id,
    wheelId: swapResult.selection?.wheel ?? null,
    stanceMm: twin.stance_mm ?? null,
    layers: twin.layers || {},
    brakeComponent: swapResult.selection?.brake || null,
    driveComponent: swapResult.selection?.drive || null,
    readiness: swapResult.readiness,
    checkoutState: swapResult.checkout_state,
    fitScore: null,
    cost: swapResult.cost,
    geometry,
    catalog,
  });
}
