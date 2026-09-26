import sys
from pathlib import Path

# Make both the repo-root `engine` package and `backend`'s own `app` package
# importable regardless of the directory pytest is invoked from.
_BACKEND = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND.parent

for path in (_REPO_ROOT, _BACKEND):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
