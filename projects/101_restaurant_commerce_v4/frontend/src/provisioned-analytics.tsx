import "./provisioned-analytics.css";
import { useState } from "react";
import { amount, count, useResource, Failure, Loading } from "./ui";
import {
  PageHeading,
  PeriodPicker,
  currentPeriod,
  type ViewProps,
} from "./workspace-views";

type Money = {
  currency: string;
  scope: string;
  captured: number;
  refunds: number;
  net: number;
  paid_orders: number;
};
type Report = {
  website: {
    status: string;
    data?: Record<string, unknown> | { x: string; y: number }[];
  };
  commerce: {
    status: string;
    data?: { orders: number; new_customers: number; money: Money[] };
  };
};
const dimensions = [
  ["summary", "Resumen"],
  ["referrers", "Fuentes"],
  ["pages", "Páginas"],
  ["devices", "Dispositivos"],
  ["browsers", "Navegadores"],
  ["countries", "Países"],
  ["utm_campaign", "Campañas"],
  ["events", "Eventos"],
  ["checkout_funnel", "Embudo de compra"],
  ["performance", "Rendimiento"],
] as const;
export function ProvisionedAnalytics(props: ViewProps) {
  const p = currentPeriod(props.params);
  const [dimension, setDimension] = useState("summary");
  // Existing workspace periods are Bogotá calendar days. API intervals remain UTC and exclusive at end.
  const start = +new Date(p.from + "T00:00:00-05:00"),
    end = +new Date(p.to + "T00:00:00-05:00") + 86400000;
  const valid =
    Number.isFinite(start) &&
    Number.isFinite(end) &&
    end > start &&
    end - start <= 366 * 86400000;
  const query = new URLSearchParams({
    start_ms: String(start),
    end_ms: String(end),
    dimension,
  });
  const data = useResource<Report>(
    valid
      ? `/api/101/businesses/${encodeURIComponent(props.business)}/analytics?${query}`
      : null,
  );
  const website = data.data?.website;
  const summary = website?.data as
    Record<string, { value?: number }> | undefined;
  const value = (key: string) => {
    const n = summary?.[key];
    return typeof n === "number"
      ? n
      : typeof n?.value === "number"
        ? n.value
        : null;
  };
  const rows = Array.isArray(website?.data)
    ? (website.data as unknown as Record<string, unknown>[])
    : [];
  return (
    <div className="page new-view analytics-view provisioned-analytics">
      <PageHeading
        title="Analítica web"
        description="Visitas y resultados del negocio."
      >
        <PeriodPicker {...props} />
      </PageHeading>
      <label className="analytics-report-control">
        Ver{" "}
        <select
          aria-label="Informe de analítica"
          value={dimension}
          onChange={(e) => setDimension(e.target.value)}
        >
          {dimensions.map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </select>
      </label>
      {!valid ? (
        <p role="alert">Elige un periodo de hasta 366 días.</p>
      ) : data.error ? (
        <Failure message={data.error} retry={data.retry} />
      ) : !data.data ? (
        <Loading />
      ) : (
        <>
          {website?.status !== "ready" ? (
            <section className="work-surface analytics-report">
              <h2>
                {website?.status === "error"
                  ? "Medición web no disponible"
                  : "Medición web pendiente"}
              </h2>
              <p>
                {website?.status === "error"
                  ? "Intenta consultar de nuevo en unos minutos."
                  : "Las visitas aparecerán cuando se complete la conexión de analítica."}
              </p>
              <button className="button secondary" onClick={data.retry}>
                Actualizar
              </button>
            </section>
          ) : dimension === "summary" ? (
            <section className="result-strip analytics-metrics">
              {[
                ["visits", "Visitas"],
                ["visitors", "Visitantes"],
                ["pageviews", "Páginas vistas"],
              ].map(([key, label]) => (
                <div key={key}>
                  <span>{label}</span>
                  <strong>
                    {value(key) === null ? "—" : count(value(key)!)}
                  </strong>
                  <small>Medición web</small>
                </div>
              ))}
            </section>
          ) : (
            <section className="work-surface analytics-report">
              <h2>{dimensions.find(([key]) => key === dimension)?.[1]}</h2>
              {rows.length ? (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Detalle</th>
                        <th>
                          {dimension === "checkout_funnel"
                            ? "Visitantes"
                            : "Valor"}
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((r, i) => (
                        <tr key={i}>
                          <td>
                            {String(r.x ?? r.value ?? r.name ?? "Sin detalle")}
                          </td>
                          <td>{String(r.y ?? r.visitors ?? r.count ?? "—")}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p>Sin datos para este periodo.</p>
              )}
            </section>
          )}
          <section className="work-surface analytics-report">
            <h2>Resultados del negocio</h2>
            <p>
              Pedidos creados en el periodo; reembolsos conocidos hasta hoy.
            </p>
            {data.data.commerce.status !== "ready" ? (
              <p>Resultados pendientes de conexión.</p>
            ) : (
              <>
                <p>
                  <strong>{count(data.data.commerce.data?.orders ?? 0)}</strong>{" "}
                  pedidos ·{" "}
                  <strong>
                    {count(data.data.commerce.data?.new_customers ?? 0)}
                  </strong>{" "}
                  clientes nuevos
                </p>
                {data.data.commerce.data?.money.length ? (
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Origen</th>
                          <th>Cobrado</th>
                          <th>Reembolsado</th>
                          <th>Neto</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.data.commerce.data.money.map((m) => (
                          <tr key={m.currency + ":" + m.scope}>
                            <td>
                              {m.scope === "test"
                                ? "Prueba"
                                : m.scope === "cash"
                                  ? "Efectivo"
                                  : "Proveedor"}{" "}
                              · {m.currency}
                            </td>
                            <td>{amount(m.captured, m.currency)}</td>
                            <td>{amount(m.refunds, m.currency)}</td>
                            <td>{amount(m.net, m.currency)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p>Sin pagos registrados.</p>
                )}
              </>
            )}
          </section>
        </>
      )}
    </div>
  );
}
