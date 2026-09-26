"""Purity enforcement (CLAUDE.md): the engine/ package imports nothing outside
the standard library — no FastAPI, no Supabase, no network, no DB, no
wall-clock. Made mechanical so a future accidental import fails CI, not review.
"""

import ast
import sys
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent.parent / "engine"


def _top_level_imports_in(path: Path) -> set:
    tree = ast.parse(path.read_text(), filename=str(path))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:  # skip relative imports (level > 0)
                modules.add(node.module.split(".")[0])
    return modules


def test_engine_package_exists_and_is_nonempty():
    py_files = sorted(ENGINE_DIR.rglob("*.py"))
    assert py_files, f"expected .py files under {ENGINE_DIR}"


def test_engine_imports_only_stdlib_and_itself():
    stdlib = sys.stdlib_module_names
    external = set()
    for path in ENGINE_DIR.rglob("*.py"):
        for module in _top_level_imports_in(path):
            if module == "engine":
                continue  # internal imports (e.g. `from engine.mpe import ...`) are fine
            if module not in stdlib:
                external.add(module)

    assert not external, (
        f"engine/ imports non-stdlib module(s): {sorted(external)} — "
        "the engine must have zero runtime dependencies (CLAUDE.md)."
    )
