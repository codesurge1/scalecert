import { useState } from "react";
import { FormBox, FormCheckbox } from "@/components/oiml/FormPrimitives";
import { createDisturbanceSessionPage } from "@/pages/disturbanceSessionPageFactory";

/** Local-only (not submitted) frequency-range selection (page 32's own
 * mutually-exclusive tick boxes) plus Rate of sweep / Material of load
 * boxed fields, and the form's fixed field-strength/modulation figures as
 * static text (same convention as AcMainsDips's own header extras). */
function RadiatedEmImmunityHeaderExtras() {
  const [frequencyRange, setFrequencyRange] = useState(null); // "26-2000" | "80-2000" | null
  const [rateOfSweep, setRateOfSweep] = useState("");
  const [materialOfLoad, setMaterialOfLoad] = useState("");

  return (
    <div className="grid gap-2 text-sm">
      <div className="grid gap-1">
        <FormCheckbox
          label="Frequency range 26-2000 MHz if the test according to B.3.6 cannot be applied (no mains or I/O ports available)"
          checked={frequencyRange === "26-2000"}
          onClick={() => setFrequencyRange("26-2000")}
        />
        <FormCheckbox
          label="Frequency range 80-2000 MHz if the test according to B.3.6 is performed"
          checked={frequencyRange === "80-2000"}
          onClick={() => setFrequencyRange("80-2000")}
        />
      </div>
      <div className="flex flex-wrap items-center gap-4">
        <FormBox label="Rate of sweep" value={rateOfSweep} editable onChange={setRateOfSweep} width="w-32" />
        <FormBox label="Material of load" value={materialOfLoad} editable onChange={setMaterialOfLoad} width="w-40" />
      </div>
      <p className="text-xs text-neutral-600">Field strength: 10 V/m. Modulation: 80 % AM, 1 kHz, sine wave.</p>
    </div>
  );
}

export const RadiatedEmImmunitySessionPage = createDisturbanceSessionPage({
  apiPath: "radiated-em-immunity",
  title: "Immunity to radiated electromagnetic fields",
  clauseLabel: "B.3.5",
  headerExtras: <RadiatedEmImmunityHeaderExtras />,
});
