"""Build a reviewer source archive from explicitly selected public files.

No Git history, private data, local settings, generated manuscript drafts, or
build metadata are included. The archive is checked before it is written.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TOP_FILES = ("README.md", "LICENSE", "pyproject.toml", ".gitignore", ".gitattributes")
SUFFIXES = {
    "src": {".py", ".typed"},
    "scripts": {".py"},
    "tests": {".py", ".json"},
    "docs": {".md", ".json", ".txt"},
    "examples": {".py", ".md", ".json", ".jsonl", ".csv"},
}
SKIP_PARTS = {"__pycache__", ".pytest_cache", "runs", "fresh_runs", ".git", ".DS_Store"}
# Data files contain public candidates' names and source-site contact details.
# Contributor checks still apply to the code, configs, and output metadata.
PUBLIC_SUBJECT_TEXT = {
    "examples/campaignview/data/bio_party.csv",
    "examples/campaignview/data/bio_party_unique.csv",
    "examples/campaignview/data/source/biographical_narratives.csv",
}
PATTERNS = {
    "local_user_path": re.compile(r"(?:/(?:Users|home)/|[A-Za-z]:[/\\]+Users[/\\]+)[^\s\"<>]+"),
    "local_file_url": re.compile("file:" + r"//[^\s\"<>]+"),
    "credential_value": re.compile(r"(?:sk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}|AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----)"),
    "email_attribution": re.compile(r"(?im)^(?:author|maintainer|contact|email)\s*[:=].*[^\s]+@[^\s]+"),
}


def public_files(root=ROOT):
    paths = [root / name for name in TOP_FILES]
    for folder, suffixes in SUFFIXES.items():
        paths.extend(p for p in sorted((root / folder).rglob("*"))
                     if p.is_file() and p.suffix in suffixes
                     and not set(p.relative_to(root).parts).intersection(SKIP_PARTS))
    for path in paths:
        if path.is_symlink():
            raise ValueError(f"Refusing symlink: {path.relative_to(root)}")
        if not path.is_file():
            raise ValueError(f"Missing public file: {path.relative_to(root)}")
    return sorted(paths)


def attribution_text(name, text, public_subject_uids):
    """Ignore verified dataset IDs only in the saved artifacts' unit-ID fields.

    This changes the view used for attribution checks, never the archived bytes.
    An author field or an unrecognized ID still receives the full identity check.
    """
    if not public_subject_uids or not name.startswith(("examples/campaignview/saved/",
                                                      "examples/campaignview/saved_unique/")):
        return text

    def inspect(value, field=None):
        if field == "uid" and isinstance(value, str) and value in public_subject_uids:
            return "[public dataset unit]"
        if field in {"measurement_uids", "slotA_uids", "slotB_uids"} and isinstance(value, list):
            return ["[public dataset unit]" if isinstance(v, str) and v in public_subject_uids else inspect(v)
                    for v in value]
        if isinstance(value, dict):
            return {key: inspect(item, key) for key, item in value.items()}
        if isinstance(value, list):
            return [inspect(item) for item in value]
        return value

    try:
        if name.endswith(".jsonl"):
            return "\n".join(json.dumps(inspect(json.loads(line)), ensure_ascii=False) for line in text.splitlines() if line.strip())
        if name.endswith(".json"):
            return json.dumps(inspect(json.loads(text)), ensure_ascii=False)
    except (ValueError, TypeError):
        pass
    return text


def findings_for(name, content, identities=(), public_subject_uids=()):
    if name in PUBLIC_SUBJECT_TEXT:
        return []
    # Inspect text only; public_files excludes binary documents and images.
    text = content.decode("utf-8")
    findings = []
    for kind, pattern in PATTERNS.items():
        if pattern.search(text):
            findings.append({"file": name, "kind": kind})
    # Preserve third-party notices, which name upstream copyright holders.
    if not name.startswith("docs/licenses/"):
        attribution = attribution_text(name, text, public_subject_uids)
        for identity in identities:
            if identity.casefold() in attribution.casefold():
                findings.append({"file": name, "kind": "contributor_identity"})
                break
    return findings


def build_release(out, identities=(), root=ROOT):
    out = Path(out)
    if out.exists():
        raise ValueError("Choose a new archive path; existing archives are not overwritten.")
    files = {p.relative_to(root).as_posix(): p.read_bytes() for p in public_files(root)}
    public_subject_uids = set()
    for name in ("examples/campaignview/data/bio_party.csv", "examples/campaignview/data/bio_party_unique.csv"):
        if name in files:
            public_subject_uids.update(row["id"] for row in csv.DictReader(io.StringIO(files[name].decode("utf-8"))))
    findings = [f for name, content in files.items()
                for f in findings_for(name, content, identities, public_subject_uids)]
    if findings:
        raise ValueError("Review-copy scan failed:\n" + json.dumps(findings, indent=2))
    manifest = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
    files["RELEASE_MANIFEST.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    out.parent.mkdir(parents=True, exist_ok=True)
    # Fixed metadata avoids embedding host paths, user names, or creation times.
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo("discern-review/" + name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return {"files": len(files), "bytes": out.stat().st_size,
            "sha256": hashlib.sha256(out.read_bytes()).hexdigest(), "findings": findings}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--identity", action="append", default=[],
                        help="Contributor name, handle, or email to check; repeat as needed")
    args = parser.parse_args()
    print(json.dumps(build_release(args.out, args.identity), indent=2))


if __name__ == "__main__":
    main()
