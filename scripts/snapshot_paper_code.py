"""Copy the public package and manuscript records into a new source snapshot."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from build_reviewer_release import public_files


def main(root):
    repo = Path(__file__).resolve().parents[1]
    dest = Path(root).resolve() / "code"
    if dest.exists():
        raise ValueError("Choose a new snapshot folder; existing snapshots are not overwritten.")
    paths = public_files(repo)
    copied = {}
    for source in paths:
        name = source.relative_to(repo)
        target = dest / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        copied[name.as_posix()] = hashlib.sha256(source.read_bytes()).hexdigest()
    (dest / "source_manifest.json").write_text(
        json.dumps({"source": "discern public files", "files_sha256": copied}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"copied_source_files": len(copied), "destination": "code/"}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", help="New snapshot folder; files are placed in its code subfolder")
    main(parser.parse_args().root)
