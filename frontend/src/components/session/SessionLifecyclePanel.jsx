import { useState } from "react";
import { toast } from "sonner";
import { API_BASE, apiFetch, ApiError } from "@/lib/api";
import { supabase } from "@/lib/supabase";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

const STEPS = [
  { key: "draft", label: "Draft" },
  { key: "submitted", label: "Submitted" },
  { key: "approved", label: "Approved" },
  { key: "issued", label: "Issued" },
];

function formatWhen(iso) {
  if (!iso) return "";
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleString();
}

// approved_by/created_by are UUIDs — there's no profile-name-lookup route
// exposed to every viewer (a technician can only see their OWN profile row
// under RLS, docs/architecture.md), so this shows a shortened id rather
// than a name. Good enough to prove "who" without a new read endpoint.
function shortId(id) {
  return id ? `${id.slice(0, 8)}…` : "—";
}

function LifecycleStepper({ status }) {
  if (status === "superseded") {
    return <Badge variant="outline">Superseded</Badge>;
  }
  const currentIndex = status === "returned" ? 1 : STEPS.findIndex((s) => s.key === status);
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {STEPS.map((step, i) => {
        const isReturnedHere = status === "returned" && step.key === "submitted";
        const done = i < currentIndex || (i === currentIndex && !isReturnedHere);
        const isCurrent = i === currentIndex;
        return (
          <div key={step.key} className="flex items-center gap-1.5">
            <Badge
              variant={isReturnedHere ? "warning" : isCurrent ? "default" : done ? "success" : "outline"}
              className={isCurrent || done ? "" : "opacity-60"}
            >
              {isReturnedHere ? "Returned for changes" : step.label}
            </Badge>
            {i < STEPS.length - 1 ? <span className="text-muted-foreground">&rarr;</span> : null}
          </div>
        );
      })}
    </div>
  );
}

function ReturnSessionDialog({ sessionId, onReturned }) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  async function handleReturn() {
    if (reason.trim() === "") {
      setError("A reason is required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const updated = await apiFetch(`/sessions/${sessionId}/return`, { method: "POST", body: { reason } });
      toast.success("Session returned to the technician.");
      setOpen(false);
      setReason("");
      onReturned(updated);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" variant="outline">
          Return
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Return this session</DialogTitle>
          <DialogDescription>
            The technician will see this reason and can edit the session before resubmitting.
          </DialogDescription>
        </DialogHeader>

        <textarea
          className="min-h-24 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring disabled:opacity-60"
          placeholder="What needs to change before this can be approved?"
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          disabled={submitting}
        />

        {error ? <p className="text-sm font-medium text-destructive">{error}</p> : null}

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)} disabled={submitting}>
            Cancel
          </Button>
          <Button onClick={handleReturn} disabled={submitting}>
            {submitting ? "Returning…" : "Return"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/**
 * The session overview's lifecycle controls: submit -> approve/return ->
 * issue, gated by the caller's own role/id and the session's current
 * status, plus a status stepper and the lifecycle trail (who/when).
 * Separation of duties is enforced server-side (RLS + API,
 * docs/architecture.md) — every button here is a UX convenience on top of
 * that, never the actual guard: a rejected call still surfaces the
 * server's own clean error via toast.
 */
export function SessionLifecyclePanel({ session, profile, canSubmit, submitBlockedReason, onChanged }) {
  const [busy, setBusy] = useState(false);

  const isCreator = profile?.id === session.created_by;
  const isApproverRole = profile?.role === "approver" || profile?.role === "admin";
  const isOwnSessionForApprover = isApproverRole && profile?.id === session.created_by;

  async function runAction(path, successMessage) {
    setBusy(true);
    try {
      const updated = await apiFetch(`/sessions/${session.id}${path}`, { method: "POST" });
      // Only ever set on the response to POST .../issue (app/routers/
      // sessions.py) — the issue itself (status + certificate number)
      // still succeeded, but automatic PDF generation didn't; surface that
      // clearly instead of a plain "Certificate issued." that would hide
      // it. "Download certificate" below is the retry — never a dead end.
      if (updated?.report_generation_error) {
        toast.error(updated.report_generation_error);
      } else {
        toast.success(successMessage);
      }
      onChanged(updated);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Something went wrong.";
      toast.error(message);
    } finally {
      setBusy(false);
    }
  }

  const canIssue =
    profile?.role === "admin" || (profile?.role === "approver" && session.approved_by === profile?.id);

  // apiFetch parses every response as JSON, so it can't be reused for a
  // binary PDF download — this fetches the raw bytes directly, attaching
  // the session token the same way apiFetch does internally, then triggers
  // a normal browser download from the resulting blob.
  async function handleDownloadCertificate() {
    setBusy(true);
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      const response = await fetch(`${API_BASE}/sessions/${session.id}/report`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!response.ok) {
        const text = await response.text();
        let detail = `Request failed with status ${response.status}`;
        try {
          detail = JSON.parse(text)?.detail ?? detail;
        } catch {
          // response wasn't JSON — keep the generic detail above
        }
        throw new Error(detail);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${session.certificate_number}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      toast.error(err.message || "Could not download the certificate.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardContent className="grid gap-4 py-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <LifecycleStepper status={session.status} />
          {session.certificate_number ? (
            <Badge variant="success" className="text-sm">
              Certificate {session.certificate_number}
            </Badge>
          ) : null}
        </div>

        <div className="grid gap-1 text-xs text-muted-foreground">
          {session.submitted_at ? <div>Submitted {formatWhen(session.submitted_at)}</div> : null}
          {session.approved_at ? (
            <div>
              Approved by {shortId(session.approved_by)} on {formatWhen(session.approved_at)}
            </div>
          ) : null}
          {session.issued_at ? <div>Issued {formatWhen(session.issued_at)}</div> : null}
        </div>

        {session.status === "returned" && session.return_reason ? (
          <div className="rounded-md border border-warning/50 bg-warning/10 px-3 py-2 text-sm">
            <span className="font-medium">Returned: </span>
            {session.return_reason}
          </div>
        ) : null}

        <div className="flex flex-wrap items-center gap-2">
          {/* Technician — draft, ready to submit. */}
          {isCreator && session.status === "draft" ? (
            <>
              <Button size="sm" onClick={() => runAction("/submit", "Submitted for review.")} disabled={busy || !canSubmit}>
                Submit for review
              </Button>
              {!canSubmit ? <span className="text-xs text-muted-foreground">{submitBlockedReason}</span> : null}
            </>
          ) : null}

          {/* Technician — returned, needs to reopen before editing/resubmitting. */}
          {isCreator && session.status === "returned" ? (
            <Button size="sm" onClick={() => runAction("/reopen", "Reopened for editing.")} disabled={busy}>
              Reopen for editing
            </Button>
          ) : null}

          {/* Approver/admin — submitted, not their own session. */}
          {isApproverRole && session.status === "submitted" && !isOwnSessionForApprover ? (
            <>
              <Button size="sm" onClick={() => runAction("/approve", "Session approved.")} disabled={busy}>
                Approve
              </Button>
              <ReturnSessionDialog sessionId={session.id} onReturned={onChanged} />
            </>
          ) : null}
          {isApproverRole && session.status === "submitted" && isOwnSessionForApprover ? (
            <span className="text-sm italic text-muted-foreground">
              You cannot approve your own session (separation of duties) — another approver or admin must act on it.
            </span>
          ) : null}

          {/* Approver/admin — approved, ready to issue. */}
          {isApproverRole && session.status === "approved" && canIssue ? (
            <Button size="sm" onClick={() => runAction("/issue", "Certificate issued.")} disabled={busy}>
              Issue certificate
            </Button>
          ) : null}
          {isApproverRole && session.status === "approved" && !canIssue ? (
            <span className="text-sm italic text-muted-foreground">
              Only an admin, or the approver who approved this session, may issue its certificate.
            </span>
          ) : null}

          {/* A technician with nothing to approve/return/issue sees no
              buttons at all — there is nothing else to say (item 10). */}

          {/* Issued — download the generated PDF and/or open the public,
              login-free verification page anyone (not just this app's
              users) can reach via the certificate's QR code. */}
          {session.status === "issued" && session.certificate_number ? (
            <>
              <Button size="sm" variant="outline" onClick={handleDownloadCertificate} disabled={busy}>
                Download certificate
              </Button>
              <Button size="sm" variant="outline" asChild>
                <a href={`/verify/${session.certificate_number}`} target="_blank" rel="noreferrer">
                  View public verification page
                </a>
              </Button>
            </>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}
