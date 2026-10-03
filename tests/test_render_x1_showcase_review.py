from tools.render_x1_showcase_review import render


def test_render_showcase_review_keeps_authority_boundary():
    manifest = {
        "configuration": "test",
        "physical_authority": False,
        "procurement_authority": False,
        "fabrication_authority": False,
        "powered_operation_authorized": False,
        "components": [
            {
                "label": "Deck",
                "evidence_state": "REFERENCE",
                "authority_gate": "rolling_chassis_physical_qualified",
                "gate_qualified": False,
            }
        ],
        "design_studies": {
            "deck_candidates": [
                {
                    "label": "Comp 95 envelope",
                    "length_mm": 950,
                    "width_mm": 251,
                    "evidence_state": "REFERENCE",
                }
            ],
            "topology_branches": [],
            "trail_armor": {
                "evidence_state": "ASSUMED",
                "source": "docs/rev_c_trail_armor.md",
                "goals": ["replaceable first-contact wear surface"],
                "note": "visual placeholder only",
            },
        },
        "risk_summary": [],
        "gates": {
            "rolling_chassis_physical_qualified": {
                "satisfied": False,
                "blockers": ["matching authority evidence not supplied"],
            }
        },
        "snowdeck_bench_signature": None,
        "snowdeck_bench_comparison": None,
    }

    text = render(manifest)

    assert "creates no procurement, fabrication, ride, or powered-operation authority" in text
    assert "Deck" in text
    assert "REFERENCE" in text
    assert "Comp 95 envelope" in text
    assert "Sacrificial trail-armor study" in text
    assert "matching authority evidence not supplied" in text


def test_render_showcase_review_labels_synthetic_snowdeck_data():
    manifest = {
        "configuration": "test",
        "physical_authority": False,
        "procurement_authority": False,
        "fabrication_authority": False,
        "powered_operation_authorized": False,
        "components": [],
        "design_studies": {"deck_candidates": [], "topology_branches": []},
        "risk_summary": [],
        "gates": {},
        "snowdeck_bench_signature": {
            "condition_id": "S1-synthetic",
            "trial_count": 3,
            "synthetic_fixture": True,
            "physical_evidence_eligible": False,
            "eligible_for_further_bench_comparison": True,
            "mechanical_rejects": [],
            "neutral": {
                "left_load_fraction": {"mean": 0.49, "sd": 0.01},
                "total_load": {"mean": 500, "sd": 8},
            },
            "heel_to_toe_forefoot_transfer": {
                "left": {"mean": 0.4, "sd": 0.02},
                "right": {"mean": 0.42, "sd": 0.02},
            },
        },
        "snowdeck_bench_comparison": {
            "signed_variant_minus_baseline": {
                "left_heel_to_toe_transfer_mean": 0.05,
            }
        },
    }

    text = render(manifest)

    assert "Synthetic fixture: **yes**" in text
    assert "Physical-evidence eligible: **no**" in text
    assert "No direction is automatically preferred" in text
    assert "left_heel_to_toe_transfer_mean: 0.05" in text
