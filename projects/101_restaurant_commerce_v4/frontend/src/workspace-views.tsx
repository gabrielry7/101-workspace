import { useEffect, useState } from "react";
import {
  ArrowRight,
  Plus,
  Users,
  ShoppingBag,
  Megaphone,
  Globe2,
  ArrowUpRight,
  Check,
  Palette,
} from "lucide-react";
import {
  amount,
  count,
  date,
  endpoint,
  useResource,
  Failure,
  Loading,
} from "./ui";
import "./workspace-views.css";
export type ViewProps = {
  business: string;
  params: URLSearchParams;
  navigate: (changes: Record<string, string | null>, push?: boolean) => void;
};
export function currentPeriod(params: URLSearchParams) {
  const today = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Bogota",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
  const end = params.get("date_to") || today;
  const parsed = new Date(end + "T12:00:00Z");
  const d = Number.isFinite(+parsed) ? parsed : new Date(today + "T12:00:00Z");
  d.setUTCDate(d.getUTCDate() - 6);
  return {
    from: params.get("date_from") || d.toISOString().slice(0, 10),
    to: end,
  };
}
export function periodQuery(params: URLSearchParams) {
  const p = new URLSearchParams();
  for (const k of ["date_from", "date_to"])
    if (params.get(k)) p.set(k, params.get(k)!);
  return p.toString();
}
export function workspaceHref(
  area: string,
  business: string,
  params: URLSearchParams,
  extra: Record<string, string> = {},
) {
  return `/workspace/${area}?${new URLSearchParams({ business, ...Object.fromEntries(new URLSearchParams(periodQuery(params))), ...extra })}`;
}
export function PeriodPicker({
  params,
  navigate,
}: Pick<ViewProps, "params" | "navigate">) {
  const p = currentPeriod(params);
  const [from, setFrom] = useState(p.from),
    [to, setTo] = useState(p.to);
  useEffect(() => {
    setFrom(p.from);
    setTo(p.to);
  }, [p.from, p.to]);
  return (
    <form
      className="period-picker"
      aria-label="Periodo"
      onSubmit={(e) => {
        e.preventDefault();
        navigate({ date_from: from, date_to: to, offset: null });
      }}
    >
      <label>
        Desde
        <input
          type="date"
          aria-label="Desde"
          value={from}
          onChange={(e) => setFrom(e.target.value)}
          required
        />
      </label>
      <span aria-hidden="true">—</span>
      <label>
        Hasta
        <input
          type="date"
          aria-label="Hasta"
          value={to}
          min={from}
          onChange={(e) => setTo(e.target.value)}
          required
        />
      </label>
      <button className="button secondary" type="submit">
        Aplicar
      </button>
    </form>
  );
}
export function PageHeading({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children?: React.ReactNode;
}) {
  return (
    <header className="view-heading">
      <div>
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {children}
    </header>
  );
}
const Icon = {
  order: ShoppingBag,
  customer: Users,
  campaign: Megaphone,
  connection: Globe2,
};
type Entry = {
  id: string;
  title: string;
  detail?: string;
  at?: string;
  href: string;
  action?: string;
  kind: keyof typeof Icon;
};
type Overview = {
  period: { from: string; to: string };
  new_customers: number;
  orders: number;
  money: {
    currency: string;
    scope: string;
    captured: number;
    refunds: number;
    net: number;
    paid_orders: number;
  }[];
  attention: Entry[];
  activity: Entry[];
  links: { customers: string; orders: string };
  accounting: string;
  attention_period: string;
};
export function HomeView(props: ViewProps) {
  const { business, params } = props;
  const p = currentPeriod(params);
  const r = useResource<Overview>(
    `${endpoint(business)}/workspace/overview?date_from=${p.from}&date_to=${p.to}`,
  );
  const d = r.data;
  const link = (area: string, extra: Record<string, string> = {}) =>
    workspaceHref(
      area,
      business,
      new URLSearchParams({
        ...Object.fromEntries(params),
        date_from: p.from,
        date_to: p.to,
      }),
      extra,
    );
  return (
    <div className="page new-view home-view">
      <PageHeading title="Inicio" description="Lo que pasó. Lo que falta.">
        <PeriodPicker {...props} />
      </PageHeading>
      {r.error ? (
        <Failure message={r.error} retry={r.retry} />
      ) : !d ? (
        <Loading />
      ) : (
        <>
          <section className="result-strip" aria-label="Resultados del periodo">
            <a href={d.links.orders}>
              <span>
                Pedidos creados
                <ShoppingBag size={17} />
              </span>
              <strong>{count(d.orders)}</strong>
              <small>
                Ver pedidos <ArrowUpRight size={13} />
              </small>
            </a>
            <a href={d.links.customers}>
              <span>
                Clientes añadidos
                <Users size={17} />
              </span>
              <strong>{count(d.new_customers)}</strong>
              <small>
                Ver clientes <ArrowUpRight size={13} />
              </small>
            </a>
            <div className="money-result">
              <span>Capturado menos devuelto</span>
              {d.money.length ? (
                d.money.map((m) => (
                  <div key={m.scope + m.currency}>
                    <strong>{amount(m.net, m.currency)}</strong>
                    <small>
                      {m.currency} ·{" "}
                      {m.scope === "test"
                        ? "Simulación"
                        : m.scope === "cash"
                          ? "Efectivo"
                          : "Registro del proveedor"}{" "}
                      · {m.paid_orders} pedidos pagados
                    </small>
                  </div>
                ))
              ) : (
                <>
                  <strong>—</strong>
                  <small>Sin pagos confirmados en estos pedidos</small>
                </>
              )}
            </div>
          </section>
          <p className="data-footnote">{d.accounting}</p>
          <div className="home-columns">
            <section className="work-surface attention-panel">
              <div className="section-heading">
                <h2>
                  Por revisar{" "}
                  <span className="number-chip">{d.attention.length}</span>
                </h2>
                <span className="caption">Pendientes actuales</span>
              </div>
              {d.attention.length ? (
                <div className="work-list">
                  {d.attention.map((item) => {
                    const I = Icon[item.kind];
                    return (
                      <a
                        key={item.id}
                        href={item.href}
                        className="attention-row"
                      >
                        <span className={"item-icon kind-" + item.kind}>
                          <I size={19} />
                        </span>
                        <div>
                          <strong>{item.title}</strong>
                          <small>{item.detail}</small>
                        </div>
                        <span className="row-action">
                          {item.action}
                          <ArrowRight size={16} />
                        </span>
                      </a>
                    );
                  })}
                </div>
              ) : (
                <div className="quiet-empty">
                  <Check />
                  <h3>No hay pendientes aquí</h3>
                  <p>
                    Los nuevos pedidos y campañas por revisar aparecerán en esta
                    lista.
                  </p>
                </div>
              )}
              <p className="panel-note">{d.attention_period}</p>
            </section>
            <aside className="home-aside">
              <section className="work-surface quick-actions">
                <h2>Hacer algo</h2>
                <a href={link("campaigns", { campaign: "new" })}>
                  <Megaphone />
                  Crear campaña
                  <Plus size={16} />
                </a>
                <a href={link("customers", { invite: "1" })}>
                  <Users />
                  Invitar clientes
                  <ArrowRight size={16} />
                </a>
                <a href={link("analytics")}>
                  <Globe2 />
                  Ver analítica web<span className="number-chip">Demo</span>
                </a>
              </section>
              <section className="identity-note">
                <Palette size={22} />
                <strong>101 Workspace</strong>
                <p>Los mismos controles, en todo tu espacio.</p>
                <a href={link("identity")}>
                  Ver identidad <ArrowUpRight size={14} />
                </a>
              </section>
            </aside>
          </div>
          <section className="work-surface activity-panel">
            <div className="section-heading">
              <h2>Actividad reciente</h2>
              <span className="caption">Registros del periodo</span>
            </div>
            {d.activity.length ? (
              d.activity.map((e) => {
                const I = Icon[e.kind];
                return (
                  <a className="activity-row" key={e.id} href={e.href}>
                    <I size={17} />
                    <span>{e.title}</span>
                    <time>{date(e.at || null)}</time>
                    <ArrowUpRight size={15} />
                  </a>
                );
              })
            ) : (
              <p className="panel-note">
                No hay actividad registrada en estas fechas.
              </p>
            )}
          </section>
        </>
      )}
    </div>
  );
}
export function AnalyticsView(props: ViewProps) {
  const p = currentPeriod(props.params);
  const [metric, setMetric] = useState<"sessions" | "views">("sessions");
  const start = new Date(p.from + "T12:00Z"),
    end = new Date(p.to + "T12:00Z");
  const days = Math.round((+end - +start) / 86400000) + 1;
  if (!Number.isFinite(days) || days < 1 || days > 366)
    return (
      <div className="page new-view">
        <PageHeading title="Analítica web" />
        <PeriodPicker {...props} />
        <p role="alert">Elige un periodo de hasta 366 días.</p>
      </div>
    );
  const data = Array.from({ length: days }, (_, i) => {
    const d = new Date(+start + i * 86400000);
    const n = Math.floor(+d / 86400000);
    const sessions = 38 + ((((n * 17) % 71) + 71) % 71);
    return {
      day: d.toISOString().slice(0, 10),
      sessions,
      views: sessions * (2 + (((n % 3) + 3) % 3)),
    };
  });
  const sessions = data.reduce((a, d) => a + d.sessions, 0),
    views = data.reduce((a, d) => a + d.views, 0);
  const max = Math.max(...data.map((d) => d[metric]));
  const shares = [
    ["Directo", 0.4],
    ["Google", 0.31],
    ["Instagram", 0.19],
  ] as const;
  const sources: { name: string; n: number }[] = shares.map(([name, n]) => ({
    name,
    n: Math.floor(sessions * n),
  }));
  sources.push({
    name: "Otros",
    n: sessions - sources.reduce((a, b) => a + b.n, 0),
  });
  return (
    <div className="page new-view analytics-view">
      <PageHeading
        title="Analítica web"
        description="Visitas, páginas y de dónde llegan."
      >
        <PeriodPicker {...props} />
      </PageHeading>
      <div className="demo-notice">
        <span className="demo-dot" />
        <strong>Datos de ejemplo</strong>
        <span>
          Este gráfico es una maqueta. No hay un medidor web conectado.
        </span>
      </div>
      <section className="result-strip analytics-metrics">
        <button
          className={metric === "sessions" ? "selected" : ""}
          onClick={() => setMetric("sessions")}
          aria-pressed={metric === "sessions"}
        >
          <span>Visitas</span>
          <strong>{count(sessions)}</strong>
          <small>Sesiones de ejemplo</small>
        </button>
        <button
          className={metric === "views" ? "selected" : ""}
          onClick={() => setMetric("views")}
          aria-pressed={metric === "views"}
        >
          <span>Páginas vistas</span>
          <strong>{count(views)}</strong>
          <small>Ejemplo · incluye visitas repetidas</small>
        </button>
        <div>
          <span>Páginas por visita</span>
          <strong>{(views / sessions).toFixed(1)}</strong>
          <small>Datos de ejemplo</small>
        </div>
      </section>
      <section className="work-surface chart-panel">
        <div className="section-heading">
          <h2>
            {metric === "sessions" ? "Visitas" : "Páginas vistas"} por día
          </h2>
          <span className="chart-legend">
            <i />
            Ejemplo
          </span>
        </div>
        <div className="chart-with-scale">
          <div className="chart-scale" aria-hidden="true">
            <span>{count(max)}</span>
            <span>{count(Math.round(max / 2))}</span>
            <span>0</span>
          </div>
          <svg
            className="traffic-chart"
            viewBox="0 0 1000 210"
            role="img"
            aria-label={`Serie de ejemplo: ${metric === "sessions" ? "visitas" : "páginas vistas"} diarias, tabla disponible debajo`}
            preserveAspectRatio="none"
          >
            {[30, 110, 190].map((y) => (
              <line
                key={y}
                x1="0"
                x2="1000"
                y1={y}
                y2={y}
                stroke="var(--wm-line)"
              />
            ))}
            {data.map((d, i) => (
              <rect
                key={d.day}
                x={(i * 1000) / days + 2}
                y={190 - (d[metric] / max) * 160}
                width={Math.max(1, 1000 / days - 5)}
                height={(d[metric] / max) * 160}
                rx={Math.min(4, 1000 / days / 5)}
                fill={
                  i === days - 1
                    ? "var(--wm-chart-primary)"
                    : "var(--wm-chart-secondary)"
                }
              >
                <title>
                  {d.day}: {d[metric]}
                </title>
              </rect>
            ))}
          </svg>
        </div>
        <div className="chart-axis">
          <span>{p.from}</span>
          <span>{p.to}</span>
        </div>
        <details className="chart-data">
          <summary>Ver datos diarios</summary>
          <div className="small-table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Visitas</th>
                  <th>Páginas vistas</th>
                </tr>
              </thead>
              <tbody>
                {data.map((d) => (
                  <tr key={d.day}>
                    <td>{d.day}</td>
                    <td>{d.sessions}</td>
                    <td>{d.views}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      </section>
      <div className="analytics-columns">
        <section className="work-surface">
          <div className="section-heading">
            <h2>De dónde llegan</h2>
            <span className="caption">Visitas de ejemplo</span>
          </div>
          {sources.map((s) => (
            <div className="source-row" key={s.name}>
              <span>{s.name}</span>
              <div className="bar-track">
                <svg
                  viewBox="0 0 100 8"
                  preserveAspectRatio="none"
                  aria-hidden="true"
                >
                  <rect
                    width={(s.n / sessions) * 100}
                    height="8"
                    rx="4"
                    fill="var(--wm-chart-secondary)"
                  />
                </svg>
              </div>
              <strong>{count(s.n)}</strong>
            </div>
          ))}
        </section>
        <section className="work-surface">
          <div className="section-heading">
            <h2>Páginas</h2>
            <span className="caption">Vistas de ejemplo</span>
          </div>
          {[
            ["/", 0.5],
            ["/carta", 0.32],
            ["/ubicacion", 0.18],
          ].map(([path, share], i) => (
            <div className="source-row page-source" key={String(path)}>
              <span>{path}</span>
              <strong>
                {count(
                  i === 2
                    ? views - Math.floor(views * 0.5) - Math.floor(views * 0.32)
                    : Math.floor(views * Number(share)),
                )}
              </strong>
            </div>
          ))}
        </section>
      </div>
      <p className="data-footnote">
        Las fechas cambian el ejemplo. Estos números no se guardan como
        actividad ni ventas de tu negocio.
      </p>
    </div>
  );
}
export function IdentityView() {
  return (
    <div className="page new-view">
      <PageHeading
        title="101 Workspace"
        description="Identidad del producto · versión 0.1.0"
      />
      <section className="work-surface identity-showcase">
        <h2>Claro. Rápido. Útil.</h2>
        <p>
          Un espacio para trabajar. Texto legible, acciones directas y datos que
          podemos explicar.
        </p>
        <div className="swatch-row">
          {[
            "canvas",
            "surface",
            "ink",
            "accent",
            "accent-soft",
            "success",
            "warning",
          ].map((role) => (
            <div key={role}>
              <span className={"swatch swatch-" + role} />
              <small>{role}</small>
            </div>
          ))}
        </div>
        <div className="type-samples">
          <div className="sample-title">Título de pantalla</div>
          <h2>Una sección</h2>
          <p>Texto de trabajo. Los detalles se leen sin esfuerzo.</p>
          <small>Una fecha, un estado o una aclaración corta.</small>
        </div>
        <div className="sample-controls">
          <button className="button primary">
            Acción principal <ArrowRight size={16} />
          </button>
          <button className="button secondary">Acción secundaria</button>
          <span className="badge verified">Verificado</span>
        </div>
        <p className="panel-note">
          Muestras visuales; estos botones no ejecutan acciones.
        </p>
      </section>
      <section className="work-surface identity-showcase">
        <h2>Una fuente, varias pantallas</h2>
        <p>
          Clientes, Ventas, Inicio, Campañas y Analítica usan la misma
          tipografía, colores y controles. Cada cambio de dirección actualiza la
          identidad y se revisa en pantallas reales.
        </p>
        <dl className="identity-rules">
          <div>
            <dt>Tipografía</dt>
            <dd>Manrope · nombres 15px · etiquetas 14px · detalle 12px</dd>
          </div>
          <div>
            <dt>Espacio</dt>
            <dd>Ritmo 4/8px · separación 24px · controles 44px</dd>
          </div>
          <div>
            <dt>Voz</dt>
            <dd>Decir qué pasó y qué puedes hacer. Sin frases vacías.</dd>
          </div>
          <div>
            <dt>Revisión</dt>
            <dd>
              Referencias → pantalla real → inspección → ajuste → otra
              inspección.
            </dd>
          </div>
        </dl>
      </section>
    </div>
  );
}
