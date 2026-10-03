import csv, hashlib, json
from pathlib import Path
import pytest
from fit.pilot_qualification import qualify_manifest
from tools.validate_x1_fit_pilot_mass_reference import validate as validate_mass

HEADER=["t_us","left_heel_raw","left_forefoot_raw","right_heel_raw","right_forefoot_raw","load_valid_mask","roll_deg","imu_ok"]


def _digest(data):
    return hashlib.sha256(
        json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _mass_item(mass_id, role, mass, uncertainty):
    return {
        "mass_id": mass_id,
        "role": role,
        "evidence_type": "REFERENCE_MASS",
        "declared_mass_kg": mass,
        "declared_uncertainty_kg": uncertainty,
        "reference_mass_evidence": {
            "source_reference": f"synthetic-{mass_id}",
            "documented_mass_kg": mass,
            "documented_uncertainty_kg": uncertainty,
        },
        "independent_scale_evidence": {
            "scale_manufacturer": "",
            "scale_model": "",
            "capacity_kg": None,
            "resolution_kg": None,
            "stated_accuracy_source": "",
            "conservative_accuracy_limit_kg": None,
            "zero_check_before": True,
            "zero_check_after": True,
            "repeated_readings_kg": [],
            "measurement_notes": "",
        },
        "notes": "",
    }


def _write_provenance(tmp: Path):
    selection = {
        "schema_version": 1,
        "scope": "x1_fit_pilot_hardware_selection_record",
        "issue": 59,
        "selection_id": "PILOT-HW-TEST",
        "selected_at_utc": "2026-10-03T12:30:00-07:00",
        "checkout_id": "CART-A-TEST",
        "checkout_authority_fingerprint_sha256": "a" * 64,
        "inventory_record_sha256": "b" * 64,
        "receiving_id": "RECEIVE-TEST",
        "receiving_authority_fingerprint_sha256": "c" * 64,
        "hardware": {
            "load_cell": {
                "item_id": "LC-3135",
                "source_kind": "RECEIVED_ORDER",
                "active_hardware_id": "LC-PILOT-A",
                "spare_hardware_id": "LC-SPARE-A",
            },
            "hx711": {
                "item_id": "ADC-HX711",
                "source_kind": "RECEIVED_ORDER",
                "active_hardware_id": "ADC-PILOT-A",
                "spare_hardware_id": "ADC-SPARE-A",
            },
            "mcu": {
                "item_id": "MCU-ESP32S3",
                "source_kind": "NOT_USED",
                "active_hardware_id": "",
            },
        },
        "notes": "",
        "physical_qualification_authority": False,
        "four_zone_duplication_authorized": False,
        "fabrication_authority": False,
        "powered_operation_authorized": False,
        "public_operation_authorized": False,
        "dog_accompanied_operation_authorized": False,
    }
    authority = {
        "schema_version": 1,
        "authority": "x1_fit_pilot_hardware_selection",
        "valid": True,
        "errors": [],
        "selection_id": selection["selection_id"],
        "selection_record_sha256": _digest(selection),
        "checkout_id": selection["checkout_id"],
        "checkout_authority_fingerprint_sha256": selection[
            "checkout_authority_fingerprint_sha256"
        ],
        "inventory_record_sha256": selection["inventory_record_sha256"],
        "receiving_id": selection["receiving_id"],
        "receiving_authority_fingerprint_sha256": selection[
            "receiving_authority_fingerprint_sha256"
        ],
        "hardware": selection["hardware"],
        "exact_evidence_hardware_verified": True,
        "untouched_spares_preserved": True,
        "physical_qualification_authority": False,
        "four_zone_duplication_authorized": False,
        "fabrication_authority": False,
        "powered_operation_authorized": False,
        "public_operation_authorized": False,
        "dog_accompanied_operation_authorized": False,
        "interpretation_boundary": "synthetic selection authority",
    }
    authority["authority_fingerprint_sha256"] = _digest(authority)

    provenance = tmp / "provenance"
    provenance.mkdir(exist_ok=True)
    selection_path = provenance / "hardware_selection.json"
    authority_path = provenance / "hardware_selection_authority.json"
    selection_path.write_text(json.dumps(selection), encoding="utf-8")
    authority_path.write_text(json.dumps(authority), encoding="utf-8")

    mass_record = {
        "schema_version": 1,
        "scope": "x1_fit_pilot_mass_reference_record",
        "issue": 61,
        "reference_set_id": "MASS-REF-TEST",
        "measured_at_utc": "2026-10-03T12:45:00-07:00",
        "purpose": "synthetic Issue #4 reference",
        "screening_policy": {
            "max_mass_kg": 20.0,
            "min_calibration_mass_count": 3,
            "validation_mass_count": 1,
            "max_relative_reference_uncertainty": 0.005,
            "uncertainty_policy_note": "synthetic",
        },
        "masses": [
            _mass_item("CAL-2", "CALIBRATION", 2.0, 0.002),
            _mass_item("CAL-5", "CALIBRATION", 5.0, 0.005),
            _mass_item("CAL-10", "CALIBRATION", 10.0, 0.010),
            _mass_item("VAL-7P5", "VALIDATION", 7.5, 0.0075),
        ],
        "claims": {
            "nist_traceable": False,
            "legal_metrology": False,
            "commercial_measurement_authority": False,
            "load_cell_performance_authority": False,
            "four_zone_duplication_authorized": False,
            "fabrication_authority": False,
            "powered_operation_authorized": False,
            "public_operation_authorized": False,
            "dog_accompanied_operation_authorized": False,
        },
    }
    mass_authority = validate_mass(mass_record)
    assert mass_authority["valid"] is True
    mass_record_path = provenance / "mass_reference.json"
    mass_authority_path = provenance / "mass_reference_authority.json"
    mass_record_path.write_text(json.dumps(mass_record), encoding="utf-8")
    mass_authority_path.write_text(json.dumps(mass_authority), encoding="utf-8")
    return selection, authority, mass_record, mass_authority


def _write_log(path:Path,mean_raw:float,seconds:float=6.0,sps:int=10,noise:int=2,header_sps:int|None=None):
    n=int(seconds*sps)+1
    with path.open("w",newline="",encoding="utf-8") as f:
        f.write(f"# hx711_sps={header_sps if header_sps is not None else sps}\n")
        w=csv.writer(f); w.writerow(HEADER)
        for i in range(n):
            j=(i%(2*noise+1))-noise if noise else 0
            w.writerow([i*int(1_000_000/sps),int(round(mean_raw+j)),"","","",1,"",0])

def _manifest(tmp:Path,nonlinear_validation=False,loaded_gap=0.30):
    raw=lambda m:100000+m*9.80665*1000
    specs=[("zero_pre",0,"zero_pre.csv",raw(0)),("load_up",2,"up2.csv",raw(2)),("load_up",5,"up5.csv",raw(5)),("load_up",10,"up10.csv",raw(10)),("load_down",5,"down5.csv",raw(5)+25),("load_down",2,"down2.csv",raw(2)+15),("zero_post",0,"zero_post.csv",raw(0)+10)]
    for _,_,fn,r in specs:_write_log(tmp/fn,r)
    _write_log(tmp/"validation.csv",raw(7.5)+(4000 if nonlinear_validation else 0))
    selection, authority, mass_record, mass_authority = _write_provenance(tmp)
    data={
        "schema_version":1,
        "hardware_selection":{
            "selection_id":authority["selection_id"],
            "selection_record_sha256":authority["selection_record_sha256"],
            "selection_authority_fingerprint_sha256":authority["authority_fingerprint_sha256"],
            "selection_record_path":"provenance/hardware_selection.json",
            "selection_authority_path":"provenance/hardware_selection_authority.json"
        },
        "mass_reference":{
            "reference_set_id":mass_authority["reference_set_id"],
            "record_sha256":mass_authority["record_sha256"],
            "authority_fingerprint_sha256":mass_authority["authority_fingerprint_sha256"],
            "record_path":"provenance/mass_reference.json",
            "authority_path":"provenance/mass_reference_authority.json"
        },
        "hardware_ids":{"load_cell_id":"LC-PILOT-A","hx711_id":"ADC-PILOT-A","pod_id":"POD-PILOT-A","zone_pad_id":"PAD-PILOT-A","mcu_id":""},
        "spare_hardware_ids":{"load_cell_id":"LC-SPARE-A","hx711_id":"ADC-SPARE-A"},
        "channel":"left_heel","hx711_sps":10,
        "acquisition":{"rate_jumper_verified":True},
        "observations":[
            {
                "kind":k,
                "mass_kg":m,
                "mass_reference_id":(
                    None if m == 0 else {2:"CAL-2",5:"CAL-5",10:"CAL-10"}[m]
                ),
                "mass_uncertainty_kg":(
                    0.0 if m == 0 else {2:0.002,5:0.005,10:0.010}[m]
                ),
                "log":f,
            }
            for k,m,f,_ in specs
        ],
        "validation":[{
            "mass_kg":7.5,
            "mass_reference_id":"VAL-7P5",
            "mass_uncertainty_kg":0.0075,
            "log":"validation.csv"
        }],
        "mechanical":{"vendor_pattern_verified":True,"fixed_loaded_orientation_verified":True,"screw_stack_verified":True,"stop_gap_unloaded_mm":0.8,"stop_gap_min_loaded_mm":loaded_gap}
    }
    p=tmp/"pilot_manifest.json"; p.write_text(json.dumps(data)); return p

def test_good_pilot_qualifies_and_is_fingerprinted(tmp_path):
    r=qualify_manifest(_manifest(tmp_path))
    assert r["qualified_for_four_zone_duplication"] is True
    assert r["failures"]==[] and r["metrics"]["r2"]>=0.999999
    assert r["hardware_ids"]["load_cell_id"]=="LC-PILOT-A"
    assert len(r["source_fingerprints"])==12
    assert r["hardware_provenance"]["selection_id"]=="PILOT-HW-TEST"
    assert r["hardware_provenance"]["untouched_spares"]["load_cell_id"]=="LC-SPARE-A"
    assert r["hardware_provenance"]["untouched_spares"]["hx711_id"]=="ADC-SPARE-A"
    assert r["mass_reference_provenance"]["reference_set_id"]=="MASS-REF-TEST"
    assert r["metrics"]["validation_error_nominal"] is not None
    assert r["metrics"]["validation_reference_uncertainty_relative"] == pytest.approx(0.001)
    assert r["metrics"]["validation_error"] > r["metrics"]["validation_error_nominal"]
    assert r["metrics"]["residual_fs"] >= r["metrics"]["residual_fs_nominal"]
    assert len(r["manifest_sha256"])==64
    assert len(r["qualification_tool_sha256"])==64
    assert len(r["authority_fingerprint_sha256"])==64

def test_independent_validation_error_blocks_duplication(tmp_path):
    r=qualify_manifest(_manifest(tmp_path,nonlinear_validation=True))
    assert r["qualified_for_four_zone_duplication"] is False
    assert any("validation_error" in x for x in r["failures"])

def test_mechanical_stop_clearance_blocks_duplication(tmp_path):
    r=qualify_manifest(_manifest(tmp_path,loaded_gap=0.05))
    assert r["qualified_for_four_zone_duplication"] is False
    assert "loaded stop gap invalid" in r["failures"]

def test_missing_hysteresis_pair_is_rejected(tmp_path):
    p=_manifest(tmp_path); d=json.loads(p.read_text())
    d["observations"]=[x for x in d["observations"] if not(x["kind"]=="load_down" and x["mass_kg"]==2)]
    p.write_text(json.dumps(d)); r=qualify_manifest(p)
    assert r["qualified_for_four_zone_duplication"] is False
    assert any("paired masses" in x for x in r["failures"])

def test_validation_mass_cannot_reuse_calibration_mass(tmp_path):
    p=_manifest(tmp_path); d=json.loads(p.read_text())
    d["validation"][0]["mass_kg"]=5
    d["validation"][0]["mass_reference_id"]="CAL-5"
    d["validation"][0]["mass_uncertainty_kg"]=0.005
    p.write_text(json.dumps(d)); r=qualify_manifest(p)
    assert r["qualified_for_four_zone_duplication"] is False
    assert "validation mass must be independent of calibration masses" in r["failures"]

def test_unknown_hx711_rate_blocks_duplication(tmp_path):
    p=_manifest(tmp_path); d=json.loads(p.read_text())
    d["hx711_sps"]=42
    p.write_text(json.dumps(d)); r=qualify_manifest(p)
    assert r["qualified_for_four_zone_duplication"] is False
    assert "hx711_sps must be 10 or 80" in r["failures"]

def test_logger_header_must_match_manifest_rate(tmp_path):
    p=_manifest(tmp_path); raw=lambda m:100000+m*9.80665*1000
    _write_log(tmp_path/"validation.csv",raw(7.5),header_sps=80)
    r=qualify_manifest(p)
    assert r["qualified_for_four_zone_duplication"] is False
    assert any("logger hx711_sps disagrees" in x for x in r["failures"])

def test_rate_jumper_verification_is_explicit(tmp_path):
    p=_manifest(tmp_path); d=json.loads(p.read_text())
    d["acquisition"]["rate_jumper_verified"]=False
    p.write_text(json.dumps(d)); r=qualify_manifest(p)
    assert r["qualified_for_four_zone_duplication"] is False
    assert "acquisition.rate_jumper_verified must be true" in r["failures"]

def test_pilot_mass_ceiling_blocks_needlessly_large_load(tmp_path):
    p=_manifest(tmp_path); d=json.loads(p.read_text())
    d["validation"][0]["mass_kg"]=21.0
    p.write_text(json.dumps(d)); r=qualify_manifest(p)
    assert r["qualified_for_four_zone_duplication"] is False
    assert any("hard 20 kg" in x for x in r["failures"])

def test_manifest_cannot_escape_private_session_root(tmp_path):
    p=_manifest(tmp_path); d=json.loads(p.read_text())
    outside=tmp_path.parent/"outside.csv"; _write_log(outside,100000)
    d["observations"][0]["log"]="../outside.csv"; p.write_text(json.dumps(d))
    with pytest.raises(ValueError,match="escapes manifest directory"): qualify_manifest(p)

def test_hardware_identity_is_required(tmp_path):
    p=_manifest(tmp_path); d=json.loads(p.read_text())
    d["hardware_ids"]["load_cell_id"]=""
    p.write_text(json.dumps(d)); r=qualify_manifest(p)
    assert r["qualified_for_four_zone_duplication"] is False
    assert "hardware_ids.load_cell_id must be a nonempty string" in r["failures"]

def test_manifest_cannot_swap_selected_active_sensor_id(tmp_path):
    p=_manifest(tmp_path); d=json.loads(p.read_text())
    d["hardware_ids"]["load_cell_id"]="LC-SPARE-A"
    p.write_text(json.dumps(d))
    r=qualify_manifest(p)
    assert r["qualified_for_four_zone_duplication"] is False
    assert any("does not match selected active load cell" in x for x in r["failures"])


def test_tampered_selection_record_blocks_pilot_even_with_good_sensor_metrics(tmp_path):
    p=_manifest(tmp_path)
    selection_path=tmp_path/"provenance"/"hardware_selection.json"
    selection=json.loads(selection_path.read_text())
    selection["hardware"]["load_cell"]["active_hardware_id"]="LC-TAMPERED"
    selection_path.write_text(json.dumps(selection))
    r=qualify_manifest(p)
    assert r["qualified_for_four_zone_duplication"] is False
    assert any("does not match copied selection record" in x for x in r["failures"])


def test_manifest_cannot_hide_untouched_spare_lineage(tmp_path):
    p=_manifest(tmp_path); d=json.loads(p.read_text())
    d["spare_hardware_ids"]["hx711_id"]="ADC-PILOT-A"
    p.write_text(json.dumps(d))
    r=qualify_manifest(p)
    assert r["qualified_for_four_zone_duplication"] is False
    assert any("HX711 spare does not match selected untouched spare" in x for x in r["failures"])


def test_load_sequence_must_be_monotonic(tmp_path):
    p=_manifest(tmp_path); d=json.loads(p.read_text())
    ups=[x for x in d["observations"] if x["kind"]=="load_up"]
    ups[0]["mass_kg"],ups[1]["mass_kg"]=ups[1]["mass_kg"],ups[0]["mass_kg"]
    p.write_text(json.dumps(d)); r=qualify_manifest(p)
    assert r["qualified_for_four_zone_duplication"] is False
    assert "load_up masses must be strictly ascending" in r["failures"]

def test_tampered_mass_reference_record_blocks_good_sensor_metrics(tmp_path):
    p=_manifest(tmp_path)
    record_path=tmp_path/"provenance"/"mass_reference.json"
    record=json.loads(record_path.read_text())
    record["masses"][0]["declared_mass_kg"]=2.1
    record_path.write_text(json.dumps(record))
    r=qualify_manifest(p)
    assert r["qualified_for_four_zone_duplication"] is False
    assert any("mass reference authority does not match copied record" in x for x in r["failures"])


def test_manifest_cannot_change_mass_uncertainty_or_reference_id(tmp_path):
    p=_manifest(tmp_path); d=json.loads(p.read_text())
    target=next(x for x in d["observations"] if x["kind"]=="load_up" and x["mass_kg"]==5)
    target["mass_uncertainty_kg"]=0.0001
    target["mass_reference_id"]="CAL-2"
    p.write_text(json.dumps(d))
    r=qualify_manifest(p)
    assert r["qualified_for_four_zone_duplication"] is False
    assert any("uncertainty differs from authority" in x for x in r["failures"])
    assert any("mass differs from authority" in x for x in r["failures"])


def test_reference_uncertainty_is_included_in_validation_gate(tmp_path):
    p=_manifest(tmp_path)
    record_path=tmp_path/"provenance"/"mass_reference.json"
    authority_path=tmp_path/"provenance"/"mass_reference_authority.json"
    record=json.loads(record_path.read_text())

    # Use a legitimate new reference record near the allowed 0.5% uncertainty
    # ceiling, then regenerate the canonical authority from that record.
    val_record=next(x for x in record["masses"] if x["role"]=="VALIDATION")
    val_record["declared_uncertainty_kg"]=0.037
    val_record["reference_mass_evidence"]["documented_uncertainty_kg"]=0.037
    authority=validate_mass(record)
    assert authority["valid"] is True
    record_path.write_text(json.dumps(record))
    authority_path.write_text(json.dumps(authority))

    d=json.loads(p.read_text())
    d["mass_reference"]["record_sha256"]=authority["record_sha256"]
    d["mass_reference"]["authority_fingerprint_sha256"]=authority["authority_fingerprint_sha256"]
    d["validation"][0]["mass_uncertainty_kg"]=0.037
    p.write_text(json.dumps(d))

    r=qualify_manifest(p)
    assert r["qualified_for_four_zone_duplication"] is True
    assert r["metrics"]["validation_error"] > r["metrics"]["validation_error_nominal"]
    assert r["metrics"]["validation_reference_uncertainty_relative"] == pytest.approx(0.037/7.5)


def test_refingerprinted_mass_authority_cannot_diverge_from_source_record(tmp_path):
    p=_manifest(tmp_path)
    authority_path=tmp_path/"provenance"/"mass_reference_authority.json"
    authority=json.loads(authority_path.read_text())
    authority["calibration_masses"][0]["uncertainty_kg"]=0.009
    authority["calibration_masses"][0]["relative_uncertainty"]=0.009/2.0
    unsigned=dict(authority)
    unsigned.pop("authority_fingerprint_sha256",None)
    authority["authority_fingerprint_sha256"]=_digest(unsigned)
    authority_path.write_text(json.dumps(authority))

    d=json.loads(p.read_text())
    d["mass_reference"]["authority_fingerprint_sha256"]=authority["authority_fingerprint_sha256"]
    p.write_text(json.dumps(d))

    r=qualify_manifest(p)
    assert r["qualified_for_four_zone_duplication"] is False
    assert any(
        "does not match canonical validation of copied record" in x
        for x in r["failures"]
    )


def test_thresholds_may_tighten_but_not_relax(tmp_path):
    p=_manifest(tmp_path); d=json.loads(p.read_text())
    d["thresholds"]={"max_validation_error":0.50}
    p.write_text(json.dumps(d)); r=qualify_manifest(p)
    assert r["qualified_for_four_zone_duplication"] is False
    assert "threshold max_validation_error may only be made stricter" in r["failures"]
