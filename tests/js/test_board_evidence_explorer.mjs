import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { buildEvidenceExplorer } from "../../builder/evidence_explorer.mjs";
import { generateBoardDesignSpace } from "../../builder/platform_engine.mjs";
import { evaluateSwap } from "../../builder/swap_engine.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const read = p => JSON.parse(fs.readFileSync(path.join(root, p), "utf8"));
const bundle = {
  questionnaire: read("configurator/questionnaire.v1.json"),
  rules: read("configurator/rules.v1.json"),
  catalog: read("catalog/board_components.v1.json"),
  architectures: read("configurator/architectures.v1.json"),
  compatibility: read("configurator/compatibility_rules.v1.json"),
  swapSlots: read("configurator/swap_slots.v1.json"),
  geometry: read("catalog/board_geometry.v1.json"),
  composer: read("configurator/composer.v1.json"),
  catalogHealth: read("catalog/catalog_health.v1.json"),
};
const trail = read("configurator/examples/trail_rider_profile.json");
const manual = read("configurator/examples/manual_carver_profile.json");

test("all candidates provide separated evidence, worklists and all-false authority", () => {
  for (const profile of [trail, manual]) {
    const result = generateBoardDesignSpace(profile, bundle);
    assert.ok(result.candidates.some(c => c.origin === "SYNTHESIZED"));
    for (const c of result.candidates) {
      const e = c.evidence;
      assert.equal(e.candidate_id, c.id);
      assert.equal(e.scope, "non_authoritative_catalog_evidence_explorer");
      assert.ok(Object.values(e.authority).every(value => value === false));
      assert.equal(e.readiness, c.readiness);
      assert.equal(e.checkout_state, c.checkout_state);
      assert.equal(e.price_basis, "KNOWN_USD_SUBTOTAL_ONLY");
      assert.equal(e.score_basis, "PLANNING_PREFERENCE_NOT_SAFETY");
      assert.equal(e.summary.open_interfaces, e.measurement_worklist.length);
      assert.equal(e.summary.incompatible_interfaces, e.interfaces.filter(f => f.state === "INCOMPATIBLE").length);
      assert.equal(e.summary.unpriced_items, e.unpriced_component_ids.length);
      assert.equal(e.summary.price_complete, e.unpriced_component_ids.length === 0);
      assert.ok(e.interfaces.every(f => f.sources.length));
      assert.equal(e.summary.physical_basis, c.origin === "SYNTHESIZED"
        ? "EXPANDED_COMPONENT_GRAPH" : "REFERENCE_BOM_ONLY");
    }
  }
});

test("TRAMPA and Boardnamics unresolved interface produces exact measurement question", () => {
  const c = generateBoardDesignSpace(trail, bundle).candidates.find(c => c.id === "trampa_boardnamics_coexistence");
  const f = c.evidence.interfaces.find(f => f.category_pair === "drive:truck" && f.state === "UNKNOWN");
  assert.ok(f);
  assert.equal(f.evidence_kind, "CONSERVATIVE_CATEGORY_FALLBACK");
  const task = c.evidence.measurement_worklist.find(t => t.id === f.id);
  assert.ok(task.question.includes("drive-mount geometry"));
  assert.ok(task.evidence_required.includes("exact-revision"));
  assert.equal(c.evidence.checkout_state, "BLOCKED");
  assert.ok(Object.values(c.evidence.authority).every(v => v === false));
});

test("MBS packaged donor compatibility exposes internal incompatible axle branch", () => {
  const result = generateBoardDesignSpace(trail, bundle);
  const selection = {
    deck:"comp95", topology:"brake_first_400mm", wheel:"TIRE-T1-8-REF",
    brake:"BRAKE-V5", drive:"DRIVE-G1-DUAL", battery:"BATTERY-RANGE-CLASS",
    rider_interface:null, armor:null, dock:null,
  };
  const swap = evaluateSwap(result.candidates[0], result.requirements, selection, bundle, bundle.swapSlots);
  const e = buildEvidenceExplorer({...swap,id:"mbs:study",
    composition:{physical_interface_ids:swap.compatibility_interface_ids}},bundle.catalog,bundle.catalogHealth);
  assert.ok(e.source_evidence.some(s => s.component_id === "TRUCK-M3-400"));
  assert.ok(!swap.bom.some(r => r.component_id === "TRUCK-M3-400"));
  assert.ok(e.interfaces.some(f => f.id === "matrix400_g1_as_shipped" && f.state === "INCOMPATIBLE"));
  assert.equal(e.readiness, "INCOMPATIBLE");
  assert.ok(Object.values(e.authority).every(v=>v===false));
});

test("source freshness and catalog enumeration never change mechanical findings", () => {
  const c = generateBoardDesignSpace(trail, bundle).candidates.find(c => c.id === "trampa_boardnamics_coexistence");
  const fresh = structuredClone(bundle.catalogHealth);
  for (const row of fresh.component_health) row.status = "SOURCE_FRESH";
  const baseline = c.evidence;
  const changed = buildEvidenceExplorer(c,bundle.catalog,fresh);
  assert.deepEqual(changed.measurement_worklist,baseline.measurement_worklist);
  assert.equal(changed.readiness,baseline.readiness);
  assert.equal(changed.checkout_state,baseline.checkout_state);
  assert.ok(Object.values(changed.authority).every(v=>v===false));
  const missing = buildEvidenceExplorer(c,bundle.catalog,null);
  assert.ok(missing.source_evidence.every(s=>s.health_status==="HEALTH_UNAVAILABLE"));
  assert.equal(missing.summary.source_refresh_or_integrity_issues,missing.source_evidence.length);
  const reverseC = structuredClone(c);
  reverseC.compatibility_findings.reverse();
  const reverseCatalog = structuredClone(bundle.catalog);
  reverseCatalog.components.reverse();
  const reverseHealth = structuredClone(bundle.catalogHealth);
  reverseHealth.component_health.reverse();
  assert.deepEqual(buildEvidenceExplorer(reverseC, reverseCatalog, reverseHealth), baseline);
});
