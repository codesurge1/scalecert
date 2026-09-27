"""Supabase Storage access for the generated certificate PDF
(app.pdf.certificate) — CLAUDE.md: "Generated PDFs go to Supabase
Storage, never local disk." Uses the caller's own per-request user-scoped
client (never service-role — the same rule CLAUDE.md applies to every
other read/write), so an upload here is gated by whatever the `reports`
bucket's own Storage policies allow for an authenticated user; the API
layer's own approver/admin-or-creator + status=='issued' check
(app/routers/sessions.py) is what actually authorizes the *action*, same
"defense in depth" split as every other write in this app.

`supabase-py`'s storage client raises its own exception type (from the
bundled `storage3` package), not `postgrest.exceptions.APIError` — this
module deliberately does NOT try to reuse `app.repositories.errors`'
Postgres-error-code detection, since a Storage failure has no Postgres
error code to inspect. `StorageError` here is a separate, narrower type
for exactly that reason.
"""

import os

from supabase import Client

REPORTS_BUCKET = os.environ.get("SUPABASE_STORAGE_BUCKET", "reports")


class StorageError(Exception):
    """Raised instead of letting a raw storage3 exception (or anything
    else the Storage client throws) escape uncaught."""

    def __init__(self, *, operation: str, hint: str, cause: Exception | None = None) -> None:
        self.operation = operation
        self.hint = hint
        super().__init__(f"{operation} failed: {hint}")
        if cause is not None:
            self.__cause__ = cause


def upload_report_pdf(client: Client, *, path: str, pdf_bytes: bytes) -> str:
    """Uploads (or overwrites — `upsert`, so regenerating a report for the
    same session is idempotent rather than erroring on "already exists")
    the PDF to the `reports` bucket at `path`. Returns `path` unchanged, on
    success, for the caller to store on `test_sessions.report_storage_path`.
    """
    try:
        client.storage.from_(REPORTS_BUCKET).upload(
            path, pdf_bytes, {"content-type": "application/pdf", "upsert": "true"}
        )
    except Exception as exc:  # storage3's own exception type, not ours to name here
        raise StorageError(
            operation="upload", hint=f"uploading {path!r} to the {REPORTS_BUCKET!r} bucket: {exc}", cause=exc
        ) from exc
    return path
