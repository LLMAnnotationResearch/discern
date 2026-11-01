"""Record the execution environment without user names, paths, or credentials."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from importlib import metadata
from pathlib import Path
import platform


def software_environment() -> dict:
    """Hash the installed package source and record versions used by the pipeline.

    This describes the current execution. It cannot recover the environment of an
    older run. Deliberately omit host names, executable paths, and Git identities.
    """
    packages = {}
    for name in ("discern", "numpy", "pandas", "openai", "anthropic", "openpyxl"):
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = None
    source = Path(__file__).resolve().parent
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(source.glob("*.py"))}
    return {
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.system(),
        "machine": platform.machine(),
        "packages": packages,
        "source_sha256": hashes,
    }
