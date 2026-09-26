import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/AppShell";
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

const ACCURACY_CLASSES = ["I", "II", "III", "IIII"];
const INDICATION_TYPES = [
  { value: "digital", label: "Digital" },
  { value: "analog", label: "Analog" },
  { value: "non_self_indicating", label: "Non-self-indicating" },
];

const DEFAULT_VALUES = {
  accuracy_class: "III",
  e_value: "",
  d_value: "",
  max_capacity: "",
  min_capacity: "",
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
// or a plain-string error (e.g. a 409/500 {"detail": "..."}) as readable text.
function formatApiError(err) {
  const detail = err?.body?.detail;
  if (Array.isArray(detail)) {
    return detail.map((issue) => `${issue.loc?.slice(-1)[0] ?? "field"}: ${issue.msg}`).join("; ");
  }
  return err?.message ?? "Something went wrong.";
}

export function InstrumentRegisterPage() {
  const navigate = useNavigate();
  const [submitError, setSubmitError] = useState(null);
  const form = useForm({ defaultValues: DEFAULT_VALUES });

  async function onSubmit(values) {
    setSubmitError(null);

    // Decimal-as-string discipline (CLAUDE.md, backend StrictDecimal
    // contract): e_value/d_value/max_capacity/min_capacity are read straight
    // from react-hook-form's string state and sent as-is. They are NEVER
    // passed through Number()/parseFloat() — a JS `number` is a float, and
    // the backend rejects a bare float outright for exactly that reason
    // (300.6 must never round-trip through binary floating point before it
    // reaches the Decimal-based engine). An optional numeric field left
        // An optional numeric field left blank is sent as `null`, not an empty
    // string, matching the contract.
    const payload = {
      accuracy_class: values.accuracy_class,
      e_value: values.e_value,
      d_value: values.d_value.trim() === "" ? null : values.d_value,
      max_capacity: values.max_capacity,
      min_capacity: values.min_capacity.trim() === "" ? null : values.min_capacity,
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
      toast.success(`Instrument registered (${instrument.type_designation || instrument.id}).`);
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
                  name="accuracy_class"
                  rules={{ required: true }}
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Accuracy class</FormLabel>
                      <Select value={field.value} onValueChange={field.onChange}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {ACCURACY_CLASSES.map((option) => (
                            <SelectItem key={option} value={option}>
                              Class {option}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
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
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Min capacity (g) — optional</FormLabel>
                      <FormControl>
                        <Input inputMode="decimal" placeholder="e.g. 10" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
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
                <Button type="submit" disabled={form.formState.isSubmitting}>
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
