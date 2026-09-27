import { useState } from "react";
import { FormBox } from "@/components/oiml/FormPrimitives";
import { createDisturbanceSessionPage } from "@/pages/disturbanceSessionPageFactory";

/** Local-only (not submitted — same known gap as every other OIML form
 * header field here) Unom/Umin/Umax + Utest fields, matching page 24's own
 * "Mains power supply voltage" / "Power supply voltage for the test"
 * lines. */
function AcMainsDipsHeaderExtras() {
  const [uNom, setUNom] = useState("");
  const [uMin, setUMin] = useState("");
  const [uMax, setUMax] = useState("");
  const [uTest, setUTest] = useState("");

  return (
    <div className="grid gap-2 text-sm">
      <div className="flex flex-wrap items-center gap-4">
        <span className="text-neutral-700">Mains power supply voltage:</span>
        <FormBox label="Unom" value={uNom} unit="V" editable onChange={setUNom} width="w-24" />
        <FormBox label="Umin" value={uMin} unit="V" editable onChange={setUMin} width="w-24" />
        <FormBox label="Umax" value={uMax} unit="V" editable onChange={setUMax} width="w-24" />
      </div>
      <div className="flex flex-wrap items-baseline gap-2">
        <span className="text-neutral-700">Power supply voltage for the test:</span>
        <FormBox label="Utest" value={uTest} unit="V" editable onChange={setUTest} width="w-24" />
        <span className="text-xs text-neutral-600">= Unom or the average value of Umin and Umax</span>
      </div>
    </div>
  );
}

export const AcMainsDipsSessionPage = createDisturbanceSessionPage({
  apiPath: "ac-mains-dips",
  title: "AC mains voltage dips and short interruptions",
  clauseLabel: "B.3.1",
  headerExtras: <AcMainsDipsHeaderExtras />,
});
