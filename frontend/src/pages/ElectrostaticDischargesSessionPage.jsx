import { useState } from "react";
import { FormCheckbox } from "@/components/oiml/FormPrimitives";
import { createDisturbanceSessionPage } from "@/pages/disturbanceSessionPageFactory";

/** Local-only (not submitted) discharge-mode checkboxes, matching page 29's
 * own "Contact discharge / Paint penetration / Air discharges" tick-boxes. */
function ElectrostaticDischargesHeaderExtras() {
  const [modes, setModes] = useState({ contact: false, paint: false, air: false });

  function toggle(key) {
    setModes((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  return (
    <div className="flex flex-wrap items-center gap-x-8 gap-y-2 text-sm">
      <FormCheckbox label="Contact discharge" checked={modes.contact} onClick={() => toggle("contact")} />
      <FormCheckbox label="Paint penetration" checked={modes.paint} onClick={() => toggle("paint")} />
      <FormCheckbox label="Air discharges" checked={modes.air} onClick={() => toggle("air")} />
    </div>
  );
}

export const ElectrostaticDischargesSessionPage = createDisturbanceSessionPage({
  apiPath: "electrostatic-discharges",
  title: "Electrostatic discharges",
  clauseLabel: "B.3.4",
  headerExtras: <ElectrostaticDischargesHeaderExtras />,
  groupLabels: {
    a: "a) Direct application — 2/4/6 kV contact, 8 kV air discharges",
    b: "b) Indirect application (contact discharges only) — horizontal then vertical coupling plane",
  },
});
