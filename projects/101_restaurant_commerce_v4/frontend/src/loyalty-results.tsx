import { useRef, useState } from "react";
import { Dialog } from "@base-ui/react/dialog";
import { Download, RefreshCw, X } from "lucide-react";
import { date, Failure, Loading, useResource } from "./ui";
import {
  CommandState,
  editableMoney,
  Field,
  minor,
  money,
  useCommand,
  type Experiment,
  type Nav,
  type Resource,
} from "./loyalty-shared";

type Evidence = {
  id?: string;
  revision: number;
  source_ref?: string;
  recorded_at?: string;
  document: null | {
    variable_cost_minor?: number;
    additional_reward_cost_minor?: number;
    operating_cost_minor?: number;
    includes_estimate: boolean;
  };
};
type CostContext = {
  financial_digest: string;
  latest: Evidence;
  stale: boolean;
  history: Evidence[];
};
type Arm = {
  variant_id: string;
  name: string;
  control: boolean;
  assigned_customers: number;
  mature_customers: number;
  nonbuyers: number;
  buyers: number;
  purchase_count: number;
  purchase_frequency: string | null;
  revenue_per_assigned_minor: string | null;
  profit_per_assigned_minor: string | null;
  exposed_customers: number;
  contaminated_customers: number;
  issued_points: string;
  redeemed_points: string;
  estimated_outstanding_cost_minor: string;
  missing_contribution_customers: number;
  missing_operating_cost: boolean;
  operating_cost_minor: string | null;
  repeat_purchase: Record<
    string,
    { eligible_assigned: number; repeat_customers: number; rate: string | null }
  >;
};
type Comparison = {
  variant_id: string;
  incremental_profit_per_assigned_minor: string | null;
  confidence_interval: null | {
    lower_minor: string;
    upper_minor: string;
    family_confidence_bps: number;
    comparisons: number;
  };
  suppression_reasons: string[];
};
type Result = {
  name: string;
  currency: string;
  as_of: string;
  data_revision: string;
  experiment_version_id: string;
  observation_days: number;
  assigned_customers: number;
  mature_customers: number;
  primary_evaluation_complete: boolean;
  analysis_protocol: Experiment["analysis_protocol"];
  arms: Arm[];
  comparisons: Comparison[];
  coverage: Record<string, number>;
  warnings: string[];
  cost_orders: {
    total: number;
    truncated: boolean;
    items: {
      order_id: string;
      order_code: string;
      variant_id: string;
      currency: string;
      stale: boolean;
      latest: Evidence;
    }[];
  };
  missing_orders: { total: number };
};

const warningLabels: Record<string, string> = {
  analysis_protocol_late:
    "El plan quedó registrado después de una asignación; la evaluación requiere revisión.",
  observed_channels_only:
    "Solo se observan las compras registradas en este sistema.",
  current_refunds_revise_window_orders:
    "Los reembolsos confirmados hoy actualizan las compras del período original.",
  no_automatic_winner: "Este informe no elige una recompensa ganadora.",
  experiment_not_enrolled:
    "Todavía no hay una cohorte asignada para este experimento.",
  analysis_protocol_missing:
    "La versión original no tiene un plan estadístico estructurado; sus resultados son descriptivos.",
  incomplete_observation_windows:
    "Hay clientes que todavía no completan su período de seguimiento.",
  insufficient_sample_size:
    "Algún grupo no alcanza el mínimo de clientes previsto.",
  scheduled_readout_not_reached:
    "Todavía no llega la fecha de evaluación acordada.",
  enrollment_still_open: "La inscripción del experimento sigue abierta.",
  missing_or_stale_contribution:
    "Faltan costos de pedidos o deben actualizarse tras cambios financieros.",
  missing_or_stale_operating_cost:
    "Faltan costos operativos por grupo o cambió la cohorte que cubren.",
  missing_financial_evidence:
    "La ganancia no puede calcularse con la evidencia financiera disponible.",
  financial_costs_include_estimates:
    "Parte de los costos incluye estimaciones; revisa sus fuentes y supuestos.",
  identity_coverage_incomplete:
    "Hay pedidos sin identidad verificada; no se atribuyen a un grupo por sus datos de contacto.",
  experiment_contamination:
    "Algunos clientes participan en otros experimentos durante el seguimiento o período de protección.",
  off_protocol_rewards:
    "Algunas compras recibieron una regla adicional diferente de la asignada.",
  allocation_imbalance:
    "La distribución observada difiere de la prevista; revisa la asignación antes de interpretar efectos.",
  allocation_diagnostic_unavailable:
    "La muestra no permite comprobar con fiabilidad la distribución entre grupos.",
  financial_review_open: "Hay compras con revisión financiera pendiente.",
  unresolved_order_at_window:
    "Hay pedidos cuyo resultado financiero no está resuelto dentro del período.",
  currency_mismatch:
    "Hay compras en otra moneda; no se suman como si fueran equivalentes.",
  payment_inconsistency: "Hay registros de cobro que requieren conciliación.",
  unattributed_reward_cost:
    "Hay movimientos de recompensas sin un pedido que permita establecer su costo.",
  mixed_simulated_and_other_payments:
    "La cohorte mezcla pagos simulados y otros medios de pago.",
  zero_observed_variance:
    "La muestra no tiene variación observada suficiente para estimar un intervalo.",
  exposures_outside_followup:
    "Hay recibos de exposición fuera del seguimiento; se muestran separados de la exposición del período.",
  exposure_receipt_warnings:
    "Algunos recibos de exposición tienen observaciones que requieren revisión.",
};
const warning = (key: string) =>
  warningLabels[key] || "Revisa la cobertura de este informe.";

// Display rounding only. Monetary values remain decimal strings/BigInt throughout.
export function meanMoney(value: string | null, currency: string) {
  if (value === null) return "Sin datos";
  const negative = value.startsWith("-"),
    [whole, fraction = ""] = value.replace("-", "").split(".");
  const exact =
    BigInt(whole) * 1000000n + BigInt(fraction.padEnd(6, "0").slice(0, 6));
  const divisor = currency === "COP" ? 10000n : 1000000n;
  const cents = (exact + divisor / 2n) / divisor;
  return `${negative && cents ? "−" : ""}$ ${(cents / 100n).toLocaleString("es-CO")},${String(cents % 100n).padStart(2, "0")} ${currency}`;
}

function WarningList({ codes }: { codes: string[] }) {
  return (
    <ul className="loyalty-result-warnings">
      {codes.map((code) => (
        <li key={code}>{warning(code)}</li>
      ))}
    </ul>
  );
}

export function LoyaltyResults({
  root,
  csrf,
  enabled,
  canFinance,
  selected,
  navigate,
}: {
  root: string;
  csrf: string;
  enabled: boolean;
  canFinance: boolean;
  selected: string | null;
  navigate: Nav;
}) {
  const experiments = useResource<Resource<Experiment>[]>(
    enabled ? `${root}/experiments` : null,
  );
  const result = useResource<Result>(
    enabled && selected
      ? `${root}/experiments/${encodeURIComponent(selected)}/report`
      : null,
  );
  const [target, setTarget] = useState<{
    kind: "orders" | "variants";
    id: string;
    title: string;
    currency: string;
  } | null>(null);
  if (!enabled)
    return (
      <section className="state">
        <h2>Resultados aún no habilitados</h2>
        <p>
          La medición financiera necesita su actualización y configuración antes
          de consultar resultados.
        </p>
      </section>
    );
  if (experiments.error)
    return <Failure message={experiments.error} retry={experiments.retry} />;
  if (!experiments.data) return <Loading />;
  const data = result.data;
  return (
    <section className="loyalty-results">
      <div className="loyalty-title-row">
        <div>
          <h2>Resultados de experimentos</h2>
          <p>
            Compara la ganancia por cada persona asignada, incluidas quienes no
            compran.
          </p>
        </div>
        {data && (
          <button className="button secondary" onClick={result.retry}>
            <RefreshCw size={16} />
            Actualizar informe
          </button>
        )}
      </div>
      <div className="loyalty-result-picker">
        <Field label="Experimento para evaluar">
          <select
            value={selected || ""}
            onChange={(e) => {
              setTarget(null);
              navigate({ loyaltyId: e.target.value || null }, true);
            }}
          >
            <option value="">Selecciona un experimento publicado</option>
            {experiments.data
              .filter((e) => e.versions.length)
              .map((e) => (
                <option key={e.id} value={e.id}>
                  {e.document.name}
                </option>
              ))}
          </select>
        </Field>
      </div>
      {!selected ? (
        <div className="state">
          <h3>Elige una comparación</h3>
          <p>
            La asignación original y su período se conservan aunque después
            cambien las reglas.
          </p>
        </div>
      ) : result.error ? (
        <Failure message={result.error} retry={result.retry} />
      ) : !data ? (
        <Loading />
      ) : (
        <>
          <div className="loyalty-title-row">
            <div>
              <h3>{data.name}</h3>
              <p>
                Seguimiento de {data.observation_days} días por cliente · datos
                al {date(data.as_of)}
              </p>
            </div>
            <a
              className="button secondary"
              href={`${root}/experiments/${encodeURIComponent(selected)}/report.csv`}
            >
              <Download size={16} />
              Exportar CSV
            </a>
          </div>
          <div className="loyalty-metrics">
            <div>
              <span>Personas asignadas</span>
              <strong>{data.assigned_customers}</strong>
              <small>Denominador original, con y sin compras</small>
            </div>
            <div>
              <span>Seguimiento completo</span>
              <strong>
                {data.mature_customers} / {data.assigned_customers}
              </strong>
              <small>{data.observation_days} días observados por persona</small>
            </div>
            <div>
              <span>Pedidos con costos pendientes</span>
              <strong>{data.missing_orders.total}</strong>
              <small>La falta de datos no equivale a costo cero</small>
            </div>
          </div>
          <section
            className="loyalty-section"
            aria-label="Evaluación principal"
          >
            <div className="loyalty-title-row">
              <h3>Ganancia incremental por cliente asignado</h3>
              <span className="badge">
                {data.primary_evaluation_complete
                  ? "Evaluación disponible"
                  : "Lectura provisional"}
              </span>
            </div>
            <p>
              La diferencia compara cada oferta con el control. Los intervalos
              expresan incertidumbre; no seleccionan una oferta automáticamente.
            </p>
            <div
              className="loyalty-table-wrap"
              role="region"
              tabIndex={0}
              aria-label="Comparaciones con el control"
            >
              <table>
                <thead>
                  <tr>
                    <th>Oferta</th>
                    <th>Diferencia por cliente</th>
                    <th>Intervalo de confianza</th>
                  </tr>
                </thead>
                <tbody>
                  {data.comparisons.map((c) => (
                    <tr key={c.variant_id}>
                      <td>
                        {
                          data.arms.find((a) => a.variant_id === c.variant_id)
                            ?.name
                        }
                      </td>
                      <td>
                        {meanMoney(
                          c.incremental_profit_per_assigned_minor,
                          data.currency,
                        )}
                      </td>
                      <td>
                        {c.confidence_interval ? (
                          <>
                            {money(
                              c.confidence_interval.lower_minor,
                              data.currency,
                            )}{" "}
                            a{" "}
                            {money(
                              c.confidence_interval.upper_minor,
                              data.currency,
                            )}
                            <small className="loyalty-hint">
                              Confianza conjunta{" "}
                              {c.confidence_interval.family_confidence_bps /
                                100}
                              % · {c.confidence_interval.comparisons}{" "}
                              comparación(es)
                            </small>
                          </>
                        ) : (
                          <details>
                            <summary>No disponible</summary>
                            <WarningList codes={c.suppression_reasons} />
                          </details>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <details className="loyalty-section loyalty-result-notes">
            <summary>
              Qué revisar antes de interpretar ({data.warnings.length})
            </summary>
            <WarningList codes={data.warnings} />
          </details>
          <section className="loyalty-section">
            <h3>Cada grupo completo</h3>
            <p>
              Las compras completadas cuentan para frecuencia; sus reembolsos
              posteriores actualizan los ingresos y la ganancia.
            </p>
            <div
              className="loyalty-table-wrap"
              role="region"
              tabIndex={0}
              aria-label="Resultados por grupo"
            >
              <table>
                <thead>
                  <tr>
                    <th>Grupo</th>
                    <th>Asignados / sin compras</th>
                    <th>Compras por cliente</th>
                    <th>Ingreso neto por cliente</th>
                    <th>Ganancia por cliente</th>
                  </tr>
                </thead>
                <tbody>
                  {data.arms.map((a) => (
                    <tr key={a.variant_id}>
                      <td>
                        <strong>{a.name}</strong>
                        {a.control && (
                          <small className="loyalty-hint">
                            Control · beneficios habituales
                          </small>
                        )}
                      </td>
                      <td>
                        {a.assigned_customers} / {a.nonbuyers}
                      </td>
                      <td>
                        {a.purchase_frequency === null
                          ? "Sin datos"
                          : Number(a.purchase_frequency).toFixed(2)}
                      </td>
                      <td>
                        {meanMoney(a.revenue_per_assigned_minor, data.currency)}
                      </td>
                      <td>
                        {meanMoney(a.profit_per_assigned_minor, data.currency)}
                        {(a.missing_contribution_customers > 0 ||
                          a.missing_operating_cost) && (
                          <small className="loyalty-hint">
                            Costos incompletos
                          </small>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <section className="loyalty-section">
            <h3>Segunda compra en 30, 60 y 90 días</h3>
            <p>
              Dos o más compras posteriores a la asignación. Cada plazo usa solo
              personas con seguimiento completo para ese plazo, incluidas
              quienes no compraron.
            </p>
            <div
              className="loyalty-table-wrap"
              role="region"
              tabIndex={0}
              aria-label="Recompra por período"
            >
              <table>
                <thead>
                  <tr>
                    <th>Grupo</th>
                    <th>30 días</th>
                    <th>60 días</th>
                    <th>90 días</th>
                  </tr>
                </thead>
                <tbody>
                  {data.arms.map((a) => (
                    <tr key={a.variant_id}>
                      <td>{a.name}</td>
                      {[30, 60, 90].map((days) => {
                        const r = a.repeat_purchase[String(days)];
                        return (
                          <td key={days}>
                            {r.rate === null
                              ? "Seguimiento incompleto"
                              : `${(Number(r.rate) * 100).toFixed(1)} %`}
                            <small className="loyalty-hint">
                              {r.repeat_customers} / {r.eligible_assigned}{" "}
                              personas
                            </small>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <details className="loyalty-section">
            <summary>Recompensas, exposición y costos</summary>
            <p>
              La exposición y el canje se describen por separado; no determinan
              quién entra en la comparación.
            </p>
            <div
              className="loyalty-table-wrap"
              role="region"
              tabIndex={0}
              aria-label="Recompensas por grupo"
            >
              <table>
                <thead>
                  <tr>
                    <th>Grupo</th>
                    <th>Personas expuestas</th>
                    <th>Puntos emitidos / canjeados</th>
                    <th>Costo pendiente estimado</th>
                    <th>Costo operativo</th>
                  </tr>
                </thead>
                <tbody>
                  {data.arms.map((a) => (
                    <tr key={a.variant_id}>
                      <td>{a.name}</td>
                      <td>{a.exposed_customers}</td>
                      <td>
                        {a.issued_points} / {a.redeemed_points}
                      </td>
                      <td>
                        {meanMoney(
                          a.estimated_outstanding_cost_minor,
                          data.currency,
                        )}
                        <small className="loyalty-hint">
                          Estimación por lotes; no se suma otra vez a la
                          ganancia
                        </small>
                      </td>
                      <td>
                        {a.operating_cost_minor === null
                          ? "Sin evidencia vigente"
                          : money(a.operating_cost_minor, data.currency)}
                        {canFinance && (
                          <button
                            className="button secondary"
                            onClick={() =>
                              setTarget({
                                kind: "variants",
                                id: a.variant_id,
                                title: `Costo operativo · ${a.name}`,
                                currency: data.currency,
                              })
                            }
                          >
                            Registrar costo de {a.name}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p>
              Los costos operativos se reparten entre todas las personas
              originalmente asignadas a su grupo, incluso si no compran. Los
              descuentos ya reducen los cobros: no se restan dos veces.
            </p>
          </details>
          <details className="loyalty-section">
            <summary>Costos de pedidos ({data.cost_orders.total})</summary>
            <p>
              Se necesitan costos variables y costos adicionales de recompensas
              respaldados por una fuente. Un cambio de reembolso o recompensa
              exige revisar la evidencia anterior.
            </p>
            <div
              className="loyalty-table-wrap"
              role="region"
              tabIndex={0}
              aria-label="Cobertura de costos por pedido"
            >
              <table>
                <thead>
                  <tr>
                    <th>Pedido</th>
                    <th>Grupo</th>
                    <th>Evidencia</th>
                    <th>Acción</th>
                  </tr>
                </thead>
                <tbody>
                  {data.cost_orders.items.map((o) => (
                    <tr key={o.order_id}>
                      <td>{o.order_code}</td>
                      <td>
                        {
                          data.arms.find((a) => a.variant_id === o.variant_id)
                            ?.name
                        }
                      </td>
                      <td>
                        {o.stale
                          ? "Revisar cambios"
                          : o.latest.revision
                            ? `Versión ${o.latest.revision}`
                            : "Sin costos registrados"}
                      </td>
                      <td>
                        {canFinance ? (
                          <button
                            className="button secondary"
                            onClick={() =>
                              setTarget({
                                kind: "orders",
                                id: o.order_id,
                                title: `Costos del pedido ${o.order_code}`,
                                currency: o.currency,
                              })
                            }
                          >
                            Registrar costos de {o.order_code}
                          </button>
                        ) : (
                          "Requiere rol financiero"
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {data.cost_orders.truncated && (
              <p>
                Se muestran los primeros 100 pedidos. La cobertura y los totales
                incluyen todos.
              </p>
            )}
          </details>
          <details className="loyalty-section">
            <summary>Criterios y procedencia</summary>
            <p>
              Solo se atribuyen pedidos con identidad verificada, iniciados y
              completados dentro del seguimiento original, y cancelaciones con
              costos. Los pedidos de contacto sin verificar quedan fuera de los
              grupos y reducen la cobertura.
            </p>
            <p>
              {data.coverage.verified_financial_orders || 0} /{" "}
              {data.coverage.observed_financial_orders || 0} pedidos financieros
              con identidad verificada en el período observado del negocio.
            </p>
            <p>
              Los costos adicionales incluyen el cumplimiento y la provisión
              estimada de recompensas pendientes, excluyendo descuentos ya
              deducidos. El costo pendiente por lotes es informativo; el saldo
              histórico sin fuente sigue sin valorar.
            </p>
            <p>
              Los reembolsos confirmados actualmente corrigen pedidos del
              período. No se reconstruye un cierre financiero histórico. Guarda
              el CSV para conservar cada lectura.
            </p>
            {data.analysis_protocol && (
              <p>
                Lectura acordada: {date(data.analysis_protocol.readout_at)}.
                Mínimo previsto:{" "}
                {data.analysis_protocol.minimum_customers_per_arm} personas por
                grupo. {data.analysis_protocol.sample_size_rationale} El mínimo
                declarado no garantiza potencia estadística.
              </p>
            )}
            <p>
              Intervalos Welch por cliente, ajustados por las comparaciones con
              control (Bonferroni). No corrigen lecturas repetidas ni compras
              fuera de los canales observados. Expresan variación entre
              clientes, condicionada a los costos suministrados; no incluyen la
              incertidumbre de estimar esos costos.
            </p>
            <p className="loyalty-hint">
              Versión del experimento: {data.experiment_version_id}
              <br />
              Revisión de datos: {data.data_revision}
            </p>
          </details>
        </>
      )}
      {target && (
        <CostDialog
          key={`${target.kind}:${target.id}`}
          root={root}
          csrf={csrf}
          target={target}
          close={() => setTarget(null)}
          saved={() => {
            setTarget(null);
            result.retry();
          }}
        />
      )}
    </section>
  );
}

function CostDialog({
  root,
  csrf,
  target,
  close,
  saved,
}: {
  root: string;
  csrf: string;
  target: {
    kind: "orders" | "variants";
    id: string;
    title: string;
    currency: string;
  };
  close: () => void;
  saved: () => void;
}) {
  const resource = useResource<CostContext>(
    `${root}/analytics/${target.kind}/${encodeURIComponent(target.id)}`,
  );
  const command = useCommand(csrf),
    blocked = command.busy || command.uncertain;
  return (
    <Dialog.Root
      open
      onOpenChange={(open) => {
        if (!open && !command.hasPending()) close();
      }}
    >
      <Dialog.Portal>
        <Dialog.Backdrop className="dialog-backdrop" />
        <Dialog.Popup className="loyalty-review">
          <div className="loyalty-title-row">
            <Dialog.Title>{target.title}</Dialog.Title>
            <Dialog.Close
              className="icon-button"
              aria-label="Cerrar costos"
              disabled={blocked}
            >
              <X />
            </Dialog.Close>
          </div>
          <Dialog.Description>
            La evidencia queda conservada con su fuente y autor. Las
            correcciones crean una versión nueva.
          </Dialog.Description>
          {resource.error ? (
            <Failure message={resource.error} retry={resource.retry} />
          ) : !resource.data ? (
            <Loading />
          ) : (
            <CostForm
              key={`${resource.data.latest.revision}:${resource.data.financial_digest}`}
              data={resource.data}
              url={`${root}/analytics/${target.kind}/${encodeURIComponent(target.id)}`}
              command={command}
              currency={target.currency}
              kind={target.kind}
              reload={resource.retry}
              saved={saved}
              close={close}
            />
          )}
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function CostForm({
  data,
  url,
  command,
  currency,
  kind,
  reload,
  saved,
  close,
}: {
  data: CostContext;
  url: string;
  command: ReturnType<typeof useCommand>;
  currency: string;
  kind: "orders" | "variants";
  reload: () => void;
  saved: () => void;
  close: () => void;
}) {
  const previous = data.latest.document;
  const [variable, setVariable] = useState(
    previous?.variable_cost_minor === undefined
      ? ""
      : editableMoney(previous.variable_cost_minor, currency),
  );
  const [reward, setReward] = useState(
    previous?.additional_reward_cost_minor === undefined
      ? ""
      : editableMoney(previous.additional_reward_cost_minor, currency),
  );
  const [operating, setOperating] = useState(
    previous?.operating_cost_minor === undefined
      ? ""
      : editableMoney(previous.operating_cost_minor, currency),
  );
  const [source, setSource] = useState(data.latest.source_ref || ""),
    [estimate, setEstimate] = useState(previous?.includes_estimate ?? true);
  const key = useRef(crypto.randomUUID());
  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    let values;
    try {
      values =
        kind === "orders"
          ? {
              variable_cost_minor: minor(variable, currency, true),
              additional_reward_cost_minor: minor(reward, currency, true),
            }
          : { operating_cost_minor: minor(operating, currency) };
    } catch (error) {
      command.fail((error as Error).message);
      return;
    }
    const body = {
      ...values,
      request_key: key.current,
      expected_revision: data.latest.revision,
      financial_digest: data.financial_digest,
      source_ref: source,
      includes_estimate: estimate,
    };
    await command.run(async () => {
      await command.send(url, "POST", body);
      if (command.alive.current) saved();
    });
  };
  return (
    <form onSubmit={save}>
      <fieldset
        disabled={command.busy || command.uncertain}
        className="loyalty-cost-fields"
      >
        {data.stale && (
          <p className="loyalty-notice">
            Los registros financieros cambiaron. Revisa los importes antes de
            crear la siguiente versión.
          </p>
        )}
        {kind === "orders" ? (
          <>
            <Field
              label={`Costos variables (${currency})`}
              hint="Ingredientes, preparación, entrega y comisiones, después de recuperaciones. Excluye los costos adicionales de recompensas."
            >
              <input
                inputMode="decimal"
                value={variable}
                onChange={(e) => setVariable(e.target.value)}
                required
              />
            </Field>
            <Field
              label={`Costos adicionales de recompensas (${currency})`}
              hint="Cumplimiento y costo estimado pendiente de beneficios habituales y adicionales. Excluye descuentos ya deducidos del cobro; registra cero solo con evidencia."
            >
              <input
                inputMode="decimal"
                value={reward}
                onChange={(e) => setReward(e.target.value)}
                required
              />
            </Field>
          </>
        ) : (
          <Field
            label={`Costo operativo total del grupo (${currency})`}
            hint="Cubre el experimento completo y todas las personas asignadas al grupo. Si crece la cohorte, esta evidencia requiere revisión."
          >
            <input
              inputMode="decimal"
              value={operating}
              onChange={(e) => setOperating(e.target.value)}
              required
            />
          </Field>
        )}
        <Field label="Fuente de los costos">
          <input
            value={source}
            minLength={3}
            maxLength={500}
            onChange={(e) => setSource(e.target.value)}
            required
          />
        </Field>
        <label className="loyalty-check">
          <input
            type="checkbox"
            checked={estimate}
            onChange={(e) => setEstimate(e.target.checked)}
          />
          Incluye costos estimados
        </label>
      </fieldset>
      <CommandState command={command} />
      <div className="loyalty-actions">
        <button className="button" disabled={command.busy || command.uncertain}>
          Guardar evidencia
        </button>
        <button
          className="button secondary"
          type="button"
          disabled={command.busy || command.uncertain}
          onClick={reload}
        >
          Recargar registros
        </button>
        <button
          className="button secondary"
          type="button"
          disabled={command.busy || command.uncertain}
          onClick={close}
        >
          Cerrar
        </button>
      </div>
      {data.history.length > 0 && (
        <details>
          <summary>Últimas {data.history.length} versiones de costos</summary>
          <ul>
            {data.history.map((h) => (
              <li key={h.id}>
                Versión {h.revision} ·{" "}
                {h.recorded_at ? date(h.recorded_at) : ""} · {h.source_ref}
                <p>
                  {h.document?.operating_cost_minor !== undefined
                    ? `Operación: ${money(h.document.operating_cost_minor, currency)}`
                    : `Variables: ${money(h.document?.variable_cost_minor || 0, currency)} · Recompensas adicionales: ${money(h.document?.additional_reward_cost_minor || 0, currency)}`}{" "}
                  {h.document?.includes_estimate
                    ? "Incluye estimaciones."
                    : "Costos realizados."}
                </p>
              </li>
            ))}
          </ul>
        </details>
      )}
    </form>
  );
}
