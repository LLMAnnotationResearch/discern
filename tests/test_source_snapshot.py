"""Source snapshots retain public records without copying local evidence or history."""
import importlib.util
import json
from pathlib import Path
import sys

import pytest


def test_snapshot_uses_public_selection_and_preserves_existing_copy(tmp_path, monkeypatch):
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    from build_reviewer_release import TOP_FILES
    spec = importlib.util.spec_from_file_location("source_snapshot", scripts / "snapshot_paper_code.py")
    snapshot = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(snapshot)
    source = tmp_path / "source"
    source.mkdir()
    for name in TOP_FILES:
        (source / name).write_text("public")
    for name in ["scripts/README.md", "docs/submission/p03_repair.json", ".git/config",
                 "output/local.json", "test datasets restricted/responses.csv"]:
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}")
    monkeypatch.setattr(snapshot, "__file__", str(source / "scripts/snapshot_paper_code.py"))
    destination = tmp_path / "snapshot"
    snapshot.main(destination)
    copied = destination / "code"
    manifest = json.loads((copied / "source_manifest.json").read_text())
    assert "scripts/README.md" in manifest["files_sha256"]
    assert "docs/submission/p03_repair.json" in manifest["files_sha256"]
    assert not (copied / ".git").exists()
    assert not (copied / "output").exists()
    assert not (copied / "test datasets restricted").exists()
    assert str(source) not in json.dumps(manifest)
    (copied / "README.md").write_text("preserved")
    with pytest.raises(ValueError, match="not overwritten"):
        snapshot.main(destination)
    assert (copied / "README.md").read_text() == "preserved"
