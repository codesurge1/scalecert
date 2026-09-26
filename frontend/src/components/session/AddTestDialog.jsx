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
 * "Add test" -> pick from the 7 -> that test's table opens. Weighing,
 * Zero/tare device accuracy, Repeatability, and Eccentricity are
 * selectable today (each opens its own route, `row.route(sessionId)` —
 * see src/lib/testChecklist.js), each subject only to its own applicability
 * check (none of the four have one — they're universal); Discrimination/
 * Tilting/Sensitivity show their N/A reason when inapplicable, or "Coming
 * soon" otherwise, since their forms aren't built yet. This is the
 * discovery surface for the full checklist — the session overview itself
 * shows Weighing directly too, since it's always already added (its
 * session_test_selection row is created unconditionally at session
 * creation), so picking Weighing here just lands on the same page "Open"
 * would.
 *
 * No forced sequence (docs/architecture.md, RRSL-confirmed): `isSelectable`
 * takes only the row and the instrument, never any other test's progress,
 * so any implemented test is openable here regardless of whether another
 * test has been touched, and the disabled reason shown for a
 * non-selectable row is always "N/A" (applicability) or "Coming soon" (not
 * built yet) — never something implying another test must be completed
 * first.
 */
export function AddTestDialog({ sessionId, instrument }) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  function handlePick(row) {
    if (!isSelectable(row, instrument)) return;
    setOpen(false);
    navigate(row.route(sessionId));
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
