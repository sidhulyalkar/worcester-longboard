import {
  formatPrice,
  generateCandidates,
  questionnaireDefaults,
} from "./engine.mjs";

const STORAGE_KEY = "worcester-board-builder-profile-v1";

const state = {
  bundle: null,
  profile: {},
  result: null,
  selectedId: null,
  advanced: false,
  renderQueued: false,
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
  const [questionnaire, rules, catalog, architectures, compatibility] = await Promise.all([
    fetchJson("../configurator/questionnaire.v1.json"),
    fetchJson("../configurator/rules.v1.json"),
    fetchJson("../catalog/board_components.v1.json"),
    fetchJson("../configurator/architectures.v1.json"),
    fetchJson("../configurator/compatibility_rules.v1.json"),
  ]);
  return { questionnaire, rules, catalog, architectures, compatibility };
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
  if (c.known_min_usd === c.known_max_usd) return "USD " + c.known_min_usd.toFixed(0);
  return "USD " + c.known_min_usd.toFixed(0) + "–" + c.known_max_usd.toFixed(0);
}

function twinUrl(candidate) {
  const spec = candidate.personalized_spec || {};
  const params = new URLSearchParams({
    preset: candidate.visual_preset,
    candidate: candidate.id,
  });
  if (Number.isFinite(Number(spec.stance_center_mm))) {
    params.set("stance_mm", String(spec.stance_center_mm));
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

  for (const candidate of candidates) {
    const card = document.createElement("article");
    card.className = "candidate" + (candidate.id === state.selectedId ? " selected" : "");

    const issueText = candidate.blockers.length
      ? '<div class="alert-mini red">' + candidate.blockers.length + ' blocker' + (candidate.blockers.length === 1 ? "" : "s") + '</div>'
      : candidate.unknowns.length
        ? '<div class="alert-mini">' + candidate.unknowns.length + ' unresolved item' + (candidate.unknowns.length === 1 ? "" : "s") + '</div>'
        : "";

    card.innerHTML =
      '<div class="candidate-top">' +
        '<div><h3>' + escapeHtml(candidate.label) + '</h3><p>' + escapeHtml(candidate.description) + '</p></div>' +
        '<div class="fit-score"><strong>' + Math.round(candidate.fit_score * 100) + '%</strong><span>profile fit</span></div>' +
      '</div>' +
      '<div class="badges">' +
        '<span class="badge ' + statusClass(candidate.readiness) + '">' + escapeHtml(readinessLabel(candidate.readiness)) + '</span>' +
        (candidate.trade_space_frontier ? '<span class="badge frontier">trade-space frontier</span>' : '') +
        '<span class="badge">' + escapeHtml(candidate.checkout_state.replaceAll("_", " ").toLowerCase()) + '</span>' +
      '</div>' +
      '<div class="traits">' + traitsHtml(candidate) + '</div>' +
      candidateSpecHtml(candidate) +
      issueText +
      '<div class="candidate-footer">' +
        '<div class="cost"><strong>' + partialCost(candidate) + '</strong><small>known-price subtotal · shipping/tax excluded</small></div>' +
        '<div class="candidate-actions">' +
          '<button type="button" data-inspect="' + escapeHtml(candidate.id) + '">Inspect BOM</button>' +
          '<a href="' + escapeHtml(twinUrl(candidate)) + '">3D</a>' +
        '</div>' +
      '</div>';

    card.querySelector("[data-inspect]").addEventListener("click", () => {
      state.selectedId = candidate.id;
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
      '<td>' + escapeHtml(formatPrice(row.price)) + '</td>' +
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

  const compatibility = '<div class="detail-box"><h3>Compatibility evidence</h3><ul>' +
    (candidate.compatibility_findings.length
      ? candidate.compatibility_findings.map(x => '<li><strong>' + escapeHtml(x.state.replaceAll("_", " ").toLowerCase()) + ':</strong> ' + escapeHtml(x.reason) + '</li>').join("")
      : '<li>No explicit selected-pair rule fired for this candidate.</li>') +
    '</ul></div>';

  $("#candidate-detail").innerHTML = blocks + unknowns + why + compatibility;
}

function recompute() {
  if (!state.bundle) return;
  state.result = generateCandidates(state.profile, state.bundle);

  if (!state.selectedId || !state.result.candidates.some(x => x.id === state.selectedId)) {
    state.selectedId = state.result.candidates[0]?.id || null;
  }

  renderRequirements(state.result.requirements);
  renderCandidates(state.result.candidates);
  renderBom(state.result.candidates.find(x => x.id === state.selectedId));
  $("#recompute-status").textContent = "Live · " + state.result.candidates.length + " candidates";
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
  } catch (error) {
    console.error(error);
    $("#questionnaire").innerHTML = '<div class="note warning">Board Builder failed to load: ' + escapeHtml(error.message) + '</div>';
    $("#recompute-status").textContent = "Load failed";
  }
}

main();
