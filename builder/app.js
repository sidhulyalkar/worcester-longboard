import {
  formatPrice,
  questionnaireDefaults,
} from "./engine.mjs";
import { generateBoardDesignSpace } from "./platform_engine.mjs";
import {
  evaluateSwap,
  seedSwapSelection,
} from "./swap_engine.mjs";
import {
  visualStateFromCandidate,
  visualStateFromSwap,
} from "./visual_state.mjs";
import {
  downloadBoardPreviewSvg,
  renderBoardPreviewSvg,
} from "./preview_renderer.mjs";

const STORAGE_KEY = "worcester-board-builder-profile-v1";

const state = {
  bundle: null,
  profile: {},
  result: null,
  selectedId: null,
  advanced: false,
  renderQueued: false,
  swapBaselineId: null,
  swapSelection: null,
  swapResult: null,
  galleryView: "hero",
  vendorFilter: "all",
  originFilter: "all",
};

const $ = selector => document.querySelector(selector);

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function fetchJson(path) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) throw new Error("Failed to load " + path);
  return response.json();
}

async function loadBundle() {
  const [questionnaire, rules, catalog, architectures, compatibility, swapSlots, geometry, composer] = await Promise.all([
    fetchJson("../configurator/questionnaire.v1.json"),
    fetchJson("../configurator/rules.v1.json"),
    fetchJson("../catalog/board_components.v1.json"),
    fetchJson("../configurator/architectures.v1.json"),
    fetchJson("../configurator/compatibility_rules.v1.json"),
    fetchJson("../configurator/swap_slots.v1.json"),
    fetchJson("../catalog/board_geometry.v1.json"),
    fetchJson("../configurator/composer.v1.json"),
  ]);
  return { questionnaire, rules, catalog, architectures, compatibility, swapSlots, geometry, composer };
}

function restoreProfile(questionnaire) {
  const defaults = questionnaireDefaults(questionnaire);
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return defaults;
    const stored = JSON.parse(raw);
    return { ...defaults, ...stored };
  } catch {
    return defaults;
  }
}

function saveProfile() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state.profile));
}

function fieldValue(field) {
  const value = state.profile[field.id];
  return value === undefined ? field.default : value;
}

function makeInput(field) {
  let input;
  const value = fieldValue(field);

  if (field.type === "select") {
    input = document.createElement("select");
    for (const [optionValue, optionLabel] of field.options || []) {
      const option = document.createElement("option");
      option.value = optionValue;
      option.textContent = optionLabel;
      input.appendChild(option);
    }
    input.value = value ?? "";
  } else if (field.type === "boolean") {
    input = document.createElement("input");
    input.type = "checkbox";
    input.checked = Boolean(value);
  } else if (field.type === "range") {
    input = document.createElement("input");
    input.type = "range";
    input.min = field.min;
    input.max = field.max;
    input.step = field.step || 1;
    input.value = value ?? field.default ?? field.min;
  } else if (field.type === "text") {
    input = document.createElement("textarea");
    input.value = value ?? "";
  } else {
    input = document.createElement("input");
    input.type = "number";
    input.min = field.min;
    input.max = field.max;
    input.step = field.step || 1;
    input.value = value ?? "";
    if (!field.required) input.placeholder = "Optional";
  }

  input.id = "field-" + field.id;
  input.dataset.fieldId = field.id;
  input.dataset.fieldType = field.type;
  input.setAttribute("aria-label", field.label);
  return input;
}

function typedValue(input) {
  if (input.dataset.fieldType === "boolean") return input.checked;
  if (input.dataset.fieldType === "number" || input.dataset.fieldType === "range") {
    return input.value === "" ? null : Number(input.value);
  }
  return input.value;
}

function renderQuestionnaire() {
  const host = $("#questionnaire");
  host.innerHTML = "";

  for (const section of state.bundle.questionnaire.sections || []) {
    const sectionEl = document.createElement("section");
    sectionEl.className = "question-section";

    const header = document.createElement("header");
    const title = document.createElement("h3");
    title.textContent = section.label;
    const summary = document.createElement("p");
    summary.textContent = section.summary || "";
    header.append(title, summary);
    sectionEl.appendChild(header);

    const fields = document.createElement("div");
    fields.className = "fields";

    for (const field of section.fields || []) {
      const wrapper = document.createElement("div");
      wrapper.className = "field" + (!field.quick && !state.advanced ? " hidden-advanced" : "");
      if (field.type === "boolean") wrapper.classList.add("boolean-field");

      const head = document.createElement("div");
      head.className = "field-head";
      const label = document.createElement("label");
      label.htmlFor = "field-" + field.id;
      label.textContent = field.label;
      head.appendChild(label);

      let output = null;
      if (field.type === "range") {
        output = document.createElement("output");
        const suffix = field.unit ? " " + field.unit : "";
        output.textContent = String(fieldValue(field) ?? field.default ?? field.min) + suffix;
        head.appendChild(output);
      } else if (field.unit && field.type === "number") {
        const unit = document.createElement("span");
        unit.className = "unit";
        unit.textContent = field.unit;
        head.appendChild(unit);
      }

      const input = makeInput(field);
      input.addEventListener("input", () => {
        state.profile[field.id] = typedValue(input);
        if (output) {
          const suffix = field.unit ? " " + field.unit : "";
          output.textContent = input.value + suffix;
        }
        saveProfile();
        scheduleRecompute();
      });
      input.addEventListener("change", () => {
        state.profile[field.id] = typedValue(input);
        saveProfile();
        scheduleRecompute();
      });

      wrapper.appendChild(head);
      wrapper.appendChild(input);

      if (field.type === "range" && (field.left_label || field.right_label)) {
        const labels = document.createElement("div");
        labels.className = "range-labels";
        const left = document.createElement("span");
        left.textContent = field.left_label || String(field.min);
        const right = document.createElement("span");
        right.textContent = field.right_label || String(field.max);
        labels.append(left, right);
        wrapper.appendChild(labels);
      }

      if (field.help) {
        const help = document.createElement("small");
        help.textContent = field.help;
        wrapper.appendChild(help);
      }
      fields.appendChild(wrapper);
    }

    sectionEl.appendChild(fields);
    host.appendChild(sectionEl);
  }
}

function wheelLabel(value) {
  return {
    eight_inch_pneumatic_reference: "8 in pneumatic reference",
    nine_inch_rollover_study: "9 in rollover study",
    pavement_efficiency_study: "Pavement efficiency study",
  }[value] || value;
}

function deckLabel(value) {
  return {
    compact: "Compact",
    balanced: "Balanced",
    long_stable: "Long / stable",
  }[value] || value;
}

function renderRequirements(requirements) {
  const cards = [
    ["Target mission range", requirements.target_range_mi + " mi", "Includes the planning ride-length margin."],
    ["Planning energy envelope", requirements.planning_installed_energy_wh + " Wh", "Comparative estimate only, not a battery selection."],
    ["Planning consumption", requirements.planning_energy_wh_per_mi + " Wh/mi", "Pre-telemetry model used only for trade studies."],
    ["Energy reserve", Math.round(requirements.energy_reserve_fraction * 100) + "%", "Model reserve for terrain / weather uncertainty."],
    ["Wheel strategy", wheelLabel(requirements.wheel_strategy), "Physical compatibility still controls."],
    ["Stance study", requirements.stance_study.min_mm + "–" + requirements.stance_study.max_mm + " mm", "Center " + requirements.stance_study.center_mm + " mm · " + requirements.stance_study.source],
    ["Brake requirement", requirements.independent_friction_brake_required ? "Independent friction brake" : "Not forced by mission", "Regenerative braking never substitutes for a required friction path."],
    ["Deck envelope", deckLabel(requirements.deck_envelope_preference), "Planning preference, not structural qualification."],
    ["Ingress priority", requirements.ingress_priority, "Driven by wet / contamination exposure."],
    ["Loaded rider mass", requirements.loaded_rider_mass_kg + " kg", "Body + stated typical carried load."],
  ];

  $("#requirements").innerHTML = cards.map(row =>
    '<div class="requirement-card"><span>' + escapeHtml(row[0]) + '</span><strong>' +
    escapeHtml(row[1]) + '</strong><small>' + escapeHtml(row[2]) + '</small></div>'
  ).join("");

  const notes = [
    ...(requirements.warnings || []).map(text => ({ text, kind: "warning" })),
    ...(requirements.assumptions || []).slice(0, 4).map(text => ({ text, kind: "" })),
  ];
  $("#requirement-notes").innerHTML = notes.map(note =>
    '<div class="note ' + note.kind + '">' + escapeHtml(note.text) + '</div>'
  ).join("");
}

function statusClass(readiness) {
  return {
    REFERENCE_COMPATIBLE: "reference",
    MEASURE_FIRST: "measure",
    BLOCKED: "blocked",
    INCOMPATIBLE: "incompatible",
  }[readiness] || "";
}

function readinessLabel(readiness) {
  return readiness.replaceAll("_", " ").toLowerCase();
}

function partialCost(candidate) {
  const c = candidate.cost;
  const unpriced = (c.unpriced_component_ids || []).length;
  if (unpriced && c.known_min_usd === 0 && c.known_max_usd === 0) {
    return "USD subtotal incomplete";
  }
  if (c.known_min_usd === c.known_max_usd) return "USD " + c.known_min_usd.toFixed(0);
  return "USD " + c.known_min_usd.toFixed(0) + "–" + c.known_max_usd.toFixed(0);
}

function twinUrl(candidate) {
  const spec = candidate.personalized_spec || {};
  const visual = candidateVisualState(candidate);
  const params = new URLSearchParams({
    preset: candidate.visual_preset,
    candidate: candidate.id,
    deck: visual.deck.id,
    topology: visual.topology.id,
    wheel: visual.wheel.study_id,
    drive_type: visual.visual_style.drive_type,
    brake_family: visual.visual_style.brake_family,
  });
  if (Number.isFinite(Number(spec.stance_center_mm))) {
    params.set("stance_mm", String(spec.stance_center_mm));
  }
  for (const [layer, visible] of Object.entries(visual.layers)) {
    params.set(layer, visible ? "1" : "0");
  }
  return "../showcase/?" + params.toString();
}

function candidateSpecHtml(candidate) {
  const spec = candidate.personalized_spec || {};
  const energy = spec.selected_energy_class
    ? spec.selected_energy_class
        .replace("BATTERY-", "")
        .replace("-CLASS", "")
        .replaceAll("-", " ")
        .toLowerCase()
    : "no pack selected";
  const wheel = wheelLabel(spec.wheel_strategy || "");
  return (
    '<div class="candidate-spec">' +
      '<span>' + escapeHtml(spec.target_range_mi + " mi target") + '</span>' +
      '<span>' + escapeHtml("stance " + spec.stance_center_mm + " mm") + '</span>' +
      '<span>' + escapeHtml(wheel) + '</span>' +
      '<span>' + escapeHtml(energy) + '</span>' +
    '</div>'
  );
}

function candidateVisualState(candidate) {
  return visualStateFromCandidate(candidate, state.bundle.geometry, state.bundle.catalog);
}

function renderCandidateVisual(candidate) {
  const visual = candidateVisualState(candidate);
  const svg = renderBoardPreviewSvg(
    visual,
    state.galleryView,
    { width: 720, height: 360, compact: true }
  );
  const wheel = visual.wheel.visible
    ? Math.round(visual.wheel.diameter_mm) + " mm wheels"
    : "fit bench";
  const stance = visual.stance_mm ? Math.round(visual.stance_mm) + " mm stance" : "stance TBD";
  return (
    '<div class="candidate-visual" data-candidate-visual="' + escapeHtml(candidate.id) + '">' +
      svg +
      '<div class="candidate-visual-meta">' +
        '<span>' + escapeHtml(visual.vendor_family) + '</span>' +
        '<span>' + escapeHtml(visual.deck.id.replaceAll("_", " ")) + '</span>' +
        '<span>' + escapeHtml(wheel) + '</span>' +
        '<span>' + escapeHtml(stance) + '</span>' +
      '</div>' +
      '<div class="candidate-preview-actions">' +
        '<button type="button" data-download-preview="' + escapeHtml(candidate.id) + '">SVG</button>' +
      '</div>' +
    '</div>'
  );
}

function setGalleryView(view) {
  if (!["hero", "top", "side"].includes(view)) return;
  state.galleryView = view;
  document.querySelectorAll("[data-gallery-view]").forEach(button => {
    button.classList.toggle("active", button.dataset.galleryView === view);
  });
  if (state.result) {
    renderCandidates(state.result.candidates);
    const candidate = state.result.candidates.find(row => row.id === state.selectedId);
    if (candidate && state.swapResult) renderSwapPreview(candidate);
  }
}

function renderVendorFilters(candidates) {
  const host = $("#vendor-filters");
  if (!host) return;
  const families = [...new Set(candidates.map(row => row.vendor_family || "Unspecified"))]
    .sort((a, b) => a.localeCompare(b));
  if (
    state.vendorFilter !== "all" &&
    !families.includes(state.vendorFilter)
  ) {
    state.vendorFilter = "all";
  }

  const options = [["all", "All"], ...families.map(value => [value, value])];
  host.innerHTML = "";
  for (const [value, label] of options) {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.vendorFilter = value;
    button.textContent = label;
    button.classList.toggle("active", state.vendorFilter === value);
    button.addEventListener("click", () => {
      state.vendorFilter = value;
      renderVendorFilters(state.result.candidates);
      renderCandidates(state.result.candidates);
    });
    host.appendChild(button);
  }

  const visible = candidates.filter(row =>
    (state.vendorFilter === "all" || row.vendor_family === state.vendorFilter) &&
    (state.originFilter === "all" || row.origin === state.originFilter)
  ).length;
  const vendors = new Set(
    candidates.flatMap(row =>
      (row.bom || []).map(item => item.manufacturer).filter(Boolean)
    )
  );
  const sourced = state.bundle.catalog.components.filter(
    item => item.source?.url
  ).length;
  const summary = state.result?.composition_summary;
  const originText = summary
    ? summary.curated_count + " curated + " + summary.synthesized_count + " composed"
    : candidates.length + " generated";
  $("#catalog-coverage").textContent =
    visible + " shown · " + originText + " · " +
    vendors.size + " named manufacturers · " + sourced +
    " catalog parts with source links";
}

function traitsHtml(candidate) {
  const labels = {
    range: "Range",
    carve: "Carve",
    stability: "Stability",
    durability: "Durability",
    portability: "Portability",
    low_maintenance: "Low maint.",
  };
  return Object.entries(labels).map(([key, label]) =>
    '<div class="trait"><span>' + label + '</span><div class="bar"><i style="width:' +
    Math.round(candidate.traits[key] * 100) + '%"></i></div></div>'
  ).join("");
}

function renderCandidates(candidates) {
  const host = $("#candidates");
  host.innerHTML = "";

  const visibleCandidates = candidates.filter(row =>
    (state.vendorFilter === "all" || row.vendor_family === state.vendorFilter) &&
    (state.originFilter === "all" || row.origin === state.originFilter)
  );

  for (const candidate of visibleCandidates) {
    const card = document.createElement("article");
    card.className = "candidate" + (candidate.id === state.selectedId ? " selected" : "");

    const issueText = candidate.blockers.length
      ? '<div class="alert-mini red">' + candidate.blockers.length + ' blocker' + (candidate.blockers.length === 1 ? "" : "s") + '</div>'
      : candidate.unknowns.length
        ? '<div class="alert-mini">' + candidate.unknowns.length + ' unresolved item' + (candidate.unknowns.length === 1 ? "" : "s") + '</div>'
        : "";

    card.innerHTML =
      renderCandidateVisual(candidate) +
      '<div class="candidate-top">' +
        '<div><h3>' + escapeHtml(candidate.label) + '</h3><p>' + escapeHtml(candidate.description) + '</p></div>' +
        '<div class="fit-score"><strong>' + Math.round(candidate.fit_score * 100) + '%</strong><span>profile fit</span></div>' +
      '</div>' +
      '<div class="badges">' +
        '<span class="badge origin-chip ' + (candidate.origin === "SYNTHESIZED" ? "composed" : "curated") + '">' +
          escapeHtml(candidate.origin === "SYNTHESIZED" ? "catalog composed" : "curated reference") +
        '</span>' +
        '<span class="badge vendor-chip">' + escapeHtml(candidate.vendor_family || "Unspecified") + '</span>' +
        '<span class="badge ' + statusClass(candidate.readiness) + '">' + escapeHtml(readinessLabel(candidate.readiness)) + '</span>' +
        (candidate.trade_space_frontier ? '<span class="badge frontier">trade-space frontier</span>' : '') +
        '<span class="badge">' + escapeHtml(candidate.checkout_state.replaceAll("_", " ").toLowerCase()) + '</span>' +
      '</div>' +
      '<div class="traits">' + traitsHtml(candidate) + '</div>' +
      candidateSpecHtml(candidate) +
      issueText +
      '<div class="candidate-footer">' +
        '<div class="cost"><strong>' + partialCost(candidate) + '</strong><small>known USD subtotal · ' +
          candidate.cost.unpriced_component_ids.length + ' unpriced/source-native item' +
          (candidate.cost.unpriced_component_ids.length === 1 ? '' : 's') +
          ' · shipping/tax excluded</small></div>' +
        '<div class="candidate-actions">' +
          '<button type="button" data-inspect="' + escapeHtml(candidate.id) + '">Inspect BOM</button>' +
          '<a href="' + escapeHtml(twinUrl(candidate)) + '">3D</a>' +
        '</div>' +
      '</div>';

    card.querySelector("[data-download-preview]").addEventListener("click", event => {
      event.stopPropagation();
      downloadBoardPreviewSvg(candidateVisualState(candidate), state.galleryView);
    });

    card.querySelector("[data-inspect]").addEventListener("click", () => {
      state.selectedId = candidate.id;
      state.swapBaselineId = null;
      state.swapSelection = null;
      state.swapResult = null;
      renderCandidates(state.result.candidates);
      renderBom(candidate);
      $("#bom-section").scrollIntoView({ behavior: "smooth", block: "start" });
    });
    host.appendChild(card);
  }
}

function renderBom(candidate) {
  if (!candidate) return;

  $("#bom-title").textContent = candidate.label;
  const twin = $("#open-twin");
  twin.classList.remove("disabled");
  twin.href = twinUrl(candidate);

  const cost = candidate.cost;
  $("#bom-summary").innerHTML =
    '<span class="summary-pill">Known subtotal: <strong>' + escapeHtml(partialCost(candidate)) + '</strong></span>' +
    '<span class="summary-pill">Readiness: <strong>' + escapeHtml(readinessLabel(candidate.readiness)) + '</strong></span>' +
    '<span class="summary-pill">Checkout: <strong>' + escapeHtml(candidate.checkout_state.replaceAll("_", " ").toLowerCase()) + '</strong></span>' +
    '<span class="summary-pill">Unpriced study items: <strong>' + cost.unpriced_component_ids.length + '</strong></span>';

  $("#bom-body").innerHTML = candidate.bom.map(row => {
    const source = row.source_url
      ? '<a class="source-link" href="' + escapeHtml(row.source_url) + '" target="_blank" rel="noreferrer">Vendor source</a>' +
        '<small>snapshot ' + escapeHtml(row.source_as_of || "unknown") + '</small>'
      : '<span>Reference / TBD</span><small>No checkout link is asserted.</small>';

    const hold = row.hold_reason ? '<small>' + escapeHtml(row.hold_reason) + '</small>' : "";
    return '<tr>' +
      '<td>' + escapeHtml(row.category.replaceAll("_", " ")) + '</td>' +
      '<td><strong>' + escapeHtml(row.label) + '</strong><small>' +
        escapeHtml([row.manufacturer, row.sku].filter(Boolean).join(" · ") || row.component_id) + '</small></td>' +
      '<td><span class="badge ' + (row.procurement_state === "POWER_GATED" ? "blocked" : row.procurement_state === "HOLD_MEASURE" ? "measure" : "") + '">' +
        escapeHtml(row.procurement_state.replaceAll("_", " ").toLowerCase()) + '</span>' + hold + '</td>' +
      '<td>' + escapeHtml(row.price ? formatPrice(row.price) : (row.source_native_price || "Unpriced")) +
        (row.source_native_price && !row.price ? '<small>native source snapshot</small>' : '') + '</td>' +
      '<td>' + source + '</td>' +
    '</tr>';
  }).join("");

  const blocks = candidate.blockers.length
    ? '<div class="detail-box"><h3>Blockers</h3><ul>' + candidate.blockers.map(x => '<li>' + escapeHtml(x) + '</li>').join("") + '</ul></div>'
    : '<div class="detail-box"><h3>Blockers</h3><ul><li>No architecture-level blocker is asserted by the current reference data. Physical gates still apply.</li></ul></div>';

  const unknowns = '<div class="detail-box"><h3>Measure / resolve next</h3><ul>' +
    candidate.unknowns.map(x => '<li>' + escapeHtml(x) + '</li>').join("") + '</ul></div>';

  const why = '<div class="detail-box"><h3>Why it fits</h3><ul>' +
    candidate.explanations.map(x => '<li>' + escapeHtml(x) + '</li>').join("") + '</ul></div>';

  const composition = candidate.origin === "SYNTHESIZED" && candidate.composition
    ? '<div class="detail-box composition-detail"><h3>How this board was composed</h3>' +
      '<p>' + escapeHtml(candidate.composition.rationale) + '</p>' +
      '<ul>' +
        Object.entries(candidate.composition.selection || {}).map(([slot, value]) =>
          '<li><strong>' + escapeHtml(slot.replaceAll("_", " ")) + ':</strong> ' +
          escapeHtml(String(value ?? "none")) + '</li>'
        ).join("") +
      '</ul>' +
      '<p class="composition-states">' +
        Object.entries(candidate.composition.compatibility_states || {})
          .filter(([, count]) => Number(count) > 0)
          .map(([status, count]) =>
            escapeHtml(status.replaceAll("_", " ").toLowerCase()) + ': ' + Number(count)
          ).join(' · ') +
      '</p></div>'
    : '<div class="detail-box"><h3>Candidate origin</h3><p>Curated reference architecture retained as a stable comparison and regression anchor.</p></div>';

  const compatibility = '<div class="detail-box"><h3>Compatibility evidence</h3><ul>' +
    (candidate.compatibility_findings.length
      ? candidate.compatibility_findings.map(x => '<li><strong>' + escapeHtml(x.state.replaceAll("_", " ").toLowerCase()) + ':</strong> ' + escapeHtml(x.reason) + '</li>').join("")
      : '<li>No explicit selected-pair rule fired for this candidate.</li>') +
    '</ul></div>';

  $("#candidate-detail").innerHTML = composition + blocks + unknowns + why + compatibility;
  renderSwapLab(candidate, state.swapBaselineId !== candidate.id);
}


function signedUsd(value) {
  const number = Number(value || 0);
  if (Math.abs(number) < 0.005) return "USD 0";
  return (number > 0 ? "+USD " : "−USD ") + Math.abs(number).toFixed(0);
}

function customTwinUrl(candidate, swapResult) {
  const twin = swapResult.twin_state || {};
  const visual = visualStateFromSwap(
    candidate,
    swapResult,
    state.bundle.geometry,
    state.bundle.catalog
  );
  const params = new URLSearchParams({
    preset: candidate.visual_preset,
    candidate: "custom:" + candidate.id,
    deck: twin.deck_candidate_id || candidate.deck_candidate_id,
    topology: twin.topology_id || candidate.topology_id,
    wheel: visual.wheel.study_id,
    drive_type: visual.visual_style.drive_type,
    brake_family: visual.visual_style.brake_family,
  });
  if (Number.isFinite(Number(twin.stance_mm))) {
    params.set("stance_mm", String(twin.stance_mm));
  }
  for (const [layer, visible] of Object.entries(twin.layers || {})) {
    params.set(layer, visible ? "1" : "0");
  }
  return "../showcase/?" + params.toString();
}

function renderSwapBom(rows) {
  const body = $("#swap-bom-body");
  if (!body) return;
  body.innerHTML = rows.map(row => {
    const source = row.source_url
      ? '<a class="source-link" href="' + escapeHtml(row.source_url) + '" target="_blank" rel="noreferrer">Vendor source</a>' +
        '<small>snapshot ' + escapeHtml(row.source_as_of || "unknown") + '</small>'
      : '<span>Reference / TBD</span><small>No checkout link is asserted.</small>';
    const hold = row.hold_reason
      ? '<small>' + escapeHtml(row.hold_reason) + '</small>'
      : "";
    const stateClass =
      row.procurement_state === "POWER_GATED"
        ? "blocked"
        : row.procurement_state === "HOLD_MEASURE"
          ? "measure"
          : "";
    return '<tr>' +
      '<td>' + escapeHtml(row.category.replaceAll("_", " ")) + '</td>' +
      '<td><strong>' + escapeHtml(row.label) + '</strong><small>' +
        escapeHtml([row.manufacturer, row.sku].filter(Boolean).join(" · ") || row.component_id) +
      '</small></td>' +
      '<td><span class="badge ' + stateClass + '">' +
        escapeHtml(row.procurement_state.replaceAll("_", " ").toLowerCase()) +
      '</span>' + hold + '</td>' +
      '<td>' + escapeHtml(row.price ? formatPrice(row.price) : (row.source_native_price || "Unpriced")) +
        (row.source_native_price && !row.price ? '<small>native source snapshot</small>' : '') + '</td>' +
      '<td>' + source + '</td>' +
    '</tr>';
  }).join("");
}

function renderSwapFindings(result) {
  const host = $("#swap-findings");
  if (!host) return;

  const blockers = result.blockers.length
    ? result.blockers.map(text => '<li>' + escapeHtml(text) + '</li>').join("")
    : '<li>No custom-design hard blocker is asserted by the current rules. Physical gates still apply.</li>';

  const unknowns = result.unknowns.length
    ? result.unknowns.map(text => '<li>' + escapeHtml(text) + '</li>').join("")
    : '<li>No additional custom-design measurement hold is asserted.</li>';

  const compatibility = result.compatibility_findings.length
    ? result.compatibility_findings.map(finding =>
        '<li><strong>' + escapeHtml(finding.state.replaceAll("_", " ").toLowerCase()) +
        ':</strong> ' + escapeHtml(finding.reason) + '</li>'
      ).join("")
    : '<li>No selected component pair triggered an explicit compatibility rule.</li>';

  const changes = result.changes.length
    ? result.changes.map(change =>
        '<li><strong>' + escapeHtml(change.slot.replaceAll("_", " ")) + ':</strong> ' +
        escapeHtml(String(change.from ?? "none")) + ' → ' +
        escapeHtml(String(change.to ?? "none")) + '</li>'
      ).join("")
    : '<li>Edited design matches the generated baseline.</li>';

  host.innerHTML =
    '<div class="detail-box"><h3>Changes from baseline</h3><ul>' + changes + '</ul></div>' +
    '<div class="detail-box"><h3>Blockers</h3><ul>' + blockers + '</ul></div>' +
    '<div class="detail-box"><h3>Measure / resolve next</h3><ul>' + unknowns + '</ul></div>' +
    '<div class="detail-box"><h3>Compatibility evidence</h3><ul>' + compatibility + '</ul></div>';
}

function renderSwapPreview(candidate) {
  const host = $("#swap-preview");
  if (!host || !state.swapResult) return;
  const visual = visualStateFromSwap(
    candidate,
    state.swapResult,
    state.bundle.geometry,
    state.bundle.catalog
  );
  host.innerHTML = renderBoardPreviewSvg(
    visual,
    state.galleryView,
    { width: 720, height: 360, compact: false }
  );
}

function renderSwapResult(candidate) {
  const result = state.swapResult;
  if (!result) return;

  renderSwapPreview(candidate);

  $("#swap-summary").innerHTML =
    '<span class="summary-pill">Edited subtotal: <strong>' +
      escapeHtml(partialCost(result)) + '</strong></span>' +
    '<span class="summary-pill">Readiness: <strong>' +
      escapeHtml(readinessLabel(result.readiness)) + '</strong></span>' +
    '<span class="summary-pill">Checkout: <strong>' +
      escapeHtml(result.checkout_state.replaceAll("_", " ").toLowerCase()) + '</strong></span>' +
    '<span class="summary-pill">Changes: <strong>' +
      result.changes.length + '</strong></span>';

  const delta = result.cost_delta_vs_baseline;
  $("#swap-delta").innerHTML =
    '<div><span>Known-price delta low</span><strong>' +
      escapeHtml(signedUsd(delta.known_min_usd)) + '</strong></div>' +
    '<div><span>Known-price delta high</span><strong>' +
      escapeHtml(signedUsd(delta.known_max_usd)) + '</strong></div>' +
    '<div><span>Unpriced study items</span><strong>' +
      result.cost.unpriced_component_ids.length + '</strong></div>';

  renderSwapFindings(result);
  renderSwapBom(result.bom);

  const twin = $("#open-custom-twin");
  twin.classList.remove("disabled");
  twin.href = customTwinUrl(candidate, result);
}

function evaluateCurrentSwap(candidate) {
  if (!candidate || !state.swapSelection) return;
  state.swapResult = evaluateSwap(
    candidate,
    state.result.requirements,
    state.swapSelection,
    state.bundle,
    state.bundle.swapSlots
  );
  renderSwapResult(candidate);
}

function renderSwapControls(candidate) {
  const host = $("#swap-controls");
  if (!host) return;
  const baseline = seedSwapSelection(candidate);
  host.innerHTML = "";

  for (const slot of state.bundle.swapSlots.slots || []) {
    const wrapper = document.createElement("div");
    wrapper.className = "swap-control";

    const label = document.createElement("label");
    label.htmlFor = "swap-" + slot.id;
    label.textContent = slot.label;

    const select = document.createElement("select");
    select.id = "swap-" + slot.id;
    select.dataset.swapSlot = slot.id;

    for (const optionRow of slot.options || []) {
      const option = document.createElement("option");
      option.value = optionRow.value === null ? "__none__" : String(optionRow.value);
      option.textContent =
        optionRow.label +
        (baseline[slot.id] === optionRow.value ? " · baseline" : "");
      select.appendChild(option);
    }

    const selected = state.swapSelection[slot.id];
    select.value = selected === null ? "__none__" : String(selected);
    select.addEventListener("change", () => {
      state.swapSelection[slot.id] =
        select.value === "__none__" ? null : select.value;
      evaluateCurrentSwap(candidate);
    });

    wrapper.append(label, select);
    host.appendChild(wrapper);
  }
}

function renderSwapLab(candidate, forceReset = false) {
  if (!candidate) return;
  if (forceReset || state.swapBaselineId !== candidate.id || !state.swapSelection) {
    state.swapBaselineId = candidate.id;
    state.swapSelection = seedSwapSelection(candidate);
  }
  renderSwapControls(candidate);
  evaluateCurrentSwap(candidate);
}

function resetSwaps() {
  const candidate = state.result?.candidates.find(row => row.id === state.selectedId);
  if (!candidate) return;
  state.swapSelection = seedSwapSelection(candidate);
  renderSwapControls(candidate);
  evaluateCurrentSwap(candidate);
}

function exportCustomDesign() {
  const candidate = state.result?.candidates.find(row => row.id === state.selectedId);
  if (!candidate || !state.swapResult) return;
  downloadJson("worcester-custom-board-" + candidate.id + ".json", {
    schema_version: 1,
    profile: state.result.profile,
    requirements: state.result.requirements,
    baseline_candidate: candidate,
    custom_study: state.swapResult,
    visual_state: visualStateFromSwap(
      candidate,
      state.swapResult,
      state.bundle.geometry,
      state.bundle.catalog
    ),
    winner_selected: false,
    source_snapshot_as_of: state.bundle.catalog.as_of,
    note:
      "Exported Swap Lab design study. It does not create procurement, fabrication, charging or powered-operation authority.",
  });
}

function recompute() {
  if (!state.bundle) return;
  state.result = generateBoardDesignSpace(state.profile, state.bundle);
  state.swapBaselineId = null;
  state.swapSelection = null;
  state.swapResult = null;

  if (!state.selectedId || !state.result.candidates.some(x => x.id === state.selectedId)) {
    state.selectedId = state.result.candidates[0]?.id || null;
  }

  renderRequirements(state.result.requirements);
  renderVendorFilters(state.result.candidates);
  renderCandidates(state.result.candidates);
  renderBom(state.result.candidates.find(x => x.id === state.selectedId));
  $("#recompute-status").textContent =
    "Live · " + state.result.candidates.length + " candidates · " +
    (state.result.composition_summary?.synthesized_count || 0) + " composed · " +
    new Set(state.result.candidates.map(row => row.vendor_family || "Unspecified")).size +
    " families";
}

function scheduleRecompute() {
  if (state.renderQueued) return;
  state.renderQueued = true;
  requestAnimationFrame(() => {
    state.renderQueued = false;
    recompute();
  });
}

function downloadJson(filename, payload) {
  const blob = new Blob([JSON.stringify(payload, null, 2) + "\n"], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function exportProfile() {
  downloadJson("worcester-board-profile.json", {
    schema_version: 1,
    profile: state.result?.profile || state.profile,
    requirements: state.result?.requirements || null,
    winner_selected: false,
    note: "Exported planning profile. This file does not create build authority.",
  });
}

function exportSelectedDesign() {
  const selected = state.result?.candidates.find(row => row.id === state.selectedId);
  if (!selected) return;
  downloadJson("worcester-board-design-" + selected.id + ".json", {
    schema_version: 1,
    profile: state.result.profile,
    requirements: state.result.requirements,
    selected_for_inspection: selected,
    visual_state: candidateVisualState(selected),
    winner_selected: false,
    authority: state.result.authority,
    source_snapshot_as_of: state.bundle.catalog.as_of,
    note:
      "Exported planning design. Selection is for inspection only and does not create procurement, fabrication, charging or powered-operation authority.",
  });
}

async function main() {
  try {
    state.bundle = await loadBundle();
    state.profile = restoreProfile(state.bundle.questionnaire);
    renderQuestionnaire();
    recompute();

    $("#detail-mode").addEventListener("click", () => {
      state.advanced = !state.advanced;
      $("#detail-mode").textContent = state.advanced ? "Hide advanced" : "Show advanced";
      renderQuestionnaire();
    });

    $("#reset-profile").addEventListener("click", () => {
      state.profile = questionnaireDefaults(state.bundle.questionnaire);
      localStorage.removeItem(STORAGE_KEY);
      state.selectedId = null;
      renderQuestionnaire();
      recompute();
    });

    $("#export-profile").addEventListener("click", exportProfile);
    $("#export-design").addEventListener("click", exportSelectedDesign);
    $("#reset-swaps").addEventListener("click", resetSwaps);
    $("#export-custom-design").addEventListener("click", exportCustomDesign);
    document.querySelectorAll("[data-gallery-view]").forEach(button => {
      button.addEventListener("click", () => setGalleryView(button.dataset.galleryView));
    });
    document.querySelectorAll("[data-origin-filter]").forEach(button => {
      button.addEventListener("click", () => {
        state.originFilter = button.dataset.originFilter;
        document.querySelectorAll("[data-origin-filter]").forEach(row => {
          row.classList.toggle("active", row.dataset.originFilter === state.originFilter);
        });
        renderVendorFilters(state.result.candidates);
        renderCandidates(state.result.candidates);
      });
    });
  } catch (error) {
    console.error(error);
    $("#questionnaire").innerHTML = '<div class="note warning">Board Builder failed to load: ' + escapeHtml(error.message) + '</div>';
    $("#recompute-status").textContent = "Load failed";
  }
}

main();
