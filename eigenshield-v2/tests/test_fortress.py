import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fortress import tcb_core, tcb_mirror, canaries, tripwire
from fortress.telemetry_mac import sign_event, verify_event, SeenEventCache
from fortress.boot_manifest import write_manifest, verify_manifest, ConfigIntegrityError, verify_or_raise

T0_VLANS = ["VLAN_ICU_CLINICAL", "VLAN_COLDCHAIN_TELEMETRY", "VLAN_CORE_AUTH"]
T0_HOSTS = ["HOST_ER_DB_PRIMARY", "HOST_BLOODBANK_CTRL_01"]


def _both(tool, args, human_ok=False):
    a = tcb_core.decide(tool, args, T0_VLANS, T0_HOSTS, human_ok=human_ok)
    b = tcb_mirror.decide(tool, args, T0_VLANS, T0_HOSTS, human_ok=human_ok)
    return a, b


def test_tcb_approves_benign_action():
    for impl in (tcb_core, tcb_mirror):
        d = impl.decide("drop_bec_cluster", {"cluster_id": "CLUS_x", "ttl_seconds": 600},
                        T0_VLANS, T0_HOSTS)
        assert d["decision"] == "APPROVED"


def test_tcb_blocks_every_tool_against_tier0():
    args_for = {
        "isolate_thermal_anomaly_host": {"host_id": "HOST_ER_DB_PRIMARY", "dump_hardware_trace": True},
        "set_service_readonly": {"service_id": "SVC_COLDCHAIN_ON_HOST_BLOODBANK_CTRL_01", "ttl_seconds": 600},
        "execute_percolation_cut": {"target_spectral_radius": 0.9, "preserve_tier0_vlans": True,
                                    "vlan_id": "VLAN_ICU_CLINICAL"},
    }
    # direct host/VLAN reference inside args must block (or be escalated to human)
    a = tcb_core.decide("isolate_thermal_anomaly_host", args_for["isolate_thermal_anomaly_host"],
                        T0_VLANS, T0_HOSTS, human_ok=False)
    b = tcb_mirror.decide("isolate_thermal_anomaly_host", args_for["isolate_thermal_anomaly_host"],
                          T0_VLANS, T0_HOSTS, human_ok=False)
    assert a["decision"] == "BLOCKED" and b["decision"] == "BLOCKED"

    # tier-0 allowed ONLY with explicit human step-up
    a2 = tcb_core.decide("isolate_thermal_anomaly_host", args_for["isolate_thermal_anomaly_host"],
                         T0_VLANS, T0_HOSTS, human_ok=True)
    assert a2["decision"] == "APPROVED"


def test_tcb_rejects_oversized_and_weird_args():
    huge = {"cluster_id": "C" * 5000, "ttl_seconds": 600}
    assert tcb_core.decide("drop_bec_cluster", huge, T0_VLANS, T0_HOSTS)["decision"] == "BLOCKED"
    assert tcb_mirror.decide("drop_bec_cluster", huge, T0_VLANS, T0_HOSTS)["decision"] == "BLOCKED"
    weird = {"cluster_id": "x", "ttl_seconds": 600, "evil": {"nested": ["a", {"b": ["c"] * 200}]}}
    d = tcb_core.decide("drop_bec_cluster", weird, T0_VLANS, T0_HOSTS)
    assert d["decision"] in ("APPROVED", "BLOCKED")  # never raises; shape is honoured either way


def test_tcb_never_approves_disallowed_tools():
    for tool in ("rm_rf", "execute_shell", "shutdown_hospital", "DROP_BEC_CLUSTER", ""):
        a = tcb_core.decide(tool, {}, T0_VLANS, T0_HOSTS)
        b = tcb_mirror.decide(tool, {}, T0_VLANS, T0_HOSTS)
        assert a["decision"] == "BLOCKED" and b["decision"] == "BLOCKED"


def test_telemetry_mac_roundtrip_and_forgery():
    evt = {"event_id": "evt_mac_test_0001", "signal_type": "PARITY_ENTROPY_COLLAPSE",
           "severity": 0.96, "entities": {"host_id": "HOST_x"}}
    signed = sign_event(evt)
    assert verify_event(signed) is True
    forged = dict(signed)
    forged["severity"] = 0.10  # attacker lowers the severity
    assert verify_event(forged) is False
    forged2 = {k: v for k, v in signed.items() if k != "mac"}
    assert verify_event(forged2) is False


def test_replay_cache_drops_second_use():
    cache = SeenEventCache(window_sec=600)
    assert cache.check_and_mark("evt_replay_1") is True
    assert cache.check_and_mark("evt_replay_1") is False
    assert cache.check_and_mark("evt_replay_2") is True


def test_canary_detection():
    line = canaries.embed_canary_line()
    token = canaries.active_canaries()[0]
    assert token in line
    assert canaries.scan_text(f"totally normal answer {token} leaked") != []
    assert canaries.scan_text("nothing to see here") == []


def test_tripwire_trips_on_burst_and_resets_with_human():
    tw = tripwire.Tripwire()
    for _ in range(4):
        tw.record("blocked")
    assert tw.is_frozen() is True
    assert tw.reset(human_stepup=False)["reset"] is False
    assert tw.reset(human_stepup=True, note="SOC acknowledged")["reset"] is True
    assert tw.is_frozen() is False
    tw2 = tripwire.Tripwire()
    tw2.record("canary_hit")
    assert tw2.is_frozen() is True  # instant trip


def test_boot_manifest_detects_tamper(tmp_path):
    target = tmp_path / "policy.yaml"
    target.write_text("version: '2.0'\n")
    manifest_path = str(tmp_path / "manifest.json")
    # pin against absolute path by monkeying with create via direct file list
    import fortress.boot_manifest as bm
    orig_default = bm.DEFAULT_PATHS
    bm.DEFAULT_PATHS = [str(target)]
    try:
        bm.write_manifest(manifest_path, base="")
        assert verify_manifest(manifest_path, base="")["ok"] is True
        target.write_text("version: '2.0'\nautonomy_mode: FULL_AUTO_EVIL: true\n")
        result = verify_manifest(manifest_path, base="")
        assert result["ok"] is False
        assert result["mismatches"][0]["reason"] == "sha256 mismatch"
        try:
            verify_or_raise(manifest_path, base="")
            assert False, "must raise"
        except ConfigIntegrityError:
            pass
    finally:
        bm.DEFAULT_PATHS = orig_default
