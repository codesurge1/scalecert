import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { apiFetch } from "@/lib/api";
import { classifyInstrument } from "@/lib/accuracyClass";
import { PageHeader } from "@/components/AppShell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const INDICATION_TYPES = [
  { value: "digital", label: "Digital" },
  { value: "analog", label: "Analog" },
  { value: "non_self_indicating", label: "Non-self-indicating" },
];

const DEFAULT_VALUES = {
  e_value: "",
  d_value: "",
  max_capacity: "",
  min_capacity: "",
  accuracy_class_choice: "",
  indication_type: "digital",
  is_mobile: false,
  is_multi_interval: false,
  application_no: "",
  type_designation: "",
  manufacturer: "",
  model: "",
  serial_number: "",
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

/**
 * Accuracy class is NEVER a free choice here — it's derived from e/Max/Min
 * per OIML R76-1 Table 3 (same rule as engine/classification.py, mirrored
 * client-side in src/lib/accuracyClass.js for instant feedback; the actual
 * POST below re-derives it server-side and is what's authoritative). This
 * prevents registering an out-of-spec instrument (e.g. the Class III /
 * n=15000 case that used to crash the Weighing load-sequence endpoint).
 */
export function InstrumentRegisterPage() {
  const navigate = useNavigate();
  const [submitError, setSubmitError] = useState(null);
  const form = useForm({ defaultValues: DEFAULT_VALUES });

  const [eValue, dValue, maxCapacity, minCapacity, accuracyClassChoice] = form.watch([
    "e_value",
    "d_value",
    "max_capacity",
    "min_capacity",
    "accuracy_class_choice",
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
    setSubmitError(null);

    // Decimal-as-string discipline (CLAUDE.md, backend StrictDecimal
    // contract): e_value/d_value/max_capacity/min_capacity are read straight
    // from react-hook-form's string state and sent as-is. They are NEVER
    // passed through Number()/parseFloat() — a JS `number` is a float, and
    // the backend rejects a bare float outright for exactly that reason
    // (300.6 must never round-trip through binary floating point before it
    // reaches the Decimal-based engine). min_capacity is required (Table 3
    // classification needs it); only d_value stays genuinely optional.
    const payload = {
      e_value: values.e_value,
      d_value: values.d_value.trim() === "" ? null : values.d_value,
      max_capacity: values.max_capacity,
      min_capacity: values.min_capacity,
      // accuracy_class is only ever sent to disambiguate when e/Max/Min
      // qualify for more than one class — otherwise omitted entirely and
      // left to the server's own derivation (engine.classification).
      accuracy_class: isAmbiguous ? resolvedClass : null,
      indication_type: values.indication_type,
      is_mobile: values.is_mobile,
      is_multi_interval: values.is_multi_interval,
      application_no: values.application_no || null,
      type_designation: values.type_designation || null,
      manufacturer: values.manufacturer || null,
      model: values.model || null,
      serial_number: values.serial_number || null,
    };

    try {
      const instrument = await apiFetch("/instruments", { method: "POST", body: payload });
      toast.success(`Instrument registered — Class ${instrument.accuracy_class} (${instrument.type_designation || instrument.id}).`);
      navigate("/instruments");
    } catch (err) {
      setSubmitError(formatApiError(err));
    }
  }

  return (
    <div>
      <PageHeader title="Register instrument" description="Add a non-automatic weighing instrument." />

      <Card className="max-w-2xl">
        <CardContent className="pt-6">
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="grid gap-6">
              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="e_value"
                  rules={{ required: "e is required" }}
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>e (verification scale interval, g)</FormLabel>
                      <FormControl>
                        <Input inputMode="decimal" placeholder="e.g. 1" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="d_value"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>d (actual scale interval, g) — optional</FormLabel>
                      <FormControl>
                        <Input inputMode="decimal" placeholder="defaults to e" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="max_capacity"
                  rules={{ required: "Max is required" }}
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Max capacity (g)</FormLabel>
                      <FormControl>
                        <Input inputMode="decimal" placeholder="e.g. 5000" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="min_capacity"
                  rules={{ required: "Min is required — needed to derive the accuracy class (Table 3)" }}
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Min capacity (g)</FormLabel>
                      <FormControl>
                        <Input inputMode="decimal" placeholder="e.g. 10" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="indication_type"
                  rules={{ required: true }}
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Indication type</FormLabel>
                      <Select value={field.value} onValueChange={field.onChange}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {INDICATION_TYPES.map((option) => (
                            <SelectItem key={option.value} value={option.value}>
                              {option.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <div className="rounded-md border bg-secondary/40 p-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Accuracy class — derived, not chosen (OIML R76-1 Table 3)
                </div>
                {!hasAllThree ? (
                  <p className="mt-1.5 text-sm text-muted-foreground">
                    Enter e, Max, and Min above to derive the accuracy class.
                  </p>
                ) : isInvalid ? (
                  <p className="mt-1.5 text-sm font-medium text-destructive">{classification.reason}</p>
                ) : isAmbiguous ? (
                  <div className="mt-2 grid gap-2">
                    <p className="text-sm">
                      These values qualify for more than one class (n={classification.n}) — pick one:
                    </p>
                    <FormField
                      control={form.control}
                      name="accuracy_class_choice"
                      render={({ field }) => (
                        <FormItem className="max-w-40">
                          <Select value={field.value} onValueChange={field.onChange}>
                            <FormControl>
                              <SelectTrigger>
                                <SelectValue placeholder="Choose a class" />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              {classification.qualifiedClasses.map((option) => (
                                <SelectItem key={option} value={option}>
                                  Class {option}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </FormItem>
                      )}
                    />
                  </div>
                ) : (
                  <div className="mt-1.5 flex items-center gap-2">
                    <Badge variant="success" className="text-sm">
                      Class {classification.qualifiedClasses[0]}
                    </Badge>
                    <span className="text-sm text-muted-foreground">
                      derived from e, Max, n={classification.n}
                    </span>
                  </div>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="type_designation"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Type designation</FormLabel>
                      <FormControl>
                        <Input {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="application_no"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Application no.</FormLabel>
                      <FormControl>
                        <Input {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="manufacturer"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Manufacturer</FormLabel>
                      <FormControl>
                        <Input {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="model"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Model</FormLabel>
                      <FormControl>
                        <Input {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="serial_number"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Serial number</FormLabel>
                      <FormControl>
                        <Input {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <div className="flex gap-6">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    className="size-4 rounded border-input accent-primary"
                    {...form.register("is_mobile")}
                  />
                  Mobile instrument
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    className="size-4 rounded border-input accent-primary"
                    {...form.register("is_multi_interval")}
                  />
                  Multi-interval instrument
                </label>
              </div>

              {submitError ? (
                <p className="rounded-md border border-destructive/50 bg-destructive/5 p-3 text-sm text-destructive">
                  {submitError}
                </p>
              ) : null}

              <div className="flex justify-end gap-3">
                <Button type="button" variant="outline" onClick={() => navigate("/instruments")}>
                  Cancel
                </Button>
                <Button type="submit" disabled={form.formState.isSubmitting || !canSubmit}>
                  {form.formState.isSubmitting ? "Registering…" : "Register instrument"}
                </Button>
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
}
