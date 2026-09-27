import { useState } from "react";
import { FormBox } from "@/components/oiml/FormPrimitives";
import { createDisturbanceSessionPage } from "@/pages/disturbanceSessionPageFactory";

/** Local-only header fields (not submitted, same gap as every OIML form
 * here) matching page 25's own Unom/Umin/Umax/Utest lines plus the fixed
 * test-voltage/duration figures the form prints as constants. */
function ElectricalBurstsHeaderExtras() {
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
      </div>
      <p className="text-xs text-neutral-600">
        (a) Test voltage on each connection of the mains power supply lines: 1 kV, 1 min per polarity. (b) Test
        voltage on each cable/interface (I/O, data, control lines): 0.5 kV, 1 min per polarity.
      </p>
    </div>
  );
}

export const ElectricalBurstsSessionPage = createDisturbanceSessionPage({
  apiPath: "electrical-bursts",
  title: "Electrical bursts",
  clauseLabel: "B.3.2",
  headerExtras: <ElectricalBurstsHeaderExtras />,
  groupLabels: {
    a: "a) Mains power supply lines — L = phase, N = neutral, PE = protective earth",
    b: "b) I/O circuits and communication lines (simplified to 3 generic cable/interface slots)",
  },
});
