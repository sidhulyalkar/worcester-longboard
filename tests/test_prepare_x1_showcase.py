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



def test_showcase_plan_can_load_synthetic_snowdeck_demo():
    plan = command_plan(
        skip_cad=True,
        skip_assets=True,
        synthetic_snowdeck_demo=True,
    )

    assert len(plan) == 1
    command = plan[0]
    assert "--snowdeck-signature" in command
    signature_index = command.index("--snowdeck-signature") + 1
    comparison_index = command.index("--snowdeck-comparison") + 1
    assert command[signature_index].endswith(
        "showcase/examples/snowdeck_s1.synthetic.json"
    )
    assert command[comparison_index].endswith(
        "showcase/examples/snowdeck_s0_to_s1.synthetic.json"
    )


def test_synthetic_demo_rejects_explicit_overlay_mix():
    try:
        command_plan(
            skip_cad=True,
            skip_assets=True,
            snowdeck_signature=Path("/tmp/private.json"),
            synthetic_snowdeck_demo=True,
        )
    except ValueError as exc:
        assert "cannot be combined" in str(exc)
    else:
        raise AssertionError("synthetic and explicit overlays must not be mixed")
