import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const KIND_LABELS = {
  max: "Max",
  min: "Min",
  band_transition: "Band transition",
  fill: "Fill",
};

// Sourced anchors (from R76-1 Table 6, via the engine) vs. a placeholder
// convention pending RRSL confirmation — the distinction the engine's
// LoadEntry.kind exists to carry, surfaced here rather than flattened away.
function KindBadge({ kind }) {
  if (kind === "fill") {
    return (
      <Badge
        variant="outline"
        title="Evenly-spaced placeholder to reach the minimum load count — a documented convention pending RRSL confirmation, not an OIML requirement."
      >
        Fill (convention)
      </Badge>
    );
  }
  return (
    <Badge
      variant="secondary"
      title="Sourced directly from OIML R76-1 Table 6 — Max, Min, or a band-transition load."
    >
      {KIND_LABELS[kind] ?? kind}
    </Badge>
  );
}

function DirectionStatus({ label, result }) {
  if (!result) {
    return (
      <Badge variant="outline" className="text-muted-foreground">
        {label} pending
      </Badge>
    );
  }
  return (
    <Badge variant={result.passed ? "success" : "destructive"}>
      {label} {result.passed ? "PASS" : "FAIL"}
    </Badge>
  );
}

/**
 * The generated load sequence — the source of truth for what `sequence_no`
 * means (docs/architecture.md: server-derives-L). `readingsByKey` is keyed
 * "<sequence_no>-<direction>" so both bidirectional readings for a load are
 * tracked independently, per the plan's up-and-down requirement.
 */
export function LoadSequenceTable({ sequence, readingsByKey, selected, onSelect }) {
  return (
    <Card>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>#</TableHead>
            <TableHead>L (g)</TableHead>
            <TableHead>m (×e)</TableHead>
            <TableHead>Kind</TableHead>
            <TableHead>MPE (±g)</TableHead>
            <TableHead>Readings</TableHead>
            <TableHead className="text-right">Action</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sequence.map((entry) => {
            const isSelected = selected?.sequence_no === entry.sequence_no;
            const up = readingsByKey[`${entry.sequence_no}-up`];
            const down = readingsByKey[`${entry.sequence_no}-down`];
            return (
              <TableRow key={entry.sequence_no} className={isSelected ? "bg-accent" : undefined}>
                <TableCell>{entry.sequence_no}</TableCell>
                <TableCell className="font-medium">{entry.L}</TableCell>
                <TableCell className="text-muted-foreground">{entry.m}</TableCell>
                <TableCell>
                  <KindBadge kind={entry.kind} />
                </TableCell>
                <TableCell>{entry.mpe}</TableCell>
                <TableCell>
                  <div className="flex gap-1.5">
                    <DirectionStatus label="↑" result={up} />
                    <DirectionStatus label="↓" result={down} />
                  </div>
                </TableCell>
                <TableCell className="text-right">
                  <Button
                    size="sm"
                    variant={isSelected ? "default" : "outline"}
                    onClick={() => onSelect(entry.sequence_no)}
                  >
                    Enter reading
                  </Button>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
      <CardContent className="border-t py-3 text-xs text-muted-foreground">
        <span className="font-medium">Kind</span> — Max/Min/Band transition are sourced from OIML R76-1
        Table 6 via the engine. <span className="font-medium">Fill</span> points are a deterministic,
        evenly-spaced placeholder used only when the sourced anchors fall short of the minimum load
        count, pending RRSL's confirmed convention — never present that as a mandated point.
      </CardContent>
    </Card>
  );
}
