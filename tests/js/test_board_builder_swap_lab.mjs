import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { generateCandidates } from "../../builder/engine.mjs";
import { evaluateSwap, seedSwapSelection } from "../../builder/swap_engine.mjs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "../..");
const read = relative => JSON.parse(fs.readFileSync(path.join(ROOT, relative), "utf8"));

const bundle = {
  questionnaire: read("configurator/questionnaire.v1.json"),
  rules: read("configurator/rules.v1.json"),
  catalog: read("catalog/board_components.v1.json"),
  architectures: read("configurator/architectures.v1.json"),
  compatibility: read("configurator/compatibility_rules.v1.json"),
};
const slots = read("configurator/swap_slots.v1.json");
const trail = read("configurator/examples/trail_rider_profile.json");
const manual = read("configurator/examples/manual_carver_profile.json");
const incompatible = read("configurator/examples/swap_incompatible_study.json");

const findCandidate = (result, id) => result.candidates.find(row => row.id === id);

test("Swap Lab seed reconstructs compact electric baseline", () => {
  const generated = generateCandidates(trail, bundle);
  const baseline = findCandidate(generated, "x1_compact_electric_study");
  const selection = seedSwapSelection(baseline);
  const result = evaluateSwap(baseline, generated.requirements, selection, bundle, slots);

  assert.equal(selection.deck, "comp95");
  assert.equal(selection.topology, "brake_hanger_70mm_topology_study");
  assert.equal(selection.wheel, "TIRE-T1-8-REF");
  assert.equal(result.readiness, "MEASURE_FIRST");
  assert.equal(result.checkout_state, "BLOCKED");
  assert.deepEqual(result.changes, []);
  assert.deepEqual(result.cost_delta_vs_baseline, {
    known_min_usd: 0,
    known_max_usd: 0,
  });
});

test("420 drive reference with V5 is incompatible", () => {
  const generated = generateCandidates(trail, bundle);
  const baseline = findCandidate(generated, "x1_compact_electric_study");
  const result = evaluateSwap(baseline, generated.requirements, incompatible, bundle, slots);

  assert.equal(result.readiness, "INCOMPATIBLE");
  assert.equal(result.checkout_state, "BLOCKED");
  assert.ok(result.compatibility_findings.some(x => x.id === "matrix420_v5" && x.state === "INCOMPATIBLE"));
  assert.ok(result.compatibility_findings.some(x => x.id === "matrix420_g1" && x.state === "REFERENCE_COMPATIBLE"));
  assert.ok(result.compatibility_findings.some(x => x.id === "rockstarII_t2_9" && x.state === "MEASURE_FIRST"));
});

test("removing required brake blocks edited design", () => {
  const generated = generateCandidates(trail, bundle);
  const baseline = findCandidate(generated, "x1_compact_electric_study");
  const selection = seedSwapSelection(baseline);
  selection.brake = null;
  const result = evaluateSwap(baseline, generated.requirements, selection, bundle, slots);

  assert.equal(result.readiness, "BLOCKED");
  assert.ok(result.blockers.some(text => text.includes("requires an independent friction brake")));
});

test("undersized selected battery class blocks mission", () => {
  const generated = generateCandidates({ ...trail, longest_miles: 35 }, bundle);
  const baseline = findCandidate(generated, "x1_compact_electric_study");
  const selection = seedSwapSelection(baseline);
  selection.battery = "BATTERY-TRAIL-CLASS";
  const result = evaluateSwap(baseline, generated.requirements, selection, bundle, slots);

  assert.ok(generated.requirements.planning_installed_energy_wh > 650);
  assert.equal(result.readiness, "BLOCKED");
  assert.ok(result.blockers.some(text => text.includes("selected battery-class ceiling")));
});

test("Swap Lab never promotes authority", () => {
  const generated = generateCandidates(manual, bundle);
  const baseline = findCandidate(generated, "snowdeck_fit_bench");
  const selection = seedSwapSelection(baseline);
  const result = evaluateSwap(baseline, generated.requirements, selection, bundle, slots);

  assert.equal(result.scope, "non_authoritative_component_swap_study");
  assert.deepEqual(result.authority, {
    procurement_authorized: false,
    fabrication_authorized: false,
    powered_operation_authorized: false,
    generic_builder_may_promote_x1_authority: false,
  });
});
