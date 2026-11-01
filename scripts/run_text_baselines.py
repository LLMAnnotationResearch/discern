"""Run conventional sentiment/LDA/LIWC pilots; see --help."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from discern.baselines import main

if __name__ == "__main__":
    main()
