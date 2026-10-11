"""Synthetic, unlicensed unit tests: no OEM or approved part geometry."""
import json
import tempfile
from pathlib import Path

import cadquery as cq
import pytest
import trimesh

from tools.convert_cad_step_to_glb import convert


def test_step_to_glb_converts_millimeters_to_spec_meters_with_receipt():
    with tempfile.TemporaryDirectory() as root:
        folder = Path(root)
        step = folder / "synthetic-fixture.step"
        out = folder / "synthetic-fixture.glb"
        cq.exporters.export(cq.Workplane("XY").box(40, 20, 12),
                            str(step), exportType="STEP")
        receipt = convert(step, out)
        saved = json.loads((folder / "synthetic-fixture.glb.conversion.json").read_text())
        assert saved == receipt
        assert receipt["scope"] == "STEP_TO_GLTF_CONVERSION_RECEIPT_NOT_MEASURED_FIT"
        assert receipt["source_cad_units"] == "mm"
        assert receipt["gltf_scene_units"] == "m"
        assert receipt["mm_to_gltf_m_scale"] == 0.001
        assert sorted(round(x, 1) for x in receipt["source_extents_mm"]) == [12, 20, 40]
        assert sorted(round(x, 3) for x in receipt["gltf_sorted_extents_m"]) == [.012, .02, .04]
        assert receipt["max_sorted_extent_error_mm"] <= 0.02
        assert receipt["geometry_revision_confirmed"] is False
        assert receipt["mounting_datums_verified"] is False
        assert receipt["fabrication_authorized"] is False
        assert receipt["procurement_authorized"] is False
        scene = trimesh.load(out, force="scene", process=False)
        assert len(scene.geometry) >= 1


def test_converter_rejects_untrusted_filename_and_tessellation_budget():
    with tempfile.TemporaryDirectory() as root:
        folder = Path(root)
        wrong = folder / "not-a-step.obj"
        wrong.write_text("no cad present")
        with pytest.raises(ValueError, match="original STEP"):
            convert(wrong, folder / "no.glb")
        expected = folder / "broken.step"
        expected.write_text("not step")
        with pytest.raises(ValueError, match="STEP input size"):
            convert(expected, folder / "no.glb")
        with pytest.raises(ValueError, match="tessellation"):
            convert(expected, folder / "no.glb", tolerance_mm=5)
