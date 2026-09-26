import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { TEST_ROWS, isSelectable } from "@/lib/testChecklist";

/**
 * "Add test" -> pick from the 7 -> that test's table opens. Only Weighing
 * is actually selectable today (and only when it isn't N/A for this
 * instrument, though Weighing never is); the other six are shown, greyed,
 * with the reason (N/A for the three conditional tests, "Coming soon" for
 * the rest, since their forms aren't built yet). This is the discovery
 * surface for the full checklist — the session overview itself shows
 * Weighing directly too, since it's always already added (its
 * session_test_selection row is created unconditionally at session
 * creation), so picking it here just lands on the same page "Open" would.
 */
export function AddTestDialog({ sessionId, instrument }) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  function handlePick(row) {
    if (!isSelectable(row, instrument)) return;
    setOpen(false);
    navigate(`/sessions/${sessionId}/weighing`);
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">Add test</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add a test</DialogTitle>
          <DialogDescription>The OIML clause 8.3.3 verification checklist.</DialogDescription>
        </DialogHeader>

        <div className="grid gap-1.5">
          {TEST_ROWS.map((row) => {
            const naReason = instrument && row.naReason ? row.naReason(instrument) : null;
            const selectable = isSelectable(row, instrument);
            return (
              <button
                key={row.key}
                type="button"
                disabled={!selectable}
                onClick={() => handlePick(row)}
                className={`flex items-center justify-between rounded-md border px-3 py-2 text-left text-sm transition-colors ${
                  selectable ? "cursor-pointer hover:bg-accent" : "cursor-not-allowed opacity-50"
                }`}
              >
                <span>
                  <span className="font-medium">{row.label}</span>
                  <span className="ml-2 text-xs text-muted-foreground">{naReason || row.note || row.clause}</span>
                </span>
                {!selectable ? (
                  <span className="shrink-0 text-xs text-muted-foreground">{naReason ? "N/A" : "Coming soon"}</span>
                ) : null}
              </button>
            );
          })}
        </div>
      </DialogContent>
    </Dialog>
  );
}
