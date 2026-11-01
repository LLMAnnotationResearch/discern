"""Offline research validation entry point; use --help for commands."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from discern.validation import main

if __name__ == "__main__":
    main()
