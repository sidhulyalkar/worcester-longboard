from pathlib import Path

from tools.prepare_x1_showcase import command_plan


def test_showcase_plan_orders_geometry_before_assets_and_manifest():
    plan = command_plan()
    flattened = [" ".join(command) for command in plan]

    assert flattened[0].endswith("-m cad.generate_rolling_chassis")
    assert any(command.endswith("-m cad.generate_snowdeck_study") for command in flattened)
    assert "tools/export_showcase_assets.py" in flattened[-3]
    assert "tools/build_showcase_manifest.py" in flattened[-2]
    assert "tools/render_x1_showcase_review.py" in flattened[-1]


def test_showcase_plan_can_skip_generated_geometry_and_forward_evidence():
    plan = command_plan(
        skip_cad=True,
        skip_assets=True,
        evidence=[Path("/tmp/a.json"), Path("/tmp/b.json")],
    )

    assert len(plan) == 2
    command = plan[0]
    assert "tools/build_showcase_manifest.py" in command
    assert "tools/render_x1_showcase_review.py" in plan[1]
    assert command.count("--evidence") == 2
    assert "/tmp/a.json" in command
    assert "/tmp/b.json" in command



def test_showcase_plan_can_load_synthetic_snowdeck_demo():
    plan = command_plan(
        skip_cad=True,
        skip_assets=True,
        synthetic_snowdeck_demo=True,
    )

    assert len(plan) == 2
    command = plan[0]
    assert "tools/build_showcase_manifest.py" in command
    assert "tools/render_x1_showcase_review.py" in plan[1]
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


def test_showcase_plan_uses_module_execution_for_all_cad_generators():
    plan = command_plan()
    cad_commands = plan[:4]

    assert [command[1:] for command in cad_commands] == [
        ["-m", "cad.generate_rolling_chassis"],
        ["-m", "cad.generate_fit_rig"],
        ["-m", "cad.generate_one_zone_pilot"],
        ["-m", "cad.generate_snowdeck_study"],
    ]
    assert all("/generate_" not in " ".join(command) for command in cad_commands)
