from pathlib import Path

from tools.prepare_x1_showcase import command_plan


def test_showcase_plan_orders_geometry_before_assets_and_manifest():
    plan = command_plan()
    flattened = [" ".join(command) for command in plan]

    assert "cad/generate_rolling_chassis.py" in flattened[0]
    assert any("cad/generate_snowdeck_study.py" in command for command in flattened)
    assert "tools/export_showcase_assets.py" in flattened[-2]
    assert "tools/build_showcase_manifest.py" in flattened[-1]


def test_showcase_plan_can_skip_generated_geometry_and_forward_evidence():
    plan = command_plan(
        skip_cad=True,
        skip_assets=True,
        evidence=[Path("/tmp/a.json"), Path("/tmp/b.json")],
    )

    assert len(plan) == 1
    command = plan[0]
    assert command.count("--evidence") == 2
    assert "/tmp/a.json" in command
    assert "/tmp/b.json" in command
