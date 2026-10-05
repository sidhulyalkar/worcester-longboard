export const READINESS_RANK = {
  REFERENCE_COMPATIBLE: 0,
  MEASURE_FIRST: 1,
  BLOCKED: 2,
  INCOMPATIBLE: 3,
};

const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
const uniq = xs => [...new Set(xs)];

export function questionnaireDefaults(questionnaire) {
  const out = {};
  for (const section of questionnaire.sections || []) {
    for (const field of section.fields || []) {
      out[field.id] = field.default === undefined ? null : structuredClone(field.default);
    }
  }
  return out;
}

export function normalizeProfile(profile, questionnaire) {
  const out = questionnaireDefaults(questionnaire);
  for (const [key, value] of Object.entries(profile || {})) {
    if (value !== "") out[key] = value;
  }
  return out;
}

function terrainMix(profile) {
  const keyMap = {
    pavement: "terrain_pavement",
    packed_dirt: "terrain_packed_dirt",
    loose_gravel: "terrain_loose_gravel",
    roots_rocks: "terrain_roots_rocks",
    grass_brush: "terrain_grass_brush",
  };
  let raw = Object.fromEntries(Object.entries(keyMap).map(([name, key]) => [name, Math.max(0, Number(profile[key] || 0))]));
  let total = Object.values(raw).reduce((a, b) => a + b, 0);
  const warnings = [];
  if (total <= 0) {
    raw = { pavement: 20, packed_dirt: 35, loose_gravel: 25, roots_rocks: 15, grass_brush: 5 };
    total = 100;
    warnings.push("Terrain mix was empty; builder defaults were used.");
  } else if (Math.abs(total - 100) > 1e-6) {
    warnings.push("Terrain sliders totaled " + total.toFixed(0) + "%; they were normalized to 100% for planning.");
  }
  return {
    terrain: Object.fromEntries(Object.entries(raw).map(([k, v]) => [k, v / total])),
    warnings,
  };
}

function priorities(profile) {
  const keyMap = {
    range: "priority_range",
    carve: "priority_carve",
    stability: "priority_stability",
    durability: "priority_durability",
    portability: "priority_portability",
    cost: "priority_cost",
    low_maintenance: "priority_low_maintenance",
  };
  const raw = Object.fromEntries(Object.entries(keyMap).map(([name, key]) => [name, Math.max(0, Number(profile[key] || 0))]));
  const total = Object.values(raw).reduce((a, b) => a + b, 0);
  if (total <= 0) {
    const share = 1 / Object.keys(raw).length;
    return Object.fromEntries(Object.keys(raw).map(k => [k, share]));
  }
  return Object.fromEntries(Object.entries(raw).map(([k, v]) => [k, v / total]));
}

export function deriveRequirements(profile, rules, questionnaire) {
  const p = normalizeProfile(profile, questionnaire);
  const mix = terrainMix(p);
  const terrain = mix.terrain;
  const warnings = [...mix.warnings];

  const loadedLb = Number(p.weight_lb) + Number(p.cargo_lb || 0);
  const loadedKg = loadedLb * rules.unit_conversions.lb_to_kg;
  const energy = rules.energy;
  const massFactor = Math.pow(loadedLb / energy.reference_loaded_mass_lb, energy.mass_exponent);
  const terrainFactor = Object.entries(terrain).reduce((s, [name, share]) => s + share * energy.terrain_multipliers[name], 0);
  const hillFactor = energy.hill_multipliers[p.hill_profile];
  const stopFactor = p.stop_start ? energy.stop_start_multiplier : 1;
  const whPerMile = energy.base_wh_per_mile * massFactor * terrainFactor * hillFactor * stopFactor;

  const typical = Number(p.typical_miles);
  const longest = Number(p.longest_miles);
  const targetRange = Math.max(longest, typical * energy.target_range_typical_multiplier);
  if (longest < typical) warnings.push("Longest desired ride was shorter than typical ride; typical-ride reserve controls.");

  const roughFraction = terrain.loose_gravel + terrain.roots_rocks + terrain.grass_brush + 0.35 * terrain.packed_dirt;
  let reserve = energy.reserve_fraction_base;
  if (roughFraction >= rules.wheel_strategy.rollover_rough_fraction_threshold) reserve += energy.reserve_fraction_rough_bonus;
  if (p.wet_exposure === "frequent") reserve += energy.reserve_fraction_wet_bonus;
  if (["steep", "long_descents"].includes(p.hill_profile)) reserve += energy.reserve_fraction_steep_bonus;
  reserve = Math.min(reserve, energy.reserve_fraction_max);
  const installedWh = targetRange * whPerMile / Math.max(0.5, 1 - reserve);

  let wheelStrategy = "eight_inch_pneumatic_reference";
  if (
    roughFraction >= rules.wheel_strategy.rollover_rough_fraction_threshold &&
    terrain.roots_rocks >= rules.wheel_strategy.rollover_roots_fraction_threshold
  ) {
    wheelStrategy = "nine_inch_rollover_study";
  } else if (
    terrain.pavement >= rules.wheel_strategy.pavement_efficiency_fraction_threshold &&
    roughFraction < 0.15
  ) {
    wheelStrategy = "pavement_efficiency_study";
  }

  let brakeRequired = p.hill_profile === "long_descents";
  if (
    p.electric_propulsion !== "no" &&
    (Number(p.speed_ceiling_mph) >= rules.brake.powered_speed_threshold_mph || p.hill_profile !== "flat")
  ) {
    brakeRequired = true;
  }

  let stanceCenter;
  let stanceSource;
  if (p.stance_width_mm !== null && p.stance_width_mm !== undefined && p.stance_width_mm !== "") {
    stanceCenter = Number(p.stance_width_mm);
    stanceSource = "user";
  } else {
    const heightMm = Number(p.height_in) * rules.unit_conversions.in_to_mm;
    stanceCenter = clamp(heightMm * rules.stance.height_ratio, rules.stance.min_center_mm, rules.stance.max_center_mm);
    stanceSource = "height_seed";
  }
  const half = rules.stance.default_half_span_mm;

  let deckPreference = "balanced";
  if (Number(p.height_in) <= rules.deck.compact_height_in_max && p.portability_need === "high") {
    deckPreference = "compact";
  } else if (
    Number(p.height_in) >= rules.deck.long_height_in_min ||
    Number(p.stability_preference) >= rules.deck.long_stability_threshold
  ) {
    deckPreference = "long_stable";
  }

  if (Number(p.hard_budget_usd) < Number(p.budget_usd)) {
    warnings.push("Absolute maximum budget is below target budget; hard maximum controls.");
  }

  const assumptions = [
    "Energy and range are comparative planning estimates, not validated X1 telemetry.",
    "Height-derived stance is an adjustable study seed, not a rider-fit prescription.",
    "Catalog price/stock is snapshot data and must be refreshed before checkout.",
    "Questionnaire answers cannot qualify structural, brake, electrical, battery, charging, or powered-operation safety.",
  ];
  if (wheelStrategy === "nine_inch_rollover_study") {
    assumptions.push("Nine-inch wheels are a rollover study only; current standard Rockstar II compatibility is not assumed.");
  }

  return {
    schema_version: 1,
    model_class: "PLANNING_ESTIMATE",
    loaded_rider_mass_kg: Number(loadedKg.toFixed(2)),
    target_range_mi: Number(targetRange.toFixed(1)),
    energy_reserve_fraction: Number(reserve.toFixed(3)),
    planning_energy_wh_per_mi: Number(whPerMile.toFixed(1)),
    planning_installed_energy_wh: Math.round(installedWh),
    terrain_normalized: Object.fromEntries(Object.entries(terrain).map(([k, v]) => [k, Number(v.toFixed(4))])),
    rough_terrain_fraction: Number(roughFraction.toFixed(4)),
    wheel_strategy: wheelStrategy,
    independent_friction_brake_required: brakeRequired,
    stance_study: {
      center_mm: Math.round(stanceCenter),
      min_mm: Math.round(clamp(stanceCenter - half, 260, 520)),
      max_mm: Math.round(clamp(stanceCenter + half, 260, 520)),
      source: stanceSource,
    },
    deck_envelope_preference: deckPreference,
    ingress_priority: { never: "low", occasional: "medium", frequent: "high" }[p.wet_exposure],
    electric_intent: p.electric_propulsion,
    budget: { target_usd: Number(p.budget_usd), hard_max_usd: Number(p.hard_budget_usd) },
    priorities: priorities(p),
    assumptions,
    warnings,
  };
}

function componentPriceRange(component) {
  const price = component.price;
  if (!price) return null;
  const qty = Number(price.qty || 1);
  if (price.kind === "unit" || price.kind === "ceiling") {
    const v = Number(price.unit_price_usd) * qty;
    return [v, v];
  }
  if (price.kind === "range") return [Number(price.min_usd) * qty, Number(price.max_usd) * qty];
  throw new Error("Unknown price kind " + price.kind + " for " + component.id);
}

function makeBom(architecture, catalog) {
  const index = new Map(catalog.components.map(x => [x.id, x]));
  let min = 0;
  let max = 0;
  const unpriced = [];
  const rows = architecture.bom.map(id => {
    const c = index.get(id);
    if (!c) throw new Error("Unknown catalog component " + id + " in architecture " + architecture.id);
    const r = componentPriceRange(c);
    if (r) {
      min += r[0];
      max += r[1];
    } else {
      unpriced.push(id);
    }
    return {
      component_id: id,
      category: c.category,
      label: c.label,
      manufacturer: c.manufacturer || null,
      sku: c.sku || null,
      evidence_state: c.evidence_state,
      procurement_state: c.procurement_state,
      price: c.price || null,
      source_url: c.source && c.source.url ? c.source.url : null,
      source_as_of: c.source ? c.source.as_of : null,
      source_native_price: c.source ? c.source.native_price_snapshot || null : null,
      hold_reason: c.hold_reason || null,
    };
  });
  return {
    rows,
    cost: {
      known_min_usd: Number(min.toFixed(2)),
      known_max_usd: Number(max.toFixed(2)),
      unpriced_component_ids: unpriced,
      shipping_tax_included: false,
    },
  };
}

function worsen(current, next) {
  return READINESS_RANK[next] > READINESS_RANK[current] ? next : current;
}

function deckFit(requirements, deckId) {
  const allowed = {
    compact: new Set(["comp95", "trampa_short_969"]),
    balanced: new Set(["comp95", "pro_warren_iii", "trampa_short_969", "trampa_hs11_969"]),
    long_stable: new Set(["pro_warren_iii", "agent", "trampa_hs11_969"]),
  };
  if (allowed[requirements.deck_envelope_preference].has(deckId)) {
    return [0.05, "Deck envelope matches the " + requirements.deck_envelope_preference + " planning preference."];
  }
  return [-0.02, "Deck envelope differs from the " + requirements.deck_envelope_preference + " planning preference."];
}

function compatibilityFindings(selectedIds, catalog, compatibility) {
  const selected = new Set(selectedIds);
  const index = new Map(catalog.components.map(row => [row.id, row]));
  const findings = [];
  const covered = new Set();
  const pairKey = (a, b) => [a, b].sort().join("::");

  for (const rule of compatibility.pair_rules || []) {
    if (!selected.has(rule.a) || !selected.has(rule.b)) continue;
    covered.add(pairKey(rule.a, rule.b));
    findings.push({
      id: rule.id,
      state: rule.state,
      reason: rule.reason,
      a: rule.a,
      b: rule.b,
      source: "explicit_rule",
    });
  }

  const rows = [...selected].map(id => index.get(id)).filter(Boolean);
  for (const fallback of compatibility.category_pair_defaults || []) {
    const [categoryA, categoryB] = fallback.categories;
    const aRows = rows.filter(row => row.category === categoryA);
    const bRows = rows.filter(row => row.category === categoryB);
    for (const a of aRows) {
      for (const b of bRows) {
        if (a.id === b.id) continue;
        const key = pairKey(a.id, b.id);
        if (covered.has(key)) continue;
        covered.add(key);
        findings.push({
          id: "default:" + categoryA + ":" + categoryB + ":" + a.id + ":" + b.id,
          state: fallback.state,
          reason: fallback.reason,
          a: a.id,
          b: b.id,
          source: "category_default",
        });
      }
    }
  }
  return findings;
}

export function scoreArchitecture(profile, requirements, architecture, catalog, compatibility) {
  const ps = requirements.priorities;
  const traits = architecture.traits;
  const preferenceFit = {
    range: Number(traits.range),
    carve: 1 - Math.abs(Number(traits.carve) - Number(profile.snowboard_feel ?? 100) / 100),
    stability: 1 - Math.abs(Number(traits.stability) - Number(profile.stability_preference ?? 100) / 100),
    durability: Number(traits.durability),
    portability: Number(traits.portability),
    cost: Number(traits.cost),
    low_maintenance: Number(traits.low_maintenance),
  };
  const weighted = Object.keys(ps).reduce(
    (sum, key) => sum + ps[key] * clamp(preferenceFit[key], 0, 1),
    0
  );
  let score = weighted;
  const explanations = [];
  const blockers = [...(architecture.hard_blockers || [])];
  let readiness = blockers.length ? "BLOCKED" : "REFERENCE_COMPATIBLE";
  const unknowns = [...(architecture.known_unknowns || [])];

  const d = deckFit(requirements, architecture.deck_candidate_id);
  score += d[0];
  explanations.push(d[1]);

  const drive = architecture.capabilities.drive_path;
  if (requirements.electric_intent === "no") {
    if (drive === "NOT_PRESENT") {
      score += 0.06;
      explanations.push("Unpowered intent avoids unnecessary propulsion complexity.");
    } else {
      score -= 0.06;
      explanations.push("This architecture carries drive complexity despite an unpowered mission.");
    }
  } else if (drive === "REFERENCE_COMPATIBLE") {
    score += 0.06;
    explanations.push("Drive reference aligns with the electric mission intent.");
  } else if (drive === "MEASURE_FIRST") {
    score += 0.01;
    readiness = worsen(readiness, "MEASURE_FIRST");
    unknowns.push("Drive path is catalog-plausible but still depends on an unresolved physical interface.");
    explanations.push("Drive path is promising for the electric mission, but coexistence still needs measurement.");
  } else if (drive === "NOT_PRESENT") {
    score -= 0.14;
    readiness = worsen(readiness, "MEASURE_FIRST");
    unknowns.push("Electric propulsion is intentionally deferred in this mechanical core.");
    explanations.push("Strong mechanical baseline, but it does not yet satisfy the electric mission.");
  }

  const friction = architecture.capabilities.friction_brake_path;
  if (requirements.independent_friction_brake_required) {
    if (friction === "REFERENCE_COMPATIBLE") {
      score += 0.06;
      explanations.push("Independent friction-brake reference matches the mission requirement.");
    } else if (friction === "MEASURE_FIRST") {
      readiness = worsen(readiness, "MEASURE_FIRST");
      unknowns.push("Independent friction braking depends on unresolved physical coexistence.");
      explanations.push("Brake path is promising but not yet established after the axle/topology change.");
    } else {
      readiness = worsen(readiness, "BLOCKED");
      blockers.push("Mission requires independent friction braking, but this architecture has no documented path.");
      score -= 0.22;
    }
  }

  if (requirements.wheel_strategy === "nine_inch_rollover_study") {
    if (architecture.capabilities.wheel_class === "9in_pneumatic") {
      score += 0.04;
      explanations.push("Nine-inch pneumatic study directly matches the rough-terrain rollover target.");
    } else if (architecture.capabilities.wheel_class === "8in_pneumatic") {
      score -= 0.03;
      unknowns.push("Rough-terrain profile justifies a separate 9-inch rollover study.");
      explanations.push("Eight-inch pneumatics remain a lower-rollover baseline for this terrain model.");
    }
  } else if (
    requirements.wheel_strategy === "eight_inch_pneumatic_reference" &&
    architecture.capabilities.wheel_class === "8in_pneumatic"
  ) {
    score += 0.03;
    explanations.push("Eight-inch pneumatic reference matches the current terrain model.");
  }

  const resolvedArchitecture = structuredClone(architecture);
  let resolvedBom = [...resolvedArchitecture.bom];
  const energyWh = Number(requirements.planning_installed_energy_wh);
  let selectedEnergyClass = null;

  if (resolvedBom.includes("BATTERY-TRAIL-CLASS")) {
    if (energyWh <= 650) {
      selectedEnergyClass = "BATTERY-TRAIL-CLASS";
      explanations.push("The 500–650 Wh trail planning class covers the derived mission-energy envelope.");
    } else if (energyWh <= 1150) {
      resolvedBom = resolvedBom.map(item =>
        item === "BATTERY-TRAIL-CLASS" ? "BATTERY-RANGE-CLASS" : item
      );
      selectedEnergyClass = "BATTERY-RANGE-CLASS";
      explanations.push("Mission energy exceeds the trail-pack class, so this study moves to the 950–1150 Wh range class.");
    } else {
      resolvedBom = resolvedBom.map(item =>
        item === "BATTERY-TRAIL-CLASS" ? "BATTERY-RANGE-CLASS" : item
      );
      selectedEnergyClass = "BATTERY-RANGE-CLASS";
      blockers.push("Derived mission energy exceeds the largest seeded 1150 Wh planning class.");
      readiness = worsen(readiness, "BLOCKED");
    }
  } else if (resolvedBom.includes("BATTERY-RANGE-CLASS")) {
    selectedEnergyClass = "BATTERY-RANGE-CLASS";
    if (energyWh > 1150) {
      blockers.push("Derived mission energy exceeds the largest seeded 1150 Wh planning class.");
      readiness = worsen(readiness, "BLOCKED");
    }
  }

  resolvedArchitecture.bom = resolvedBom;
  const packed = makeBom(resolvedArchitecture, catalog);
  const bom = packed.rows;
  const cost = packed.cost;
  const ids = new Set(bom.map(x => x.component_id));
  const findings = compatibilityFindings(ids, catalog, compatibility);

  for (const finding of findings) {
    if (finding.state === "INCOMPATIBLE") {
      readiness = worsen(readiness, "INCOMPATIBLE");
      blockers.push(finding.reason);
    } else if (finding.state === "MEASURE_FIRST" || finding.state === "UNKNOWN") {
      readiness = worsen(readiness, "MEASURE_FIRST");
      unknowns.push(finding.reason);
    }
  }

  if (cost.known_min_usd > requirements.budget.hard_max_usd) {
    blockers.push(
      "Known-price portion alone (USD " + cost.known_min_usd.toFixed(0) +
      ") exceeds the hard budget (USD " + requirements.budget.hard_max_usd.toFixed(0) + ")."
    );
    readiness = worsen(readiness, "BLOCKED");
    score -= 0.18;
  } else if (cost.known_max_usd > requirements.budget.target_usd) {
    explanations.push("Known-price portion is above the target budget but remains below the hard maximum.");
    score -= 0.04;
  } else {
    score += 0.03;
  }

  const procurementStates = new Set(bom.map(x => x.procurement_state));
  let checkout = "SOURCE_LINKS";
  if (procurementStates.has("POWER_GATED") || blockers.length) checkout = "BLOCKED";
  else if ([...procurementStates].some(x => x === "HOLD_MEASURE" || x === "STUDY_ONLY")) checkout = "HOLD_MEASURE";

  if (cost.unpriced_component_ids.length) {
    unknowns.push("Some study/reference components are unpriced; displayed BOM total is partial.");
  }

  score = clamp(score, 0, 1);
  explanations.unshift(
    "Priority-weighted preference match is " + (weighted * 100).toFixed(0) +
    "% before mission compatibility adjustments."
  );

  return {
    id: architecture.id,
    architecture_id: architecture.id,
    label: architecture.label,
    short_label: architecture.short_label,
    vendor_family: architecture.vendor_family || "Unspecified",
    description: architecture.description,
    fit_score: Number(score.toFixed(4)),
    readiness,
    checkout_state: checkout,
    visual_preset: architecture.visual_preset,
    deck_candidate_id: architecture.deck_candidate_id,
    topology_id: architecture.topology_id,
    traits: structuredClone(traits),
    preference_fit: Object.fromEntries(
      Object.entries(preferenceFit).map(([key, value]) => [
        key,
        Number(clamp(value, 0, 1).toFixed(4)),
      ])
    ),
    capabilities: structuredClone(architecture.capabilities),
    personalized_spec: {
      target_range_mi: requirements.target_range_mi,
      planning_installed_energy_wh: requirements.planning_installed_energy_wh,
      selected_energy_class: selectedEnergyClass,
      wheel_strategy: requirements.wheel_strategy,
      stance_center_mm: requirements.stance_study.center_mm,
      stance_range_mm: [
        requirements.stance_study.min_mm,
        requirements.stance_study.max_mm,
      ],
      independent_friction_brake_required:
        requirements.independent_friction_brake_required,
    },
    bom,
    cost,
    compatibility_findings: findings,
    explanations: uniq(explanations),
    blockers: uniq(blockers),
    unknowns: uniq(unknowns),
    authority: {
      procurement_authorized: false,
      fabrication_authorized: false,
      powered_operation_authorized: false,
    },
  };
}

function nonDominated(candidates) {
  const metrics = ["range", "carve", "stability", "durability", "portability", "cost", "low_maintenance"];
  const frontier = new Set();
  for (const candidate of candidates) {
    let dominated = false;
    for (const other of candidates) {
      if (other === candidate) continue;
      const noWorse = metrics.every(m => Number(other.traits[m]) >= Number(candidate.traits[m]));
      const better = metrics.some(m => Number(other.traits[m]) > Number(candidate.traits[m]));
      if (noWorse && better) {
        dominated = true;
        break;
      }
    }
    if (!dominated) frontier.add(candidate.id);
  }
  return frontier;
}

export function generateCandidates(profile, bundle) {
  const normalized = normalizeProfile(profile, bundle.questionnaire);
  const requirements = deriveRequirements(normalized, bundle.rules, bundle.questionnaire);
  const candidates = bundle.architectures.architectures.map(a =>
    scoreArchitecture(normalized, requirements, a, bundle.catalog, bundle.compatibility)
  );
  const frontier = nonDominated(candidates);
  for (const c of candidates) c.trade_space_frontier = frontier.has(c.id);
  candidates.sort((a, b) =>
    b.fit_score - a.fit_score ||
    READINESS_RANK[a.readiness] - READINESS_RANK[b.readiness] ||
    a.label.localeCompare(b.label)
  );
  return {
    schema_version: 1,
    profile: normalized,
    requirements,
    candidates,
    winner_selected: false,
    authority: {
      generic_builder_may_promote_x1_authority: false,
      procurement_authorized: false,
      fabrication_authorized: false,
      powered_operation_authorized: false,
    },
  };
}

export function formatPrice(price) {
  if (!price) return "Unpriced";
  const qty = Number(price.qty || 1);
  if (price.kind === "unit" || price.kind === "ceiling") {
    return "USD " + (Number(price.unit_price_usd) * qty).toFixed(2);
  }
  return "USD " + (Number(price.min_usd) * qty).toFixed(2) + "–" + (Number(price.max_usd) * qty).toFixed(2);
}
