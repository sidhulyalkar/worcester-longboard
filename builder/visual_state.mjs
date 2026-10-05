function visualIndices(twinSeed, catalog) {
  const studies = twinSeed.design_studies || {};
  return {
    decks: new Map((studies.deck_candidates || []).map(row => [row.id, row])),
    topologies: new Map((studies.topology_branches || []).map(row => [row.id, row])),
    components: new Map((catalog.components || []).map(row => [row.id, row])),
  };
}

function wheelState(wheelId, components) {
  if (!wheelId) {
    return { study_id: "none", diameter_mm: 0, width_mm: 0, visible: false };
  }

  const component = components.get(wheelId);
  if (!component) throw new Error("Unknown visual wheel component " + wheelId);
  const interfaces = component.interfaces || {};

  if (wheelId === "TIRE-T1-8-REF") {
    return {
      study_id: wheelId,
      diameter_mm: Number(interfaces.measured_reference_diameter_mm),
      width_mm: Number(interfaces.measured_reference_width_mm),
      visible: true,
    };
  }
  if (wheelId === "TIRE-T2-9") {
    return {
      study_id: wheelId,
      diameter_mm: Number(interfaces.published_diameter_mm),
      width_mm: Number(interfaces.published_width_mm),
      visible: true,
    };
  }
  throw new Error("Unsupported visual wheel study " + wheelId);
}

function candidateWheelId(candidate) {
  const bomIds = new Set((candidate.bom || []).map(row => row.component_id));
  if (bomIds.has("TIRE-T2-9")) return "TIRE-T2-9";
  if (candidate.capabilities?.wheel_class === "8in_pneumatic") return "TIRE-T1-8-REF";
  return null;
}

function layersFromComponentIds(ids) {
  return {
    brake: ids.has("BRAKE-V5"),
    drive: ids.has("DRIVE-G1-DUAL"),
    pack: ids.has("BATTERY-TRAIL-CLASS") || ids.has("BATTERY-RANGE-CLASS"),
    snowdeck: ids.has("SNOWDECK-V01-CUSTOM"),
    armor: ids.has("TRAIL-ARMOR-STUDY"),
    dock: ids.has("PASSIVE-DOCK-STUDY"),
  };
}

function baseVisualState({
  scope,
  subjectId,
  label,
  deckId,
  topologyId,
  wheelId,
  stanceMm,
  layers,
  readiness,
  checkoutState,
  fitScore,
  cost,
  twinSeed,
  catalog,
}) {
  const { decks, topologies, components } = visualIndices(twinSeed, catalog);
  const deck = decks.get(deckId);
  const topology = topologies.get(topologyId);
  if (!deck) throw new Error("Unknown visual deck candidate " + deckId);
  if (!topology) throw new Error("Unknown visual topology " + topologyId);

  const stance = stanceMm === null || stanceMm === undefined ? null : Number(stanceMm);
  if (stance !== null && (!Number.isFinite(stance) || stance < 260 || stance > 520)) {
    throw new Error("Visual stance outside 260..520 mm study bounds");
  }

  return {
    schema_version: 1,
    scope,
    subject_id: subjectId,
    label,
    deck: {
      id: deckId,
      length_mm: Number(deck.length_mm),
      width_mm: Number(deck.width_mm),
      evidence_state: deck.evidence_state,
    },
    topology: {
      id: topologyId,
      truck_total_width_mm: Number(topology.truck_total_width_mm),
      wheel_center_lateral_mm: Number(topology.wheel_center_lateral_mm),
      evidence_state: topology.evidence_state,
    },
    wheel: wheelState(wheelId, components),
    stance_mm: stance,
    layers: Object.fromEntries(
      ["brake", "drive", "pack", "snowdeck", "armor", "dock"].map(key => [key, Boolean(layers?.[key])])
    ),
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

export function visualStateFromCandidate(candidate, twinSeed, catalog) {
  const ids = new Set((candidate.bom || []).map(row => row.component_id));
  return baseVisualState({
    scope: "candidate_preview",
    subjectId: candidate.id,
    label: candidate.label,
    deckId: candidate.deck_candidate_id,
    topologyId: candidate.topology_id,
    wheelId: candidateWheelId(candidate),
    stanceMm: candidate.personalized_spec?.stance_center_mm ?? null,
    layers: layersFromComponentIds(ids),
    readiness: candidate.readiness,
    checkoutState: candidate.checkout_state,
    fitScore: candidate.fit_score,
    cost: candidate.cost,
    twinSeed,
    catalog,
  });
}

export function visualStateFromSwap(baselineCandidate, swapResult, twinSeed, catalog) {
  const twin = swapResult.twin_state || {};
  return baseVisualState({
    scope: "custom_swap_preview",
    subjectId: "custom:" + baselineCandidate.id,
    label: baselineCandidate.label + " · Custom",
    deckId: twin.deck_candidate_id,
    topologyId: twin.topology_id,
    wheelId: swapResult.selection?.wheel ?? null,
    stanceMm: twin.stance_mm ?? null,
    layers: twin.layers || {},
    readiness: swapResult.readiness,
    checkoutState: swapResult.checkout_state,
    fitScore: null,
    cost: swapResult.cost,
    twinSeed,
    catalog,
  });
}
