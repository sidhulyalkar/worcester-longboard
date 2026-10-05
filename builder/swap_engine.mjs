import { READINESS_RANK } from "./engine.mjs";

const uniq = values => [...new Set(values)];

function worsen(current, candidate) {
  return READINESS_RANK[candidate] > READINESS_RANK[current] ? candidate : current;
}

function componentIndex(catalog) {
  return new Map(catalog.components.map(row => [row.id, row]));
}

function priceRange(component) {
  const price = component.price;
  if (!price) return null;
  const qty = Number(price.qty || 1);
  if (price.kind === "unit" || price.kind === "ceiling") {
    const value = Number(price.unit_price_usd) * qty;
    return [value, value];
  }
  if (price.kind === "range") {
    return [Number(price.min_usd) * qty, Number(price.max_usd) * qty];
  }
  throw new Error("Unknown price kind " + price.kind + " for " + component.id);
}

function bomRows(ids, catalog) {
  const index = componentIndex(catalog);
  let low = 0;
  let high = 0;
  const unpriced = [];
  const rows = [];
  for (const id of uniq(ids)) {
    const component = index.get(id);
    if (!component) throw new Error("Unknown catalog component " + id);
    const range = priceRange(component);
    if (range) {
      low += range[0];
      high += range[1];
    } else {
      unpriced.push(id);
    }
    rows.push({
      component_id: id,
      category: component.category,
      label: component.label,
      manufacturer: component.manufacturer || null,
      sku: component.sku || null,
      evidence_state: component.evidence_state,
      procurement_state: component.procurement_state,
      price: component.price || null,
      source_url: component.source && component.source.url ? component.source.url : null,
      source_as_of: component.source ? component.source.as_of : null,
      hold_reason: component.hold_reason || null,
    });
  }
  return {
    rows,
    cost: {
      known_min_usd: Number(low.toFixed(2)),
      known_max_usd: Number(high.toFixed(2)),
      unpriced_component_ids: unpriced,
      shipping_tax_included: false,
    },
  };
}

function slotOptionIndex(slots) {
  const out = {};
  for (const slot of slots.slots) {
    out[slot.id] = new Map(slot.options.map(option => [option.value, option]));
  }
  return out;
}

export function seedSwapSelection(candidate) {
  const bomIds = new Set(candidate.bom.map(row => row.component_id));
  let wheel = null;
  if (candidate.capabilities && candidate.capabilities.wheel_class === "8in_pneumatic") {
    wheel = "TIRE-T1-8-REF";
  } else if (bomIds.has("TIRE-T2-9")) {
    wheel = "TIRE-T2-9";
  }

  let battery = null;
  for (const id of ["BATTERY-TRAIL-CLASS", "BATTERY-RANGE-CLASS"]) {
    if (bomIds.has(id)) {
      battery = id;
      break;
    }
  }

  return {
    deck: candidate.deck_candidate_id,
    topology: candidate.topology_id,
    wheel,
    brake: bomIds.has("BRAKE-V5") ? "BRAKE-V5" : null,
    drive: bomIds.has("DRIVE-G1-DUAL") ? "DRIVE-G1-DUAL" : null,
    battery,
    rider_interface: bomIds.has("SNOWDECK-V01-CUSTOM") ? "SNOWDECK-V01-CUSTOM" : null,
    armor: bomIds.has("TRAIL-ARMOR-STUDY") ? "TRAIL-ARMOR-STUDY" : null,
    dock: bomIds.has("PASSIVE-DOCK-STUDY") ? "PASSIVE-DOCK-STUDY" : null,
  };
}

export function validateSwapSelection(selection, slots) {
  const options = slotOptionIndex(slots);
  const expected = new Set(Object.keys(options));
  const actual = new Set(Object.keys(selection));
  const missing = [...expected].filter(key => !actual.has(key));
  const extra = [...actual].filter(key => !expected.has(key));
  if (missing.length || extra.length) {
    throw new Error("Swap selection keys mismatch; missing=" + missing.join(",") + " extra=" + extra.join(","));
  }
  for (const [slotId, value] of Object.entries(selection)) {
    if (!options[slotId].has(value)) {
      throw new Error(slotId + ": unknown swap option " + String(value));
    }
  }
}

function ruleMatches(rule, selection) {
  return Object.entries(rule.when || {}).every(([key, value]) => selection[key] === value);
}

export function resolveSwapComponentIds(selection, slots) {
  validateSwapSelection(selection, slots);
  const options = slotOptionIndex(slots);
  const packaged = (slots.packaged_foundation_rules || []).find(rule => ruleMatches(rule, selection));

  const ids = [];
  if (packaged) {
    ids.push(...(packaged.use || []));
  } else {
    for (const slotId of ["deck", "topology", "wheel"]) {
      const option = options[slotId].get(selection[slotId]);
      if (option && option.component_id) ids.push(option.component_id);
    }
    if (selection.wheel === "TIRE-T1-8-REF" || selection.wheel === "TIRE-T2-9") {
      ids.push("HUB-RSII");
    }
    ids.push(...((slots.topology_support_components || {})[selection.topology] || []));
  }

  for (const slotId of ["brake", "drive", "battery", "rider_interface", "armor", "dock"]) {
    const value = selection[slotId];
    if (!value) continue;
    const option = options[slotId].get(value);
    if (option && option.component_id) ids.push(option.component_id);
  }

  if (selection.drive) {
    ids.push(...((slots.automatic_support_components || {})[selection.drive] || []));
  }

  return uniq(ids);
}

function pairFindings(ids, compatibility) {
  const selected = new Set(ids);
  const findings = [];
  for (const rule of compatibility.pair_rules || []) {
    if (!selected.has(rule.a) || !selected.has(rule.b)) continue;
    findings.push({
      id: rule.id,
      state: rule.state,
      a: rule.a,
      b: rule.b,
      reason: rule.reason,
    });
  }
  return findings;
}

function batteryMaxWh(selection, catalog) {
  if (!selection.battery) return null;
  const component = componentIndex(catalog).get(selection.battery);
  const energy = component && component.interfaces ? component.interfaces.energy_class_wh : null;
  if (!energy) return null;
  return Math.max(...energy.map(Number));
}

export function evaluateSwap(baselineCandidate, requirements, selection, bundle, slots) {
  validateSwapSelection(selection, slots);
  const ids = resolveSwapComponentIds(selection, slots);
  const packed = bomRows(ids, bundle.catalog);
  const bom = packed.rows;
  const cost = packed.cost;
  const findings = pairFindings(ids, bundle.compatibility);

  let readiness = "REFERENCE_COMPATIBLE";
  const blockers = [];
  const unknowns = [];
  const notes = [];

  for (const finding of findings) {
    if (finding.state === "INCOMPATIBLE") {
      readiness = worsen(readiness, "INCOMPATIBLE");
      blockers.push(finding.reason);
    } else if (finding.state === "MEASURE_FIRST" || finding.state === "UNKNOWN") {
      readiness = worsen(readiness, "MEASURE_FIRST");
      unknowns.push(finding.reason);
    }
  }

  if (selection.deck !== "comp95") {
    readiness = worsen(readiness, "MEASURE_FIRST");
    unknowns.push(
      "Deck-to-truck structural interface is not normalized for this seed catalog; received geometry or a sourced mount pattern is required."
    );
  }

  if (requirements.independent_friction_brake_required && !selection.brake) {
    readiness = worsen(readiness, "BLOCKED");
    blockers.push(
      "The rider mission requires an independent friction brake, but the edited design removes it."
    );
  }

  if (requirements.electric_intent !== "no") {
    if (!selection.drive) {
      readiness = worsen(readiness, "MEASURE_FIRST");
      unknowns.push(
        "The rider requested an electric-capable mission, but the edited design contains no drive."
      );
    } else if (!selection.battery) {
      readiness = worsen(readiness, "BLOCKED");
      blockers.push("A drive is selected without a traction-energy class.");
    }
  }

  if (selection.battery && !selection.drive) {
    readiness = worsen(readiness, "MEASURE_FIRST");
    unknowns.push(
      "A traction-energy class is selected without a drive; keep it only as a packaging study."
    );
  }

  const maxWh = batteryMaxWh(selection, bundle.catalog);
  if (maxWh !== null && Number(requirements.planning_installed_energy_wh) > maxWh) {
    readiness = worsen(readiness, "BLOCKED");
    blockers.push(
      "Derived mission energy (" + Number(requirements.planning_installed_energy_wh).toFixed(0) +
      " Wh) exceeds the selected battery-class ceiling (" + maxWh.toFixed(0) + " Wh)."
    );
  }

  if (
    requirements.wheel_strategy === "nine_inch_rollover_study" &&
    selection.wheel === "TIRE-T1-8-REF"
  ) {
    readiness = worsen(readiness, "MEASURE_FIRST");
    unknowns.push(
      "The terrain model calls for a 9-inch rollover study, but the edited design retains the 8-inch reference."
    );
  }

  if (selection.wheel === "TIRE-T2-9") {
    notes.push(
      "The 9-inch tire is a rollover study only; hub fit, clearance and gearing remain separate checks."
    );
  }

  const procurementStates = new Set(bom.map(row => row.procurement_state));
  let checkout = "SOURCE_LINKS";
  if (procurementStates.has("POWER_GATED") || blockers.length) {
    checkout = "BLOCKED";
  } else if ([...procurementStates].some(value => value === "HOLD_MEASURE" || value === "STUDY_ONLY")) {
    checkout = "HOLD_MEASURE";
  }

  const baselineCost = baselineCandidate.cost;
  const baselineSelection = seedSwapSelection(baselineCandidate);
  const changes = Object.keys(baselineSelection)
    .filter(slot => baselineSelection[slot] !== selection[slot])
    .map(slot => ({ slot, from: baselineSelection[slot], to: selection[slot] }));

  const layers = {
    brake: Boolean(selection.brake),
    drive: Boolean(selection.drive),
    pack: Boolean(selection.battery),
    snowdeck: Boolean(selection.rider_interface),
    armor: Boolean(selection.armor),
    dock: Boolean(selection.dock),
  };

  return {
    schema_version: 1,
    scope: "non_authoritative_component_swap_study",
    baseline_candidate_id: baselineCandidate.id,
    selection: structuredClone(selection),
    changes,
    readiness,
    checkout_state: checkout,
    bom,
    cost,
    cost_delta_vs_baseline: {
      known_min_usd: Number((cost.known_min_usd - baselineCost.known_min_usd).toFixed(2)),
      known_max_usd: Number((cost.known_max_usd - baselineCost.known_max_usd).toFixed(2)),
    },
    compatibility_findings: findings,
    blockers: uniq(blockers),
    unknowns: uniq(unknowns),
    notes: uniq(notes),
    twin_state: {
      deck_candidate_id: selection.deck,
      topology_id: selection.topology,
      stance_mm: baselineCandidate.personalized_spec
        ? baselineCandidate.personalized_spec.stance_center_mm
        : null,
      layers,
    },
    authority: {
      procurement_authorized: false,
      fabrication_authorized: false,
      powered_operation_authorized: false,
      generic_builder_may_promote_x1_authority: false,
    },
  };
}
