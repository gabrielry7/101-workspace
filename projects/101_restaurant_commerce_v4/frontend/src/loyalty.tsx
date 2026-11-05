import { useState } from "react";
import { Dialog } from "@base-ui/react/dialog";
import { ArrowLeft, Plus, RefreshCw, X } from "lucide-react";
import { api, date, endpoint, Failure, Loading, useResource } from "./ui";
import { ProgramEditor } from "./loyalty-program";
import { ExperimentEditor } from "./loyalty-experiment";
import { Economics } from "./loyalty-economics";
import { LoyaltyResults } from "./loyalty-results";
import {
  CommandState,
  money,
  percent,
  points,
  statuses,
  useCommand,
  type Experiment,
  type Nav,
  type Program,
  type Resource,
} from "./loyalty-shared";
import "./loyalty.css";

type Overview = {
  currency: string;
  as_of: string;
  wallets: Record<string, string>;
  costs: {
    currency: string;
    recorded_cost_minor: string;
    expected_cost_minor: string;
    due_expiry_points: string;
    due_expiry_cost_minor: string;
    tracked_points: string;
  }[];
  budgets: {
    program_id: string;
    name: string;
    currency: string | null;
    reserved_minor: string;
    committed_minor: string;
  }[];
  legacy_cost_minor: string | null;
  execution_history_available: boolean;
  refund_holds: {
    items: {
      order_id: string;
      order_code: string;
      customer: string;
      currency: string;
      refund_minor: string;
      reasons: string[];
    }[];
    truncated: boolean;
    scan_limit: number;
  };
  financial_reviews: {
    count: number;
    limit: number;
    items: {
      id: string;
      order_id: string;
      order_code: string;
      reason: string;
      at: string;
    }[];
  };
  ledger: {
    id: string;
    customer: string;
    order_id: string | null;
    order_code: string | null;
    points: number;
    reason: string;
    at: string;
    version_id: string | null;
  }[];
};
const tabNames: Record<string, string> = {
  programs: "Programas",
  experiments: "Experimentos",
  economics: "Calculadora",
  exposure: "Saldos y costos",
  results: "Resultados",
};
const holdLabels: Record<string, string> = {
  historical_policy_missing: "Falta la política original",
  refund_allocation_required: "Falta distribuir el reembolso",
  execution_history_unavailable: "Historial de recompensa no disponible",
};
const eventLabels: Record<string, string> = {
  "order.completed": "Compra completada",
  "order.refunded": "Puntos revertidos por reembolso",
  "reward.reserved": "Puntos reservados",
  "reward.released": "Puntos devueltos",
  "loyalty.earned": "Puntos adicionales ganados",
  "loyalty.refund_reversal": "Reversión de puntos adicionales",
  "loyalty.refund_credit": "Canje devuelto",
  "loyalty.expired": "Vencimiento",
  "loyalty.refund_retired": "Reversión conciliada",
  "refund.reward_credit": "Puntos de canje devueltos",
  "refund.debt_repaid": "Saldo pendiente recuperado",
  "loyalty.refund_recovery_returned": "Saldo recuperado devuelto",
  "loyalty.refunded_return_retired": "Puntos de compra reembolsada retirados",
  "loyalty.restored_expired": "Puntos devueltos ya vencidos",
};

export function LoyaltyWorkspace({
  business,
  permissions,
  csrf,
  params,
  navigate,
}: {
  business: string;
  permissions: string[];
  csrf: string;
  params: URLSearchParams;
  navigate: Nav;
}) {
  const root = `${endpoint(business)}/loyalty-config`,
    tab = tabNames[params.get("loyaltyTab") || ""]
      ? params.get("loyaltyTab")!
      : "programs";
  const capabilities = useResource<{
    currency: string;
    configuration_enabled: boolean;
    execution_enabled: boolean;
    analytics_enabled: boolean;
  }>(`${root}/capabilities`);
  const selected = params.get("loyaltyId"),
    edit = params.get("loyaltyEdit") === "1",
    creating = selected === "new";
  const overview = useResource<Overview>(
    capabilities.data && tab === "exposure" ? `${root}/overview` : null,
  );
  const programs = useResource<Resource<Program>[]>(
    capabilities.data &&
      ((tab === "programs" && !selected) ||
        (tab === "experiments" && !!selected))
      ? `${root}/programs`
      : null,
  );
  const experiments = useResource<Resource<Experiment>[]>(
    capabilities.data && tab === "experiments" && !selected
      ? `${root}/experiments`
      : null,
  );
  const list = tab === "experiments" ? experiments : programs;
  const detail = useResource<Resource>(
    capabilities.data &&
      selected &&
      !creating &&
      ["programs", "experiments"].includes(tab)
      ? `${root}/${tab}/${encodeURIComponent(selected)}`
      : null,
  );
  const canWrite = permissions.includes("growth.write"),
    canRead = permissions.includes("growth.read");
  const changeTab = (value: string) =>
    navigate(
      {
        view: "loyalty",
        loyaltyTab: value,
        loyaltyId: null,
        loyaltyEdit: null,
        loyaltyVersion: null,
      },
      true,
    );
  const back = () =>
    navigate(
      { loyaltyId: null, loyaltyEdit: null, loyaltyVersion: null },
      true,
    );
  const refresh = () => {
    programs.retry();
    experiments.retry();
    overview.retry();
    detail.retry();
  };
  const saved = (r: Resource) => {
    if (tab === "programs") programs.retry();
    else experiments.retry();
    detail.retry();
    navigate({ loyaltyId: r.id, loyaltyEdit: null, loyaltyVersion: null });
  };
  if (!canRead)
    return (
      <div className="page">
        <p role="status">Tu rol no permite consultar la fidelización.</p>
      </div>
    );
  return (
    <div className="page loyalty-page">
      <div className="loyalty-title-row">
        <div>
          <span className="eyebrow">CLIENTES · FIDELIZACIÓN</span>
          <h1>Fidelización</h1>
          <p>Prepara recompensas, revisa sus costos y compara ofertas.</p>
        </div>
        <button
          className="button secondary"
          onClick={() =>
            navigate(
              {
                view: null,
                loyaltyTab: null,
                loyaltyId: null,
                loyaltyEdit: null,
                loyaltyVersion: null,
              },
              true,
            )
          }
        >
          <ArrowLeft size={16} />
          Directorio
        </button>
      </div>
      <nav className="loyalty-tabs" aria-label="Fidelización">
        {Object.entries(tabNames).map(([key, name]) => (
          <a
            key={key}
            aria-current={tab === key ? "page" : undefined}
            className={tab === key ? "active" : ""}
            href={`?business=${encodeURIComponent(business)}&view=loyalty&loyaltyTab=${key}`}
            onClick={(e) => {
              if (!e.metaKey && !e.ctrlKey && !e.shiftKey && !e.altKey) {
                e.preventDefault();
                changeTab(key);
              }
            }}
          >
            {name}
          </a>
        ))}
      </nav>
      {capabilities.error ? (
        capabilities.status === 404 ? (
          <div className="state">
            <h2>Fidelización aún no está habilitada</h2>
            <p>
              Este espacio necesita la configuración de fidelización habilitada
              para preparar programas.
            </p>
          </div>
        ) : (
          <Failure message={capabilities.error} retry={capabilities.retry} />
        )
      ) : !capabilities.data ? (
        <Loading />
      ) : (
        <>
          <p className="loyalty-gate">
            <span className="badge">Preparación</span> Las ofertas adicionales
            todavía no están activadas. Publicar conserva las reglas revisadas.
          </p>
          {tab === "results" ? (
            <LoyaltyResults
              key={business}
              root={root}
              csrf={csrf}
              enabled={capabilities.data.analytics_enabled}
              canFinance={permissions.includes("finance.resolve")}
              selected={selected}
              navigate={navigate}
            />
          ) : tab === "exposure" && overview.error ? (
            <Failure message={overview.error} retry={overview.retry} />
          ) : tab === "exposure" && !overview.data ? (
            <Loading />
          ) : tab === "economics" ? (
            <Economics
              key={business}
              currency={capabilities.data.currency}
              root={root}
              csrf={csrf}
            />
          ) : tab === "exposure" ? (
            <Exposure
              data={overview.data!}
              business={business}
              refresh={refresh}
              permissions={permissions}
            />
          ) : creating || (edit && detail.data) ? (
            canWrite ? (
              tab === "programs" ? (
                <ProgramEditor
                  key={`${business}:${selected}:${detail.data?.revision || "new"}`}
                  resource={
                    creating ? undefined : (detail.data as Resource<Program>)
                  }
                  currency={capabilities.data.currency}
                  business={business}
                  root={root}
                  csrf={csrf}
                  onSaved={saved}
                  onCancel={back}
                />
              ) : (
                <ExperimentEditor
                  key={`${business}:${selected}:${detail.data?.revision || "new"}`}
                  resource={
                    creating ? undefined : (detail.data as Resource<Experiment>)
                  }
                  programs={programs.data || []}
                  currency={capabilities.data.currency}
                  business={business}
                  root={root}
                  csrf={csrf}
                  onSaved={saved}
                  onCancel={back}
                />
              )
            ) : (
              <p>
                Tu rol permite consultar las reglas. La edición requiere
                permisos de administración.
              </p>
            )
          ) : selected ? (
            detail.error ? (
              <Failure message={detail.error} retry={detail.retry} />
            ) : !detail.data ? (
              <Loading />
            ) : (
              <Definition
                key={`${business}:${tab}:${detail.data.id}:${detail.data.revision}`}
                resource={detail.data}
                programs={programs.data || []}
                root={root}
                kind={tab}
                canWrite={canWrite}
                csrf={csrf}
                back={back}
                navigate={navigate}
                version={params.get("loyaltyVersion")}
                refresh={refresh}
              />
            )
          ) : (
            <section className="loyalty-list">
              <div className="loyalty-title-row">
                <div>
                  <h2>{tabNames[tab]}</h2>
                  <p>
                    {tab === "programs"
                      ? "Reglas y versiones de las recompensas."
                      : "Variantes simultáneas con una comparación de control."}
                  </p>
                </div>
                {canWrite && (
                  <button
                    className="button primary"
                    onClick={() =>
                      navigate({ loyaltyId: "new", loyaltyEdit: "1" }, true)
                    }
                  >
                    <Plus size={17} />
                    {tab === "programs"
                      ? "Crear programa"
                      : "Crear experimento"}
                  </button>
                )}
              </div>
              {list.error ? (
                <Failure message={list.error} retry={list.retry} />
              ) : !list.data ? (
                <Loading />
              ) : !list.data.length ? (
                <div className="state">
                  <h3>
                    {tab === "programs"
                      ? "Tu primer programa empieza aquí"
                      : "Prepara tu primera comparación"}
                  </h3>
                  <p>
                    {tab === "programs"
                      ? "Define qué se gana, cuánto cuesta y cuándo se puede usar."
                      : "Publica un programa y elige cómo repartir las ofertas adicionales."}
                  </p>
                </div>
              ) : (
                <div className="loyalty-table-wrap" tabIndex={0}>
                  <table>
                    <thead>
                      <tr>
                        <th>Nombre</th>
                        <th>Estado</th>
                        <th>Versiones</th>
                        <th>Moneda</th>
                      </tr>
                    </thead>
                    <tbody>
                      {list.data.map((r) => (
                        <tr key={r.id}>
                          <td>
                            <a
                              className="loyalty-object"
                              href={`?business=${encodeURIComponent(business)}&view=loyalty&loyaltyTab=${tab}&loyaltyId=${r.id}`}
                              onClick={(e) => {
                                if (
                                  !e.metaKey &&
                                  !e.ctrlKey &&
                                  !e.shiftKey &&
                                  !e.altKey
                                ) {
                                  e.preventDefault();
                                  navigate(
                                    { loyaltyId: r.id, loyaltyEdit: null },
                                    true,
                                  );
                                }
                              }}
                            >
                              {r.document.name}
                              <small>
                                {r.document.description || "Sin descripción"}
                              </small>
                            </a>
                          </td>
                          <td>
                            <span className="badge">
                              {statuses[r.state] || r.state}
                            </span>
                          </td>
                          <td>
                            {r.versions.length} publicada
                            {r.versions.length === 1 ? "" : "s"}
                          </td>
                          <td>{r.document.currency}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          )}
        </>
      )}
    </div>
  );
}

function Definition({
  resource,
  root,
  kind,
  canWrite,
  csrf,
  back,
  navigate,
  version,
  refresh,
  programs,
}: {
  resource: Resource;
  programs: Resource<Program>[];
  root: string;
  kind: string;
  canWrite: boolean;
  csrf: string;
  back: () => void;
  navigate: Nav;
  version: string | null;
  refresh: () => void;
}) {
  const [review, setReview] = useState<"publish" | "archive" | null>(null),
    command = useCommand(csrf),
    historical = resource.versions.find((v) => v.id === version),
    doc = historical?.document || resource.document;
  const labels = useResource<{
    customers: string[];
    included: string[];
    excluded: string[];
  }>(
    `${root}/${kind}/${resource.id}/eligibility?${historical ? `version_id=${historical.id}` : `expected_revision=${resource.revision}`}`,
  );
  const diagnostics = useResource<{
    assigned_customers: number;
    exposure_receipts: number;
    bound_orders: number;
    allowed_overlap_pairs: number;
    variants: {
      name: string;
      control: boolean;
      assigned_customers: number;
      allocation_bps: number;
    }[];
  }>(
    kind === "experiments" && resource.versions.length
      ? `${root}/experiments/${resource.id}/enrollment`
      : null,
  );
  const act = async (state: string) => {
    const rev = resource.revision;
    await command.run(async () => {
      try {
        await command.send(`${root}/${kind}/${resource.id}/state`, "POST", {
          expected_revision: rev,
          state,
        });
      } catch (error) {
        const current = await api<Resource>(`${root}/${kind}/${resource.id}`);
        if (current.state !== state) throw error;
      }
      if (command.alive.current) {
        setReview(null);
        refresh();
      }
    });
  };
  const publish = async () => {
    const payload = {
      expected_revision: resource.revision,
      digest: resource.digest,
    };
    await command.run(async () => {
      await command.send(
        `${root}/${kind}/${resource.id}/publish`,
        "POST",
        payload,
      );
      if (command.alive.current) {
        setReview(null);
        refresh();
      }
    });
  };
  const unsupportedDefinition =
    "earning" in doc && doc.reward && doc.reward.type !== "fixed_value";
  const currentPublished = resource.versions.some(
    (v) => v.digest === resource.digest,
  );
  if (version && !historical)
    return (
      <section className="state">
        <h2>Esta versión no está disponible</h2>
        <button
          className="button secondary"
          onClick={() => navigate({ loyaltyVersion: null }, true)}
        >
          Ver propuesta actual
        </button>
      </section>
    );
  return (
    <section className="loyalty-definition">
      <div className="loyalty-title-row">
        <button className="button secondary" onClick={back}>
          <ArrowLeft size={16} />
          Volver a {tabNames[kind].toLowerCase()}
        </button>
        <span className="badge">
          {historical ? "Versión publicada" : statuses[resource.state]}
        </span>
      </div>
      <div className="loyalty-title-row">
        <div>
          <h2>{doc.name}</h2>
          <p>{doc.description || "Sin descripción"}</p>
        </div>
        {canWrite && resource.state !== "archived" && !historical && (
          <button
            className="button secondary"
            disabled={command.busy || command.uncertain}
            onClick={() => navigate({ loyaltyEdit: "1" }, true)}
          >
            Editar propuesta
          </button>
        )}
      </div>
      <CommandState command={command} />
      {historical && (
        <p className="loyalty-notice">
          Versión histórica del {date(historical.published_at)}. Las nuevas
          propuestas conservan estas reglas.
        </p>
      )}
      <DefinitionSummary
        document={doc}
        programs={programs}
        labels={labels.data}
      />
      {labels.error && (
        <Failure
          message="La propuesta cambió o sus participantes no están disponibles. Recarga antes de publicar."
          retry={refresh}
        />
      )}
      {unsupportedDefinition && (
        <p className="loyalty-notice">
          Esta regla conserva su historial, pero necesita un editor compatible
          antes de revisar una nueva publicación. Esta versión del editor
          prepara puntos y descuentos de valor fijo.
        </p>
      )}
      {!historical && canWrite && (
        <div className="loyalty-actions">
          {!currentPublished && resource.state !== "archived" && (
            <button
              className="button primary"
              disabled={
                command.busy ||
                command.uncertain ||
                !labels.data ||
                !!labels.error ||
                !!unsupportedDefinition
              }
              onClick={() => setReview("publish")}
            >
              Revisar y publicar
            </button>
          )}
          {resource.versions.length > 0 &&
            resource.state !== "paused" &&
            resource.state !== "archived" && (
              <button
                className="button secondary"
                disabled={command.busy || command.uncertain}
                onClick={() => void act("paused")}
              >
                Pausar
              </button>
            )}
          {resource.state !== "archived" && (
            <button
              className="button secondary"
              disabled={command.busy || command.uncertain}
              onClick={() => setReview("archive")}
            >
              Archivar
            </button>
          )}
        </div>
      )}
      {resource.state === "paused" && (
        <p className="loyalty-hint">
          La pausa se conserva al editar o publicar. La reanudación requiere una
          habilitación operativa posterior.
        </p>
      )}
      <section className="loyalty-section">
        <h3>Historial de versiones</h3>
        {resource.versions.length ? (
          <ol className="loyalty-history">
            {resource.versions.map((v, i) => (
              <li key={v.id}>
                <button
                  className="loyalty-object"
                  onClick={() =>
                    navigate({ loyaltyVersion: v.id, loyaltyEdit: null }, true)
                  }
                >
                  Versión {i + 1}
                  <small>
                    {date(v.published_at)} · {v.document.name}
                  </small>
                </button>
                <span className="loyalty-hint">Reglas conservadas</span>
              </li>
            ))}
          </ol>
        ) : (
          <p className="loyalty-hint">Aún no hay versiones publicadas.</p>
        )}
        {historical && (
          <button
            className="button secondary"
            onClick={() => navigate({ loyaltyVersion: null }, true)}
          >
            Ver propuesta actual
          </button>
        )}
      </section>
      {kind === "experiments" && resource.versions.length > 0 && (
        <section className="loyalty-section">
          <h3>Participación registrada</h3>
          {diagnostics.data ? (
            <>
              <div className="loyalty-metrics">
                <div>
                  <span>Clientes asignados</span>
                  <strong>{points(diagnostics.data.assigned_customers)}</strong>
                </div>
                <div>
                  <span>Exposiciones registradas</span>
                  <strong>{points(diagnostics.data.exposure_receipts)}</strong>
                </div>
                <div>
                  <span>Pedidos vinculados</span>
                  <strong>{points(diagnostics.data.bound_orders)}</strong>
                </div>
              </div>
              {diagnostics.data.variants.map((v) => (
                <p className="loyalty-hint" key={v.name}>
                  {v.name}
                  {v.control ? " · control" : ""}: {v.assigned_customers}{" "}
                  clientes asignados
                </p>
              ))}
              {diagnostics.data.allowed_overlap_pairs > 0 && (
                <p className="loyalty-notice">
                  Hay superposición con otros experimentos. Debe considerarse al
                  evaluar resultados.
                </p>
              )}
              <p className="loyalty-hint">
                Asignación, exposición y uso son registros distintos. La
                comparación de ganancia y su incertidumbre se incorporará en la
                evaluación de resultados.
              </p>
            </>
          ) : diagnostics.error ? (
            <p className="loyalty-hint">
              El historial de asignación todavía no está disponible en este
              espacio.
            </p>
          ) : (
            <Loading />
          )}
        </section>
      )}
      <Dialog.Root
        open={review !== null}
        onOpenChange={(open) => {
          if (!command.busy && !command.uncertain)
            setReview(open ? "publish" : null);
        }}
      >
        <Dialog.Portal>
          <Dialog.Backdrop className="dialog-backdrop" />
          <Dialog.Popup className="loyalty-review">
            <div className="loyalty-title-row">
              <Dialog.Title>
                {review === "archive"
                  ? "Archivar esta configuración"
                  : "Revisar versión antes de publicar"}
              </Dialog.Title>
              <Dialog.Close
                className="icon-button"
                aria-label="Cerrar revisión"
                disabled={command.busy || command.uncertain}
              >
                <X />
              </Dialog.Close>
            </div>
            <Dialog.Description>
              {review === "archive"
                ? "La configuración quedará cerrada para nuevas ediciones. Se conservarán sus versiones, asignaciones y movimientos."
                : "Publicaremos exactamente esta propuesta. La versión quedará conservada y las ofertas adicionales seguirán sin activarse."}
            </Dialog.Description>
            {review === "publish" && (
              <DefinitionSummary
                document={resource.document}
                programs={programs}
                labels={labels.data}
              />
            )}
            <CommandState command={command} />
            <button
              className="button primary"
              disabled={command.busy}
              onClick={() =>
                review === "archive" ? void act("archived") : void publish()
              }
            >
              {command.busy
                ? "Publicando…"
                : command.uncertain
                  ? "Reintentar publicación"
                  : review === "archive"
                    ? "Confirmar archivo"
                    : "Publicar esta versión"}
            </button>
          </Dialog.Popup>
        </Dialog.Portal>
      </Dialog.Root>
    </section>
  );
}

function DefinitionSummary({
  document: doc,
  programs,
  labels,
}: {
  document: Program | Experiment;
  programs: Resource<Program>[];
  labels?: { customers: string[]; included: string[]; excluded: string[] };
}) {
  const eligibility = doc.eligibility;
  return (
    <div className="loyalty-summary">
      <dl>
        {"earning" in doc ? (
          <>
            <div>
              <dt>Acumulación</dt>
              <dd>
                {doc.earning
                  ? `${doc.earning.points_per_unit} punto(s) por ${money(doc.earning.spend_minor_per_point, doc.currency)}`
                  : "Sin acumulación"}
              </dd>
            </div>
            <div>
              <dt>Recompensa</dt>
              <dd>
                {doc.reward?.type === "fixed_value"
                  ? `${money(doc.reward.discount_minor || 0, doc.currency)} por ${doc.reward.points_cost} puntos`
                  : doc.reward
                    ? `Tipo configurado: ${doc.reward.type}`
                    : "Sin canje"}
              </dd>
            </div>
            <div>
              <dt>Mínimo para canjear</dt>
              <dd>{doc.minimum_redeem_points} puntos</dd>
            </div>
            <div>
              <dt>Descuento máximo</dt>
              <dd>{money(doc.maximum_reward_minor, doc.currency)}</dd>
            </div>
            <div>
              <dt>Presupuesto por cliente / total</dt>
              <dd>
                {money(doc.per_customer_budget_minor, doc.currency)} /{" "}
                {money(doc.campaign_budget_minor, doc.currency)}
              </dd>
            </div>
            <div>
              <dt>Costo por punto / canje esperado</dt>
              <dd>
                {money(doc.estimated_cost_per_point_minor, doc.currency)} /{" "}
                {percent(doc.expected_redemption_bps)} %
              </dd>
            </div>
            <div>
              <dt>Vencimiento</dt>
              <dd>
                {doc.expiration_days
                  ? `${doc.expiration_days} días`
                  : "Sin vencimiento"}
              </dd>
            </div>
            <div>
              <dt>Período del programa</dt>
              <dd>
                {timeLabel(doc.start_at)} → {timeLabel(doc.end_at)}
              </dd>
            </div>
            <div>
              <dt>Combina con promociones</dt>
              <dd>{doc.stack_with_promotions ? "Sí" : "No"}</dd>
            </div>
          </>
        ) : (
          <>
            <div>
              <dt>Participación</dt>
              <dd>
                {timeLabel(doc.enrollment_start)} →{" "}
                {timeLabel(doc.enrollment_end)}
              </dd>
            </div>
            <div>
              <dt>Evaluación / resguardo</dt>
              <dd>
                {doc.observation_days} / {doc.carryover_days} días
              </dd>
            </div>
            <div>
              <dt>Grupo de exclusión</dt>
              <dd>{doc.exclusion_group}</dd>
            </div>
            <div>
              <dt>Superposición</dt>
              <dd>
                {doc.allow_overlap
                  ? `Permitida: ${doc.overlap_reason}`
                  : "No permitida"}
              </dd>
            </div>
            <div>
              <dt>Beneficios habituales</dt>
              <dd>Se conservan</dd>
            </div>
            <div>
              <dt>Plan de evaluación</dt>
              <dd>{doc.analysis_plan}</dd>
            </div>
            <div>
              <dt>Evaluación estadística</dt>
              <dd>
                {doc.analysis_protocol
                  ? `Lectura: ${date(doc.analysis_protocol.readout_at)} · mínimo ${doc.analysis_protocol.minimum_customers_per_arm} por grupo · confianza conjunta ${doc.analysis_protocol.confidence_bps / 100}% · Welch / Bonferroni. ${doc.analysis_protocol.sample_size_rationale}`
                  : "Sin protocolo estructurado; resultados descriptivos."}
              </dd>
            </div>
          </>
        )}
        <div>
          <dt>Compra mínima</dt>
          <dd>{money(eligibility.minimum_purchase_minor, doc.currency)}</dd>
        </div>
        <div>
          <dt>Clientes elegibles</dt>
          <dd>
            {eligibility.customer_ids.length
              ? labels?.customers.join(", ") ||
                `${eligibility.customer_ids.length} seleccionados · cargando nombres`
              : "Todos los clientes con identidad verificada"}
          </dd>
        </div>
        <div>
          <dt>Productos incluidos / excluidos</dt>
          <dd>
            {eligibility.included_product_ids.length
              ? labels?.included.join(", ") || "Cargando productos"
              : "Todos"}{" "}
            /{" "}
            {eligibility.excluded_product_ids.length
              ? labels?.excluded.join(", ") || "Cargando exclusiones"
              : "Ninguno"}
          </dd>
        </div>
      </dl>
      {"variants" in doc && (
        <div className="loyalty-table-wrap" tabIndex={0}>
          <table>
            <thead>
              <tr>
                <th>Variante</th>
                <th>Distribución</th>
                <th>Oferta</th>
              </tr>
            </thead>
            <tbody>
              {doc.variants.map((v) => (
                <tr key={v.name}>
                  <td>{v.name}</td>
                  <td>{percent(v.allocation_bps)} %</td>
                  <td>
                    {v.strategy_version_id
                      ? programVersionLabel(programs, v.strategy_version_id)
                      : "Control · sin oferta adicional"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Exposure({
  data: d,
  business,
  refresh,
  permissions,
}: {
  data: Overview;
  business: string;
  refresh: () => void;
  permissions: string[];
}) {
  return (
    <section>
      <div className="loyalty-title-row">
        <div>
          <h2>Saldos y costos</h2>
          <p>Registros al {new Date(d.as_of).toLocaleString("es-CO")}.</p>
        </div>
        <button className="button secondary" onClick={refresh}>
          <RefreshCw size={16} />
          Actualizar saldos
        </button>
      </div>
      <div className="loyalty-metrics">
        <div>
          <span>Puntos disponibles registrados</span>
          <strong>{points(d.wallets.available_points)}</strong>
          <small>{points(d.wallets.accounts)} cuentas</small>
        </div>
        <div>
          <span>Puntos por recuperar de reembolsos</span>
          <strong>{points(d.wallets.refund_debt_points)}</strong>
          <small>Bloquean nuevos canjes mientras estén pendientes</small>
        </div>
        <div>
          <span>Puntos sin costo histórico atribuible</span>
          <strong>{points(d.wallets.unattributed_points)}</strong>
          <small>Su costo pendiente es desconocido</small>
        </div>
      </div>
      {!d.execution_history_available && (
        <p className="loyalty-notice">
          El historial de lotes todavía no está instalado. Los saldos
          registrados no permiten estimar su costo.
        </p>
      )}
      {d.wallets.lot_balance_mismatches !== "0" && (
        <p className="loyalty-notice">
          Hay diferencias entre lotes y saldos. Requieren conciliación antes de
          usar estas cifras.
        </p>
      )}
      <div className="loyalty-section">
        <h3>Costo estimado de puntos pendientes</h3>
        <p className="loyalty-hint">
          Estimaciones de cumplimiento por lote, separadas por moneda histórica.
          No equivalen a una provisión contable; el saldo sin procedencia queda
          sin valorar.
        </p>
        {d.costs.length ? (
          <div className="loyalty-table-wrap" tabIndex={0}>
            <table>
              <thead>
                <tr>
                  <th>Moneda</th>
                  <th>Costo registrado</th>
                  <th>Costo con canje esperado</th>
                  <th>Vencimiento pendiente</th>
                </tr>
              </thead>
              <tbody>
                {d.costs.map((c) => (
                  <tr key={c.currency}>
                    <td>{c.currency}</td>
                    <td>{money(c.recorded_cost_minor, c.currency)}</td>
                    <td>{money(c.expected_cost_minor, c.currency)}</td>
                    <td>
                      {points(c.due_expiry_points)} puntos ·{" "}
                      {money(c.due_expiry_cost_minor, c.currency)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p>No hay lotes valorados para mostrar.</p>
        )}
      </div>
      <div className="loyalty-section">
        <h3>Uso de presupuestos de campaña</h3>
        <p className="loyalty-hint">
          La emisión de puntos ya puede formar parte del costo comprometido. No
          sumes esta tabla al costo de puntos pendientes.
        </p>
        {d.budgets.length ? (
          <div className="loyalty-table-wrap" tabIndex={0}>
            <table>
              <thead>
                <tr>
                  <th>Programa</th>
                  <th>Reservado</th>
                  <th>Comprometido</th>
                </tr>
              </thead>
              <tbody>
                {d.budgets.map((b) => (
                  <tr key={b.program_id}>
                    <td>{b.name}</td>
                    <td>
                      {b.currency
                        ? money(b.reserved_minor, b.currency)
                        : `${points(b.reserved_minor)} · moneda sin determinar`}
                    </td>
                    <td>
                      {b.currency
                        ? money(b.committed_minor, b.currency)
                        : `${points(b.committed_minor)} · moneda sin determinar`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p>No hay presupuesto de ofertas adicionales utilizado.</p>
        )}
      </div>
      <div className="loyalty-section">
        <h3>Reembolsos que requieren revisión</h3>
        {d.refund_holds.truncated && (
          <p className="loyalty-notice">
            Vista limitada a los {d.refund_holds.scan_limit} pedidos
            reembolsados más recientes; puede haber casos anteriores.
          </p>
        )}
        {d.refund_holds.items.length ? (
          <div className="loyalty-table-wrap" tabIndex={0}>
            <table>
              <thead>
                <tr>
                  <th>Pedido / cliente</th>
                  <th>Reembolso observado</th>
                  <th>Pendiente</th>
                </tr>
              </thead>
              <tbody>
                {d.refund_holds.items.map((h) => (
                  <tr key={h.order_id}>
                    <td>
                      {permissions.includes("operations.read") ? (
                        <a
                          className="loyalty-object"
                          href={`/workspace/sales?business=${encodeURIComponent(business)}&order=${encodeURIComponent(h.order_id)}`}
                        >
                          {h.order_code}
                          <small>{h.customer}</small>
                        </a>
                      ) : (
                        <>
                          {h.order_code}
                          <small>{h.customer}</small>
                        </>
                      )}
                    </td>
                    <td>{money(h.refund_minor, h.currency)}</td>
                    <td>
                      {h.reasons.map((r) => holdLabels[r] || r).join(" · ")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p>No se encontraron bloqueos en los pedidos revisados.</p>
        )}
      </div>
      <div className="loyalty-section">
        <h3>Revisión financiera pendiente</h3>
        <p className="loyalty-hint">
          Estos casos pueden incluir notificaciones que aún no se pudieron
          validar. No son reembolsos confirmados ni se suman a sus importes.
        </p>
        <p>
          {d.financial_reviews.count} caso(s) abiertos · últimos{" "}
          {d.financial_reviews.limit}
        </p>
        {d.financial_reviews.items.map((r) => (
          <p key={r.id}>
            {permissions.includes("operations.read") ? (
              <a
                className="loyalty-object"
                href={`/workspace/sales?business=${encodeURIComponent(business)}&order=${encodeURIComponent(r.order_id)}`}
              >
                {r.order_code} · revisar pago
              </a>
            ) : (
              r.order_code
            )}
          </p>
        ))}
      </div>
      <div className="loyalty-section">
        <h3>Movimientos recientes</h3>
        <p className="loyalty-hint">
          Últimos 20 registros. Las cifras y los movimientos no demuestran un
          efecto de fidelización.
        </p>
        {d.ledger.length ? (
          <div className="loyalty-table-wrap" tabIndex={0}>
            <table>
              <thead>
                <tr>
                  <th>Cliente / pedido</th>
                  <th>Movimiento</th>
                  <th>Puntos</th>
                  <th>Fecha</th>
                </tr>
              </thead>
              <tbody>
                {d.ledger.map((l) => (
                  <tr key={l.id}>
                    <td>
                      {l.customer}
                      <small>{l.order_code || "Sin pedido vinculado"}</small>
                    </td>
                    <td>
                      {eventLabels[l.reason] || "Movimiento de recompensa"}
                      <small>
                        {l.version_id
                          ? "Regla adicional con versión conservada"
                          : "Programa habitual o registro anterior"}
                      </small>
                    </td>
                    <td>
                      {l.points > 0 ? "+" : ""}
                      {points(l.points)}
                    </td>
                    <td>{date(l.at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p>Aún no hay movimientos de puntos.</p>
        )}
      </div>
    </section>
  );
}

function timeLabel(value: string | null) {
  return value ? new Date(value).toLocaleString("es-CO") : "Sin límite";
}
function programVersionLabel(programs: Resource<Program>[], id: string) {
  for (const p of programs) {
    const index = p.versions.findIndex((v) => v.id === id);
    if (index >= 0)
      return `${p.versions[index].document.name} · versión ${index + 1}`;
  }
  return "Versión histórica de programa";
}
