"""Synthetic, unlicensed unit tests: no OEM or approved part geometry."""
import json
import shutil
import subprocess
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


def test_step_conversion_and_manifest_staging_isolated_in_temporary_repository():
    """Exercise real CLI success/failure without touching the user's source catalog."""
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as temporary:
        target = Path(temporary)
        for rel in (
            "tools/stage_cad_asset.mjs",
            "builder/cad_glb_contract.mjs",
            "builder/cad_asset_registry.mjs",
            "builder/cad_conversion_receipt.mjs",
            "catalog/outdoor_complete_kit_claims.v1.json",
            "catalog/outdoor_cad_asset_registry.v1.json",
        ):
            dest = target / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / rel, dest)

        step = target / "synthetic-source.step"
        glb = target / "candidate.glb"
        cq.exporters.export(cq.Workplane("XY").box(40, 20, 12),
                            str(step), exportType="STEP")
        conversion = convert(step, glb)
        assert conversion["mm_to_gltf_m_scale"] == 0.001
        variant = "loaded-tangent-complete-105 mm Dad Bod 77a"
        receipt_file = Path(str(glb) + ".conversion.json")
        base_command = [
            "node", str(target / "tools/stage_cad_asset.mjs"),
            "--file", str(glb),
            "--conversion-receipt", str(receipt_file),
            "--kit-variant-id", variant,
            "--role", "deck",
            "--part-number", "synthetic-box",
            "--revision", "synthetic-r1",
            "--source-url", "https://example.org/fixture-license",
            "--license", "synthetic-test-only",
            "--origin", "INDEPENDENTLY_MEASURED",
            "--evidence-date", "2026-10-11",
        ]
        result = subprocess.run(base_command, capture_output=True,
                                text=True, check=True, timeout=30)
        staged = json.loads(result.stdout)
        reg = json.loads((target / "catalog/outdoor_cad_asset_registry.v1.json").read_text())
        assert len(reg["assets"]) == 1
        a = reg["assets"][0]
        assert a["kit_variant_id"] == variant
        assert a["mm_to_gltf_m_scale"] == 0.001
        assert a["gltf_scene_units"] == "m"
        assert a["verified_mount_datums"] is False
        assert a["physical_fit_qualified"] is False
        assert a["separate_order_lines"] == 0
        assert (target / a["path"].lstrip("/")).is_file()
        assert (target / a["conversion_receipt_path"].lstrip("/")).is_file()
        assert staged["sha256"] == conversion["output_glb_sha256"]
        tampered = dict(conversion, gltf_scene_units="mm")
        receipt_file.write_text(json.dumps(tampered))
        bad = subprocess.run(base_command[:-18] + base_command[-18:],
                             capture_output=True, text=True, timeout=30)
        assert bad.returncode != 0
        assert "conversion receipt" in bad.stderr.lower()
        assert len(json.loads((target / "catalog/outdoor_cad_asset_registry.v1.json")
                              .read_text())["assets"]) == 1
