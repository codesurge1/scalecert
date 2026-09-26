"""Pydantic v2 API-layer contracts — one module per test_type.

Only `weighing.py` exists so far (the vertical slice; docs/plan.md Phase 2).
The other five in-scope test types (repeatability, eccentricity,
discrimination, tilting, sensitivity) and the zero/tare Weighing variant each
get their own `<test_type>.py` module here later, following weighing.py's
shape: a `<Name>ReadingIn`, a `<Name>ResultOut`, and the two adapter
functions (reading -> engine kwargs, engine result -> Out). None of them are
implemented yet — this note is the placeholder, not speculative stub files.
"""
