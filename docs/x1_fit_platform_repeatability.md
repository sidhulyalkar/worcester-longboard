# Worcester X1 Issue #63 one-zone platform repeatability

**Purpose:** verify that the fully assembled Issue #4 single-point sensor/pad stack preserves the existing calibration envelope across realistic off-axis platform loads before it is duplicated into four rider-fit zones.

**Authority emitted:** `x1_fit_platform_repeatability`

**Powered-operation authority:** none.

## Why this exists

Issue #4 proves that one assembled load-cell path calibrates cleanly.

Issue #59 proves which exact sensor hardware was used.

Issue #61 proves the physical calibration and validation masses.

Issue #63 asks a different question:

> Does the complete pad/pod/load-cell assembly still measure the same qualified validation mass when the load is moved around the usable pad surface?

Phidgets describes single-point cells as platform-scale sensors intended to tolerate off-axis loading. That is an architectural property of the sensor type, not proof that X1's printed/machined pad, fastener stack, overload stops, wiring, and carrier preserve it.

The assembled fixture therefore gets its own platform test.

## Gate placement

The authority chain is intentionally split:

```text
Issue #4 one-zone calibration
        |
        +----> Rev-C chassis-release evidence may continue
        |
        v
Issue #63 platform repeatability
        |
        v
four-zone duplication
        |
        v
rider-fit qualification
```

Issue #63 should not hold chassis selection hostage. It exists specifically to stop a center-calibrated but position-sensitive sensor module from being copied four times.

## Preconditions

Before starting:

- Issue #4 has a fingerprint-valid `x1_one_zone_pilot` authority;
- Issue #59 and Issue #61 provenance are already embedded in that authority;
- the exact one-zone hardware remains assembled;
- the one-zone linear fit is not changed;
- the independent validation mass from Issue #61 is available;
- the fixture remains rigidly secured to the bench.

Do not use a different weight merely because it is easier to reposition.

## Initialize the private session

```bash
PYTHONPATH=. python tools/init_x1_fit_platform_repeatability.py \
  rider/private/fit_rig/issue63-platform \
  --one-zone-authority rider/private/fit_rig/issue4-pilot/pilot_authority.json \
  --session-id PLATFORM-001
```

The initializer copies the exact Issue #4 authority into the new workspace and exposes the bound validation mass, uncertainty, linear fit, channel, and HX711 rate.

## Load interface

Use one stable contact interface for all five positions.

Record:

- interface ID;
- contact length;
- contact width;
- notes describing the actual contact surface.

The contact footprint must remain entirely on the 105 x 78 mm zone pad for every placement.

Do not change the contact adapter between center and edge tests.

## Required positions

Capture:

- `CENTER`;
- `+X`;
- `-X`;
- `+Y`;
- `-Y`.

These names describe actual measured centroid coordinates in the pad coordinate frame.

Record the centroid, do not infer it from a visual label.

The test deliberately does **not** prescribe an arbitrary corner offset. Move far enough to create a meaningful off-axis load while keeping the declared contact footprint fully supported and maintaining positive overload-stop clearance.

`CENTER` must have the smallest radial centroid offset of the five positions.

## Capture sequence

1. Record `zero_pre`.
2. Place the same Issue #61 validation mass at each declared position.
3. Capture at least three settled plateau logs per position.
4. Do not re-zero between positions.
5. Do not refit/recalibrate between positions.
6. Keep the fixture secured and wiring/strain relief unchanged.
7. Measure the minimum overload-stop clearance at each position.
8. Record any rocking, interference, or cable-force observation.
9. Record `zero_post`.

Use the same HX711 rate as the qualified Issue #4 authority.

## Per-position evaluation

Each plateau is converted to force using the **existing Issue #4 linear fit**.

For every run the qualifier reports:

- predicted force;
- predicted mass;
- nominal error against the Issue #61 validation mass;
- conservative validation error including Issue #61 reference uncertainty.

The same canonical Issue #4 validation-error ceiling applies independently to every run.

A center pass cannot compensate for an edge failure.

## Mechanical failures

A position fails if:

- the declared contact footprint leaves the pad;
- overload-stop clearance falls below the qualified Issue #4 minimum;
- the load rocks;
- pad/pod/fastener interference appears;
- repositioning introduces cable/strain-relief force;
- the load is not fully supported.

These conditions indicate that the platform mechanics changed the sensor load path.

## Cross-position spread

The report also computes:

- mean predicted force per position;
- repeatability half-range per position;
- relative bias versus CENTER;
- max-to-min cross-position spread relative to reference force.

Those are diagnostic metrics.

Issue #63 does **not** invent a Phidgets corner-load tolerance that the vendor has not published.

The gate remains simpler: every position must preserve the already-qualified Issue #4 conservative validation envelope.

## Zero return

The pre/post zero drift is evaluated against the existing Issue #4 full-scale calibration force and the existing `max_zero_return_fs` limit.

This catches fixture creep while the mass is being moved around the pad.

## Qualification

```bash
PYTHONPATH=. python tools/qualify_x1_fit_platform_repeatability.py \
  rider/private/fit_rig/issue63-platform/platform_repeatability_manifest.json \
  --one-zone-authority rider/private/fit_rig/issue63-platform/provenance/one_zone_pilot_authority.json \
  --out rider/private/fit_rig/issue63-platform/platform_repeatability_authority.json
```

A passing report has:

```text
authority = x1_fit_platform_repeatability
scope = unpowered_fit_platform_repeatability_only
qualified = true
position_repeatability_qualified = true
four_zone_duplication_authorized = false
powered_operation_authorized = false
```

The project build-authority graph, not this report alone, combines Issue #4 and Issue #63 before allowing four-zone duplication.

## What a failure means

Do not compensate for an edge failure by recalibrating each position.

Investigate the assembly:

- pad flex;
- loaded-end fastener stack;
- fixed-end preload/alignment;
- pod rocking;
- overload-stop contact;
- cable strain;
- contact adapter geometry;
- carrier flatness;
- load-cell orientation.

Repair the mechanical cause, then create a new Issue #63 session.

## Boundary

Issue #63 remains:

- unpowered;
- bench-only;
- limited to the existing <=20 kg Issue #4 evidence regime;
- not ride-structure validation;
- not a new load-cell specification;
- not fabrication authority;
- not powered/public/dog-accompanied authority.
