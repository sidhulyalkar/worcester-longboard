#!/usr/bin/env python3
"""Offline STEP -> self-contained glTF 2.0 binary candidate converter.

STAGING / VISUALIZATION ONLY. The source STEP is imported using OCCT's
declared units converted to millimeters. Mesh coordinates become meters as
required by glTF. The receipt establishes byte provenance and numeric
conversion, NOT source authenticity, mounting geometry or safety.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import tempfile


def sha256(contents: bytes) -> str:
    return hashlib.sha256(contents).hexdigest()


def convert(step_path: Path, glb_path: Path, *, tolerance_mm: float = 0.2,
            angle_rad: float = 0.15) -> dict:
    import cadquery as cq
    import numpy as np
    import trimesh

    if step_path.suffix.lower() not in (".step", ".stp"):
        raise ValueError("An original STEP (.step/.stp) file is required.")
    if not 0.05 <= tolerance_mm <= 1.0 or not 0.05 <= angle_rad <= 0.8:
        raise ValueError("Use a declared bounded tessellation tolerance.")
    contents = step_path.read_bytes()
    if not 64 <= len(contents) <= 100_000_000:
        raise ValueError("STEP input size outside 64 B to 100 MB budget.")
    glb_path.parent.mkdir(parents=True, exist_ok=True)

    # CadQuery/OCCT interprets the STEP header unit and produces millimeters.
    shape = cq.importers.importStep(str(step_path), unit="MM")
    with tempfile.TemporaryDirectory() as folder:
        stl = Path(folder) / "candidate-in-mm.stl"
        cq.exporters.export(shape, str(stl), exportType="STL",
                            tolerance=tolerance_mm,
                            angularTolerance=angle_rad)
        mesh = trimesh.load_mesh(str(stl), file_type="stl", process=False)
    if not isinstance(mesh, trimesh.Trimesh) or mesh.is_empty:
        raise ValueError("No usable solid/mesh emitted from STEP.")
    if len(mesh.vertices) > 1_000_000 or len(mesh.faces) > 1_500_000:
        raise ValueError("Tessellation exceeds preview vertex/triangle budget.")
    bounds_mm = mesh.bounds.astype(float)
    extents_mm = bounds_mm[1] - bounds_mm[0]
    if not np.isfinite(bounds_mm).all() or not np.isfinite(extents_mm).all():
        raise ValueError("Nonfinite STEP mesh coordinates.")
    if np.any(extents_mm <= 0) or np.max(extents_mm) > 10_000:
        raise ValueError("Degenerate or over-range mesh; confirm original source units.")
    mesh.apply_scale(0.001)  # mm in OCC -> meters in glTF
    glb = mesh.export(file_type="glb")
    if not isinstance(glb, bytes) or not 28 <= len(glb) <= 25_000_000:
        raise ValueError("Exported GLB exceeds browser budget.")
    scene = trimesh.load(io.BytesIO(glb), file_type="glb",
                         force="scene", process=False)
    extents_m = (scene.bounds[1] - scene.bounds[0]).astype(float)
    # Frame orientation may be rotated by the glTF exporter (Y up versus
    # CAD Z up). Only sorted extents, not unverified axes, are compared.
    error_mm = float(np.max(np.abs(np.sort(extents_m * 1000) -
                                   np.sort(extents_mm))))
    if not math.isfinite(error_mm) or error_mm > max(tolerance_mm * 0.1, 0.02):
        raise ValueError("GLB conversion altered source bounding dimensions.")
    glb_path.write_bytes(glb)
    receipt = {
        "schema_version": 1,
        "scope": "STEP_TO_GLTF_CONVERSION_RECEIPT_NOT_MEASURED_FIT",
        "source_step_sha256": sha256(contents),
        "output_glb_sha256": sha256(glb),
        "source_cad_units": "mm",
        "gltf_scene_units": "m",
        "mm_to_gltf_m_scale": 0.001,
        "source_step_bytes": len(contents),
        "output_glb_bytes": len(glb),
        "source_bounds_mm": bounds_mm.tolist(),
        "source_extents_mm": extents_mm.tolist(),
        "gltf_sorted_extents_m": sorted(float(x) for x in extents_m),
        "max_sorted_extent_error_mm": error_mm,
        "tessellation_tolerance_mm": tolerance_mm,
        "angular_tolerance_rad": angle_rad,
        "geometry_revision_confirmed": False,
        "mounting_datums_verified": False,
        "physical_clearance_qualified": False,
        "procurement_authorized": False,
        "fabrication_authorized": False,
    }
    receipt_path = glb_path.with_suffix(glb_path.suffix + ".conversion.json")
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--tolerance-mm", type=float, default=0.2)
    parser.add_argument("--angular-tolerance-rad", type=float, default=0.15)
    args = parser.parse_args()
    info = convert(args.source, args.out, tolerance_mm=args.tolerance_mm,
                   angle_rad=args.angular_tolerance_rad)
    print(json.dumps({"glb": str(args.out),
                      "receipt": str(args.out) + ".conversion.json",
                      "digest": info["output_glb_sha256"],
                      "physical_fit_qualified": False}, indent=2))


if __name__ == "__main__":
    main()
