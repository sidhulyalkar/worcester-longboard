// Example inputs are authored scenarios, not safety recommendations or stocked bundles.
export function validateExampleRides(manifest, questionnaire, architectures) {
  if (manifest?.scope !== "non_authoritative_example_rider_missions" || manifest.schema_version !== 1) {
    throw new Error("Unknown example-rides contract");
  }
  const fields = new Map((questionnaire.sections || []).flatMap(s => (s.fields || []).map(f => [f.id,f])));
  const ids = new Set();
  const references = new Set((architectures.architectures || []).map(a => a.id));
  for (const scenario of manifest.scenarios || []) {
    if (!scenario.id || ids.has(scenario.id) || !references.has(scenario.reference_candidate_id)) {
      throw new Error("Duplicate/missing scenario ID or unknown reference architecture: " + scenario.id);
    }
    ids.add(scenario.id);
    if (!Number.isFinite(scenario.budget_usd) || scenario.budget_usd !== scenario.overrides.budget_usd) {
      throw new Error("Scenario budget metadata mismatch: " + scenario.id);
    }
    for (const [key, value] of Object.entries(scenario.overrides)) {
      const field = fields.get(key);
      if (!field) throw new Error("Unknown example profile field: " + key);
      if (typeof value === "number" && (value < (field.min ?? -Infinity) || value > (field.max ?? Infinity))) {
        throw new Error("Out-of-bounds example input: " + scenario.id + "." + key);
      }
      if (field.type === "select" && !(field.options || []).some(o => (Array.isArray(o) ? o[0] : (o.value ?? o.id)) === value)) {
        throw new Error("Unsupported example selection: " + scenario.id + "." + key);
      }
    }
    const terrain = ["terrain_pavement","terrain_packed_dirt","terrain_loose_gravel","terrain_roots_rocks","terrain_grass_brush"];
    if (terrain.reduce((sum,key)=>sum + Number(scenario.overrides[key] || 0),0) !== 100) {
      throw new Error("Example terrain must total 100: " + scenario.id);
    }
  }
  if (!ids.size) throw new Error("Example ride catalog empty");
  return manifest.scenarios;
}
export function profileForExample(scenario, questionnaireDefaults) {
  return {...questionnaireDefaults, ...scenario.overrides};
}
