import { useState } from "react";
import { FormBox } from "@/components/oiml/FormPrimitives";
import { createDisturbanceSessionPage } from "@/pages/disturbanceSessionPageFactory";

/** Local-only (not submitted) Rate of sweep / Load / Material of load
 * boxed fields (page 34's own three header boxes), plus the form's fixed
 * frequency-range/RF-amplitude/modulation figures as static text. */
function ConductedRfImmunityHeaderExtras() {
  const [rateOfSweep, setRateOfSweep] = useState("");
  const [load, setLoad] = useState("");
  const [materialOfLoad, setMaterialOfLoad] = useState("");

  return (
    <div className="grid gap-2 text-sm">
      <div className="flex flex-wrap items-center gap-4">
        <FormBox label="Rate of sweep" value={rateOfSweep} editable onChange={setRateOfSweep} width="w-32" />
        <FormBox label="Load" value={load} editable onChange={setLoad} width="w-28" />
        <FormBox label="Material of load" value={materialOfLoad} editable onChange={setMaterialOfLoad} width="w-40" />
      </div>
      <p className="text-xs text-neutral-600">
        Frequency range: 0.15-80 MHz. RF amplitude (50 ohms): 10 V (e.m.f.). Modulation: 80 % AM, 1 kHz, sine wave.
      </p>
    </div>
  );
}

export const ConductedRfImmunitySessionPage = createDisturbanceSessionPage({
  apiPath: "conducted-rf-immunity",
  title: "Immunity to conducted radio-frequency fields",
  clauseLabel: "B.3.6",
  headerExtras: <ConductedRfImmunityHeaderExtras />,
});
