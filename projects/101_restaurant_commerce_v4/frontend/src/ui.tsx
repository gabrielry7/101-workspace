import { useEffect, useState } from "react";
import { CircleHelp } from "lucide-react";
export type Customer = {
  id: string;
  name: string | null;
  email: string | null;
  phone: string | null;
  created_at: string;
  last_order_at: string | null;
  registered: boolean;
  source: string | null;
};
export class ApiError extends Error {
  constructor(public status: number) {
    super(
      status === 401
        ? "Tu sesión terminó. Vuelve a entrar."
        : status === 403
          ? "No tienes acceso a este negocio."
          : status === 409
            ? "El pedido cambió. Actualiza antes de continuar."
            : "No pudimos cargar la información. Inténtalo de nuevo.",
    );
  }
}
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(path, { credentials: "same-origin", ...init });
  if (!r.ok) {
    if (r.status === 401) window.dispatchEvent(new Event("session-expired"));
    throw new ApiError(r.status);
  }
  return r.json();
}
export const endpoint = (business: string) =>
  `/api/operator/restaurants/${encodeURIComponent(business)}`;
const dateFormatter = new Intl.DateTimeFormat("es-CO", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "America/Bogota",
});
export const date = (value: string | null) =>
  value ? dateFormatter.format(new Date(value)) : "—";
const moneyFormatters = new Map<string, Intl.NumberFormat>();
export function amount(n: number, currency: string) {
  let formatter = moneyFormatters.get(currency);
  if (!formatter) {
    formatter = new Intl.NumberFormat("es-CO", {
      style: "currency",
      currency,
      maximumFractionDigits: currency === "COP" ? 0 : 2,
    });
    moneyFormatters.set(currency, formatter);
  }
  return formatter.format(currency === "COP" ? n : n / 100);
}
const countFormatter = new Intl.NumberFormat("es-CO");
export const count = (n: number) => countFormatter.format(n);
export const initials = (name: string | null) =>
  name
    ? name
        .trim()
        .split(/\s+/)
        .slice(0, 2)
        .map((x) => x[0])
        .join("")
        .toUpperCase()
    : "?";
export const label = (c: Customer) =>
  c.name || c.email || c.phone || "Sin nombre";
export const source = (value: string | null) =>
  ({ qr: "Código QR", website: "Sitio web", direct: "Enlace directo" })[
    value || ""
  ] || "Contacto existente";
export function Avatar({
  customer,
  large = false,
}: {
  customer: Customer;
  large?: boolean;
}) {
  const hue =
    Array.from(customer.id).reduce((n, c) => n + c.charCodeAt(0), 0) % 5;
  return (
    <span
      className={`avatar tone-${hue} ${large ? "large" : ""}`}
      aria-hidden="true"
    >
      {initials(customer.name)}
    </span>
  );
}
export function useResource<T>(key: string | null) {
  const [state, set] = useState<{
    key: string | null;
    data?: T;
    error?: string;
  }>({ key: null });
  const [retry, bump] = useState(0);
  useEffect(() => {
    if (!key) return;
    const abort = new AbortController();
    api<T>(key, { signal: abort.signal })
      .then((data) => set({ key, data }))
      .catch((e) => {
        if (!abort.signal.aborted) set({ key, error: e.message });
      });
    return () => abort.abort();
  }, [key, retry]);
  return {
    data: state.key === key ? state.data : undefined,
    error: state.key === key ? state.error : undefined,
    retry: () => {
      set({ key: null });
      bump((v) => v + 1);
    },
  };
}
export function Failure({
  message,
  retry,
}: {
  message: string;
  retry: () => void;
}) {
  return (
    <div className="state error" role="alert">
      <CircleHelp />
      <h3>No se pudo cargar</h3>
      <p>{message}</p>
      <button className="button secondary" onClick={retry}>
        Reintentar
      </button>
    </div>
  );
}
export function Loading() {
  return (
    <div className="loading" role="status" aria-label="Cargando información">
      <span />
      <span />
      <span />
      <span />
      <span />
    </div>
  );
}
