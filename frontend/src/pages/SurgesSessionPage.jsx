import { useState } from "react";
import { FormBox, FormCheckbox, FormLine } from "@/components/oiml/FormPrimitives";
import { createDisturbanceSessionPage } from "@/pages/disturbanceSessionPageFactory";

/** Local-only (not submitted — same known gap as every other OIML form
 * header field here) "Kind or type of power supply" fields, matching page
 * 28's own DC/Other form/Voltage boxes for part (b) — the AC mains part
 * (a) has no such fields of its own on the form. */
function SurgesHeaderExtras() {
  const [kind, setKind] = useState("");
  const [isDc, setIsDc] = useState(false);
  const [otherForm, setOtherForm] = useState("");
  const [voltage, setVoltage] = useState("");

  return (
    <div className="grid gap-2 text-sm">
      <p className="text-xs italic text-neutral-600">
        (b) Any other kind of power supply — the following fields apply to part (b) only.
      </p>
      <FormLine label="Kind or type of power supply:" value={kind} editable onChange={setKind} />
      <div className="flex flex-wrap items-center gap-4">
        <FormCheckbox label="DC" checked={isDc} onClick={() => setIsDc((v) => !v)} />
        <FormBox label="Other form" value={otherForm} editable onChange={setOtherForm} width="w-32" />
        <FormBox label="Voltage" value={voltage} editable onChange={setVoltage} width="w-24" />
      </div>
    </div>
  );
}

export const SurgesSessionPage = createDisturbanceSessionPage({
  apiPath: "surges",
  title: "Surges",
  clauseLabel: "B.3.3",
  headerExtras: <SurgesHeaderExtras />,
  groupLabels: {
    a: "a) AC mains power supply — 3 positive and 3 negative surges synchronously with AC supply voltage angle",
    b: "b) Any other kind of power supply — 3 positive and 3 negative surges",
  },
});
