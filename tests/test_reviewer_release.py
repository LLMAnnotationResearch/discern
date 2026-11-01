"""Submission copies exclude private files and stop on identifying metadata."""
import importlib.util
import json
from pathlib import Path
import sys
import zipfile

SPEC = importlib.util.spec_from_file_location("reviewer_release", Path(__file__).resolve().parents[1] / "scripts/build_reviewer_release.py")
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def test_archive_excludes_history_private_data_and_fresh_runs(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    for name in module.TOP_FILES:
        (root / name).write_text("public source")
    for name in ["src/discern/a.py", "examples/campaignview/saved/real_r1/04_selected.json",
                 ".git/config", "output/proposal.tex", "examples/campaignview/fresh_runs/secret.json",
                 "test datasets (not to be made public)/private.csv", "src/discern/__pycache__/a.py"]:
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{}")
    archive = tmp_path / "review.zip"
    module.build_release(archive, root=root)
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        assert "discern-review/src/discern/a.py" in names
        assert "discern-review/examples/campaignview/saved/real_r1/04_selected.json" in names
        assert not any("secret" in name or "__pycache__" in name or name.startswith("discern-review/.git/") for name in names)
        manifest = json.loads(z.read("discern-review/RELEASE_MANIFEST.json"))
        assert all("output/" not in name and "private.csv" not in name for name in manifest)


def test_scan_detects_local_identity_and_preserves_upstream_credit():
    # Construct examples in parts to avoid identifying paths in the release source.
    local_path = "/" + "Users" + "/example-user/project"
    assert module.findings_for("docs/a.json", json.dumps({"dataset": local_path}).encode())
    assert module.findings_for("pyproject.toml", b'authors = ["Example Researcher"]', ["Example Researcher"])
    assert not module.findings_for("docs/licenses/upstream-LICENSE.txt", b"Copyright Upstream Author", ["Upstream Author"])


def test_scan_distinguishes_verified_subject_ids_from_contributor_attribution():
    name = "examples/campaignview/saved_unique/real_r1/events.jsonl"
    uid = "Example Researcher_XX_1_2020"
    identities = ["Example Researcher"]
    subjects = {uid}
    assert not module.findings_for(name, json.dumps({"uid": uid}).encode(), identities, subjects)
    assert module.findings_for(name, json.dumps({"uid": uid, "author": identities[0]}).encode(), identities, subjects)
    assert module.findings_for(name, json.dumps({"uid": "Example Researcher_unknown"}).encode(), identities, subjects)
    partition = "examples/campaignview/saved_unique/real_r1/00_partition.json"
    assert not module.findings_for(partition, json.dumps({"measurement_uids": [uid]}).encode(), identities, subjects)
    local_path = "/" + "Users" + "/example-user/project"
    assert module.findings_for(name, json.dumps({"uid": uid, "path": local_path}).encode(), identities, subjects)
