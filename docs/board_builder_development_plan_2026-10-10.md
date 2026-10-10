# Worcester Board Builder: Development Plan (2026-10-10)

## North star

A new rider describes size, terrain, style, range, budget and constraints in ordinary language. In a short guided session, Board Builder returns up to three **mechanically distinct, inspectable engineering hypotheses** with synchronized 3D/2D visuals, explanations, source-aware BOMs and an actionable list of what has to be measured or professionally qualified before anything is ordered, fabricated, charged or ridden.

**Never equate a good design score with safe, compatible, in stock or build-ready.** Keep the existing X1 physical authority and Issue #25 release independent.

## Verified baseline

Merged: PR #84 (multi-vendor), #86 (catalog composition), #88 (source health), #89 (evidence explorer), #90 (example briefs/comparison/assembly onboarding), #91 (review-first deterministic natural-language parser). Current Builder includes Swap Lab, automated previews, 3D handoff, pairwise evidence and Python/browser parity. PR #91 is a local interpreter, not an LLM conversational agent. Independent real-browser UX and accessibility walkthroughs are still needed.

## Ship order and small PR contracts

### Gate 0: regression + UX baseline

- Run full Python, JS, catalog, CAD, firmware and procurement-authority suites before/after each PR; no changes in the X1 authority chain.
- Test the six existing starter briefs on desktop and mobile with mouse, touch and keyboard.
- Publish UI screenshots and accessibility findings with browser viewport sizes, not just static contract assertions.
- Characterize generation time and largest catalog fixture; capture reproducible before/after results.

**Done when:** source/build authority remains locked and the browser walkthrough has no blocker preventing completing a brief, selecting and comparing designs, or exporting planning evidence.

### Stage 1: conversation state v1.1, first slice (this PR)

- Add typed, versioned local session state with baseline profile, proposal, accepted change, rejected change, field provenance, undo history, revision and deterministic export.
- Convert relative requests (lighter, cheaper, lower maintenance, more snowboard-like) to non-authoritative **suggested diffs**, never silent profile changes or mechanical claims.
- Reuse existing questionnaire validation and ride-brief review; reject unknown keys, stale reviews, contradictory numeric bounds and unauthorized authority fields.
- One suggested question per review; preserve unanswered questions in the record.
- Add regression conversations including ambiguous distance, conflicting intents, correction, undo and manual-field provenance.

**Done when:** deterministic tests pass, no accepted field changes without explicit approval, all authority flags remain false, and no untouched key is mutated.

### Stage 1b: conversation UI and edit reconciliation

- Wire state into `builder/app.js` with turn history, proposed before/after field changes, grouped accept/reject, one clarifying question, undo, session export, and visible contradiction explanations.
- Handle manual questionnaire edits, example-brief resets, browser reloads and stale pending reviews without discarding accepted history or silently applying old suggestions.
- Validate local-only storage, aria-live announcements, keyboard flow, cross-device layout and long-text robustness.
- If integrating an LLM later, restrict it to producing *proposed* typed structured edits and clarifying questions. Deterministic validation remains authoritative.

**Done when:** a user can complete the canonical 175 lb / mixed dirt / 20-mile / $1,200 session and then ask for a lighter, cheaper variation without reentering specs. Every changed field is inspectable, reversible and source-labeled.

### Stage 2: feasibility and diverse search v1.2

- Separate hard constraints (incompatible axle/hub, required independent brake, maximum width, hard budget when known, physical authorization gate) from soft targets (carving feel, weight goal, range target, maintenance).
- Keep costs incomplete when source prices, shipping, labor, taxes or exchange rate are unknown. Hard budget feasibility is UNKNOWN when all-in total cannot be bounded.
- Add conflict-directed elimination and informative alternatives: `INCOMPATIBLE`, `UNKNOWN`, `MEASURE_FIRST`, `REFERENCE_COMPATIBLE`.
- Select three candidates via a diversity-aware Pareto frontier over actual deck/truck/wheel/brake/drive topology. Show fewer if fewer qualify, with reasons.
- Improve geometry/physics *planning* studies: loaded clearance, wheel radius, expected propulsion topology, brake space, stance geometry, weight-envelope scenarios, uncertainties and tolerance stackups. Never infer structural safety from a render.

**Done when:** controlled fixtures produce demonstrably distinct manual dirt, brake-first trail and budget electric concepts where viable; adversarial cross-vendor combinations remain unresolved or rejected; Python/browser parity holds.

### Stage 3: Build Passport and source health v1.3

- An exportable per-candidate record with every exact part variant and qty, manufacturer revision, interfaces, official source date/URL, regional price/currency, seller, and verified-vs-unknown stock.
- Separate planning known-price subtotal from supplier-confirmed quote, and from all-in estimate including shipping/tax/tools/labor/specialist integration.
- Add source refresh queue, stale/changed listing warnings, alternates limited to compatibility-evidenced parts, and quote expiry.
- Add receiving inspection and versioned photo/measurement slots.
- Source URLs remain navigational until an independently authorized procurement release, especially for battery/BMS/controller/charger.

**Done when:** exports are reproducible, omissions conspicuous, every buyer-facing listing has evidence of exact variant, source date and a clearly defined gate.

### Stage 4: assembly learning and qualified handoff v1.4

- Assembly path by skill: unpowered rolling chassis, reversible mechanical fit, measured friction braking, electrical system by a qualified integrator, isolated bench commissioning, venue-specific tests.
- Per-step skill/tool/fastener/torque-document requirements, dependency graph, risk warnings and photo checklists. Manufacturer values must be sourced, never guessed.
- Inert fit and brake-first checks remain prerequisites. Include personal protective equipment, inspection, maintenance and battery handling guidance without loose-cell DIY tutorials.
- Versioned physical measurement receipt binds part IDs + exact revisions + evidence review and blocks unsupported substitutions.

**Done when:** a beginner knows what they can inspect themselves, what requires a technician, why a measured fit isn't a ride permit, and what steps are still blocked.

### Stage 5: physical pilots and X1/reference validation

- Follow existing Issue #4 one-zone and Issue #25 chassis purchase release; do not buy X1 parts before gates actually pass.
- Inert dimensional mockup, signed brake path qualification, loaded clearance/steering sweep, packaging, environmental and controlled commissioning protocols.
- Collect real observed ride-energy, vibrational/carve feel and maintenance data only after safe authorized testing; use these to calibrate confidence in the generic planner.
- Shasta companion use and public paths require their own venue/safety review, not just a general rider preference.

**Done when:** measured evidence can explain why a *specific* exact-version build advances through physical gates, without conferring that authority to unrelated generated designs.

### Stage 6: launch hardening and catalog growth

- More manufacturer families with standardized interface dimensions, dedicated 3D assets and retained source snapshots; prefer quality over raw SKU count.
- Accessibility, privacy, saved/exported projects, diff/share snapshots, guided onboarding, explainability and performance budgets.
- Optional live pricing/availability service and vendor integrations must use independent freshness checks; no claims from stale static snapshots.

## Product experience contract

1. **Describe**: natural language or six starter ride briefs; capture height/weight only when volunteered or directly asked. Private asymmetry and fit notes remain optional and local.
2. **Clarify**: ask the single highest-value unanswered question; clearly distinguish explicit facts from inferred recommendations.
3. **Review**: before/after specs with default opt-out for inferences; explicit commit and undo.
4. **Compare**: synchronized Hero/Top/Side and 3D, three *physically different* architectures when feasible, with confidence and blockers not collapsed into one rating.
5. **Refine**: "more snowboard feel", "lighter", "cheaper", "lower maintenance", "safer stopping", and component swaps create inspectable diffs.
6. **Source**: per-part provenance, pricing completeness and a purchase-readiness explanation, not a simulated checkout.
7. **Learn/qualify**: realistic assembly route, required tools and specialist steps, manufacturer-specific measurement and separate physical authority.

## Engineering invariants

- All conversation and visualization artifacts contain false procurement/fabrication/charging/powered-operation authority.
- Only questionnaire-whitelisted fields may change; an accepted diff must pass whole-profile cross-field validation.
- Field provenance distinguishes baseline, direct user fact, reviewed inference and manual editing. Undo must restore prior provenance.
- Source freshness is not availability; all-in cost is not known from a parts subtotal.
- Unknown fit/strength/clearance/braking/electrical interfaces do not become compatible by plausible narration.
- No ranking, animation, agent suggestion or "I understand" checkbox ever promotes physical authority.
- Document exact accepted revisions and replay the same profile through both Python and JS planners.

## Immediate next PR queue

1. **Conversation state core** (this PR): module, deterministic tests, CI, roadmap. No UI promotion claim.
2. **UI conversation integration**: turn history, change review, clarifying prompt and undo, manual-edit reconciliation, keyboard/mobile browser review.
3. **Constraint delta explanation**: soft vs hard distinction, rejections and candidate elimination receipts.
4. **Diverse candidate selection**: topology coverage tests, gracefully fewer than three viable candidates.
5. **Build Passport preview**: complete sourced record, unknown costs, learning-only assembly packet.

## Definition of user-facing success

A first-time user can complete the canonical ride brief, see why three boards differ, ask for one revision, and inspect exactly what changed without having to understand component vocabulary. Nobody is told a board is ready to buy or ride without the separate physical evidence and approval path.
