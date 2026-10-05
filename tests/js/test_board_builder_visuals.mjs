import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { generateCandidates } from "../../builder/engine.mjs";
import { renderBoardPreviewSvg } from "../../builder/preview_renderer.mjs";
import { evaluateSwap } from "../../builder/swap_engine.mjs";
import {
  visualStateFromCandidate,
  visualStateFromSwap,
} from "../../builder/visual_state.mjs";

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
const twin = read("showcase/x1_rev_c.json");
const trail = read("configurator/examples/trail_rider_profile.json");
const manual = read("configurator/examples/manual_carver_profile.json");
const incompatible = read("configurator/examples/swap_incompatible_study.json");

const get = (result, id) => result.candidates.find(row => row.id === id);

test("candidate visual state mirrors X1 geometry contract", () => {
  const generated = generateCandidates(trail, bundle);
  const row = get(generated, "x1_compact_electric_study");
  const visual = visualStateFromCandidate(row, twin, bundle.catalog);

  assert.equal(visual.deck.id, "comp95");
  assert.equal(visual.deck.length_mm, 950);
  assert.equal(visual.topology.id, "brake_hanger_70mm_topology_study");
  assert.equal(visual.topology.truck_total_width_mm, 440);
  assert.equal(visual.wheel.diameter_mm, 194);
  assert.deepEqual(visual.layers, {
    brake: true,
    drive: true,
    pack: true,
    snowdeck: true,
    armor: true,
    dock: false,
  });
  assert.equal(visual.authority.visualization_only, true);
  assert.equal(visual.authority.powered_operation_authorized, false);
});

test("fit bench hides wheels while keeping rider interface", () => {
  const generated = generateCandidates(manual, bundle);
  const visual = visualStateFromCandidate(
    get(generated, "snowdeck_fit_bench"),
    twin,
    bundle.catalog
  );
  assert.equal(visual.wheel.visible, false);
  assert.equal(visual.layers.snowdeck, true);
  assert.equal(visual.layers.drive, false);
});

test("Swap Lab visual carries 9-inch study and incompatible readiness", () => {
  const generated = generateCandidates(trail, bundle);
  const baseline = get(generated, "x1_compact_electric_study");
  const swap = evaluateSwap(
    baseline,
    generated.requirements,
    incompatible,
    bundle,
    read("configurator/swap_slots.v1.json")
  );
  const visual = visualStateFromSwap(baseline, swap, twin, bundle.catalog);

  assert.equal(visual.scope, "custom_swap_preview");
  assert.equal(visual.readiness, "INCOMPATIBLE");
  assert.equal(visual.wheel.study_id, "TIRE-T2-9");
  assert.equal(visual.wheel.diameter_mm, 219);
  assert.equal(visual.topology.id, "drive_clearance_420mm");
});

test("renderer produces distinct deterministic Hero Top and Side SVGs", () => {
  const generated = generateCandidates(trail, bundle);
  const visual = visualStateFromCandidate(
    get(generated, "x1_compact_electric_study"),
    twin,
    bundle.catalog
  );

  const hero = renderBoardPreviewSvg(visual, "hero");
  const top = renderBoardPreviewSvg(visual, "top");
  const side = renderBoardPreviewSvg(visual, "side");

  for (const svg of [hero, top, side]) {
    assert.ok(svg.startsWith("<svg"));
    assert.ok(svg.includes("VISUAL STUDY"));
    assert.ok(svg.includes("Compact Electric Coexistence Study"));
  }
  assert.notEqual(hero, top);
  assert.notEqual(top, side);
  assert.ok(side.includes("<circle"));
  assert.ok(top.includes("linearGradient"));
});

test("renderer escapes candidate labels", () => {
  const generated = generateCandidates(trail, bundle);
  const visual = visualStateFromCandidate(
    get(generated, "brake_first_trail_core"),
    twin,
    bundle.catalog
  );
  visual.label = '<script>alert("x")</script>';
  const svg = renderBoardPreviewSvg(visual, "top");

  assert.ok(!svg.includes("<script>"));
  assert.ok(svg.includes("&lt;script&gt;"));
});
