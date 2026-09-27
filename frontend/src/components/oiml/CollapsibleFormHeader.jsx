import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { Badge } from "@/components/ui/badge";

const VERIFICATION_TYPE_LABELS = {
  initial: "Initial verification",
  subsequent: "Subsequent verification",
  in_service: "In-service verification",
};

/**
 * Sits above the OIML bordered document sheet on every test-entry screen —
 * see docs/architecture.md, Frontend, "focused test-entry mode." Always
 * shows a tight, app-styled (sans-serif, small) summary of the essentials —
 * instrument, e, Max, verification type, and whichever of date/observer the
 * calling form actually tracks (not every test has a Date field; `date` is
 * simply omitted from the strip when a caller doesn't pass one, never
 * invented) — so the technician's eye lands on the data table, not a page
 * of form header. `children` is the form's own full header block (masthead,
 * identity lines, environmental grid, zero-device checkboxes, formula),
 * completely unchanged, just rendered conditionally instead of always:
 * collapsed by default, one click away, still exactly as document-styled
 * and printable-looking as before.
 */
export function CollapsibleFormHeader({ instrument, verificationType, date, observer, children }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="grid gap-2">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 rounded-md border bg-card px-3 py-1.5 text-xs">
        <span className="font-semibold text-foreground">
          {instrument?.type_designation || instrument?.model || "Instrument"}
        </span>
        <span className="text-muted-foreground">
          e = {instrument?.e_value ?? "—"} g &middot; Max = {instrument?.max_capacity ?? "—"} g
        </span>
        {verificationType ? (
          <Badge variant="outline" className="font-normal">
            {VERIFICATION_TYPE_LABELS[verificationType] ?? verificationType}
          </Badge>
        ) : null}
        {date ? <span className="text-muted-foreground">{date}</span> : null}
        {observer ? <span className="truncate text-muted-foreground">{observer}</span> : null}
        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          className="ml-auto flex items-center gap-1 whitespace-nowrap font-medium text-primary hover:underline"
        >
          {expanded ? "Hide full form header" : "Show full form header"}
          {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
        </button>
      </div>
      {expanded ? children : null}
    </div>
  );
}
