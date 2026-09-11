import csv, json
from pathlib import Path
from fit.pilot_qualification import qualify_manifest

HEADER=["t_us","left_heel_raw","left_forefoot_raw","right_heel_raw","right_forefoot_raw","load_valid_mask","roll_deg","imu_ok"]

def _write_log(path:Path,mean_raw:float,seconds:float=6.0,sps:int=10,noise:int=2):
    n=int(seconds*sps)+1
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(HEADER)
        for i in range(n):
            j=(i%(2*noise+1))-noise if noise else 0
            w.writerow([i*int(1_000_000/sps),int(round(mean_raw+j)),"","","",1,"",0])

def _manifest(tmp:Path,nonlinear_validation=False,loaded_gap=0.30):
    raw=lambda m:100000+m*9.80665*1000
    specs=[("zero_pre",0,"zero_pre.csv",raw(0)),("load_up",2,"up2.csv",raw(2)),("load_up",5,"up5.csv",raw(5)),("load_up",10,"up10.csv",raw(10)),("load_down",5,"down5.csv",raw(5)+25),("load_down",2,"down2.csv",raw(2)+15),("zero_post",0,"zero_post.csv",raw(0)+10)]
    for _,_,fn,r in specs:_write_log(tmp/fn,r)
    _write_log(tmp/"validation.csv",raw(7.5)+(4000 if nonlinear_validation else 0))
    data={"schema_version":1,"channel":"left_heel","hx711_sps":10,"observations":[{"kind":k,"mass_kg":m,"log":f} for k,m,f,_ in specs],"validation":[{"mass_kg":7.5,"log":"validation.csv"}],"mechanical":{"vendor_pattern_verified":True,"fixed_loaded_orientation_verified":True,"screw_stack_verified":True,"stop_gap_unloaded_mm":0.8,"stop_gap_min_loaded_mm":loaded_gap}}
    p=tmp/"pilot_manifest.json"; p.write_text(json.dumps(data)); return p

def test_good_pilot_qualifies_and_is_fingerprinted(tmp_path):
    r=qualify_manifest(_manifest(tmp_path))
    assert r["qualified_for_four_zone_duplication"] is True
    assert r["failures"]==[] and r["metrics"]["r2"]>=0.999999
    assert len(r["source_fingerprints"])==8
    assert len(r["manifest_sha256"])==64 and len(r["authority_fingerprint_sha256"])==64

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
