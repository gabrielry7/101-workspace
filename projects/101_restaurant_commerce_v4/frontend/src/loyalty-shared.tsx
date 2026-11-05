import {
  useEffect,
  useRef,
  useState,
  useId,
  cloneElement,
  isValidElement,
  type ReactNode,
} from "react";
import { api, ApiError } from "./ui";

export type Eligibility = {
  verified_identity_required: true;
  included_product_ids: string[];
  excluded_product_ids: string[];
  customer_ids: string[];
  minimum_purchase_minor: number;
};
export type Program = {
  schema_version: 1;
  name: string;
  description: string;
  currency: string;
  start_at: string | null;
  end_at: string | null;
  eligibility: Eligibility;
  earning: null | {
    type: "points";
    spend_minor_per_point: number;
    points_per_unit: number;
  };
  reward: null | {
    type: string;
    points_cost?: number;
    discount_minor?: number;
  };
  minimum_redeem_points: number;
  maximum_reward_minor: number;
  expiration_days: number | null;
  per_customer_budget_minor: number;
  campaign_budget_minor: number;
  estimated_cost_per_point_minor: number;
  expected_redemption_bps: number;
  stack_with_promotions: boolean;
  eligible_spend_basis: "net_items_excluding_tax_and_delivery";
  rounding: "floor_per_order";
};
export type Variant = {
  name: string;
  allocation_bps: number;
  strategy_version_id: string | null;
};
export type Experiment = {
  schema_version: 1;
  name: string;
  description: string;
  currency: string;
  enrollment_start: string;
  enrollment_end: string;
  observation_days: number;
  carryover_days: number;
  eligibility: Eligibility;
  variants: Variant[];
  exclusion_group: string;
  allow_overlap: boolean;
  overlap_reason: string | null;
  baseline_benefits_preserved: true;
  primary_metric: "incremental_contribution_profit_per_randomized_customer";
  assignment_algorithm: "sha256-v1";
  analysis_plan: string;
  analysis_protocol?: null | {
    method: "welch_bonferroni_v1";
    confidence_bps: 9000 | 9500 | 9900;
    minimum_customers_per_arm: number;
    sample_size_rationale: string;
    readout_at: string;
  };
};
export type Resource<T = Program | Experiment> = {
  id: string;
  business_id: string;
  state: string;
  revision: number;
  document: T;
  digest: string;
  execution_enabled: false;
  versions: {
    id: string;
    revision: number;
    digest: string;
    document: T;
    actor_id: string;
    published_at: string;
  }[];
};
export type Nav = (
  changes: Record<string, string | null>,
  push?: boolean,
) => void;
export const statuses: Record<string, string> = {
  draft: "Borrador",
  published: "Publicada",
  paused: "Pausada",
  archived: "Archivada",
  active: "Activa",
};
export const emptyEligibility = (): Eligibility => ({
  verified_identity_required: true,
  included_product_ids: [],
  excluded_product_ids: [],
  customer_ids: [],
  minimum_purchase_minor: 0,
});
export const normalize = (v: unknown): string =>
  JSON.stringify(v, (_, value) =>
    value && typeof value === "object" && !Array.isArray(value)
      ? Object.fromEntries(
          Object.entries(value).sort(([a], [b]) => a.localeCompare(b)),
        )
      : value,
  );
export function integer(value: string, min = 0, max = Number.MAX_SAFE_INTEGER) {
  if (
    !/^-?\d+$/.test(value) ||
    !Number.isSafeInteger(Number(value)) ||
    Number(value) < min ||
    Number(value) > max
  )
    throw new Error("Revisa los valores enteros y sus límites.");
  return Number(value);
}
export function scaled(value: string, places: number, signed = false) {
  if (!(signed ? /^-?\d+(\.\d+)?$/ : /^\d+(\.\d+)?$/).test(value.trim()))
    throw new Error("Escribe un número válido usando punto decimal.");
  const [whole, fraction = ""] = value.trim().replace("-", "").split(".");
  if (fraction.length > places)
    throw new Error(`Usa como máximo ${places} decimales.`);
  const result =
    BigInt(whole) * 10n ** BigInt(places) +
    BigInt(fraction.padEnd(places, "0") || "0");
  return integer(
    String(value.trim().startsWith("-") ? -result : result),
    signed ? -Number.MAX_SAFE_INTEGER : 0,
  );
}
export const minor = (value: string, currency: string, signed = false) =>
  scaled(value, currency === "COP" ? 0 : 2, signed);
export function editableMoney(value: number, currency: string) {
  if (currency === "COP") return String(value);
  const n = BigInt(value),
    sign = n < 0n ? "-" : "";
  const a = n < 0n ? -n : n;
  return sign + a / 100n + "." + String(a % 100n).padStart(2, "0");
}
export function money(value: string | number, currency: string) {
  const n = BigInt(value),
    sign = n < 0n ? "−" : "";
  const a = n < 0n ? -n : n;
  return currency === "COP"
    ? `${sign}$ ${a.toLocaleString("es-CO")} COP`
    : `${sign}${(a / 100n).toLocaleString("es-CO")},${String(a % 100n).padStart(2, "0")} ${currency}`;
}
export const points = (value: string | number) =>
  BigInt(value).toLocaleString("es-CO");
export const percent = (bps: number) => String(bps / 100);
export const bps = (value: string, signed = false) => scaled(value, 2, signed);
export const localDate = (value: string | null) => {
  if (!value) return "";
  const d = new Date(value);
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);
};
export const utcDate = (value: string) =>
  value ? new Date(value).toISOString() : null;
export function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
}) {
  const id = useId(),
    labelId = id + "-label",
    hintId = id + "-hint";
  const control = isValidElement<{
    id?: string;
    "aria-labelledby"?: string;
    "aria-describedby"?: string;
  }>(children)
    ? cloneElement(children, {
        id,
        "aria-labelledby": labelId,
        "aria-describedby": hint ? hintId : undefined,
      })
    : children;
  return (
    <label className="loyalty-field" htmlFor={id}>
      <span id={labelId}>{label}</span>
      {control}
      {hint && <small id={hintId}>{hint}</small>}
    </label>
  );
}
export function MoneyField({
  label,
  value,
  onChange,
  currency,
  signed = false,
}: {
  label: string;
  value: number;
  onChange: (n: number) => void;
  currency: string;
  signed?: boolean;
}) {
  const [text, setText] = useState(editableMoney(value, currency)),
    ref = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (document.activeElement !== ref.current)
      setText(editableMoney(value, currency));
  }, [value, currency]);
  return (
    <Field label={`${label} (${currency})`}>
      <input
        ref={ref}
        type="text"
        inputMode="decimal"
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          try {
            onChange(minor(e.target.value, currency, signed));
            e.target.setCustomValidity("");
          } catch (error) {
            e.target.setCustomValidity((error as Error).message);
          }
        }}
        required
      />
    </Field>
  );
}
export function NumberField({
  label,
  value,
  onChange,
  min = 0,
  max = 2147483647,
}: {
  label: string;
  value: number;
  onChange: (n: number) => void;
  min?: number;
  max?: number;
}) {
  return (
    <Field label={label}>
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        step="1"
        required
        onChange={(e) =>
          onChange(e.target.value === "" ? 0 : Number(e.target.value))
        }
      />
    </Field>
  );
}
export function PercentField({
  label,
  value,
  onChange,
  max = 100,
  min = 0,
}: {
  label: string;
  value: number;
  onChange: (n: number) => void;
  max?: number;
  min?: number;
}) {
  const [text, setText] = useState(percent(value)),
    ref = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (document.activeElement !== ref.current) setText(percent(value));
  }, [value]);
  return (
    <Field label={label}>
      <input
        ref={ref}
        type="number"
        value={text}
        min={min}
        max={max}
        step="0.01"
        required
        onChange={(e) => {
          setText(e.target.value);
          try {
            onChange(bps(e.target.value, min < 0));
            e.target.setCustomValidity("");
          } catch (error) {
            e.target.setCustomValidity((error as Error).message);
          }
        }}
      />
    </Field>
  );
}

// One pending intent per mounted object, stable across lost replies. An old
// business's callback cannot navigate the current business after unmount.
export function useCommand(csrf: string) {
  const pending = useRef<null | (() => Promise<void>)>(null),
    inFlight = useRef(false),
    alive = useRef(true);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [uncertain, setUncertain] = useState(false);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  async function run(task: () => Promise<void>) {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setError("");
    const intent = pending.current || task;
    pending.current = intent;
    try {
      await intent();
      if (alive.current) {
        pending.current = null;
        setUncertain(false);
      }
    } catch (e) {
      if (alive.current) {
        const status = e instanceof ApiError ? e.status : 0;
        setError(
          e instanceof ApiError
            ? status === 409
              ? "La versión cambió. Recarga los datos antes de volver a guardar."
              : status === 422
                ? "Revisa las reglas, los límites y las fechas del formulario."
                : e.message
            : e instanceof TypeError &&
                /fetch|network|load failed/i.test(e.message)
              ? "No pudimos confirmar la respuesta. Conservamos tu solicitud para verificarla."
              : (e as Error).message,
        );
        const unknown = !status || status >= 500;
        setUncertain(unknown);
        if (!unknown) pending.current = null;
      }
    } finally {
      inFlight.current = false;
      if (alive.current) setBusy(false);
    }
  }
  const send = <T,>(url: string, method: string, body: unknown) =>
    api<T>(url, {
      method,
      headers: { "Content-Type": "application/json", "X-101-CSRF": csrf },
      body: JSON.stringify(body),
    });
  return {
    run,
    retry: () => {
      void run(async () => {});
    },
    send,
    busy,
    error,
    uncertain,
    alive,
    hasPending: () => pending.current !== null,
    clearError: () => {
      if (!pending.current) setError("");
    },
    fail: (s: string) => setError(s),
  };
}
export function CommandState({
  command,
}: {
  command: ReturnType<typeof useCommand>;
}) {
  return (
    <>
      {command.error && (
        <p className="loyalty-error" role="alert">
          {command.error}
        </p>
      )}
      {command.uncertain && (
        <button
          type="button"
          className="button secondary"
          disabled={command.busy}
          onClick={command.retry}
        >
          Verificar solicitud pendiente
        </button>
      )}
      {command.uncertain && (
        <p className="loyalty-notice" role="status">
          No recibimos la confirmación. Conservamos esta solicitud: usa el mismo
          botón para verificar y reintentar.
        </p>
      )}
    </>
  );
}
