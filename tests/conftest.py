import sys
from pathlib import Path

# Make the repo-root `engine` package importable regardless of the directory
# pytest is invoked from (no install step, no src-layout).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
