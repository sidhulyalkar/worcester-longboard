import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import {
  deriveRequirements,
  generateCandidates,
} from "../../builder/engine.mjs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "../..");

const readJson = relative =>
  JSON.parse(fs.readFileSync(path.join(ROOT, relative), "utf8"));

const bundle = {
  questionnaire: readJson("configurator/questionnaire.v1.json"),
  rules: readJson("configurator/rules.v1.json"),
  catalog: readJson("catalog/board_components.v1.json"),
  architectures: readJson("configurator/architectures.v1.json"),
  compatibility: readJson("configurator/compatibility_rules.v1.json"),
};

const trail = readJson("configurator/examples/trail_rider_profile.json");
const manual = readJson("configurator/examples/manual_carver_profile.json");

const candidate = (result, id) =>
  result.candidates.find(row => row.id === id);

test("trail requirements stay planning-only and require friction braking", () => {
  const req = deriveRequirements(trail, bundle.rules, bundle.questionnaire);
  assert.equal(req.model_class, "PLANNING_ESTIMATE");
  assert.equal(req.electric_intent, "yes");
  assert.equal(req.independent_friction_brake_required, true);
  assert.ok(req.target_range_mi >= trail.longest_miles);
  assert.ok(req.planning_installed_energy_wh > 0);
});

test("candidate generation never selects a winner or grants authority", () => {
  const result = generateCandidates(trail, bundle);
  assert.equal(result.winner_selected, false);
  assert.deepEqual(result.authority, {
    generic_builder_may_promote_x1_authority: false,
    procurement_authorized: false,
    fabrication_authorized: false,
    powered_operation_authorized: false,
  });
  assert.ok(result.candidates.some(row => row.trade_space_frontier));
});

test("compact electric study remains measure-first and checkout blocked", () => {
  const result = generateCandidates(trail, bundle);
  const electric = candidate(result, "x1_compact_electric_study");
  assert.equal(electric.readiness, "MEASURE_FIRST");
  assert.equal(electric.checkout_state, "BLOCKED");
  assert.ok(electric.compatibility_findings.some(
    finding => finding.id === "axle70_v5" && finding.state === "MEASURE_FIRST"
  ));
});

test("drive-only range study is blocked by missing friction brake path", () => {
  const result = generateCandidates(trail, bundle);
  const rangeStudy = candidate(result, "drive_clearance_range_study");
  assert.equal(rangeStudy.readiness, "BLOCKED");
  assert.ok(rangeStudy.blockers.some(text => text.includes("friction-brake")));
});

test("manual mission scores fit bench above electric coexistence complexity", () => {
  const result = generateCandidates(manual, bundle);
  assert.ok(
    candidate(result, "snowdeck_fit_bench").fit_score >
    candidate(result, "x1_compact_electric_study").fit_score
  );
});

test("power placeholders never receive invented source links", () => {
  for (const component of bundle.catalog.components) {
    if (!["drive", "motor", "esc", "battery", "charger"].includes(component.category)) continue;
    assert.equal(component.procurement_state, "POWER_GATED");
    if (component.source.kind === "planning_placeholder") {
      assert.equal(component.source.url, null);
    }
  }
});


test("compact electric study scales from trail to range energy class", () => {
  const longRange = { ...trail, longest_miles: 35 };
  const result = generateCandidates(longRange, bundle);
  const electric = candidate(result, "x1_compact_electric_study");
  assert.ok(electric.personalized_spec.planning_installed_energy_wh > 650);
  assert.ok(electric.personalized_spec.planning_installed_energy_wh <= 1150);
  assert.equal(electric.personalized_spec.selected_energy_class, "BATTERY-RANGE-CLASS");
  assert.ok(electric.bom.some(row => row.component_id === "BATTERY-RANGE-CLASS"));
  assert.ok(!electric.bom.some(row => row.component_id === "BATTERY-TRAIL-CLASS"));
});

test("mission beyond seeded range class fails closed", () => {
  const veryLong = { ...trail, longest_miles: 50 };
  const result = generateCandidates(veryLong, bundle);
  const electric = candidate(result, "x1_compact_electric_study");
  assert.equal(electric.readiness, "BLOCKED");
  assert.ok(electric.blockers.some(text => text.includes("largest seeded 1150 Wh")));
});

test("stability fit follows rider preference direction", () => {
  const playfulResult = generateCandidates({ ...manual, stability_preference: 20 }, bundle);
  const plantedResult = generateCandidates({ ...manual, stability_preference: 95 }, bundle);
  assert.ok(
    candidate(playfulResult, "drive_clearance_range_study").preference_fit.stability <
    candidate(plantedResult, "drive_clearance_range_study").preference_fit.stability
  );
});
