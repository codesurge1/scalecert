import { useMemo } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { apiFetch } from "@/lib/api";
import { classifyInstrument } from "@/lib/accuracyClass";
import { PageHeader } from "@/components/AppShell";
import { Button } from "@/components/ui/button";
import { FormBox, FormCheckbox, FormLine } from "@/components/oiml/FormPrimitives";

const ACCURACY_CLASSES = ["I", "II", "III", "IIII"];

// "Self/semi-self/non-self-indicating" (the form's own line) maps directly
// onto the existing indication_type enum (digital/analog/non_self_indicating)
// — no new column; only the labels shown here are the form's own wording.
const INDICATION_OPTIONS = [
  { value: "digital", label: "Self-indicating" },
  { value: "analog", label: "Semi-self-indicating" },
  { value: "non_self_indicating", label: "Non-self-indicating" },
];

const ZERO_DEVICE_OPTIONS = [
  { value: "non_automatic", label: "Non-automatic" },
  { value: "semi_automatic", label: "Semi-automatic" },
  { value: "automatic_zero_setting", label: "Automatic zero-setting" },
  { value: "initial_zero_setting", label: "Initial zero-setting" },
  { value: "zero_tracking", label: "Zero-tracking" },
];

const TARE_DEVICE_OPTIONS = [
  { value: "tare_balancing", label: "Tare balancing" },
  { value: "tare_weighing", label: "Tare weighing" },
  { value: "preset_tare_device", label: "Preset tare device" },
  { value: "subtractive_tare", label: "Subtractive tare" },
  { value: "additive_tare", label: "Additive tare" },
];

const COMBINED_ZERO_TARE = { value: "combined_zero_tare_device", label: "Combined zero/tare device" };

const PRINTER_OPTIONS = [
  { value: "built_in", label: "Built-in" },
  { value: "connected", label: "Connected" },
  { value: "not_present", label: "Not present but connectable" },
  { value: "no_connection", label: "No connection" },
];

const DEFAULT_VALUES = {
  application_no: "",
  type_designation: "",
  manufacturer: "",
  applicant: "",
  instrument_category: "",
  model: "",
  serial_number: "",
  indication_type: "digital",
  e_value: "",
  d_value: "",
  max_capacity: "",
  min_capacity: "",
  accuracy_class_choice: "",
  temperature_range_min: "",
  temperature_range_max: "",
  u_nom: "",
  u_min: "",
  u_max: "",
  mains_frequency: "",
  battery_u_nom: "",
  zero_device_type: "",
  tare_device_type: "",
  initial_zero_setting_range_pct: "",
  printer_status: "",
  identification_no: "",
  software_version: "",
  interfaces: "",
  load_cell_manufacturer: "",
  load_cell_type: "",
  load_cell_capacity: "",
  load_cell_number: "",
  load_cell_class_symbol: "",
  is_mobile: false,
  is_multi_interval: false,
};

// Renders the backend's validation error (Pydantic 422: {"detail": [...]})
// or a plain-string error (e.g. a 409/500/422 {"detail": "..."} — this
// screen's own classify-rejection 422s come back this way) as readable text.
function formatApiError(err) {
  const detail = err?.body?.detail;
  if (Array.isArray(detail)) {
    return detail.map((issue) => `${issue.loc?.slice(-1)[0] ?? "field"}: ${issue.msg}`).join("; ");
  }
  if (typeof detail === "string") return detail;
  return err?.message ?? "Something went wrong.";
}

/** One of a set of mutually-exclusive FormCheckbox options, bound to a
 * single RHF field via watch/setValue rather than a native <select> — the
 * form's own tick-box vocabulary, not an app dropdown. */
function CheckboxGroup({ options, value, onChange, disabled }) {
  return (
    <div className="grid gap-1.5">
      {options.map((option) => (
        <FormCheckbox
          key={option.value}
          label={option.label}
          checked={value === option.value}
          disabled={disabled}
          onClick={() => !disabled && onChange(option.value)}
        />
      ))}
    </div>
  );
}

/**
 * Instrument registration as the OIML R 76-2 page-6 "General information
 * concerning the type" form — a faithful reproduction of that form's
 * layout (bordered document sheet, dotted fill-in lines, boxed numeric
 * fields, tick-box option groups), the registration-screen equivalent of
 * WeighingFormTable's page-10 reproduction. This is fidelity to the FORM'S
 * LAYOUT for data-entry purposes, not a copy of the copyrighted OIML
 * document itself — no OIML explanatory/normative text beyond the form's
 * own field labels and structural chrome.
 *
 * Accuracy class is NEVER a free choice — same rule as before, unchanged:
 * derived from e/Max/Min per OIML R76-1 Table 3 (engine/classification.py,
 * mirrored client-side in src/lib/accuracyClass.js for instant feedback;
 * the real POST re-derives it server-side and is authoritative). Here the
 * derived class is shown as an auto-ticked box among the form's own four
 * accuracy-class boxes (I / II / III / IIII) rather than a badge — when
 * more than one class qualifies, only the qualifying boxes become
 * clickable; when none does, every box stays unticked and the reason is
 * shown below in red, submit disabled.
 *
 * Many page-6 fields have no schema column yet (module/error-fraction
 * testing, multi-interval sub-ranges, "Instrument submitted"/"Connected
 * equipment"/evaluation period/date of report/observer/remarks — see
 * docs/architecture.md) — those are rendered as blank, read-only form
 * lines/boxes for full layout fidelity (exactly what an unfilled paper
 * form looks like), never as misleadingly-interactive disabled inputs.
 * `model`/`serial_number`/`is_mobile`/`is_multi_interval` aren't on page 6
 * at all but are kept as small additions beneath the identity block since
 * the app already depends on them (instrument identity and the
 * conditional-test gating in the session overview).
 */
export function InstrumentRegisterPage() {
  const navigate = useNavigate();
  const form = useForm({ defaultValues: DEFAULT_VALUES });

  const [
    eValue,
    dValue,
    maxCapacity,
    minCapacity,
    accuracyClassChoice,
    indicationType,
    zeroDeviceType,
    tareDeviceType,
    printerStatus,
    temperatureRangeMin,
    temperatureRangeMax,
  ] = form.watch([
    "e_value",
    "d_value",
    "max_capacity",
    "min_capacity",
    "accuracy_class_choice",
    "indication_type",
    "zero_device_type",
    "tare_device_type",
    "printer_status",
    "temperature_range_min",
    "temperature_range_max",
  ]);

  const classification = useMemo(
    () => classifyInstrument({ e: eValue, maxCapacity, minCapacity, d: dValue }),
    [eValue, maxCapacity, minCapacity, dValue],
  );

  const hasAllThree = eValue && maxCapacity && minCapacity;
  const isAmbiguous = classification.qualifiedClasses.length > 1;
  const isInvalid = hasAllThree && classification.reason && classification.qualifiedClasses.length === 0;
  const resolvedClass = isAmbiguous ? accuracyClassChoice || null : classification.qualifiedClasses[0] ?? null;
  const canSubmit = hasAllThree && !isInvalid && (!isAmbiguous || Boolean(resolvedClass));

  async function onSubmit(values) {
    // Decimal-as-string discipline (CLAUDE.md, backend StrictDecimal
    // contract): every numeric field below is read straight from
    // react-hook-form's string state and sent as-is — never through
    // Number()/parseFloat(). Optional numeric/text fields send `null` when
    // blank, not an empty string, matching the contract.
    const blank = (value) => (value == null || value.trim() === "" ? null : value);

    const payload = {
      application_no: blank(values.application_no),
      type_designation: blank(values.type_designation),
      manufacturer: blank(values.manufacturer),
      model: blank(values.model),
      serial_number: blank(values.serial_number),
      applicant: blank(values.applicant),
      instrument_category: blank(values.instrument_category),
      indication_type: values.indication_type,
      e_value: values.e_value,
      d_value: blank(values.d_value),
      max_capacity: values.max_capacity,
      min_capacity: values.min_capacity,
      // accuracy_class is only ever sent to disambiguate when e/Max/Min
      // qualify for more than one class — otherwise omitted entirely and
      // left to the server's own derivation (engine.classification).
      accuracy_class: isAmbiguous ? resolvedClass : null,
      is_mobile: values.is_mobile,
      is_multi_interval: values.is_multi_interval,
      temperature_range_min: blank(values.temperature_range_min),
      temperature_range_max: blank(values.temperature_range_max),
      u_nom: blank(values.u_nom),
      u_min: blank(values.u_min),
      u_max: blank(values.u_max),
      mains_frequency: blank(values.mains_frequency),
      battery_u_nom: blank(values.battery_u_nom),
      zero_device_type: blank(values.zero_device_type),
      tare_device_type: blank(values.tare_device_type),
      initial_zero_setting_range_pct: blank(values.initial_zero_setting_range_pct),
      printer_status: blank(values.printer_status),
      identification_no: blank(values.identification_no),
      software_version: blank(values.software_version),
      interfaces: blank(values.interfaces),
      load_cell_manufacturer: blank(values.load_cell_manufacturer),
      load_cell_type: blank(values.load_cell_type),
      load_cell_capacity: blank(values.load_cell_capacity),
      load_cell_number: blank(values.load_cell_number),
      load_cell_class_symbol: blank(values.load_cell_class_symbol),
    };

    try {
      const instrument = await apiFetch("/instruments", { method: "POST", body: payload });
      toast.success(`Instrument registered — Class ${instrument.accuracy_class} (${instrument.type_designation || instrument.id}).`);
      navigate("/instruments");
    } catch (err) {
      form.setError("root", { message: formatApiError(err) });
    }
  }

  const rootError = form.formState.errors.root?.message;

  return (
    <div className="grid gap-4">
      <PageHeader title="Register instrument" description="OIML R 76-2 page-6 general information form." />

      <form onSubmit={form.handleSubmit(onSubmit)} className="grid gap-4">
        <div className="mx-auto w-full max-w-4xl border-2 border-neutral-900 bg-white p-6 font-serif text-neutral-900 sm:p-8">
          <div className="mb-4 flex items-baseline justify-between border-b border-neutral-900 pb-1 text-xs">
            <span>OIML R 76-2: 2007 (E)</span>
            <span>Report page &hellip;./&hellip;.</span>
          </div>

          <h2 className="text-center text-lg font-bold">General information concerning the type</h2>

          <div className="mt-6 grid gap-1.5 text-sm">
            <FormLine label="Application no.:" value={form.watch("application_no")} editable onChange={(v) => form.setValue("application_no", v)} />
            <FormLine label="Type designation:" value={form.watch("type_designation")} editable onChange={(v) => form.setValue("type_designation", v)} />
            <FormLine label="Manufacturer:" value={form.watch("manufacturer")} editable onChange={(v) => form.setValue("manufacturer", v)} />
            <FormLine label="Applicant:" value={form.watch("applicant")} editable onChange={(v) => form.setValue("applicant", v)} />
            <FormLine label="Instrument category:" value={form.watch("instrument_category")} editable onChange={(v) => form.setValue("instrument_category", v)} />
            {/* Not on page 6 itself, but the app already relies on these
                two for instrument identity — kept as a small addition. */}
            <FormLine label="Model:" value={form.watch("model")} editable onChange={(v) => form.setValue("model", v)} />
            <FormLine label="Serial number:" value={form.watch("serial_number")} editable onChange={(v) => form.setValue("serial_number", v)} />
          </div>

          <div className="mt-5 flex flex-wrap items-center gap-x-8 gap-y-2 text-sm">
            <FormCheckbox label="Complete instrument" checked={false} readOnly />
            <span className="flex items-center gap-2">
              <FormCheckbox label={<>Module<sup>1</sup> with</>} checked={false} readOnly />
              <FormBox label="error fraction pᵢ" value="" width="w-16" />
            </span>
          </div>

          <div className="mt-5">
            <div className="mb-2 text-sm">
              Accuracy class<sup>2</sup>:
            </div>
            <div className="flex flex-wrap gap-x-10 gap-y-2">
              {ACCURACY_CLASSES.map((cls) => {
                const isQualified = classification.qualifiedClasses.includes(cls);
                const selectable = isAmbiguous && isQualified;
                const isTicked = hasAllThree && !isInvalid && (isAmbiguous ? accuracyClassChoice === cls : classification.qualifiedClasses[0] === cls);
                return (
                  <FormCheckbox
                    key={cls}
                    checked={isTicked}
                    readOnly={!selectable}
                    disabled={!selectable}
                    onClick={() => selectable && form.setValue("accuracy_class_choice", cls)}
                    label={
                      <span className="inline-flex h-6 w-9 items-center justify-center rounded-full border border-neutral-900 text-xs font-semibold">
                        {cls}
                      </span>
                    }
                  />
                );
              })}
            </div>
            <p className="mt-2 text-xs text-neutral-600">
              Derived from e / Max / Min (OIML R76-1 Table 3) — never chosen freely.
              {hasAllThree && classification.n != null ? ` n = ${classification.n}.` : ""}
            </p>
            {!hasAllThree ? (
              <p className="mt-1 text-xs text-neutral-600">Fill in Min, e, and Max below to derive the class.</p>
            ) : isInvalid ? (
              <p className="mt-1 text-sm font-medium text-destructive">{classification.reason}</p>
            ) : isAmbiguous ? (
              <p className="mt-1 text-sm">These values qualify for more than one class — tick one above.</p>
            ) : null}
          </div>

          <div className="mt-5 flex flex-wrap gap-x-10 gap-y-2 text-sm">
            <CheckboxGroup
              options={INDICATION_OPTIONS}
              value={indicationType}
              onChange={(v) => form.setValue("indication_type", v)}
            />
          </div>

          {/* Not on page 6 — kept because the session overview's
              conditional-test gating (Tilting/Sensitivity) depends on them. */}
          <div className="mt-3 flex gap-6 text-sm">
            <label className="flex items-center gap-2">
              <input type="checkbox" className="size-4 rounded border-input accent-primary" {...form.register("is_mobile")} />
              Mobile instrument
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" className="size-4 rounded border-input accent-primary" {...form.register("is_multi_interval")} />
              Multi-interval instrument
            </label>
          </div>

          <div className="mt-5 grid gap-2 text-sm">
            <FormBox label="Min" value={form.watch("min_capacity")} editable width="w-28" onChange={(v) => form.setValue("min_capacity", v)} />
            <div className="flex flex-wrap gap-x-8 gap-y-2">
              <FormBox label="e" value={form.watch("e_value")} editable width="w-28" onChange={(v) => form.setValue("e_value", v)} />
              <FormBox label="Max" value={form.watch("max_capacity")} editable width="w-28" onChange={(v) => form.setValue("max_capacity", v)} />
              <FormBox label="d" value={form.watch("d_value")} editable width="w-28" onChange={(v) => form.setValue("d_value", v)} />
              <FormBox label="n" value={hasAllThree ? String(classification.n ?? "") : ""} width="w-28" />
            </div>
            {/* Multi-interval sub-ranges — the form's e1/Max1/d1/n1 rows.
                No schema column yet (docs/architecture.md known gap); shown
                blank for layout fidelity, not editable. */}
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex flex-wrap gap-x-8 gap-y-2">
                <FormBox label={`e${i}`} value="" width="w-28" />
                <FormBox label={`Max${i}`} value="" width="w-28" />
                <FormBox label={`d${i}`} value="" width="w-28" />
                <FormBox label={`n${i}`} value="" width="w-28" />
              </div>
            ))}
          </div>

          <div className="mt-5 flex flex-wrap gap-x-8 gap-y-2 text-sm">
            <FormBox label="T = +" unit="°C" value={temperatureRangeMax} editable width="w-20" onChange={(v) => form.setValue("temperature_range_max", v)} />
            <FormBox label="T = −" unit="°C" value={temperatureRangeMin} editable width="w-20" onChange={(v) => form.setValue("temperature_range_min", v)} />
          </div>

          <div className="mt-5 flex flex-wrap gap-x-6 gap-y-2 text-sm">
            <FormBox label={<i>U</i>}
              unit="V" value={form.watch("u_nom")} editable width="w-20" onChange={(v) => form.setValue("u_nom", v)} />
            <FormBox label={<>U<sub>min</sub></>} unit="V" value={form.watch("u_min")} editable width="w-20" onChange={(v) => form.setValue("u_min", v)} />
            <FormBox label={<>U<sub>max</sub></>} unit="V" value={form.watch("u_max")} editable width="w-20" onChange={(v) => form.setValue("u_max", v)} />
            <FormBox label="f" unit="Hz" value={form.watch("mains_frequency")} editable width="w-20" onChange={(v) => form.setValue("mains_frequency", v)} />
            <FormBox label="Battery, U" unit="V" value={form.watch("battery_u_nom")} editable width="w-20" onChange={(v) => form.setValue("battery_u_nom", v)} />
          </div>

          <div className="mt-5 grid gap-3 text-sm sm:grid-cols-3">
            <div>
              <div className="mb-1.5 font-medium">Zero-setting device:</div>
              <CheckboxGroup
                options={ZERO_DEVICE_OPTIONS}
                value={zeroDeviceType}
                onChange={(v) => form.setValue("zero_device_type", v)}
              />
            </div>
            <div>
              <div className="mb-1.5 font-medium">Tare device:</div>
              <CheckboxGroup
                options={TARE_DEVICE_OPTIONS}
                value={tareDeviceType}
                onChange={(v) => form.setValue("tare_device_type", v)}
              />
            </div>
            <div>
              <div className="mb-1.5 font-medium opacity-0 sm:block">&nbsp;</div>
              <FormCheckbox
                label={COMBINED_ZERO_TARE.label}
                checked={tareDeviceType === COMBINED_ZERO_TARE.value}
                onClick={() => form.setValue("tare_device_type", COMBINED_ZERO_TARE.value)}
              />
            </div>
          </div>

          <div className="mt-5 flex flex-wrap items-baseline gap-x-8 gap-y-2 text-sm">
            <FormBox
              label="Initial zero-setting range"
              unit="% of Max"
              value={form.watch("initial_zero_setting_range_pct")}
              editable
              width="w-20"
              onChange={(v) => form.setValue("initial_zero_setting_range_pct", v)}
            />
            <span>
              Temperature range: {temperatureRangeMin || temperatureRangeMax ? `${temperatureRangeMin || "…"} to ${temperatureRangeMax || "…"}` : "…"} °C
            </span>
          </div>

          <div className="mt-5 text-sm">
            <div className="mb-1.5 font-medium">Printer:</div>
            <div className="flex flex-wrap gap-x-8 gap-y-2">
              {PRINTER_OPTIONS.map((option) => (
                <FormCheckbox
                  key={option.value}
                  label={option.label}
                  checked={printerStatus === option.value}
                  onClick={() => form.setValue("printer_status", option.value)}
                />
              ))}
            </div>
          </div>

          <div className="mt-6 grid gap-1.5 text-sm sm:grid-cols-2 sm:gap-x-10">
            <div className="grid gap-1.5">
              <FormLine label="Instrument submitted:" value="" />
              <FormLine label="Identification no.:" value={form.watch("identification_no")} editable onChange={(v) => form.setValue("identification_no", v)} />
              <FormLine label="Software version:" value={form.watch("software_version")} editable onChange={(v) => form.setValue("software_version", v)} />
              <FormLine label="Connected equipment:" value="" />
              <FormLine label="Interfaces (number, nature):" value={form.watch("interfaces")} editable onChange={(v) => form.setValue("interfaces", v)} />
              <FormLine label="Evaluation period:" value="" />
              <FormLine label="Date of report:" value="" />
              <FormLine label="Observer:" value="" />
            </div>
            <div className="grid gap-1.5">
              <div className="font-medium">Load cell:</div>
              <FormLine label="Manufacturer:" value={form.watch("load_cell_manufacturer")} editable onChange={(v) => form.setValue("load_cell_manufacturer", v)} />
              <FormLine label="Type:" value={form.watch("load_cell_type")} editable onChange={(v) => form.setValue("load_cell_type", v)} />
              <FormLine label="Capacity:" value={form.watch("load_cell_capacity")} editable onChange={(v) => form.setValue("load_cell_capacity", v)} />
              <FormLine label="Number:" value={form.watch("load_cell_number")} editable onChange={(v) => form.setValue("load_cell_number", v)} />
              <FormLine label="Classification symbol:" value={form.watch("load_cell_class_symbol")} editable onChange={(v) => form.setValue("load_cell_class_symbol", v)} />
              <FormLine label="Remarks:" value="" />
            </div>
          </div>

          <div className="mt-6 border-t border-neutral-900 pt-2 text-[10px] text-neutral-600">
            <p>
              <sup>1</sup> The test equipment (simulator or a part of a complete instrument) connected to the module shall be defined in the test form(s) used. Not captured in this build.
            </p>
            <p>
              <sup>2</sup> The oval shown around each class numeral above follows the form's own styling; it carries no meaning beyond identifying the class.
            </p>
          </div>
        </div>

        <p className="mx-auto max-w-4xl text-xs text-muted-foreground">
          Reproduced for data-entry fidelity to OIML R 76-2's page-6 "General information concerning the
          type" form — not a copy of the copyrighted OIML document itself. Only the fields listed in
          docs/architecture.md are actually stored; the rest (module/error-fraction testing, multi-interval
          sub-ranges, evaluation/report metadata) are shown blank for layout fidelity only, per the current
          schema.
        </p>

        {rootError ? (
          <p className="mx-auto w-full max-w-4xl rounded-md border border-destructive/50 bg-destructive/5 p-3 text-sm text-destructive">
            {rootError}
          </p>
        ) : null}

        <div className="mx-auto flex w-full max-w-4xl justify-end gap-3">
          <Button type="button" variant="outline" onClick={() => navigate("/instruments")}>
            Cancel
          </Button>
          <Button type="submit" disabled={form.formState.isSubmitting || !canSubmit}>
            {form.formState.isSubmitting ? "Registering…" : "Register instrument"}
          </Button>
        </div>
      </form>
    </div>
  );
}
