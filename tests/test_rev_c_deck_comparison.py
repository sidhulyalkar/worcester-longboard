from tools.qualify_rev_c_deck_comparison import qualify


def _candidate(cid: str, *, pass_checks: bool = True):
    return {
        "id": cid,
        "remount_trials": [
            {
                "natural_stance_recorded": True,
                "heel_toe_leverage_checked": True,
                "bilateral_step_off_checked": True,
                "deep_knee_position_checked": True,
            }
            for _ in range(3)
        ],
        "summary_checks": {
            "bilateral_emergency_step_off_pass": pass_checks,
            "deep_knee_carve_position_pass": pass_checks,
            "heel_toe_leverage_accepted": pass_checks,
            "remount_repeatability_accepted": pass_checks,
            "subjective_comfort_accepted": pass_checks,
        },
    }


def _manifest():
    return {
        "schema_version": 1,
        "scope": "rev_c_full_scale_deck_envelope_comparison",
        "selected_candidate_id": "comp95_class",
        "selection_reason": "preferred leverage and step-off behavior",
        "candidates": [
            _candidate("comp95_class"),
            _candidate("pro_warren_iii_class"),
            _candidate("agent_class"),
        ],
        "rejected_candidates": [
            {
                "id": "pro_warren_iii_class",
                "reason": "comparison fixture rejection reason",
            },
            {
                "id": "agent_class",
                "reason": "wider envelope did not justify the leverage tradeoff",
            },
        ],
        "powered_operation_authorized": False,
    }


def test_valid_private_comparison_emits_sanitized_authority():
    source = _manifest()
    report = qualify(source)
    assert report["qualified"] is True
    assert report["authority"] == "x1_rev_c_deck_comparison"
    assert report["selected_candidate_id"] == "comp95_class"
    assert "selection_reason" not in report
    assert "remount_trials" not in report
    assert len(report["private_source_sha256"]) == 64
    assert report["powered_operation_authorized"] is False


def test_selected_candidate_must_pass_all_safety_and_usability_checks():
    source = _manifest()
    source["candidates"][0]["summary_checks"]["bilateral_emergency_step_off_pass"] = False
    report = qualify(source)
    assert report["qualified"] is False
    assert any("bilateral_emergency_step_off_pass" in e for e in report["errors"])


def test_each_candidate_needs_three_remount_trials():
    source = _manifest()
    source["candidates"][1]["remount_trials"] = source["candidates"][1]["remount_trials"][:2]
    report = qualify(source)
    assert report["qualified"] is False
    assert any("three remount trials" in e for e in report["errors"])


def test_current_three_candidate_set_is_required_exactly():
    source = _manifest()
    source["candidates"] = [
        candidate
        for candidate in source["candidates"]
        if candidate["id"] != "pro_warren_iii_class"
    ]
    source["rejected_candidates"] = [
        entry
        for entry in source["rejected_candidates"]
        if entry["id"] != "pro_warren_iii_class"
    ]
    report = qualify(source)
    assert report["qualified"] is False
    assert any("current Rev-C candidate set" in e for e in report["errors"])


def test_every_nonselected_candidate_must_be_rejected_with_reason():
    source = _manifest()
    source["rejected_candidates"] = []
    report = qualify(source)
    assert report["qualified"] is False
    assert any("explicitly rejected" in e for e in report["errors"])


def test_raw_private_measurements_do_not_leak_to_report():
    source = _manifest()
    source["candidates"][0]["remount_trials"][0]["stance_width_mm"] = 999
    source["candidates"][0]["remount_trials"][0]["left_yaw_deg"] = 123
    report = qualify(source)
    serialized = str(report)
    assert "999" not in serialized
    assert "123" not in serialized
