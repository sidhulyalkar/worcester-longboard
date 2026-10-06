import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { generateBoardDesignSpace } from "../../builder/platform_engine.mjs";
import { evaluateSwap } from "../../builder/swap_engine.mjs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "../..");
const read = relative => JSON.parse(fs.readFileSync(path.join(ROOT, relative), "utf8"));

const bundle = {
  questionnaire: read("configurator/questionnaire.v1.json"),
  rules: read("configurator/rules.v1.json"),
  catalog: read("catalog/board_components.v1.json"),
  architectures: read("configurator/architectures.v1.json"),
  compatibility: read("configurator/compatibility_rules.v1.json"),
  swapSlots: read("configurator/swap_slots.v1.json"),
  geometry: read("catalog/board_geometry.v1.json"),
  composer: read("configurator/composer.v1.json"),
};

const trail = read("configurator/examples/trail_rider_profile.json");
const manual = read("configurator/examples/manual_carver_profile.json");

const signature = candidate =>
  candidate.bom.map(row => row.component_id).sort().join("|");

test("platform engine preserves curated candidates and adds bounded synthesis", () => {
  const result = generateBoardDesignSpace(trail, bundle);
  const summary = result.composition_summary;

  assert.equal(summary.curated_count, bundle.architectures.architectures.length);
  assert.ok(summary.synthesized_count > 0);
  assert.ok(summary.synthesized_count <= bundle.composer.max_synthesized_candidates);
  assert.equal(summary.total_count, result.candidates.length);
  assert.equal(summary.composer_enabled, true);

  const curated = result.candidates.filter(row => row.origin === "CURATED");
  const synthesized = result.candidates.filter(row => row.origin === "SYNTHESIZED");
  assert.equal(curated.length, summary.curated_count);
  assert.equal(synthesized.length, summary.synthesized_count);
});

test("synthesized candidates remain fail-closed and authority false", () => {
  const result = generateBoardDesignSpace(trail, bundle);
  const synthesized = result.candidates.filter(row => row.origin === "SYNTHESIZED");

  assert.ok(synthesized.length > 0);
  for (const candidate of synthesized) {
    assert.ok(["REFERENCE_COMPATIBLE", "MEASURE_FIRST"].includes(candidate.readiness));
    assert.deepEqual(candidate.blockers, []);
    assert.equal(candidate.composition.engine, "catalog_composer_v1");
    assert.ok(candidate.composition.unknown_count <= bundle.composer.max_unknown_findings);
    assert.ok(candidate.swap_defaults.drive);
    assert.ok(candidate.swap_defaults.battery);
    assert.deepEqual(candidate.authority, {
      procurement_authorized: false,
      fabrication_authorized: false,
      powered_operation_authorized: false,
    });
  }
});

test("manual composer never adds propulsion or traction battery", () => {
  const result = generateBoardDesignSpace(manual, bundle);
  const synthesized = result.candidates.filter(row => row.origin === "SYNTHESIZED");

  assert.ok(synthesized.length > 0);
  for (const candidate of synthesized) {
    assert.equal(candidate.swap_defaults.drive, null);
    assert.equal(candidate.swap_defaults.battery, null);
    const ids = new Set(candidate.bom.map(row => row.component_id));
    assert.ok(![...ids].some(id => id.startsWith("DRIVE-")));
    assert.ok(![...ids].some(id => id.startsWith("BATTERY-")));
  }
});

test("synthesis is deterministic and deduplicated against curated BOMs", () => {
  const left = generateBoardDesignSpace(trail, bundle);
  const right = generateBoardDesignSpace(trail, bundle);
  assert.deepEqual(
    left.candidates.map(row => row.id),
    right.candidates.map(row => row.id)
  );

  const curated = new Set(
    left.candidates
      .filter(row => row.origin === "CURATED")
      .map(signature)
  );
  const synthesized = left.candidates
    .filter(row => row.origin === "SYNTHESIZED")
    .map(signature);

  assert.equal(synthesized.length, new Set(synthesized).size);
  assert.ok(synthesized.every(value => !curated.has(value)));
});

test("synthesized candidate round-trips through Swap Lab with no changes", () => {
  const result = generateBoardDesignSpace(trail, bundle);
  const candidate = result.candidates.find(row => row.origin === "SYNTHESIZED");
  assert.ok(candidate);

  const evaluated = evaluateSwap(
    candidate,
    result.requirements,
    candidate.swap_defaults,
    bundle,
    bundle.swapSlots
  );

  assert.deepEqual(evaluated.changes, []);
  assert.ok(["REFERENCE_COMPATIBLE", "MEASURE_FIRST"].includes(evaluated.readiness));
  assert.deepEqual(evaluated.blockers, []);
  assert.equal(
    evaluated.bom.map(row => row.component_id).sort().join("|"),
    signature(candidate)
  );
});

test("composer never promotes platform authority", () => {
  const result = generateBoardDesignSpace(trail, bundle);
  assert.deepEqual(result.authority, {
    generic_builder_may_promote_x1_authority: false,
    procurement_authorized: false,
    fabrication_authorized: false,
    powered_operation_authorized: false,
  });
});
