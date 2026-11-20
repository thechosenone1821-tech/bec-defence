import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spine.ledger import AuditLedger


def test_hash_chain_verifies(tmp_path):
    ledger = AuditLedger(str(tmp_path / "audit.jsonl"))
    for i in range(3):
        ledger.append("test_record", {"n": i})
    result = ledger.verify()
    assert result["valid"] is True
    assert result["entries"] == 3


def test_tampering_is_detected(tmp_path):
    path = tmp_path / "audit.jsonl"
    ledger = AuditLedger(str(path))
    entry = ledger.append("test_record", {"n": 0})
    ledger.append("test_record", {"n": 1})

    lines = path.read_text().splitlines()
    tampered = json.loads(lines[0])
    tampered["payload"]["n"] = 999
    lines[0] = json.dumps(tampered)
    path.write_text("\n".join(lines) + "\n")

    result = ledger.verify()
    assert result["valid"] is False
    assert result["broken_at_seq"] == 0
