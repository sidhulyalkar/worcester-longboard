# Worcester X1 Rev-C chassis-release playbook

**Purpose:** close Issue #25 with low-energy, pre-purchase evidence before ordering the chassis/brake measurement hardware.

This playbook does **not** authorize powered operation, battery construction, permanent rider-interface drilling, drivetrain purchase, or a claim that the eventual brake and drive physically coexist.

The release sequence is:

```
Issue #4 fit-pilot authority
        +
full-scale deck comparison authority
        +
pre-purchase topology trade authority
        +
inert pack-envelope authority
        ↓
x1_rev_c_chassis_release
        ↓
MEASURE_FIRST chassis/brake purchase may open
        ↓
Issue #14 brake interface
        ↓
Issue #12 physical rolling chassis
        ↓
Issue #19 physical brake/drive topology
        ↓
Rev-B + inert dummy-pack + power architecture
```

## 0. Workspace

Keep rider measurements and raw notes private:

```bash
mkdir -p rider/private/rev_c_release
```

Do not commit exact stance, body, foot, comfort or remount measurements.

Public templates and tools are allowed to operate on private files because the emitted authorities are sanitized.

---

## 1. Prerequisite: close Issue #4

The Rev-C chassis-release gate depends on `fit_pilot_qualified`.

Do not fake this authority to advance the purchase gate.

Your qualified fit-pilot authority should already contain:

- `qualified_for_four_zone_duplication = true`
- a valid `authority_fingerprint_sha256`

Keep its path available for the final release command.

For the examples below:

```
rider/private/fit_rig/issue4-pilot/qualified_fit_pilot.json
```

is a placeholder. Use the actual authority path produced by the Issue #4 workflow.

---

## 2. Generate the two full-scale deck envelopes

Generate:

```bash
python cad/generate_rev_c_deck_templates.py \
  --out-dir rider/private/rev_c_release/deck_templates
```

Current candidate maximum envelopes are:

| Candidate | Length | Max width |
|---|---:|---:|
| Comp 95 class | 950 mm | 251 mm |
| Agent class | 1020 mm | 280 mm |

These are stance/leverage envelopes only.

They are **not** exact deck outlines, structural CAD, hole patterns or fabrication templates.

### Physical construction

Use cardboard, foam board, thin plywood scrap or taped paper.

Mark:

- centerline;
- 50 mm grid;
- front/rear direction;
- approximate usable standing region;
- no permanent mounting holes.

Keep both templates on the same floor/surface and use the same shoes for the comparison.

---

## 3. Perform the deck comparison

Copy the private template:

```bash
cp hardware/rev_c_deck_comparison_private_template.json \
  rider/private/rev_c_release/deck_comparison.json
```

For **each** candidate perform at least three independent remount trials.

A remount means:

1. step completely off the template;
2. reset;
3. approach naturally;
4. step into a comfortable riding stance without matching the prior trial by eye.

For every trial, record privately:

- natural stance position;
- left/right foot yaw;
- heel/toe overhang or leverage impression;
- whether bilateral emergency step-off was easy;
- whether a deep-knee carve posture stayed inside a usable region;
- any pressure/comfort problem;
- whether the stance felt constrained by width or length.

The public qualifier only needs the booleans in each trial. Exact measurements may be added to the private file but are intentionally removed from the emitted authority.

### Pass criteria for the selected envelope

The selected candidate must have:

- at least three complete remount trials;
- bilateral emergency step-off accepted;
- deep-knee carve position accepted;
- heel/toe leverage accepted;
- remount repeatability accepted;
- subjective comfort accepted.

Every non-selected candidate must receive an explicit rejection reason.

Run:

```bash
python tools/qualify_rev_c_deck_comparison.py \
  rider/private/rev_c_release/deck_comparison.json \
  --out rider/private/rev_c_release/deck_comparison_authority.json
```

A passing report must say:

```
"authority": "x1_rev_c_deck_comparison"
"qualified": true
"powered_operation_authorized": false
```

The authority contains a hash of the private source but no raw rider measurements.

---

## 4. Run the front-vs-rear traction sensitivity sweep

Generate the mass-normalized topology screen:

```bash
python simulation/rev_c_topology_traction_sweep.py \
  --grades 0 0.10 0.20 0.30 \
  > rider/private/rev_c_release/topology_traction_sweep.json
```

This model is a rejection/sensitivity tool only.

It answers:

> As grade and longitudinal load transfer increase, how much tire/terrain friction would front versus rear 2WD require?

It does **not** estimate actual Worcester trail friction.

Hash the record:

```bash
python tools/hash_file.py \
  rider/private/rev_c_release/topology_traction_sweep.json
```

Copy that digest into the topology-trade manifest.

---

## 5. Complete the topology trade

Copy:

```bash
cp hardware/rev_c_topology_trade_template.json \
  rider/private/rev_c_release/topology_trade.json
```

Evaluate all four Rev-C branches:

### A. `REAR_V5_FRONT_2WD`

Preserves the documented MBS rear V5 brake architecture.

Primary unresolved risks:

- front traction unloading uphill;
- drive torque through the steering axle;
- possible front/rear width mismatch.

### B. `REAR_V5_REAR_2WD_SHARED`

Conventional rear-drive traction with rear V5 braking.

Primary unresolved risk:

- brake rotor/arm/cable and drive/coupler/guard coexistence around the same wheel end.

This branch cannot pass physical qualification from catalog compatibility alone.

### C. `REAR_2WD_FRONT_VENDOR_HYDRAULIC`

Preserves rear propulsion and moves independent braking to a complete vendor-engineered front brake architecture.

TRAMPA Infinity + Magura is an existence proof for this architecture family.

It is **not** permission to bolt unrelated hydraulic brake hardware onto a Matrix truck using a custom safety-critical adapter.

### D. `ALTERNATE_REAR_DRIVE_PRESERVING_V5`

Keeps the rear V5 envelope while studying a more compact drive.

Primary risks:

- mount retention;
- debris exposure;
- tension/service complexity;
- guard packaging.

### Selection rule

Select exactly **one** topology for the first physical measurement campaign.

Other candidates may remain `KEEP_LIVE`, `DEFERRED`, or be `REJECTED`.

The selected branch:

- must not retain a known catalog/safety contradiction;
- must have a credible independent stopping path;
- must have a concrete physical measurement plan;
- cannot depend on an unqualified brake adapter or spacer.

Run:

```bash
python tools/qualify_rev_c_topology_trade.py \
  rider/private/rev_c_release/topology_trade.json \
  --out rider/private/rev_c_release/topology_trade_authority.json
```

This selects only what to **measure first**. It is not the final Issue #19 topology authority.

---

## 6. Build inert battery-volume proxies

The Rev-C energy classes are:

- trail: 500–650 Wh;
- range: 950–1150 Wh.

Current MBS commercial references provide a useful mass warning:

- 540 Wh pack: 15 lb;
- 1089 Wh pack: 20 lb.

Do **not** infer exact X1 dimensions from those products.

The pre-purchase experiment uses inert volume only.

### Make two mock envelopes

Use empty cardboard, rigid foam, wood blocks or another harmless material.

Do not use cells, a live pack, loose lithium cells, high-current connectors, or a ballast arrangement that can fall onto your feet.

Represent:

- one trail-pack candidate;
- one range-pack candidate.

The goal is not to prove final battery construction.

The goal is to reject a chassis concept where the required energy volume obviously consumes the stance area, steering sweep or trail-clearance envelope.

Copy:

```bash
cp hardware/rev_c_inert_pack_envelope_template.json \
  rider/private/rev_c_release/inert_pack_envelope.json
```

Fill in:

- candidate chassis ID;
- declared available mounting envelope;
- trail/range inert envelope dimensions;
- inert target mass assumption;
- candidate placement;
- vulnerable-component ground keep-out;
- service-removal concept;
- retention concept;
- impact/skid concept.

### Required checks

Both pack classes must fit inside the declared candidate mounting envelope and you must explicitly confirm:

- rider stance keep-out clear;
- steering sweep keep-out clear;
- deck-flex keep-out clear;
- service removal direction defined;
- positive retention concept defined;
- sacrificial skid/impact path defined;
- no live battery used.

Run:

```bash
python tools/qualify_rev_c_inert_pack_envelope.py \
  rider/private/rev_c_release/inert_pack_envelope.json \
  --out rider/private/rev_c_release/inert_pack_envelope_authority.json
```

This is still only pre-purchase plausibility.

Issue #21 later performs the real inert **mass + CG + retention** test on the received rolling chassis.

---

## 7. Check the mass budget

Run both commercial-reference lower bounds:

```bash
python simulation/rev_c_mass_budget.py --configuration trail
python simulation/rev_c_mass_budget.py --configuration range
```

Current reference arithmetic:

```
Trail:
35.0 lb target
-14.6 lb Comp 95 reference
-15.0 lb 540 Wh MBS battery reference
= 5.4 lb headroom before drive/ESC/guards/etc.

Range:
45.0 lb target
-14.6 lb Comp 95 reference
-20.0 lb 1089 Wh MBS battery reference
= 10.4 lb headroom before drive/ESC/guards/etc.
```

Positive headroom is **not** proof the target can be met.

If the selected architecture cannot plausibly close the rest of the mass budget, record that as an open question or revise the aspirational finished-mass target before chassis freeze.

Never trade away:

- independent braking;
- positive battery retention;
- impact protection;
- safe structural load paths

merely to hit a round weight number.

---

## 8. Assemble the final Issue #25 release manifest

Copy:

```bash
cp hardware/rev_c_chassis_release_template.json \
  rider/private/rev_c_release/chassis_release.json
```

Use the authority fingerprints from:

- qualified fit pilot;
- `deck_comparison_authority.json`;
- `topology_trade_authority.json`;
- `inert_pack_envelope_authority.json`.

The final manifest must record:

- selected deck candidate;
- selected chassis family;
- selected wheel family;
- selected independent brake architecture;
- selected topology for first physical measurement;
- rejected alternatives;
- unresolved questions.

Run:

```bash
python tools/qualify_rev_c_chassis_release.py \
  rider/private/rev_c_release/chassis_release.json \
  --fit-pilot-authority <ACTUAL_ISSUE_4_AUTHORITY.json> \
  --deck-authority rider/private/rev_c_release/deck_comparison_authority.json \
  --topology-authority rider/private/rev_c_release/topology_trade_authority.json \
  --inert-pack-authority rider/private/rev_c_release/inert_pack_envelope_authority.json \
  --out rider/private/rev_c_release/chassis_release_authority.json
```

Passing output:

```
"authority": "x1_rev_c_chassis_release"
"qualified": true
"powered_operation_authorized": false
```

---

## 9. Verify what the release actually changes

Evaluate build authority using both Issue #4 and Rev-C evidence:

```bash
python tools/evaluate_build_authority.py \
  hardware/build_authority.json \
  hardware/procurement_manifest.json \
  --evidence <ACTUAL_ISSUE_4_AUTHORITY.json> \
  --evidence rider/private/rev_c_release/chassis_release_authority.json \
  --out rider/private/rev_c_release/build_authority_after_release.json
```

Expected result after a valid release:

### May open

- preferred `MEASURE_FIRST` chassis/brake ordering;
- currently selected donor/brake path only, subject to manifest preference rules.

### Must remain blocked

- wheel upgrades that have their own unresolved compatibility gates;
- 70 mm axle conversion until brake-first geometry is measured;
- G1 drive;
- motors;
- ESC;
- traction battery;
- powered operation;
- physical brake qualification;
- physical rolling-chassis qualification;
- final brake/drive topology;
- final power architecture.

If any power item becomes orderable from this authority alone, treat it as a regression.

---

## 10. Physical purchase boundary

Only after the Issue #25 report passes should the procurement packet be regenerated:

```bash
python tools/render_procurement_packet.py \
  --evidence <ACTUAL_ISSUE_4_AUTHORITY.json> \
  --evidence rider/private/rev_c_release/chassis_release_authority.json \
  --out rider/private/rev_c_release/current_procurement_packet.md
```

The public packet without private evidence remains intentionally fail-closed. Supplying the two private authority files above renders the evidence-aware measurement-stage checkout packet without changing repository policy.

Do not substitute a vendor sale, low used price, or shipping deadline for the release evidence.

---

## Exit condition

Issue #25 is complete when:

1. Issue #4 authority is valid;
2. the deck comparison authority is qualified;
3. the topology-trade authority is qualified;
4. the inert pack-envelope authority is qualified;
5. the chained `x1_rev_c_chassis_release` authority is qualified;
6. power ordering and powered operation remain blocked.

Only then should the project spend real money on the chassis/brake measurement path.
