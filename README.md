# Worcester X1

Experimental off-road electric mountainboard platform focused on controllability, rider-specific fit, redundant stopping authority, instrumentation, and evidence-driven commissioning.

> **Status:** Alpha engineering development platform. No powered riding is authorized. The current physical program is deliberately low-energy: qualify one fit-rig force zone, measure/qualify an unpowered donor chassis and mechanical brake, then freeze personalized rider-interface geometry. Traction power remains gated.

## Current source of truth

X1 has moved beyond the original TRAMPA/14S Alpha sketch. Current build and purchasing decisions follow this order of authority:

1. machine-readable qualification reports produced from real physical evidence;
2. `hardware/build_authority.json` and `hardware/procurement_manifest.json`;
3. current geometry/measurement authorities under `cad/`, `hardware/`, and `docs/`;
4. older Alpha notes retained only as historical design exploration.

If an older document conflicts with a current manifest or qualified authority, the older document does **not** authorize a purchase, fabrication step, or ride test.

## Ordering and sourcing

Start with `docs/complete_ordering_guide.md` for the complete staged checkout and receiving procedure.

The ordering stack is deliberately split by function:

- `hardware/procurement_manifest.json` says what is currently orderable or blocked;
- `hardware/order_sources_2026-09-11.json` records the dated vendor/source snapshot used for the current shopping guide;
- `hardware/planned_system_bom.json` maps the complete future board without pretending TBD powered parts are frozen;
- `tools/render_procurement_packet.py` renders the currently authorized checkout packet;
- `tools/validate_ordering_spec.py` detects source/price/compatibility drift against repository authority.

The current complete Issue #4 convenience ceiling is **$120.90 before shipping/tax**, and optional owned tools/materials should be skipped. The preferred chassis path remains a complete MBS Comp 95 donor plus V5 mechanical brake after the fit-pilot handoff. Standard Rockstar II hubs are not assumed to accept the optional T2 9-inch tire; the 9-inch path remains physically and compatibility gated.

Storefront stock and prices can change faster than the repository. Refresh live availability before payment, but never use a storefront page to bypass a blocked repository item.

## Current development architecture

### Rider-fit path

```text
one 3135 load cell + one HX711
        -> physical one-zone qualification
        -> four-zone unpowered fit rig
        -> repeatable asymmetric stance evidence
        -> Rev-B left/right rider-interface CAD
```

The fit layer intentionally supports independent left/right foot dimensions, yaw, position, and removable cant while keeping truck geometry symmetric by default. Exact rider measurements and raw recordings stay under gitignored `rider/private/`.

### Chassis/brake path

The preferred cost-efficient reference is currently a complete **MBS Comp 95 donor chassis**, because it provides a coherent Matrix III / Rockstar II / pneumatic-wheel platform more cheaply than reconstructing the same mechanical interfaces piecemeal.

The current reference split is explicit:

- **Matrix III 400 mm brake-first geometry:** primary unpowered/brake measurement path.
- **MBS V5 mechanical brake:** physical interface must be measured and bench-qualified.
- **Matrix III 420 mm drive-clearance geometry:** comparison/reference only until brake/drive coexistence is demonstrated.
- **8-inch donor pneumatic wheels:** default first physical wheelset; 9-inch is an optional measured upgrade requiring a compatible hub architecture, not an assumed tire swap.

No rider-specific permanent drilling is authorized from shoe-size labels, approximate web dimensions, or Wi-Fi pose.

### Power path

Power hardware is **provisional and `POWER_GATED`**. The current procurement manifest tracks candidates such as a 12S4P professionally built pack, VESC-class controller, 6374-class motors, and MBS G1 drive only to preserve cost/compatibility comparisons. None of these are frozen or order-authorized yet.

Regenerative braking will remain supplemental. A qualified independent mechanical stopping path comes first.

## Executable build gates

Run:

```bash
python tools/evaluate_build_authority.py \
  hardware/build_authority.json \
  hardware/procurement_manifest.json
```

With no private physical-evidence reports, the public repository must remain conservative: inexpensive pilot parts and measurement-stage chassis parts can be considered, but four-zone duplication, rideable fabrication, power ordering, and powered operation stay blocked.

Local/private authority reports can be supplied with repeated `--evidence` arguments. CI tests the gate machinery with synthetic fixtures, but synthetic CI data never becomes physical authority.

## Repository map

- `hardware/` procurement, fit-rig interfaces, and build-state authority
- `cad/` parametric fit-rig and rolling-chassis reference geometry
- `fit/` calibration, provenance, stance scoring, and Rev-B data gates
- `tools/` capture, qualification, procurement, and authority evaluators
- `firmware/` fit-rig logger plus provisional vehicle-control research
- `simulation/` first-order sizing models
- `docs/` current rationale, measurement contracts, and commissioning boundaries
- `rider/` public schemas only; private measurements belong under `rider/private/`
- `bom/` historical Alpha BOM notes plus procurement snapshots

## Current physical milestones

- **#4** qualify one load-cell/HX711/pod zone before four-zone duplication
- **#2** build and qualify X1 Fit Rig v0.3
- **#14** measure and qualify the V5 mechanical-brake interface
- **#12** qualify the unpowered rolling chassis
- **#3** generate measurement-qualified Rev-B rider-interface CAD after fit evidence

These tracks can advance in parallel where their evidence does not depend on one another.

## Rider-specific modeling boundary

The profile schema uses direct measured values such as `mass_kg`, `board_mass_kg`, independent foot dimensions, natural yaw, and stance geometry. Shoe-size labels are descriptive only and are never converted into manufacturing dimensions.

RuView-style Wi-Fi pose can be used as auxiliary dynamic-comparison data, but it is not metric CAD authority and cannot command the board.

## Safety boundary

This repository is an engineering workspace, not a product certification. Printed fit-rig parts are calibration hardware, not qualified ride structure. High-current traction battery construction belongs with a qualified pack builder. Powered operation requires future explicit authority beyond the current gate graph; software limits never replace hard mechanical/electrical safety layers.
