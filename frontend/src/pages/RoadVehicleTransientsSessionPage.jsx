import { useState } from "react";
import { FormBox, FormCheckbox } from "@/components/oiml/FormPrimitives";
import { createDisturbanceSessionPage } from "@/pages/disturbanceSessionPageFactory";

/** Local-only (not submitted) 12V/24V battery-voltage indicator checkboxes
 * (pages 35/36's own pair, both batteries are always tested/recorded in
 * this app's condition list regardless of which is ticked here — see
 * app/services/disturbance.py's module comment) and the "Kind or type of
 * other lines" field part (b) asks for. */
function RoadVehicleTransientsHeaderExtras() {
  const [battery, setBattery] = useState(null); // "12v" | "24v" | null
  const [otherLinesKind, setOtherLinesKind] = useState("");

  return (
    <div className="grid gap-2 text-sm">
      <div className="flex flex-wrap items-center gap-6">
        <FormCheckbox label="12 V battery voltage" checked={battery === "12v"} onClick={() => setBattery("12v")} />
        <FormCheckbox label="24 V battery voltage" checked={battery === "24v"} onClick={() => setBattery("24v")} />
      </div>
      <FormBox
        label="Kind or type of other lines (no power supply lines, part b)"
        value={otherLinesKind}
        editable
        onChange={setOtherLinesKind}
        width="w-64"
      />
    </div>
  );
}

export const RoadVehicleTransientsSessionPage = createDisturbanceSessionPage({
  apiPath: "road-vehicle-transients",
  title: "Electrical transients on instruments powered from a road vehicle power supply",
  clauseLabel: "B.3.7",
  headerExtras: <RoadVehicleTransientsHeaderExtras />,
  groupLabels: {
    a: "a) Conduction along supply lines of external 12 V and 24 V batteries",
    b: "b) Capacitive and inductive coupling via lines other than supply lines",
  },
});
