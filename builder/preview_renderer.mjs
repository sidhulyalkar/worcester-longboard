const PALETTE = {
  bg: "#0b0f16",
  deck: "#2e3948",
  deckTop: "#3b4859",
  deckEdge: "#7a8798",
  truck: "#9aa4b2",
  tire: "#131922",
  tireEdge: "#596577",
  hub: "#8c98aa",
  pack: "#4b627d",
  snowdeck: "#c6d2df",
  armor: "#798493",
  dock: "#546477",
  brake: "#d7a44d",
  drive: "#6ea8fe",
  reference: "#62d7a0",
  measure: "#efc86f",
  blocked: "#f2737d",
  incompatible: "#ff5966",
  text: "#eef3f8",
  muted: "#8c98a8",
  grid: "#1b2431",
};

function esc(value) {
  return String(value == null ? "" : value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&apos;");
}

function statusAccent(readiness) {
  return {
    REFERENCE_COMPATIBLE: PALETTE.reference,
    MEASURE_FIRST: PALETTE.measure,
    BLOCKED: PALETTE.blocked,
    INCOMPATIBLE: PALETTE.incompatible,
  }[readiness] || PALETTE.muted;
}

function costLabel(cost) {
  if (!cost) return "";
  const low = Number(cost.known_min_usd || 0);
  const high = Number(cost.known_max_usd || 0);
  if (Math.abs(low - high) < 0.005) return "USD " + low.toFixed(0);
  return "USD " + low.toFixed(0) + "–" + high.toFixed(0);
}

function safeId(state) {
  return String(state.subject_id).replace(/[^a-zA-Z0-9]/g, "");
}

function geometry(state) {
  const deckScale = 430 / Number(state.deck.length_mm);
  const deckLength = Number(state.deck.length_mm) * deckScale;
  const deckWidth = Number(state.deck.width_mm) * deckScale;
  const wheelDiameter = Number(state.wheel.diameter_mm) * deckScale;
  const wheelWidth = Number(state.wheel.width_mm) * deckScale;
  const wheelLateral = Number(state.topology.wheel_center_lateral_mm) * deckScale;
  const truckWidth = Number(state.topology.truck_total_width_mm) * deckScale;
  const wheelbase = Math.min(deckLength * 0.81, 395);
  const stance = state.stance_mm ? Number(state.stance_mm) * deckScale : deckLength * 0.38;
  return {
    deckScale,
    deckLength,
    deckWidth,
    wheelDiameter,
    wheelWidth,
    wheelLateral,
    truckWidth,
    wheelbase,
    stance,
  };
}

function svgShell(state, inner, view, width, height, options) {
  const accent = statusAccent(state.readiness);
  const compact = Boolean(options && options.compact);
  let label = "";
  if (!compact) {
    label =
      '<text x="28" y="30" fill="' + PALETTE.text + '" font-size="15" font-weight="650">' +
      esc(state.label) +
      '</text>' +
      '<text x="28" y="49" fill="' + PALETTE.muted + '" font-size="10">' +
      esc(view.toUpperCase()) +
      ' · ' +
      esc(state.readiness.replaceAll("_", " ").toLowerCase()) +
      '</text>' +
      '<text x="' + (width - 28) + '" y="30" text-anchor="end" fill="' + accent +
      '" font-size="11" font-weight="650">' + esc(costLabel(state.cost)) + '</text>';
  }

  const id = safeId(state);
  return (
    '<svg class="board-preview-svg" viewBox="0 0 ' + width + ' ' + height +
    '" role="img" aria-label="' + esc(state.label) + ' ' + esc(view) +
    ' preview" xmlns="http://www.w3.org/2000/svg">' +
      '<defs>' +
        '<linearGradient id="deck-' + id + '" x1="0" x2="1" y1="0" y2="1">' +
          '<stop offset="0" stop-color="' + PALETTE.deckTop + '"/>' +
          '<stop offset="1" stop-color="' + PALETTE.deck + '"/>' +
        '</linearGradient>' +
        '<filter id="shadow-' + id + '" x="-30%" y="-30%" width="160%" height="160%">' +
          '<feDropShadow dx="0" dy="8" stdDeviation="9" flood-color="#000" flood-opacity=".34"/>' +
        '</filter>' +
      '</defs>' +
      '<rect width="' + width + '" height="' + height + '" rx="18" fill="' + PALETTE.bg + '"/>' +
      '<path d="M 0 ' + (height * 0.72) + ' H ' + width + '" stroke="' + PALETTE.grid + '" stroke-width="1"/>' +
      label +
      inner +
      '<g opacity=".94">' +
        '<circle cx="' + (width - 31) + '" cy="' + (height - 27) + '" r="4" fill="' + accent + '"/>' +
        '<text x="' + (width - 42) + '" y="' + (height - 23) + '" text-anchor="end" fill="' +
        PALETTE.muted + '" font-size="8">VISUAL STUDY</text>' +
      '</g>' +
    '</svg>'
  );
}

function deckPathTop(cx, cy, length, width) {
  const x0 = cx - length / 2;
  const x1 = cx + length / 2;
  const y0 = cy - width / 2;
  const y1 = cy + width / 2;
  const nose = Math.min(28, length * 0.07);
  const taper = Math.min(15, width * 0.12);
  return [
    "M " + (x0 + nose) + " " + (y0 + taper),
    "Q " + (x0 + 2) + " " + (y0 + width * 0.22) + " " + x0 + " " + cy,
    "Q " + (x0 + 2) + " " + (y1 - width * 0.22) + " " + (x0 + nose) + " " + (y1 - taper),
    "Q " + cx + " " + (y1 + 3) + " " + (x1 - nose) + " " + (y1 - taper),
    "Q " + (x1 - 2) + " " + (y1 - width * 0.22) + " " + x1 + " " + cy,
    "Q " + (x1 - 2) + " " + (y0 + width * 0.22) + " " + (x1 - nose) + " " + (y0 + taper),
    "Q " + cx + " " + (y0 - 3) + " " + (x0 + nose) + " " + (y0 + taper),
    "Z",
  ].join(" ");
}

function topShapes(state, width, height) {
  const g = geometry(state);
  const cx = width / 2;
  const cy = height * 0.55;
  const accent = statusAccent(state.readiness);
  const truckX = g.wheelbase / 2;
  const wheelH = Math.max(8, g.wheelWidth);
  const wheelW = Math.max(18, g.wheelDiameter * 0.48);
  const deckPath = deckPathTop(cx, cy, g.deckLength, g.deckWidth);
  let wheels = "";
  let trucks = "";

  if (state.wheel.visible) {
    for (const axle of [-1, 1]) {
      const x = cx + axle * truckX;
      trucks +=
        '<line x1="' + x + '" x2="' + x + '" y1="' + (cy - g.truckWidth / 2) +
        '" y2="' + (cy + g.truckWidth / 2) + '" stroke="' + PALETTE.truck +
        '" stroke-width="6" stroke-linecap="round"/>';
      for (const side of [-1, 1]) {
        const y = cy + side * g.wheelLateral;
        wheels +=
          '<rect x="' + (x - wheelW / 2) + '" y="' + (y - wheelH / 2) +
          '" width="' + wheelW + '" height="' + wheelH + '" rx="' + (wheelH / 2) +
          '" fill="' + PALETTE.tire + '" stroke="' + PALETTE.tireEdge +
          '" stroke-width="2"/>' +
          '<circle cx="' + x + '" cy="' + y + '" r="' + Math.max(4, wheelH * 0.24) +
          '" fill="' + PALETTE.hub + '"/>';
      }
    }
  }

  const stanceX = Math.min(g.stance / 2, g.deckLength * 0.32);
  let plates = "";
  if (state.layers.snowdeck) {
    for (const side of [-1, 1]) {
      const x = cx + side * stanceX;
      const plateH = Math.min(76, g.deckWidth * 0.60);
      plates +=
        '<rect x="' + (x - 34) + '" y="' + (cy - plateH / 2) +
        '" width="68" height="' + plateH + '" rx="10" fill="' + PALETTE.snowdeck +
        '" fill-opacity=".18" stroke="' + PALETTE.snowdeck +
        '" stroke-opacity=".62" stroke-width="1.5"/>';
    }
  }

  let systems = "";
  if (state.layers.pack) {
    systems += '<rect x="' + (cx - 74) + '" y="' + (cy - 32) +
      '" width="148" height="64" rx="12" fill="' + PALETTE.pack +
      '" fill-opacity=".48" stroke="' + PALETTE.pack + '" stroke-width="1.5"/>';
  }
  if (state.layers.brake && state.wheel.visible) {
    systems += '<circle cx="' + (cx - truckX) + '" cy="' + (cy + g.wheelLateral) +
      '" r="13" fill="none" stroke="' + PALETTE.brake + '" stroke-width="3"/>';
  }
  if (state.layers.drive && state.wheel.visible) {
    systems += '<rect x="' + (cx + truckX - 17) + '" y="' + (cy - g.wheelLateral - 11) +
      '" width="34" height="22" rx="6" fill="' + PALETTE.drive + '" fill-opacity=".68"/>';
  }
  if (state.layers.armor) {
    systems += '<rect x="' + (cx - 116) + '" y="' + (cy + g.deckWidth * 0.29) +
      '" width="232" height="7" rx="3.5" fill="' + PALETTE.armor + '" opacity=".7"/>';
  }
  if (state.layers.dock) {
    systems += '<path d="M ' + (cx - 32) + ' ' + (cy + g.deckWidth * 0.42) +
      ' L ' + cx + ' ' + (cy + g.deckWidth * 0.57) +
      ' L ' + (cx + 32) + ' ' + (cy + g.deckWidth * 0.42) +
      '" fill="none" stroke="' + PALETTE.dock +
      '" stroke-width="3" stroke-dasharray="7 5"/>';
  }

  return (
    '<g filter="url(#shadow-' + safeId(state) + ')">' +
      wheels +
      trucks +
      '<path d="' + deckPath + '" fill="url(#deck-' + safeId(state) +
      ')" stroke="' + accent + '" stroke-opacity=".58" stroke-width="2"/>' +
      systems +
      plates +
    '</g>' +
    '<line x1="' + (cx - stanceX) + '" y1="' + cy + '" x2="' + (cx + stanceX) +
    '" y2="' + cy + '" stroke="' + PALETTE.snowdeck +
    '" stroke-opacity=".35" stroke-width="1" stroke-dasharray="4 4"/>'
  );
}

function sideShapes(state, width, height) {
  const g = geometry(state);
  const cx = width / 2;
  const groundY = height * 0.73;
  const wheelR = Math.max(0, g.wheelDiameter / 2);
  const wheelCenterY = groundY - wheelR;
  const deckY = state.wheel.visible ? wheelCenterY - wheelR * 0.42 : groundY - 65;
  const truckX = g.wheelbase / 2;
  const deckX0 = cx - g.deckLength / 2;
  const deckX1 = cx + g.deckLength / 2;
  const accent = statusAccent(state.readiness);
  const deckThickness = 9;
  let wheels = "";
  let trucks = "";

  if (state.wheel.visible) {
    for (const side of [-1, 1]) {
      const x = cx + side * truckX;
      wheels +=
        '<circle cx="' + x + '" cy="' + wheelCenterY + '" r="' + wheelR +
        '" fill="' + PALETTE.tire + '" stroke="' + PALETTE.tireEdge +
        '" stroke-width="3"/>' +
        '<circle cx="' + x + '" cy="' + wheelCenterY + '" r="' + Math.max(6, wheelR * 0.27) +
        '" fill="' + PALETTE.hub + '"/>';
      trucks +=
        '<path d="M ' + (x - 20) + ' ' + (deckY + 9) + ' L ' + x + ' ' +
        (wheelCenterY - 3) + ' L ' + (x + 20) + ' ' + (deckY + 9) +
        '" fill="none" stroke="' + PALETTE.truck +
        '" stroke-width="5" stroke-linecap="round"/>';
    }
  }

  const deckPath = [
    "M " + deckX0 + " " + (deckY + 2),
    "Q " + (deckX0 + 32) + " " + (deckY - 13) + " " + (deckX0 + 70) + " " + (deckY - 4),
    "Q " + cx + " " + (deckY + 6) + " " + (deckX1 - 70) + " " + (deckY - 4),
    "Q " + (deckX1 - 32) + " " + (deckY - 13) + " " + deckX1 + " " + (deckY + 2),
    "L " + (deckX1 - 9) + " " + (deckY + deckThickness),
    "Q " + cx + " " + (deckY + deckThickness + 8) + " " + (deckX0 + 9) + " " + (deckY + deckThickness),
    "Z",
  ].join(" ");

  const stanceX = Math.min(g.stance / 2, g.deckLength * 0.32);
  let systems = "";

  if (state.layers.pack) {
    systems += '<rect x="' + (cx - 92) + '" y="' + (deckY + 18) +
      '" width="184" height="38" rx="9" fill="' + PALETTE.pack +
      '" fill-opacity=".58" stroke="' + PALETTE.pack + '" stroke-width="1.5"/>';
  }
  if (state.layers.armor) {
    systems += '<rect x="' + (cx - 116) + '" y="' + (deckY + 58) +
      '" width="232" height="8" rx="4" fill="' + PALETTE.armor + '" opacity=".74"/>';
  }
  if (state.layers.snowdeck) {
    for (const side of [-1, 1]) {
      systems += '<rect x="' + (cx + side * stanceX - 31) + '" y="' + (deckY - 10) +
        '" width="62" height="8" rx="4" fill="' + PALETTE.snowdeck + '" opacity=".72"/>';
    }
  }
  if (state.layers.brake && state.wheel.visible) {
    systems += '<circle cx="' + (cx - truckX) + '" cy="' + wheelCenterY +
      '" r="' + Math.max(10, wheelR * 0.55) +
      '" fill="none" stroke="' + PALETTE.brake + '" stroke-width="3"/>';
  }
  if (state.layers.drive && state.wheel.visible) {
    systems += '<rect x="' + (cx + truckX - 19) + '" y="' + (wheelCenterY - wheelR * 0.52) +
      '" width="38" height="24" rx="6" fill="' + PALETTE.drive + '" fill-opacity=".78"/>';
  }
  if (state.layers.dock) {
    systems += '<path d="M ' + (cx - 48) + ' ' + (groundY + 8) + ' Q ' + cx + ' ' +
      (groundY - 20) + ' ' + (cx + 48) + ' ' + (groundY + 8) +
      '" fill="none" stroke="' + PALETTE.dock +
      '" stroke-width="3" stroke-dasharray="7 5"/>';
  }

  return (
    '<g filter="url(#shadow-' + safeId(state) + ')">' +
      wheels + trucks +
      '<path d="' + deckPath + '" fill="' + PALETTE.deck + '" stroke="' + accent +
      '" stroke-opacity=".6" stroke-width="2"/>' +
      systems +
    '</g>' +
    '<line x1="65" y1="' + groundY + '" x2="' + (width - 65) + '" y2="' + groundY +
    '" stroke="' + PALETTE.grid + '" stroke-width="2"/>'
  );
}

function heroShapes(state, width, height) {
  const inner = topShapes(state, width, height);
  return '<g transform="translate(18 48) scale(.93 .78) skewY(-6)">' + inner + '</g>';
}

export function renderBoardPreviewSvg(state, view, options) {
  const actualView = view || "hero";
  const opts = options || {};
  if (!(state.views || []).includes(actualView)) {
    throw new Error("Unsupported preview view " + actualView);
  }
  const width = Number(opts.width || 720);
  const height = Number(opts.height || 360);
  let inner;
  if (actualView === "top") inner = topShapes(state, width, height);
  else if (actualView === "side") inner = sideShapes(state, width, height);
  else inner = heroShapes(state, width, height);
  return svgShell(state, inner, actualView, width, height, opts);
}

export function boardPreviewDataUrl(state, view, options) {
  const svg = renderBoardPreviewSvg(state, view || "hero", options || {});
  return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
}

export function downloadBoardPreviewSvg(state, view) {
  const actualView = view || "hero";
  const svg = renderBoardPreviewSvg(state, actualView);
  const blob = new Blob([svg], { type: "image/svg+xml;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  const safe = String(state.subject_id).replace(/[^a-zA-Z0-9_-]+/g, "-");
  anchor.href = url;
  anchor.download = safe + "-" + actualView + ".svg";
  anchor.click();
  URL.revokeObjectURL(url);
}
