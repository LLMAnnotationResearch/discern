"""Environment records distinguish new executions from historical artifacts."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from discern.provenance import software_environment


def test_environment_records_versions_and_hashes_without_local_identity():
    record = software_environment()
    assert record["python"]
    assert record["packages"]["numpy"]
    assert "core.py" in record["source_sha256"]
    assert all(len(h) == 64 for h in record["source_sha256"].values())
    encoded = json.dumps(record)
    assert str(Path.home()) not in encoded
    assert "/Users/" not in encoded
    assert "API_KEY" not in encoded
    assert set(record) == {"recorded_at_utc", "python", "python_implementation",
                           "platform", "machine", "packages", "source_sha256"}
