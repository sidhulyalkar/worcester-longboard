import { READINESS_RANK, scoreArchitecture } from "./engine.mjs";
import { evaluateSwap } from "./swap_engine.mjs";

const clamp = (value, lo = 0, hi = 1) => Math.min(hi, Math.max(lo, value));
const uniq = values => [...new Set(values)];

function slotOptionIndex(slots) {
  const out = {};
  for (const slot of slots.slots || []) {
    out[slot.id] = new Map((slot.options || []).map(option => [option.value, option]));
  }
  return out;
}

function componentIndex(catalog) {
  return new Map((catalog.components || []).map(row => [row.id, row]));
}

function normalized(value, bounds) {
  const [lo, hi] = bounds.map(Number);
  if (!(hi > lo)) return 0.5;
  return clamp((Number(value) - lo) / (hi - lo));
}

function chosenBattery(requirements, composer) {
  if (requirements.electric_intent === "no") return null;
  const classes = composer.electric_policy?.battery_classes || [];
  const energy = Number(requirements.planning_installed_energy_wh);
  if (energy <= 650 && classes.includes("BATTERY-TRAIL-CLASS")) {
    return "BATTERY-TRAIL-CLASS";
  }
  if (classes.includes("BATTERY-RANGE-CLASS")) return "BATTERY-RANGE-CLASS";
  return classes[0] || null;
}

function geometryIndex(geometry) {
  return {
    decks: new Map((geometry.decks || []).map(row => [row.id, row])),
    topologies: new Map((geometry.topologies || []).map(row => [row.id, row])),
  };
}

function wheelGeometry(component) {
  const interfaces = component?.interfaces || {};
  return {
    diameter_mm: Number(
      interfaces.measured_reference_diameter_mm ??
      interfaces.published_diameter_mm ??
      0
    ),
    width_mm: Number(
      interfaces.measured_reference_width_mm ??
      interfaces.published_width_mm ??
      0
    ),
    wheel_class: interfaces.wheel_class || "unknown",
  };
}

function pathState(selectedId, category, evaluation) {
  if (!selectedId) return "NOT_PRESENT";
  const rows = evaluation.bom.filter(row => row.category === category);
  if (!rows.some(row => row.component_id === selectedId)) return "NOT_PRESENT";

  const relevant = evaluation.compatibility_findings.filter(
    finding => finding.a === selectedId || finding.b === selectedId
  );
  if (relevant.some(finding => finding.state === "INCOMPATIBLE")) return "INCOMPATIBLE";
  if (relevant.some(finding =>
    finding.state === "UNKNOWN" || finding.state === "MEASURE_FIRST"
  )) return "MEASURE_FIRST";
  return "REFERENCE_COMPATIBLE";
}

function vendorFamily(evaluation) {
  const makers = uniq(
    evaluation.bom
      .map(row => row.manufacturer)
      .filter(Boolean)
      .map(String)
  ).sort();
  if (!makers.length) return "Catalog mix";
  if (makers.length === 1) return makers[0];
  return "Cross-vendor";
}

function traitsFor(selection, evaluation, bundle) {
  const model = bundle.composer.trait_model;
  const { decks, topologies } = geometryIndex(bundle.geometry);
  const components = componentIndex(bundle.catalog);
  const deck = decks.get(selection.deck);
  const topology = topologies.get(selection.topology);
  const wheel = wheelGeometry(components.get(selection.wheel));
  const drive = selection.drive ? components.get(selection.drive) : null;
  const brake = selection.brake ? components.get(selection.brake) : null;

  const deckN = normalized(deck?.length_mm ?? 950, model.deck_length_bounds_mm);
  const truckN = normalized(
    topology?.truck_total_width_mm ?? 400,
    model.truck_width_bounds_mm
  );
  const wheelN = normalized(
    wheel.diameter_mm || 200,
    model.wheel_diameter_bounds_mm
  );

  const steering = String(topology?.steering_family || "");
  let steeringCarve = 0.04;
  if (steering.includes("channel")) steeringCarve = 0.08;
  else if (steering.includes("parallel")) steeringCarve = 0.05;
  else if (steering.includes("precision")) steeringCarve = 0.10;

  const driveType = String(drive?.interfaces?.drive_type || "none");
  const powered = Boolean(selection.drive);
  const batteryRange = selection.battery === "BATTERY-RANGE-CLASS";
  const unknownPenalty = Math.min(0.12, evaluation.unknowns.length * 0.03);
  const knownCost = Number(evaluation.cost.known_min_usd || 0);
  const unpricedPenalty = Math.min(
    0.20,
    (evaluation.cost.unpriced_component_ids || []).length * 0.04
  );

  let lowMaintenance = 0.92;
  if (driveType === "gear") lowMaintenance = 0.72;
  else if (driveType.includes("belt")) lowMaintenance = 0.56;
  else if (powered) lowMaintenance = 0.62;
  if (String(brake?.interfaces?.brake_family || "").includes("hs11")) {
    lowMaintenance -= 0.04;
  }

  const r6 = value => Number(clamp(value).toFixed(6));
  return {
    range: r6(powered ? (batteryRange ? 0.95 : 0.76) : 0.18),
    carve: r6(0.70 + (1 - deckN) * 0.15 + steeringCarve - truckN * 0.03),
    stability: r6(0.58 + truckN * 0.17 + deckN * 0.10 + wheelN * 0.06),
    durability: r6(0.84 - (powered ? 0.07 : 0) - unknownPenalty),
    portability: r6(0.93 - deckN * 0.18 - wheelN * 0.12 - (powered ? 0.16 : 0)),
    cost: r6(
      1 -
      knownCost / Number(model.known_cost_reference_usd || 2500) -
      unpricedPenalty
    ),
    low_maintenance: r6(lowMaintenance - unknownPenalty * 0.4),
    rough_terrain: r6(0.58 + wheelN * 0.30 + truckN * 0.08),
  };
}

function visualPreset(selection) {
  if (selection.drive) return "drive_packaging";
  if (selection.brake) return "brake_first_trail";
  return "snowdeck_fit";
}

function shortOptionLabel(options, slot, value) {
  const label = options[slot]?.get(value)?.label || String(value ?? "none");
  return label.split("·")[0].trim();
}

function compositionLabel(selection, options) {
  const deck = shortOptionLabel(options, "deck", selection.deck);
  const truck = shortOptionLabel(options, "topology", selection.topology);
  const wheel = shortOptionLabel(options, "wheel", selection.wheel);
  return "Compose · " + deck + " / " + truck + " / " + wheel;
}

function slug(value) {
  return String(value ?? "none")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function selectionId(selection) {
  return [
    "synth",
    slug(selection.deck),
    slug(selection.topology),
    slug(selection.wheel),
    slug(selection.brake),
    slug(selection.drive),
    slug(selection.battery),
  ].join("__");
}

function syntheticBaseline(requirements, selection) {
  return {
    id: "catalog_composer_seed",
    architecture_id: "catalog_composer_seed",
    label: "Catalog composer seed",
    deck_candidate_id: selection.deck,
    topology_id: selection.topology,
    bom: [],
    cost: {
      known_min_usd: 0,
      known_max_usd: 0,
      unpriced_component_ids: [],
      shipping_tax_included: false,
    },
    capabilities: {
      wheel_class: "unknown",
    },
    personalized_spec: {
      stance_center_mm: requirements.stance_study.center_mm,
    },
    swap_defaults: structuredClone(selection),
  };
}

function architectureFromSelection(profile, requirements, selection, evaluation, bundle) {
  const options = slotOptionIndex(bundle.swapSlots);
  const components = componentIndex(bundle.catalog);
  const wheelComponent = components.get(selection.wheel);
  const wheelClass = wheelComponent?.interfaces?.wheel_class || "unknown";
  const brakePath = pathState(selection.brake, "brake", evaluation);
  const drivePath = pathState(selection.drive, "drive", evaluation);
  const family = vendorFamily(evaluation);
  const id = selectionId(selection);

  const architecture = {
    id,
    label: compositionLabel(selection, options),
    short_label: family === "Cross-vendor" ? "Composed mix" : "Composed " + family,
    vendor_family: family,
    description:
      "Catalog-composed planning study generated from normalized parts. " +
      "Every critical interface is evaluated through the same fail-closed compatibility rules as Swap Lab.",
    visual_preset: visualPreset(selection),
    deck_candidate_id: selection.deck,
    topology_id: selection.topology,
    traits: traitsFor(selection, evaluation, bundle),
    capabilities: {
      friction_brake_path: brakePath,
      drive_path: drivePath,
      electric_complete: false,
      wheel_class: wheelClass,
      snowdeck: false,
    },
    bom: evaluation.bom.map(row => row.component_id),
    known_unknowns: [...evaluation.unknowns],
    hard_blockers: [...evaluation.blockers],
  };

  const scored = scoreArchitecture(
    profile,
    requirements,
    architecture,
    bundle.catalog,
    bundle.compatibility
  );
  scored.origin = "SYNTHESIZED";
  scored.swap_defaults = structuredClone(selection);
  scored.composition = {
    schema_version: 1,
    engine: "catalog_composer_v1",
    selection: structuredClone(selection),
    manufacturers: uniq(
      evaluation.bom.map(row => row.manufacturer).filter(Boolean).map(String)
    ).sort(),
    compatibility_states: Object.fromEntries(
      ["REFERENCE_COMPATIBLE", "MEASURE_FIRST", "UNKNOWN", "INCOMPATIBLE"].map(
        state => [
          state,
          evaluation.compatibility_findings.filter(finding => finding.state === state).length,
        ]
      )
    ),
    unknown_count: evaluation.unknowns.length,
    rationale:
      "Generated from catalog slots, pruned by Swap Lab compatibility, then scored by the standard rider-fit engine.",
  };
  return scored;
}

function bomSignature(candidate) {
  return (candidate.bom || [])
    .map(row => row.component_id)
    .sort()
    .join("|");
}

export function composeCandidates(profile, requirements, bundle) {
  const composer = bundle.composer;
  if (!composer?.enabled) return [];

  const slotOptions = slotOptionIndex(bundle.swapSlots);
  const allowed = composer.allowed_readiness || [
    "REFERENCE_COMPATIBLE",
    "MEASURE_FIRST",
  ];
  const battery = chosenBattery(requirements, composer);
  const drives =
    requirements.electric_intent === "no"
      ? [composer.manual_policy?.drive ?? null]
      : [...(composer.slots.drive || [])];
  const batteries =
    requirements.electric_intent === "no"
      ? [composer.manual_policy?.battery ?? null]
      : [battery];
  const brakes = requirements.independent_friction_brake_required
    ? [...(composer.slots.brake || [])]
    : [null, ...(composer.slots.brake || [])];

  const selections = [];
  let rawCount = 0;
  outer:
  for (const deck of composer.slots.deck || []) {
    for (const topology of composer.slots.topology || []) {
      for (const wheel of composer.slots.wheel || []) {
        for (const brake of brakes) {
          for (const drive of drives) {
            for (const selectedBattery of batteries) {
              rawCount += 1;
              if (rawCount > Number(composer.max_raw_combinations || 5000)) break outer;
              if (drive && !selectedBattery) continue;
              if (!drive && selectedBattery) continue;
              selections.push({
                deck,
                topology,
                wheel,
                brake,
                drive,
                battery: selectedBattery,
                rider_interface: composer.fixed_selection?.rider_interface ?? null,
                armor: composer.fixed_selection?.armor ?? null,
                dock: composer.fixed_selection?.dock ?? null,
              });
            }
          }
        }
      }
    }
  }

  const candidates = [];
  const seenBom = new Set();
  for (const selection of selections) {
    // Skip stale config values instead of allowing a malformed composer contract
    // to create phantom components.
    const valid = Object.entries(selection).every(([slot, value]) =>
      slotOptions[slot]?.has(value)
    );
    if (!valid) continue;

    const evaluation = evaluateSwap(
      syntheticBaseline(requirements, selection),
      requirements,
      selection,
      bundle,
      bundle.swapSlots
    );

    if (!allowed.includes(evaluation.readiness)) continue;
    if (evaluation.blockers.length) continue;
    if (
      evaluation.unknowns.length >
      Number(composer.max_unknown_findings ?? 3)
    ) continue;

    const candidate = architectureFromSelection(
      profile,
      requirements,
      selection,
      evaluation,
      bundle
    );
    if (!allowed.includes(candidate.readiness)) continue;
    if (candidate.blockers.length) continue;

    const signature = bomSignature(candidate);
    if (seenBom.has(signature)) continue;
    seenBom.add(signature);
    candidates.push(candidate);
  }

  candidates.sort(
    (a, b) =>
      b.fit_score - a.fit_score ||
      READINESS_RANK[a.readiness] - READINESS_RANK[b.readiness] ||
      a.id.localeCompare(b.id)
  );

  const selected = [];
  const familyCounts = new Map();
  const maxPerFamily = Number(composer.max_per_vendor_family || 3);
  for (const candidate of candidates) {
    const count = familyCounts.get(candidate.vendor_family) || 0;
    if (count >= maxPerFamily) continue;
    selected.push(candidate);
    familyCounts.set(candidate.vendor_family, count + 1);
    if (selected.length >= Number(composer.max_synthesized_candidates || 8)) break;
  }

  return selected;
}
