"""Pure data assembly for the issued-session certificate PDF (Part A of
this task). No DB, no HTTP, no reportlab — takes already-fetched rows and
already-computed test states and shapes them into `CertificateData`, so
this module and `app.pdf.certificate` (the actual renderer) are each
independently unit-testable without a live DB or a PDF library.

Each test's aggregate pass/fail is computed the RIGHT way for that test,
not by a single naive rule applied everywhere:
  - Weighing, zero/tare, eccentricity, discrimination, sensitivity: every
    reading's own stored `test_results.passed` IS a complete, independent
    verdict (no whole-set criterion) — "all readings passed" is correct
    here, matching SessionPage.jsx's own `computeProgress` on the frontend.
  - Repeatability: a series' real verdict needs BOTH the per-reading mpe
    check AND the spread check
    (app.services.repeatability.compute_series) — looking only at stored
    per-reading `passed` values would silently ignore the spread
    criterion and could report PASS when the series actually failed.
  - Tilting: its per-reading `test_results.passed` is always `None` by
    design (app/routers/sessions.py stores no per-reading verdict, since
    the criteria are whole-dataset properties) — the real verdict is
    `TiltingStateOut.passed` (app.services.tilting.compute_state).
"""

from dataclasses import dataclass
from typing import Optional

from app.contracts.instrument import InstrumentOut


class CertificateConfigError(Exception):
    """Raised when certificate generation can't proceed because required
    deployment configuration is missing — currently just `PUBLIC_APP_BASE_URL`
    (`app/routers/sessions.py`'s `_verify_url`). Deliberately its own type,
    never silently worked around: a QR code baked into an issued,
    physical-equivalent certificate that encodes the WRONG verify URL is
    worse than refusing to generate the certificate at all
    (`fix/certificate-generation-wiring`)."""


@dataclass(frozen=True)
class WeighingRow:
    """One row of the Weighing certificate table — pulled straight from a
    reading's stored `data`/paired `result` JSON, never recomputed."""

    sequence_no: int
    direction: str
    L: str
    I: str
    delta_l: str
    E: str
    Ec: str
    mpe: str
    passed: bool


@dataclass(frozen=True)
class TestSummary:
    """One line of the "other tests performed" section."""

    __test__ = False  # not a pytest test class — its name just starts with "Test"

    label: str
    performed: bool
    passed: Optional[bool]  # None: not performed, or performed but not yet resolved


@dataclass(frozen=True)
class CertificateData:
    certificate_number: str
    verification_type: str
    issued_at: Optional[str]
    approved_at: Optional[str]
    instrument: InstrumentOut
    weighing_rows: list
    weighing_overall_passed: Optional[bool]
    other_tests: list


def weighing_rows_from_db(reading_rows: list, result_rows: list) -> list:
    """Only the real bidirectional load-sequence rows (`direction` is not
    null). A zero/tare-device reading is ALSO stored under
    `test_type='weighing'` but with `direction` null (docs/architecture.md)
    — it is a distinct sub-procedure, summarized separately via
    `simple_passed_summary`, never folded into this table.

    Same last-write-wins dedup as `GET .../weighing/readings`
    (app/routers/sessions.py): `reading_rows` must already be ordered by
    `created_at` (readings_repo.list_readings's own contract).
    """
    results_by_reading_id = {row["reading_id"]: row for row in result_rows if row.get("reading_id")}
    latest_by_key: dict = {}
    for reading_row in reading_rows:
        if reading_row.get("direction") is None:
            continue
        if reading_row["id"] not in results_by_reading_id:
            continue
        key = (reading_row["sequence_no"], reading_row["direction"])
        latest_by_key[key] = (reading_row, results_by_reading_id[reading_row["id"]])

    rows = []
    for reading_row, result_row in latest_by_key.values():
        data = reading_row["data"]
        result = result_row["result"]
        rows.append(
            WeighingRow(
                sequence_no=reading_row["sequence_no"],
                direction=reading_row["direction"],
                L=data["L"],
                I=data["I"],
                delta_l=data["delta_l"],
                E=result["E"],
                Ec=result["Ec"],
                mpe=result["mpe"],
                passed=result_row["passed"],
            )
        )
    rows.sort(key=lambda row: (row.sequence_no, row.direction))
    return rows


def weighing_overall_passed(rows: list) -> Optional[bool]:
    if not rows:
        return None
    return all(row.passed for row in rows)


def simple_passed_summary(label: str, passed_values: list) -> TestSummary:
    """For a test with no whole-set pass criterion — every value in
    `passed_values` is one reading's own complete, independent verdict."""
    resolved = [value for value in passed_values if value is not None]
    if not passed_values:
        return TestSummary(label=label, performed=False, passed=None)
    if not resolved:
        return TestSummary(label=label, performed=True, passed=None)
    return TestSummary(label=label, performed=True, passed=all(resolved))


def series_aggregate_summary(label: str, series_list: list) -> TestSummary:
    """Repeatability — `series_list` is the two `RepeatabilitySeriesOut`
    (app.services.repeatability.compute_series), each already carrying its
    OWN real verdict (mpe AND spread). A series' `.passed` is `None` until
    it has at least one reading."""
    any_readings = any(series.readings for series in series_list)
    if not any_readings:
        return TestSummary(label=label, performed=False, passed=None)
    resolved = [series.passed for series in series_list if series.passed is not None]
    if len(resolved) < len(series_list):
        return TestSummary(label=label, performed=True, passed=None)
    return TestSummary(label=label, performed=True, passed=all(resolved))


def state_summary(label: str, state) -> TestSummary:
    """Tilting — `state` is a `TiltingStateOut`
    (app.services.tilting.compute_state) already carrying the real
    whole-dataset verdict in `.passed`."""
    performed = bool(state.readings)
    return TestSummary(label=label, performed=performed, passed=state.passed if performed else None)
