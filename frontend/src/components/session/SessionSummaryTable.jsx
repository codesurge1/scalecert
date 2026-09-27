import { Fragment, useState } from "react";
import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";
import { FormCheckbox, FormLine } from "@/components/oiml/FormPrimitives";
import { TEST_ROWS } from "@/lib/testChecklist";
import { SUMMARY_ROWS } from "@/lib/summaryChecklist";

const TEST_ROWS_BY_KEY = Object.fromEntries(TEST_ROWS.map((row) => [row.key, row]));

function fmt(value) {
  return value === undefined || value === null || value === "" ? "" : value;
}

// A leaf row's clickable label — implemented + applicable (regardless of
// not-started/in-progress/complete, per docs/architecture.md's "no forced
// sequence" rule) is the ONLY clickable state; N/A and not-implemented are
// plain text. `naReason` mirrors the exact same instrument-driven check
// `SessionPage`/`AddTestDialog` already use (`row.naReason(instrument)`),
// not a new rule.
function RowLabel({ sub, instrument, sessionId }) {
  if (sub.placeholder) {
    return <span className="text-neutral-400">{sub.label}</span>;
  }
  const testRow = TEST_ROWS_BY_KEY[sub.testKey];
  const naReason = instrument && testRow?.naReason ? testRow.naReason(instrument) : null;
  if (naReason) {
    return <span className="text-neutral-500">{sub.label}</span>;
  }
  return (
    <Link to={testRow.route(sessionId)} className="text-primary hover:underline">
      {sub.label}
      {sub.appAddition ? <span className="ml-1.5 text-[10px] italic text-neutral-500">(app addition — A.4.4 variant, not on the printed form)</span> : null}
    </Link>
  );
}

// The four data columns (Report page / PASSED / FAILED / Remarks) for one
// leaf row — three shapes, matching CLAUDE.md's status taxonomy exactly:
// not-implemented (this app never built that clause), N/A (the "– –"
// convention, an instrument-driven exclusion — never a placeholder), and
// implemented (real PASSED/FAILED ticks driven by the same
// `computeProgress` result `SessionPage` already derives, with a plain
// "Not started"/"In progress" remark when there's no verdict yet).
function StatusCells({ sub, instrument, progressByKey }) {
  if (sub.placeholder) {
    return (
      <>
        <td className="border border-neutral-900 bg-neutral-50 px-2 py-1 text-center text-neutral-400">—</td>
        <td className="border border-neutral-900 bg-neutral-50 px-2 py-1 text-center text-neutral-400">—</td>
        <td className="border border-neutral-900 bg-neutral-50 px-2 py-1 text-center text-neutral-400">—</td>
        <td className="border border-neutral-900 bg-neutral-50 px-2 py-1 text-[11px] italic text-neutral-400">
          Not implemented
        </td>
      </>
    );
  }

  const testRow = TEST_ROWS_BY_KEY[sub.testKey];
  const naReason = instrument && testRow?.naReason ? testRow.naReason(instrument) : null;

  if (naReason) {
    return (
      <>
        <td className="border border-neutral-900 px-2 py-1 text-center text-neutral-500">&ndash; &ndash;</td>
        <td className="border border-neutral-900 px-2 py-1 text-center text-neutral-500">&ndash; &ndash;</td>
        <td className="border border-neutral-900 px-2 py-1 text-center text-neutral-500">&ndash; &ndash;</td>
        <td className="border border-neutral-900 px-2 py-1 text-[11px] text-neutral-600">{naReason}</td>
      </>
    );
  }

  const progress = progressByKey[sub.testKey] ?? { status: "loading" };
  const passed = progress.status === "complete" && progress.verdict === "PASS";
  const failed = progress.status === "complete" && progress.verdict === "FAIL";
  const remark =
    progress.status === "not_started"
      ? "Not started"
      : progress.status === "in_progress"
        ? `In progress (${progress.completed}/${progress.total})`
        : "";

  return (
    <>
      <td className="border border-neutral-900 px-2 py-1" />
      <td className="border border-neutral-900 px-2 py-1 text-center">
        <FormCheckbox checked={passed} readOnly />
      </td>
      <td className="border border-neutral-900 px-2 py-1 text-center">
        <FormCheckbox checked={failed} readOnly />
      </td>
      <td className="border border-neutral-900 px-2 py-1 text-[11px] text-neutral-600">{remark}</td>
    </>
  );
}

function SummaryRowGroup({ group, instrument, progressByKey, sessionId }) {
  if (group.sectionHeader) {
    return (
      <tr className="bg-neutral-100">
        <td className="border border-neutral-900 px-2 py-1" />
        <td colSpan={2} className="border border-neutral-900 px-2 py-1 font-bold">
          {group.sectionHeader}
        </td>
        <td className="border border-neutral-900" />
        <td className="border border-neutral-900" />
        <td className="border border-neutral-900" />
        <td className="border border-neutral-900" />
      </tr>
    );
  }

  const isGrouped = Boolean(group.subRows);
  const subRows = group.subRows ?? [group];

  return (
    <>
      {subRows.map((sub, subIdx) => (
        <tr key={subIdx} className={cn(sub.appAddition && "bg-amber-50/60")}>
          {subIdx === 0 ? (
            <td
              rowSpan={subRows.length}
              className="border border-neutral-900 px-2 py-1 text-center align-top font-bold"
            >
              {group.number}
            </td>
          ) : null}
          {isGrouped ? (
            <>
              {subIdx === 0 ? (
                <td rowSpan={subRows.length} className="border border-neutral-900 px-2 py-1 align-top">
                  {group.label}
                </td>
              ) : null}
              <td className="border border-neutral-900 px-2 py-1">
                <RowLabel sub={sub} instrument={instrument} sessionId={sessionId} />
              </td>
            </>
          ) : (
            <td colSpan={2} className="border border-neutral-900 px-2 py-1">
              <RowLabel sub={sub} instrument={instrument} sessionId={sessionId} />
            </td>
          )}
          <StatusCells sub={sub} instrument={instrument} progressByKey={progressByKey} />
        </tr>
      ))}
    </>
  );
}

/**
 * The session overview's centerpiece — a faithful reproduction of OIML
 * R 76-2's page-9 "Summary of type evaluation" form, the master ~18-clause
 * checklist with Report page / PASSED / FAILED / Remarks columns, read as
 * a rendered image (`pdftoppm`, same method as every other OIML-form
 * component) to match its exact numbering and row grouping. This is a
 * faithful reproduction of the FORM'S LAYOUT for data-entry fidelity, not
 * a copy of the copyrighted OIML document itself — no OIML explanatory
 * text beyond the form's own row labels and structural chrome.
 *
 * Every leaf row is one of exactly three states (see `summaryChecklist.js`
 * for the full reasoning): an implemented, applicable test (clickable,
 * live PASSED/FAILED ticks driven by the SAME `progressByKey` shape
 * `SessionPage` has always computed via `computeProgress` — no new
 * status logic here, just a different table to render it into); N/A (the
 * form's own "– –" convention, driven by the exact same
 * `TEST_ROWS[*].naReason(instrument)` check `SessionPage`/`AddTestDialog`
 * already use); or not-implemented (a real OIML clause this app has never
 * built an engine/form for — CLAUDE.md's scope guardrail — greyed and
 * explicitly labeled "Not implemented," never conflated with "Not
 * started," which is reserved for an implemented test with no data yet).
 *
 * `max-h-[60vh] overflow-y-auto` + `sticky top-0` thead on the table's own
 * wrapper — the same internal-scroll-region pattern
 * `fix/vertical-fit-no-page-scroll` established for the Weighing table —
 * so a ~40-row checklist doesn't force the whole page (breadcrumb, summary
 * card, lifecycle panel, Add-test button) out of view on a short viewport;
 * this page still lives in `AppShell` (sidebar visible, normal page
 * scroll), so this is a usability nicety on the table itself, not the
 * full height-constrained/no-page-scroll treatment `FocusedShell` pages
 * got — that treatment is specific to the sidebar-free entry workstation,
 * not this browsing/overview screen.
 */
export function SessionSummaryTable({ sessionId, instrument, progressByKey }) {
  const [remarks, setRemarks] = useState("");

  return (
    <div className="mx-auto w-full max-w-5xl border-2 border-neutral-900 bg-white p-4 font-serif text-neutral-900 sm:p-6">
      <div className="mb-4 flex items-baseline justify-between border-b border-neutral-900 pb-1 text-xs">
        <span>OIML R 76-2: 2007 (E)</span>
        <span>Report page &hellip;./&hellip;.</span>
      </div>

      <h2 className="text-center text-lg font-bold">Summary of type evaluation</h2>

      <div className="mt-4 grid gap-1 text-sm">
        <FormLine label="Application no.:" value={fmt(instrument?.application_no)} />
        <FormLine label="Type designation:" value={fmt(instrument?.type_designation)} />
      </div>

      <div className="mt-4 max-h-[60vh] overflow-y-auto">
        <table className="w-full min-w-[720px] border-collapse text-xs">
          <thead className="sticky top-0 z-10 bg-white">
            <tr>
              <th className="border border-neutral-900 px-2 py-1" />
              <th colSpan={2} className="border border-neutral-900 px-2 py-1">
                Tests
              </th>
              <th className="border border-neutral-900 px-2 py-1">Report page</th>
              <th className="border border-neutral-900 px-2 py-1">PASSED</th>
              <th className="border border-neutral-900 px-2 py-1">FAILED</th>
              <th className="border border-neutral-900 px-2 py-1">Remarks</th>
            </tr>
          </thead>
          <tbody>
            {SUMMARY_ROWS.map((group, idx) => (
              <Fragment key={group.number ?? group.sectionHeader ?? idx}>
                <SummaryRowGroup group={group} instrument={instrument} progressByKey={progressByKey} sessionId={sessionId} />
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-4">
        <p className="text-sm">Remarks:</p>
        <textarea
          className="mt-1 min-h-14 w-full border border-neutral-900 bg-transparent px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-inset focus:ring-neutral-900"
          value={remarks}
          onChange={(event) => setRemarks(event.target.value)}
        />
      </div>

      <p className="mt-3 text-xs text-muted-foreground">
        Reproduced for data-entry fidelity to OIML R 76-2's page-9 "Summary of type evaluation" form — not a copy
        of the copyrighted OIML document itself. Only the seven clause 8.3.3 items this app implements
        (Weighing/Zero-tare, Repeatability, Eccentricity, Discrimination, Sensitivity, Tilting) carry live status;
        every other line is a real OIML clause this app has not built — greyed and marked "Not implemented," never
        "Not started." The bottom Remarks field is local to this page only, same known gap as every other OIML
        form here (no session-update endpoint yet — docs/architecture.md).
      </p>
    </div>
  );
}
