import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const VERIFICATION_TYPES = [
  { value: "initial", label: "Initial verification" },
  { value: "subsequent", label: "Subsequent verification" },
  { value: "in_service", label: "In-service verification" },
];

/**
 * The one entry point into the Weighing workflow: pick a verification_type
 * for an instrument, POST /api/sessions, and land on its session page.
 */
export function StartVerificationDialog({ instrumentId, instrumentLabel }) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [verificationType, setVerificationType] = useState("initial");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  async function handleStart() {
    setSubmitting(true);
    setError(null);
    try {
      const session = await apiFetch("/sessions", {
        method: "POST",
        body: { instrument_id: instrumentId, verification_type: verificationType },
      });
      toast.success("Verification session started.");
      setOpen(false);
      navigate(`/sessions/${session.id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">Start verification</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Start verification</DialogTitle>
          <DialogDescription>{instrumentLabel}</DialogDescription>
        </DialogHeader>

        <div className="grid gap-2">
          <Label htmlFor="verification-type">Verification type</Label>
          <Select value={verificationType} onValueChange={setVerificationType}>
            <SelectTrigger id="verification-type">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {VERIFICATION_TYPES.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {error ? <p className="text-sm font-medium text-destructive">{error}</p> : null}

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)} disabled={submitting}>
            Cancel
          </Button>
          <Button onClick={handleStart} disabled={submitting}>
            {submitting ? "Starting…" : "Start"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
