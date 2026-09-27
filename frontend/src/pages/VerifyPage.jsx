import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { toast } from "sonner";
import { ApiError, publicFetch } from "@/lib/publicApi";
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
import { Skeleton } from "@/components/ui/skeleton";

const VERIFICATION_TYPE_LABELS = {
  initial: "Initial verification",
  subsequent: "Subsequent verification",
  in_service: "In-service verification",
};

function formatWhen(iso) {
  if (!iso) return "";
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
}

function ReportDiscrepancyDialog({ certNumber }) {
  const [open, setOpen] = useState(false);
  const [description, setDescription] = useState("");
  const [contact, setContact] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [submitted, setSubmitted] = useState(false);

  async function handleSubmit() {
    if (description.trim() === "") {
      setError("Please describe the issue.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await publicFetch(`/verify/${certNumber}/report-discrepancy`, {
        method: "POST",
        body: { description, contact: contact.trim() === "" ? null : contact },
      });
      setSubmitted(true);
      toast.success("Thank you — your report has been recorded.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) {
          setSubmitted(false);
          setDescription("");
          setContact("");
          setError(null);
        }
      }}
    >
      <DialogTrigger asChild>
        <Button variant="outline">Report a discrepancy</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Report a discrepancy</DialogTitle>
          <DialogDescription>
            Tell us what looks wrong with this certificate. No account is needed.
          </DialogDescription>
        </DialogHeader>

        {submitted ? (
          <p className="text-sm font-medium text-emerald-700">
            Thank you. Your report has been recorded and will be reviewed.
          </p>
        ) : (
          <>
            <div className="grid gap-3">
              <textarea
                className="min-h-24 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring disabled:opacity-60"
                placeholder="Describe the issue you noticed..."
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                disabled={submitting}
              />
              <input
                className="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring disabled:opacity-60"
                placeholder="Your contact info (optional)"
                value={contact}
                onChange={(event) => setContact(event.target.value)}
                disabled={submitting}
              />
            </div>
            {error ? <p className="text-sm font-medium text-destructive">{error}</p> : null}
          </>
        )}

        <DialogFooter>
          {submitted ? (
            <Button onClick={() => setOpen(false)}>Close</Button>
          ) : (
            <>
              <Button variant="outline" onClick={() => setOpen(false)} disabled={submitting}>
                Cancel
              </Button>
              <Button onClick={handleSubmit} disabled={submitting}>
                {submitting ? "Sending…" : "Submit report"}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/**
 * The public, login-free certificate-verification page — no AppShell, no
 * nav, reachable by anyone (a citizen or field inspector scanning the QR
 * code on a printed certificate). Deliberately shows only the safe field
 * list the backend's SECURITY DEFINER function returns (ADR-0009) — never
 * technician/approver identity, raw readings, or anything from a
 * non-issued session. "Not found" covers both a nonexistent certificate
 * number AND a real-but-not-yet-issued one, indistinguishably, by design.
 */
export function VerifyPage() {
  const { certNumber } = useParams();
  const [certificate, setCertificate] = useState(undefined); // undefined=loading, null=not found, object=found

  useEffect(() => {
    let cancelled = false;
    publicFetch(`/verify/${certNumber}`)
      .then((data) => {
        if (!cancelled) setCertificate(data);
      })
      .catch(() => {
        if (!cancelled) setCertificate(null);
      });
    return () => {
      cancelled = true;
    };
  }, [certNumber]);

  return (
    <div className="flex min-h-screen items-start justify-center bg-slate-50 px-4 py-10 dark:bg-slate-950 sm:py-16">
      <div className="w-full max-w-lg">
        <div className="mb-6 text-center">
          <div className="text-lg font-semibold tracking-tight text-slate-900 dark:text-slate-100">ScaleCert</div>
          <div className="text-xs text-muted-foreground">Public certificate verification</div>
        </div>

        {certificate === undefined ? (
          <Card>
            <CardContent className="grid gap-3 py-8">
              <Skeleton className="mx-auto h-6 w-40" />
              <Skeleton className="h-24 w-full" />
            </CardContent>
          </Card>
        ) : certificate === null ? (
          <Card className="border-destructive/40">
            <CardContent className="grid gap-3 py-10 text-center">
              <div className="text-3xl">&#10007;</div>
              <div className="text-lg font-semibold text-destructive">Certificate not found</div>
              <p className="text-sm text-muted-foreground">
                No valid, issued certificate matches <span className="font-mono">{certNumber}</span>. It may not
                exist, or verification may not yet be complete.
              </p>
            </CardContent>
          </Card>
        ) : (
          <Card className="border-emerald-600/40">
            <CardContent className="grid gap-4 py-6">
              <div className="flex items-center justify-center gap-2 border-b pb-4 text-center">
                <span className="text-2xl text-emerald-600">&#10003;</span>
                <span className="text-lg font-semibold text-emerald-700">Valid Certificate</span>
              </div>

              <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
                <dt className="text-muted-foreground">Certificate No.</dt>
                <dd className="font-mono font-medium">{certificate.certificate_number}</dd>

                <dt className="text-muted-foreground">Status</dt>
                <dd>
                  <Badge variant="success" className="capitalize">
                    {certificate.status}
                  </Badge>
                </dd>

                <dt className="text-muted-foreground">Issued</dt>
                <dd>{formatWhen(certificate.issued_at)}</dd>

                <dt className="text-muted-foreground">Verification type</dt>
                <dd>{VERIFICATION_TYPE_LABELS[certificate.verification_type] ?? certificate.verification_type}</dd>

                <dt className="text-muted-foreground">Instrument</dt>
                <dd>{certificate.instrument_type_designation || certificate.instrument_model || "—"}</dd>

                <dt className="text-muted-foreground">Manufacturer</dt>
                <dd>{certificate.instrument_manufacturer || "—"}</dd>

                <dt className="text-muted-foreground">Accuracy class</dt>
                <dd>{certificate.accuracy_class}</dd>
              </dl>

              <p className="text-center text-xs text-muted-foreground">
                Issued under OIML R 76 by an authorized Regional Reference Standards Laboratory.
              </p>
            </CardContent>
          </Card>
        )}

        <div className="mt-6 flex justify-center">
          <ReportDiscrepancyDialog certNumber={certNumber} />
        </div>
      </div>
    </div>
  );
}
