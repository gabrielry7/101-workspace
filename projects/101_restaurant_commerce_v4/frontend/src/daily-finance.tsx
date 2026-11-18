import { useEffect, useState } from "react";
import { MonthlyReports } from "./monthly-reports";
import { endpoint, amount, useResource, Failure, Loading } from "./ui";
import type { OperationSettings } from "./operation-settings";
import "./operations-workspace.css";
type Daily = {
  date: string;
  timezone: string;
  currency: string | null;
  currencies: string[];
  orders: number;
  gross_minor: number;
  confirmed_full_refunds_minor: number;
  confirmed_partial_refunds_minor: number;
  known_balance_minor: number;
  provider_fees_minor: null;
  settled_net_minor: null;
  unconfirmed_orders: number;
  open_reviews_all_dates: number;
};
export function ReportsWorkspace({
  business,
  csrf,
  params,
  navigate,
}: {
  business: string;
  csrf: string;
  params: URLSearchParams;
  navigate: (changes: Record<string, string | null>) => void;
}) {
  const daily = params.get("view") === "daily";
  return (
    <>
      <div className="tabs sales-views" aria-label="Secciones de reportes">
        {[
          ["monthly", "Mensual"],
          ["daily", "Resumen diario"],
        ].map(([key, title]) => (
          <button
            key={key}
            aria-pressed={daily === (key === "daily")}
            className={daily === (key === "daily") ? "selected" : ""}
            onClick={() => navigate({ view: key })}
          >
            {title}
          </button>
        ))}
      </div>
      {daily ? (
        <DailyFinance
          key={business}
          business={business}
          params={params}
          navigate={navigate}
        />
      ) : (
        <MonthlyReports key={business} business={business} csrf={csrf} />
      )}
    </>
  );
}
function DailyFinance({
  business,
  params,
  navigate,
}: {
  business: string;
  params: URLSearchParams;
  navigate: (changes: Record<string, string | null>) => void;
}) {
  const settings = useResource<OperationSettings>(
    endpoint(business) + "/settings",
  );
  const [entered, setEntered] = useState("");
  const today = settings.data
    ? new Intl.DateTimeFormat("en-CA", {
        timeZone: settings.data.timezone,
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
      }).format(new Date())
    : "";
  const day = params.get("day") || today,
    currency = params.get("currency") || "";
  const report = useResource<Daily>(
    day
      ? endpoint(business) +
          `/daily-finance?day=${encodeURIComponent(day)}${currency ? "&currency=" + encodeURIComponent(currency) : ""}`
      : null,
  );
  useEffect(() => setEntered(""), [day]);
  const d = report.data;
  return (
    <div className="page daily-finance">
      <section className="page-heading">
        <div>
          <h1>Resumen diario</h1>
          <p>
            Pedidos creados en el día elegido, con el estado actual de sus
            pagos.
          </p>
        </div>
      </section>
      <form
        className="operation-filters"
        onSubmit={(e) => {
          e.preventDefault();
          navigate({ day: entered || day, currency: null });
        }}
      >
        <label>
          Fecha del resumen
          <input
            aria-label="Fecha del resumen"
            type="date"
            min="1900-01-01"
            max="9998-12-31"
            required
            value={entered || day}
            onChange={(e) => setEntered(e.target.value)}
          />
        </label>
        <button className="button secondary" disabled={!day}>
          Ver resumen
        </button>
        {d && d.currencies.length > 1 && (
          <label>
            Moneda
            <select
              aria-label="Moneda del resumen"
              value={currency}
              onChange={(e) => navigate({ currency: e.target.value || null })}
            >
              <option value="">Selecciona una moneda</option>
              {d.currencies.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </label>
        )}
        <button
          type="button"
          className="button secondary"
          disabled={!day}
          onClick={report.retry}
        >
          Actualizar resumen
        </button>
      </form>
      {settings.error ? (
        <Failure message={settings.error} retry={settings.retry} />
      ) : report.error ? (
        <Failure message={report.error} retry={report.retry} />
      ) : !d ? (
        <Loading />
      ) : (
        <>
          <p className="source-note">
            {d.date} · {d.timezone} · {d.currency || "Varias monedas"}
          </p>
          {!d.currency ? (
            <p className="operation-notice">
              Hay pedidos en distintas monedas. Selecciona una para consultar
              los importes.
            </p>
          ) : (
            <section
              className="sales-summary daily-money"
              aria-label="Importes del resumen"
            >
              {[
                ["Pagos confirmados · incluye devueltos", d.gross_minor],
                ["Devoluciones completas", d.confirmed_full_refunds_minor],
                ["Devoluciones parciales", d.confirmed_partial_refunds_minor],
                ["Balance conocido de estos pedidos", d.known_balance_minor],
              ].map(([title, value]) => (
                <div key={String(title)}>
                  <span>{title}</span>
                  <strong>{amount(Number(value), d.currency!)}</strong>
                </div>
              ))}
            </section>
          )}
          <section className="customer-surface operation-form">
            <h2>Alcance del resumen</h2>
            <p>
              {d.orders} pedidos · {d.unconfirmed_orders} sin pago confirmado.
            </p>
            <p>
              {d.open_reviews_all_dates} revisiones abiertas de todas las
              fechas.
            </p>
            <p>
              Comisiones del proveedor: sin verificar. Neto liquidado: sin
              verificar.
            </p>
            <p className="source-note">
              Este balance no es un cierre bancario. No se mezcla con el reporte
              mensual ni con las visitas al sitio web.
            </p>
          </section>
        </>
      )}
    </div>
  );
}
