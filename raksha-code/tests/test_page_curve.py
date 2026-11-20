import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sentinel.shields.ring3_endpoint_silicon import PageCurveTrap


def test_parity_trap_detects_first_4kb_overwrite(tmp_path):
    trap = PageCurveTrap(allow_real_kill=False)
    armed = trap.arm(str(tmp_path), host_id="HOST_TEST", density_level="low")
    victim = armed["files"][0]

    assert trap.verify_file(victim)["intact"] is True
    with open(victim, "r+b") as f:
        f.write(b"\x99" * 4096)

    check = trap.verify_file(victim)
    assert check["intact"] is False

    decision = trap.on_write(victim, pid=31337, host_id="HOST_TEST")
    assert decision["action"] == "PID_TERMINATED"
    assert decision["dry_run"] is True  # never SIGKILLs by default
    assert decision["event"]["signal_type"] == "PARITY_ENTROPY_COLLAPSE"
