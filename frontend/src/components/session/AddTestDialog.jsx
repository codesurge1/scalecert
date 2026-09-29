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
 * "Add test" -> pick from the 7 -> that test's table opens. All seven now
 * have working forms (each opens its own route, `row.route(sessionId)` —
 * see src/lib/testChecklist.js): Weighing, Zero/tare device accuracy,
 * Repeatability, and Eccentricity are universal (no applicability check at
 * all); Discrimination, Tilting, and Sensitivity are gated by their own
 * `naReason(instrument)` (indication_type / is_mobile) and show that reason
 * instead of opening when inapplicable. The "Coming soon" branch below is
 * kept for the day a checklist row exists without a form yet — with all
 * seven built, it's currently unreachable, not deleted. This is the
 * discovery surface for the full checklist — the session overview itself
 * shows every applicable test directly too, since each derives its status
 * purely from its own submitted data (only Weighing has an actual
 * session_test_selection row, created unconditionally at session
 * creation), so picking a test here just lands on the same page "Open"
 * would.
 *
 * No forced sequence (docs/architecture.md, RRSL-confirmed): `isSelectable`
 * takes only the row and the instrument, never any other test's progress,
 * so any applicable test is openable here regardless of whether another
 * test has been touched, and the disabled reason shown for a
 * non-selectable row is always "N/A" (applicability) — never something
 * implying another test must be completed first.
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
      {/* flex column + a `min-h-0 overflow-y-auto` list: the dialog is
          already capped at the viewport height (ui/dialog.jsx), and this
          makes only the test list scroll inside that cap — title and close
          button stay pinned — instead of the whole dialog scrolling. */}
      <DialogContent className="flex flex-col overflow-hidden">
        <DialogHeader className="shrink-0">
          <DialogTitle>Add a test</DialogTitle>
          <DialogDescription>The OIML clause 8.3.3 verification checklist.</DialogDescription>
        </DialogHeader>

        <div className="-mx-1 grid min-h-0 gap-1.5 overflow-y-auto overscroll-contain px-1 pb-1">
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
