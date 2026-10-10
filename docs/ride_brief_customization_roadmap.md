# Rider Brief v1: review-first, deterministic customization

This milestone introduces a plain-language **draft** above the existing questionnaire. It is not an LLM, shopping agent or certified board engineer.

## Interaction contract

1. User describes a ride in up to 2,400 characters. Parsing runs locally without a network request.
2. Parser produces a non-authoritative review with grouped suggestions. It never edits the profile.
3. Suggestions tagged EXPLICIT are checked by default; INFERRED suggestions (carve preference, terrain allocation and dog-accompanied stop/start) are unchecked. Users choose what to apply.
4. The review presents previous and proposed values, rationale, warning and remaining questions.
5. Only accepted groups update a copy of the existing questionnaire profile. Input is checked against canonical field identifiers, numeric bounds, option enums, terrain-sum constraints, typical vs longest ride, and hard vs target budget.
6. After acceptance, the existing Board Builder reruns requirements, curated and composed candidate synthesis, compatibility, geometry, 3D visuals, evidence explorer, priced/unpriced BOM, comparison and assembly-learning worklist.
7. No intent parsing, profile acceptance, preview, source health or score can change the X1 physical qualification, procurement, fabrication, charging or operation authorities.

### Cases deliberately NOT guessed

- A bare distance such as "16 miles" without saying whether it is typical or longest.
- "I don't know about electric boards" as a request for electric propulsion.
- Exact technical terrain percentages based on descriptive words: the suggested 100% mix is opt-in.
- Body weight or rider experience from height, shoe size, snowboarding, or age.
- An all-in build cost from a parts-budget target.
- Manufacturer fit, stock, torque specifications, or battery readiness from a catalog reference.

## Reproduce tests

Run:

    node --check builder/ride_brief.mjs
    node --test tests/js/test_board_ride_brief.mjs
    python -m pytest -q tests/test_board_builder_ui_contract.py

The workflow also exercises the full cross-runtime catalog and physical authority regressions.

## Agentic customization roadmap

### v1.1: conversational clarification and corrections
Add a turn-based review state that asks at most one high-value question at a time, can update only whitelisted requirements with provenance and preserves untouched profile keys. Support input like "make it less expensive" by producing a *delta preview* rather than silently re-ranking or ordering. Record user-confirmed answers separately from inferred suggestions.

**Acceptance:** deterministic golden conversations, contradictory instruction handling, no lost manual edits, no state promotion or undisclosed model assumptions.

### v1.2: constraint-driven design search
Add normalized hard vs soft requirements and explicit feasibility explanations. Score three diverse mechanical families with independent diversity constraints, not clones differing only in finish or component IDs. Expose exact source references and uncertainty for every substituted component.

**Acceptance:** mechanical consistency and conflict-directed search, documented pruning, diversity checks, cross-runtime parity, worst-case catalog corruption tests.

### v1.3: build passport and sourcing
Present a per-candidate bill of materials with qty, revision/variant, supplier, source date, USD + original-currency price, stock unknown, required tools and professional integration work. Export an inspectable assembly-learning packet and receiving checklist. Define *planning cost* separately from *confirmed quote* and separate known vs unknown totals.

**Acceptance:** stale / missing vendor data does not become a buy button; no implied total price; no charging or assembly authority from acknowledgement checkboxes.

### v2: physical qualification and supported assembly
Manufacturer-specific installation documents, measured interface records, a brake-first inert fit rig, load/clearance inspections, and independently reviewed high-energy component selection feed a separate qualification authority. Electrical/hardware changes are governed by the existing X1 physical gates, never by generative text.

**Acceptance:** physical evidence chain and independent sign-off before releasing purchasing, fabrication, powered testing or road use.

## Design decision

The goal is not to make a chatbot declare a board safe. It is to let people state intent naturally, understand tradeoffs visually, and iteratively improve a **traceable engineering hypothesis** until qualified suppliers, dimensions, manuals and tests support the next real-world action.
