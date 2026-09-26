// Shared visual primitives for the OIML R 76-2 "bordered official form"
// look — used by WeighingFormTable.jsx (page 10, "Weighing performance")
// and InstrumentRegisterPage.jsx (page 6, "General information concerning
// the type"). Kept in one place rather than duplicated per-form, so both
// forms' fill-in lines and tick-boxes stay pixel-identical by construction.

/** A label + dotted fill-in line, matching the form's "Label: …………" rows. */
export function FormLine({ label, value, editable, disabled, onChange }) {
  return (
    <div className="flex items-baseline gap-2">
      <span className="shrink-0">{label}</span>
      {editable ? (
        <input
          className="min-w-0 flex-1 border-0 border-b border-dotted border-neutral-500 bg-transparent px-1 text-sm focus:outline-none focus:border-solid focus:border-neutral-900 disabled:opacity-60"
          disabled={disabled}
          value={value}
          onChange={(event) => onChange(event.target.value)}
        />
      ) : (
        <span className="min-w-0 flex-1 truncate border-b border-dotted border-neutral-500 px-1 text-sm">
          {value || " "}
        </span>
      )}
    </div>
  );
}

/** A "Label = [box]" boxed field, matching the form's bordered-rectangle
 * inputs (as distinct from FormLine's dotted-fill-in style — the OIML forms
 * use both styles in different sections, and this reproduces the boxed
 * one). `unit` renders a small trailing label (e.g. "V", "Hz", "% of Max"). */
export function FormBox({ label, value, unit, editable, disabled, onChange, width = "w-24" }) {
  return (
    <span className="inline-flex items-baseline gap-1.5 text-sm">
      <span className="whitespace-nowrap">{label} =</span>
      {editable ? (
        <input
          className={`h-7 ${width} border border-neutral-900 bg-transparent px-1.5 text-center text-sm focus:outline-none focus:ring-1 focus:ring-inset focus:ring-neutral-900 disabled:opacity-60`}
          disabled={disabled}
          value={value}
          onChange={(event) => onChange(event.target.value)}
        />
      ) : (
        <span className={`inline-block h-7 ${width} truncate border border-neutral-900 bg-transparent px-1.5 text-center text-sm leading-7`}>
          {value || ""}
        </span>
      )}
      {unit ? <span className="whitespace-nowrap text-xs text-neutral-600">{unit}</span> : null}
    </span>
  );
}

/** A square ☐-style checkbox, matching the form's tick-box controls. Used
 * both interactively (a technician picking an option) and read-only (a
 * value reflecting computed/derived state rather than a manual click). */
export function FormCheckbox({ checked, onClick, label, readOnly, disabled }) {
  const inert = readOnly || disabled;
  return (
    <span
      role={inert ? undefined : "checkbox"}
      aria-checked={checked}
      onClick={inert ? undefined : onClick}
      className={`flex items-center gap-2 text-sm ${inert ? "" : "cursor-pointer"} ${disabled ? "opacity-50" : ""}`}
    >
      <span className="flex h-4 w-4 shrink-0 items-center justify-center border border-neutral-900">
        {checked ? <span className="h-2.5 w-2.5 bg-neutral-900" /> : null}
      </span>
      {label}
    </span>
  );
}
