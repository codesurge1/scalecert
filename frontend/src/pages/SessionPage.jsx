import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiFetch } from "@/lib/api";
import { useSession as useAuthSession } from "@/lib/supabase";
import { useProfile } from "@/hooks/useProfile";
import { PageHeader } from "@/components/AppShell";
import { AddTestDialog } from "@/components/session/AddTestDialog";
import { SessionLifecyclePanel } from "@/components/session/SessionLifecyclePanel";
import { SessionSummaryTable } from "@/components/session/SessionSummaryTable";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

const VERIFICATION_TYPE_LABELS = {
  initial: "Initial verification",
  subsequent: "Subsequent verification",
  in_service: "In-service verification",
};

function StatusBadge({ status }) {
  const variant = status === "draft" ? "secondary" : status === "issued" || status === "approved" ? "success" : "outline";
  return <Badge variant={variant} className="capitalize">{status}</Badge>;
}

// A single shared progress shape for every implemented test: given how many
// of `total` expected readings/positions/series-slots are in and whether
// everything submitted so far passed, derive Not started / In progress /
// Complete Pass-Fail. `total === undefined` means still loading.
function computeProgress(total, completedCount, allPassed) {
  if (total === undefined) return { status: "loading" };
  if (completedCount === 0) return { status: "not_started" };
  if (completedCount < total) return { status: "in_progress", completed: completedCount, total };
  return { status: "complete", verdict: allPassed ? "PASS" : "FAIL" };
}

/**
 * The session overview: instrument -> instrument detail -> THIS PAGE -> a
 * test page, via "Add test" (AddTestDialog) -> pick from the 7 -> that
 * test's table opens. The overview's own centerpiece is now
 * `SessionSummaryTable` (`feat/oiml-summary-overview`) — a faithful
 * reproduction of OIML R 76-2's page-9 "Summary of type evaluation" form,
 * the master ~18-clause checklist, replacing the previous ad hoc
 * seven-row app-styled table. `PROGRESS_BY_KEY` below is computed exactly
 * as before (unchanged `computeProgress` shape) and simply handed to that
 * component, which maps each of this app's seven implemented tests onto
 * its correct page-9 line and renders every other clause as a clearly
 * marked "not implemented" placeholder — see `summaryChecklist.js` for
 * the full row structure and `SessionSummaryTable.jsx` for the status
 * taxonomy. The dialog (`AddTestDialog`) remains the discovery surface
 * with the same N/A/"Coming soon" distinctions. The verification_type was
 * already chosen once, at session creation (StartVerificationDialog),
 * never re-asked here.
 *
 * No forced sequence (docs/architecture.md, RRSL-confirmed): every
 * applicable test row in the summary table is always clickable regardless
 * of any other test's status — nothing here ever reads another test's
 * status to decide a row's clickability.
 */
export function SessionPage() {
  const { id } = useParams();
  const authSession = useAuthSession();
  const profile = useProfile(authSession);

  // undefined = loading, null = load failed, object/array = loaded.
  const [session, setSession] = useState(undefined);
  const [instrument, setInstrument] = useState(undefined);
  const [weighingSequence, setWeighingSequence] = useState(undefined);
  const [weighingReadings, setWeighingReadings] = useState(undefined);
  const [zeroTareChecks, setZeroTareChecks] = useState(undefined);
  const [zeroTareReadings, setZeroTareReadings] = useState(undefined);
  const [repeatabilitySeries, setRepeatabilitySeries] = useState(undefined);
  const [eccentricityReadings, setEccentricityReadings] = useState(undefined);
  const [discriminationChecks, setDiscriminationChecks] = useState(undefined);
  const [discriminationReadings, setDiscriminationReadings] = useState(undefined);
  const [sensitivityChecks, setSensitivityChecks] = useState(undefined);
  const [sensitivityReadings, setSensitivityReadings] = useState(undefined);
  const [tiltingState, setTiltingState] = useState(undefined);
  const [voltageVariationsReadings, setVoltageVariationsReadings] = useState(undefined);
  const [acMainsDipsReadings, setAcMainsDipsReadings] = useState(undefined);
  const [electricalBurstsReadings, setElectricalBurstsReadings] = useState(undefined);
  const [electrostaticDischargesReadings, setElectrostaticDischargesReadings] = useState(undefined);
  const [surgesReadings, setSurgesReadings] = useState(undefined);
  const [radiatedEmImmunityReadings, setRadiatedEmImmunityReadings] = useState(undefined);
  const [conductedRfImmunityReadings, setConductedRfImmunityReadings] = useState(undefined);
  const [roadVehicleTransientsReadings, setRoadVehicleTransientsReadings] = useState(undefined);
  // Damp heat/Endurance (feat/damp-heat-endurance) — multi-run tests, so
  // their progress needs the run list first (from the same idempotent
  // POST .../setup the test pages themselves call) before per-run
  // readings can be fetched and summed; see the second effect below.
  const [dampHeatRuns, setDampHeatRuns] = useState(undefined);
  const [dampHeatReadingCount, setDampHeatReadingCount] = useState(undefined);
  const [dampHeatAllPassed, setDampHeatAllPassed] = useState(undefined);
  const [enduranceRuns, setEnduranceRuns] = useState(undefined);
  const [enduranceReadingCount, setEnduranceReadingCount] = useState(undefined);
  const [enduranceAllPassed, setEnduranceAllPassed] = useState(undefined);
  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setError(null);

    apiFetch(`/sessions/${id}`)
      .then((sessionData) => {
        if (cancelled) return undefined;
        setSession(sessionData);
        // Damp heat/Endurance run listing: POST .../setup auto-provisions
        // the fixed a/b/c (or a/c) runs and is draft-only (409s otherwise,
        // db/schema.sql's runs_write policy) — it may only fire when this
        // session is actually draft. A non-draft session (e.g. an approver
        // viewing a submitted session) uses the read-only GET .../runs
        // listing instead, which never creates anything and carries no
        // draft requirement (runs_select) — see docs/errors/ERROR_LOG.md.
        const isDraft = sessionData.status === "draft";
        const dampHeatRunsFetch = isDraft
          ? apiFetch(`/sessions/${id}/damp-heat/setup`, { method: "POST" })
          : apiFetch(`/sessions/${id}/damp-heat/runs`);
        const enduranceRunsFetch = isDraft
          ? apiFetch(`/sessions/${id}/endurance/setup`, { method: "POST" })
          : apiFetch(`/sessions/${id}/endurance/runs`);
        // allSettled, not all: every one of these is a secondary/optional
        // read for a specific test's progress row — one failing (network
        // blip, or a draft-only call that somehow still 409s) must never
        // blank the whole overview. Only a rejection from the primary
        // `GET /sessions/{id}` fetch above reaches the .catch() below.
        return Promise.allSettled([
          apiFetch(`/instruments/${sessionData.instrument_id}`),
          apiFetch(`/sessions/${id}/weighing/sequence`),
          apiFetch(`/sessions/${id}/weighing/readings`),
          apiFetch(`/sessions/${id}/zero-tare/checks`),
          apiFetch(`/sessions/${id}/zero-tare/readings`),
          apiFetch(`/sessions/${id}/repeatability/readings`),
          apiFetch(`/sessions/${id}/eccentricity/readings`),
          apiFetch(`/sessions/${id}/discrimination/checks`),
          apiFetch(`/sessions/${id}/discrimination/readings`),
          apiFetch(`/sessions/${id}/sensitivity/checks`),
          apiFetch(`/sessions/${id}/sensitivity/readings`),
          apiFetch(`/sessions/${id}/tilting/readings`),
          apiFetch(`/sessions/${id}/voltage-variations/readings`),
          apiFetch(`/sessions/${id}/ac-mains-dips/readings`),
          apiFetch(`/sessions/${id}/electrical-bursts/readings`),
          apiFetch(`/sessions/${id}/electrostatic-discharges/readings`),
          apiFetch(`/sessions/${id}/surges/readings`),
          apiFetch(`/sessions/${id}/radiated-em-immunity/readings`),
          apiFetch(`/sessions/${id}/conducted-rf-immunity/readings`),
          apiFetch(`/sessions/${id}/road-vehicle-transients/readings`),
          dampHeatRunsFetch,
          enduranceRunsFetch,
        ]);
      })
      .then((settledResults) => {
        if (cancelled || !settledResults) return;
        const value = (result, fallback) => (result.status === "fulfilled" ? result.value : fallback);
        const [
          instrumentData,
          sequenceData,
          weighingReadingsData,
          checksData,
          zeroTareReadingsData,
          seriesData,
          eccentricityReadingsData,
          discriminationChecksData,
          discriminationReadingsData,
          sensitivityChecksData,
          sensitivityReadingsData,
          tiltingStateData,
          voltageVariationsReadingsData,
          acMainsDipsReadingsData,
          electricalBurstsReadingsData,
          electrostaticDischargesReadingsData,
          surgesReadingsData,
          radiatedEmImmunityReadingsData,
          conductedRfImmunityReadingsData,
          roadVehicleTransientsReadingsData,
          dampHeatRunsResult,
          enduranceRunsResult,
        ] = settledResults;
        setInstrument(value(instrumentData, null));
        setWeighingSequence(value(sequenceData, []));
        setWeighingReadings(value(weighingReadingsData, []));
        setZeroTareChecks(value(checksData, []));
        setZeroTareReadings(value(zeroTareReadingsData, []));
        setRepeatabilitySeries(value(seriesData, []));
        setEccentricityReadings(value(eccentricityReadingsData, []));
        setDiscriminationChecks(value(discriminationChecksData, []));
        setDiscriminationReadings(value(discriminationReadingsData, []));
        setSensitivityChecks(value(sensitivityChecksData, []));
        setSensitivityReadings(value(sensitivityReadingsData, []));
        setTiltingState(value(tiltingStateData, null));
        setVoltageVariationsReadings(value(voltageVariationsReadingsData, []));
        setAcMainsDipsReadings(value(acMainsDipsReadingsData, []));
        setElectricalBurstsReadings(value(electricalBurstsReadingsData, []));
        setElectrostaticDischargesReadings(value(electrostaticDischargesReadingsData, []));
        setSurgesReadings(value(surgesReadingsData, []));
        setRadiatedEmImmunityReadings(value(radiatedEmImmunityReadingsData, []));
        setConductedRfImmunityReadings(value(conductedRfImmunityReadingsData, []));
        setRoadVehicleTransientsReadings(value(roadVehicleTransientsReadingsData, []));
        setDampHeatRuns(value(dampHeatRunsResult, []));
        setEnduranceRuns(value(enduranceRunsResult, []));
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message);
          setSession(null);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [id, reloadKey]);

  // Damp heat/Endurance readings, summed across their (fixed) multiple
  // runs — a second stage because it depends on the run ids the setup
  // calls above just resolved. Fetched once per run, in parallel; each
  // test's own total is `weighingSequence.length * 2 directions * its own
  // run count` — the SAME load sequence Weighing itself uses (both tests
  // reuse it verbatim, docs/architecture.md), so no separate sequence
  // fetch is needed here.
  useEffect(() => {
    if (!dampHeatRuns || dampHeatRuns.length === 0) return undefined;
    let cancelled = false;
    Promise.all(
      dampHeatRuns.map((run) => apiFetch(`/sessions/${id}/damp-heat/readings?run_id=${encodeURIComponent(run.id)}`)),
    )
      .then((perRunReadings) => {
        if (cancelled) return;
        const all = perRunReadings.flat();
        setDampHeatReadingCount(all.length);
        setDampHeatAllPassed(all.length > 0 && all.every((r) => r.passed));
      })
      .catch(() => {
        if (!cancelled) {
          setDampHeatReadingCount(0);
          setDampHeatAllPassed(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [id, dampHeatRuns]);

  useEffect(() => {
    if (!enduranceRuns || enduranceRuns.length === 0) return undefined;
    let cancelled = false;
    Promise.all(
      enduranceRuns.map((run) => apiFetch(`/sessions/${id}/endurance/readings?run_id=${encodeURIComponent(run.id)}`)),
    )
      .then((perRunReadings) => {
        if (cancelled) return;
        const all = perRunReadings.flat();
        setEnduranceReadingCount(all.length);
        setEnduranceAllPassed(all.length > 0 && all.every((r) => r.passed));
      })
      .catch(() => {
        if (!cancelled) {
          setEnduranceReadingCount(0);
          setEnduranceAllPassed(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [id, enduranceRuns]);

  const weighingProgress = useMemo(() => {
    const total = weighingSequence ? weighingSequence.length * 2 : undefined; // every load, both directions
    return computeProgress(total, weighingReadings?.length ?? 0, weighingReadings?.every((r) => r.passed));
  }, [weighingSequence, weighingReadings]);

  const zeroTareProgress = useMemo(() => {
    const total = zeroTareChecks ? zeroTareChecks.length : undefined;
    return computeProgress(total, zeroTareReadings?.length ?? 0, zeroTareReadings?.every((r) => r.passed));
  }, [zeroTareChecks, zeroTareReadings]);

  const repeatabilityProgress = useMemo(() => {
    if (!repeatabilitySeries) return { status: "loading" };
    const total = 20; // 10 readings x 2 series
    const completedCount = repeatabilitySeries.reduce((sum, s) => sum + s.readings.length, 0);
    return computeProgress(total, completedCount, repeatabilitySeries.every((s) => s.passed === true));
  }, [repeatabilitySeries]);

  const eccentricityProgress = useMemo(() => {
    const total = eccentricityReadings ? 4 : undefined;
    return computeProgress(total, eccentricityReadings?.length ?? 0, eccentricityReadings?.every((r) => r.passed));
  }, [eccentricityReadings]);

  const discriminationProgress = useMemo(() => {
    const total = discriminationChecks ? discriminationChecks.length : undefined;
    return computeProgress(total, discriminationReadings?.length ?? 0, discriminationReadings?.every((r) => r.passed));
  }, [discriminationChecks, discriminationReadings]);

  const sensitivityProgress = useMemo(() => {
    const total = sensitivityChecks ? sensitivityChecks.length : undefined;
    return computeProgress(total, sensitivityReadings?.length ?? 0, sensitivityReadings?.every((r) => r.passed));
  }, [sensitivityChecks, sensitivityReadings]);

  const tiltingProgress = useMemo(() => {
    if (!tiltingState) return { status: "loading" };
    const total = 15; // 3 phases x 5 positions
    return computeProgress(total, tiltingState.readings.length, tiltingState.passed === true);
  }, [tiltingState]);

  // The four disturbance/voltage-variation tests each have a FIXED
  // condition-list length (never instrument-dependent, unlike Sensitivity's
  // checks) — same "hardcode the known total" convention Repeatability
  // (20) and Tilting (15) already use, matching the counts
  // app/services/disturbance.py's own condition lists produce.
  const voltageVariationsProgress = useMemo(() => {
    const total = voltageVariationsReadings ? 3 : undefined; // reference/lower/upper
    return computeProgress(total, voltageVariationsReadings?.length ?? 0, voltageVariationsReadings?.every((r) => r.passed));
  }, [voltageVariationsReadings]);

  const acMainsDipsProgress = useMemo(() => {
    const total = acMainsDipsReadings ? 7 : undefined; // baseline + 6 conditions
    return computeProgress(total, acMainsDipsReadings?.length ?? 0, acMainsDipsReadings?.every((r) => r.passed));
  }, [acMainsDipsReadings]);

  const electricalBurstsProgress = useMemo(() => {
    const total = electricalBurstsReadings ? 18 : undefined; // 9 (a) + 9 (b, 3 slots)
    return computeProgress(total, electricalBurstsReadings?.length ?? 0, electricalBurstsReadings?.every((r) => r.passed));
  }, [electricalBurstsReadings]);

  const electrostaticDischargesProgress = useMemo(() => {
    const total = electrostaticDischargesReadings ? 26 : undefined; // 10 (a) + 16 (b, 2 planes)
    return computeProgress(
      total,
      electrostaticDischargesReadings?.length ?? 0,
      electrostaticDischargesReadings?.every((r) => r.passed),
    );
  }, [electrostaticDischargesReadings]);

  // feat/remaining-disturbance-forms — same fixed-total convention as the
  // three disturbance tests above; totals match each test's own condition
  // list length in app/services/disturbance.py (never instrument-dependent).
  const surgesProgress = useMemo(() => {
    const total = surgesReadings ? 36 : undefined; // 27 (a) + 9 (b)
    return computeProgress(total, surgesReadings?.length ?? 0, surgesReadings?.every((r) => r.passed));
  }, [surgesReadings]);

  const radiatedEmImmunityProgress = useMemo(() => {
    const total = radiatedEmImmunityReadings ? 9 : undefined; // 1 baseline + 2 polarizations x 4 facings
    return computeProgress(
      total,
      radiatedEmImmunityReadings?.length ?? 0,
      radiatedEmImmunityReadings?.every((r) => r.passed),
    );
  }, [radiatedEmImmunityReadings]);

  const conductedRfImmunityProgress = useMemo(() => {
    const total = conductedRfImmunityReadings ? 6 : undefined; // 3 slots x (baseline + sweep)
    return computeProgress(
      total,
      conductedRfImmunityReadings?.length ?? 0,
      conductedRfImmunityReadings?.every((r) => r.passed),
    );
  }, [conductedRfImmunityReadings]);

  const roadVehicleTransientsProgress = useMemo(() => {
    const total = roadVehicleTransientsReadings ? 30 : undefined; // 12 (a) + 18 (b, 3 slots x 2 batteries)
    return computeProgress(
      total,
      roadVehicleTransientsReadings?.length ?? 0,
      roadVehicleTransientsReadings?.every((r) => r.passed),
    );
  }, [roadVehicleTransientsReadings]);

  // Damp heat (3 runs) / Endurance (2 runs) — both reuse the exact same
  // Weighing load sequence (feat/damp-heat-endurance), so `total` is that
  // sequence's own length x2 directions x however many runs this test has.
  const dampHeatProgress = useMemo(() => {
    const total = weighingSequence && dampHeatRuns ? weighingSequence.length * 2 * dampHeatRuns.length : undefined;
    return computeProgress(total, dampHeatReadingCount ?? 0, dampHeatAllPassed);
  }, [weighingSequence, dampHeatRuns, dampHeatReadingCount, dampHeatAllPassed]);

  const enduranceProgress = useMemo(() => {
    const total = weighingSequence && enduranceRuns ? weighingSequence.length * 2 * enduranceRuns.length : undefined;
    return computeProgress(total, enduranceReadingCount ?? 0, enduranceAllPassed);
  }, [weighingSequence, enduranceRuns, enduranceReadingCount, enduranceAllPassed]);

  const PROGRESS_BY_KEY = {
    weighing: weighingProgress,
    zero_tare: zeroTareProgress,
    repeatability: repeatabilityProgress,
    eccentricity: eccentricityProgress,
    discrimination: discriminationProgress,
    sensitivity: sensitivityProgress,
    tilting: tiltingProgress,
    voltage_variations: voltageVariationsProgress,
    ac_mains_dips: acMainsDipsProgress,
    electrical_bursts: electricalBurstsProgress,
    electrostatic_discharges: electrostaticDischargesProgress,
    surges: surgesProgress,
    radiated_em_immunity: radiatedEmImmunityProgress,
    conducted_rf_immunity: conductedRfImmunityProgress,
    road_vehicle_transients: roadVehicleTransientsProgress,
    damp_heat: dampHeatProgress,
    endurance: enduranceProgress,
  };

  // Submit-for-review is only meaningfully offered once at least one test
  // has SOME recorded progress — the server is the actual source of truth
  // (409 "no test has recorded" otherwise, app/services/sessions.py), this
  // is just a friendlier disabled state instead of a round-trip error.
  const hasAnyProgress = Object.values(PROGRESS_BY_KEY).some(
    (p) => p.status === "in_progress" || p.status === "complete",
  );
  const canSubmit = hasAnyProgress;
  const submitBlockedReason = "Complete at least one test before submitting for review.";

  if (session === undefined) {
    return (
      <div>
        <PageHeader title="Session overview" />
        <div className="space-y-3">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      </div>
    );
  }

  if (session === null) {
    return (
      <div>
        <PageHeader title="Session overview" />
        <Card className="border-destructive/50 bg-destructive/5">
          <CardContent className="flex items-center justify-between py-4 text-sm text-destructive">
            <span>Couldn't load this session: {error}</span>
            <Button variant="outline" size="sm" onClick={() => setReloadKey((key) => key + 1)}>
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="grid gap-6">
      <div>
        <Link
          to={`/instruments/${session.instrument_id}`}
          className="text-sm text-muted-foreground hover:text-foreground hover:underline"
        >
          &larr; {instrument === undefined ? "Instrument" : instrument?.type_designation || "Instrument"}
        </Link>
        <PageHeader
          title="Session overview"
          description={VERIFICATION_TYPE_LABELS[session.verification_type] ?? session.verification_type}
          actions={instrument === undefined ? null : <AddTestDialog sessionId={id} instrument={instrument} />}
        />
      </div>

      <Card>
        <CardContent className="grid grid-cols-2 gap-4 py-4 sm:grid-cols-4">
          <div>
            <div className="text-xs text-muted-foreground">Instrument</div>
            <div className="text-sm font-medium">
              {instrument === undefined ? (
                <Skeleton className="h-4 w-24" />
              ) : (
                instrument?.type_designation || instrument?.model || "—"
              )}
            </div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">Class / e / Max</div>
            <div className="text-sm font-medium">
              {instrument === undefined ? (
                <Skeleton className="h-4 w-24" />
              ) : (
                `Class ${instrument.accuracy_class} · e=${instrument.e_value}g · Max=${instrument.max_capacity}g`
              )}
            </div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">Status</div>
            <div className="mt-0.5">
              <StatusBadge status={session.status} />
            </div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">Verification type</div>
            <div className="text-sm font-medium">
              {VERIFICATION_TYPE_LABELS[session.verification_type] ?? session.verification_type}
            </div>
          </div>
        </CardContent>
      </Card>

      {profile ? (
        <SessionLifecyclePanel
          session={session}
          profile={profile}
          canSubmit={canSubmit}
          submitBlockedReason={submitBlockedReason}
          onChanged={(updated) => setSession(updated)}
        />
      ) : null}

      {instrument === undefined ? (
        <Skeleton className="h-96 w-full" />
      ) : (
        <SessionSummaryTable sessionId={id} instrument={instrument} progressByKey={PROGRESS_BY_KEY} />
      )}
    </div>
  );
}
