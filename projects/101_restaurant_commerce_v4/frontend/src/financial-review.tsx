import { useEffect, useRef, useState } from "react";
import { Dialog } from "@base-ui/react/dialog";
import { ArrowLeft, ArrowRight, RefreshCw, Search, X } from "lucide-react";
import { api, endpoint, amount, useResource, Failure, Loading } from "./ui";
import { minor, editableMoney } from "./loyalty-shared";
import { OperationNotice, useOperation } from "./operations-ui";
import "./operations-workspace.css";

type Row = {
  id: string;
  public_code: string;
  status: string;
  payment_status: string;
  total_minor: number;
  currency: string;
  open_reviews: number;
};
type RecordOp = {
  id: string;
  kind: string;
  state: string;
  reason: string;
  actor_id: string;
  created_at: string;
  result: Record<string, unknown> | null;
};
type Review = {
  id: string;
  reason: string;
  status: string;
  resolvable: boolean;
  created_at: string;
};
type History = {
  capabilities: {
    lookup: boolean;
    refund: boolean;
    inspect_refund: boolean;
    refund_block_reason: string;
  };
  operations: RecordOp[];
  reviews: Review[];
  audit: {
    id: string;
    actor_id: string;
    action: string;
    reason: string;
    created_at: string;
    evidence: Record<string, unknown>;
  }[];
};
type Allocation = {
  basis: string;
  blocker: string | null;
  remaining_food_minor: number;
  remaining_delivery_fee_minor: number;
  lines: {
    id: string;
    name: string;
    quantity: number;
    remaining_minor: number | null;
  }[];
  allocations: {
    refund_id: string;
    document: { lines: Record<string, number>; delivery_fee_minor: number };
  }[];
};
type Metadata = {
  order: Row;
  timezone: string;
  full_refund_amount_minor: number | null;
  full_refund_currency: string | null;
  refunds: {
    id: string;
    reference: string;
    amount_minor: number;
    currency: string;
  }[];
  allocation: Allocation;
};
const pay: Record<string, string> = {
  paid: "Pagado",
  unpaid: "Sin pagar",
  pending: "Pendiente",
  failed: "Fallido",
  refunded: "Devuelto",
};
const state: Record<string, string> = {
  pending: "Pendiente",
  processing: "En proceso",
  unknown: "Sin confirmar",
  review_required: "Requiere revisión",
  failed: "Fallida",
  withdrawn: "Retirada",
  succeeded: "Completada",
};
const reasons: Record<string, string> = {
  refund_in_progress: "Devolución en proceso",
  refund_evidence_review: "Evidencia de devolución sin verificar",
  paid_after_cancellation: "Pago recibido después de cancelar",
  contradictory_payment_notification: "Información de pago contradictoria",
  wompi_provider_review: "El pago necesita revisión",
  provider_reference_conflict: "Referencia de pago en conflicto",
  wompi_refund_contract_unverified:
    "La devolución con este proveedor aún no está habilitada",
};
const localTime = (s: string, z: string) =>
  new Intl.DateTimeFormat("es-CO", {
    timeZone: z,
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(/[Zz]|[+-]\d\d:\d\d$/.test(s) ? s : s + "Z"));
function key() {
  return Array.from(crypto.getRandomValues(new Uint8Array(24)), (b) =>
    b.toString(16).padStart(2, "0"),
  ).join("");
}

export function FinancialReviewWorkspace({
  business,
  csrf,
  permissions,
  params,
  navigate,
}: {
  business: string;
  csrf: string;
  permissions: string[];
  params: URLSearchParams;
  navigate: (changes: Record<string, string | null>, push?: boolean) => void;
}) {
  const root = endpoint(business) + "/financial-orders",
    selected = params.get("review_order"),
    offset = Math.max(0, Number(params.get("finance_offset")) || 0),
    query = params.get("finance_q") || "",
    scope = params.get("review_scope") || "open";
  const [search, setSearch] = useState(query);
  const list = useResource<{ items: Row[]; count: number }>(
    `${root}?scope=${scope}&q=${encodeURIComponent(query)}&offset=${offset}&limit=25`,
  );
  return (
    <div
      className={`sales-workspace operations-panel ${selected ? "sale-selected" : ""}`}
    >
      <div className="page">
        <section className="page-heading">
          <div>
            <h1>Revisión de pagos</h1>
            <p>
              Consulta los pagos, las devoluciones y la evidencia de cada
              pedido.
            </p>
          </div>
          <button className="button secondary" onClick={list.retry}>
            <RefreshCw size={16} />
            Actualizar
          </button>
        </section>
        <section className="customer-surface">
          <div className="surface-heading">
            <h2>
              Pedidos <span>{list.data?.count ?? "…"}</span>
            </h2>
          </div>
          <form
            className="toolbar"
            onSubmit={(e) => {
              e.preventDefault();
              navigate({
                finance_q: search || null,
                finance_offset: null,
                review_order: null,
              });
            }}
          >
            <label className="search">
              <Search size={16} />
              <input
                aria-label="Buscar pedido para revisión"
                placeholder="Código del pedido"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </label>
            <button className="button secondary">Buscar</button>
            <label className="reservation-filter">
              Mostrar
              <select
                aria-label="Pedidos para revisión"
                value={scope}
                onChange={(e) =>
                  navigate({
                    review_scope: e.target.value,
                    finance_offset: null,
                    review_order: null,
                  })
                }
              >
                <option value="open">Con revisiones abiertas</option>
                <option value="all">Todos los pedidos</option>
              </select>
            </label>
          </form>
          {list.error ? (
            <Failure message={list.error} retry={list.retry} />
          ) : !list.data ? (
            <Loading />
          ) : !list.data.items.length ? (
            <div className="state">
              <h3>No hay pedidos en esta vista</h3>
              <p>Puedes consultar todos los pedidos para ver su historial.</p>
            </div>
          ) : (
            <div className="list-scroll operation-rows">
              {list.data.items.map((o) => (
                <a
                  className="operation-row"
                  key={o.id}
                  href={`/workspace/sales?${new URLSearchParams({ ...Object.fromEntries(params), review_order: o.id })}`}
                  onClick={(e) => {
                    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey)
                      return;
                    e.preventDefault();
                    navigate({ review_order: o.id }, true);
                  }}
                >
                  <span>
                    <strong>#{o.public_code}</strong>
                    <small>{o.open_reviews} revisiones abiertas</small>
                  </span>
                  <span>{pay[o.payment_status] || "Estado por revisar"}</span>
                  <strong>{amount(o.total_minor, o.currency)}</strong>
                </a>
              ))}
            </div>
          )}
          {list.data && (
            <div className="table-footer">
              <span>{list.data.count} pedidos</span>
              <div className="pagination">
                <button
                  className="icon-button"
                  aria-label="Revisiones anteriores"
                  disabled={!offset}
                  onClick={() =>
                    navigate({
                      finance_offset: String(Math.max(0, offset - 25)),
                      review_order: null,
                    })
                  }
                >
                  <ArrowLeft size={17} />
                </button>
                <button
                  className="icon-button"
                  aria-label="Más revisiones"
                  disabled={offset + 25 >= list.data.count}
                  onClick={() =>
                    navigate({
                      finance_offset: String(offset + 25),
                      review_order: null,
                    })
                  }
                >
                  <ArrowRight size={17} />
                </button>
              </div>
            </div>
          )}
        </section>
      </div>
      {selected && (
        <FinanceDetail
          key={business + selected}
          business={business}
          id={selected}
          csrf={csrf}
          permissions={permissions}
          changed={list.retry}
          close={() => {
            if (history.state?.customerWorkspace) history.back();
            else navigate({ review_order: null });
          }}
        />
      )}
    </div>
  );
}
type Pending = {
  action: "lookup" | "inspect" | "refund" | "resolve";
  reason: string;
  requestKey: string;
  reference?: string;
  review?: string;
  operation?: string;
};
function FinanceDetail({
  business,
  id,
  csrf,
  permissions,
  close,
  changed,
}: {
  business: string;
  id: string;
  csrf: string;
  permissions: string[];
  close: () => void;
  changed: () => void;
}) {
  const root = `/api/finance/restaurants/${encodeURIComponent(business)}/orders/${encodeURIComponent(id)}`;
  const historyResource = useResource<History>(root),
    metaResource = useResource<Metadata>(
      endpoint(business) + "/financial-orders/" + encodeURIComponent(id),
    );
  const [historyData, setHistory] = useState<History>(),
    [metaData, setMeta] = useState<Metadata>(),
    [reason, setReason] = useState(""),
    [reference, setReference] = useState("");
  const [pending, setPending] = useState<Pending | null>(null),
    [checked, setChecked] = useState(false);
  const retained = useRef<Pending | null>(null);
  const action = useOperation(csrf),
    h = historyData || historyResource.data,
    m = metaData || metaResource.data;
  async function refresh() {
    try {
      const [history, meta] = await Promise.all([
        api<History>(root),
        api<Metadata>(
          endpoint(business) + "/financial-orders/" + encodeURIComponent(id),
        ),
      ]);
      setHistory(history);
      setMeta(meta);
      action.checked();
      changed();
    } catch {
      action.setMessage(
        "No pudimos actualizar el historial. No repitas una solicitud sin comprobar su estado.",
      );
    }
  }
  function prepare(
    type: Pending["action"],
    review?: string,
    operation?: string,
  ) {
    if (!reason.trim()) {
      action.setMessage("Escribe el motivo de la acción.");
      return;
    }
    if (type === "inspect" && !/^[1-9][0-9]{0,19}$/.test(reference)) {
      action.setMessage("Indica un ID numérico de devolución válido.");
      return;
    }
    const draft = {
      action: type,
      reason: reason.trim(),
      reference,
      review,
      operation,
    };
    const previous = retained.current;
    const requestKey =
      previous &&
      JSON.stringify({ ...previous, requestKey: undefined }) ===
        JSON.stringify({ ...draft, requestKey: undefined })
        ? previous.requestKey
        : key();
    retained.current = { ...draft, requestKey };
    setChecked(false);
    setPending(retained.current);
  }
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    if (m) heading.current?.focus({ preventScroll: true });
  }, [m?.order.id]);
  const refundIntent = h?.operations.some((o) => o.kind === "refund");
  return (
    <aside
      className="detail sale-detail operation-detail finance-detail"
      aria-label="Detalle financiero"
    >
      <div className="detail-top">
        <button
          className="icon-button"
          aria-label="Cerrar revisión"
          onClick={close}
        >
          <X size={19} />
        </button>
      </div>
      {historyResource.error && !h ? (
        <Failure
          message={historyResource.error}
          retry={historyResource.retry}
        />
      ) : metaResource.error && !m ? (
        <Failure message={metaResource.error} retry={metaResource.retry} />
      ) : !h || !m ? (
        <Loading />
      ) : (
        <div className="detail-body">
          <span className="eyebrow">Historial financiero</span>
          <h2 ref={heading} tabIndex={-1}>
            Pedido #{m.order.public_code}
          </h2>
          <p>
            {pay[m.order.payment_status] || "Por revisar"} ·{" "}
            {amount(m.order.total_minor, m.order.currency)}
          </p>
          <button
            className="button secondary"
            disabled={action.busy}
            onClick={refresh}
          >
            <RefreshCw size={16} />
            {action.uncertain ? "Comprobar historial" : "Actualizar historial"}
          </button>
          <OperationNotice message={action.message} />
          <section>
            <h3>Revisiones abiertas</h3>
            {!h.reviews.some((r) => r.status === "open") && (
              <p>No hay revisiones abiertas para este pedido.</p>
            )}
            {h.reviews
              .filter((r) => r.status === "open")
              .map((r) => (
                <div className="finance-record" key={r.id}>
                  <strong>
                    {reasons[r.reason] || "Evidencia pendiente de revisión"}
                  </strong>
                  {!r.resolvable && (
                    <p>
                      La evidencia disponible todavía no permite resolver esta
                      revisión.
                    </p>
                  )}
                  {r.resolvable &&
                    permissions.includes("finance.resolve") &&
                    h.operations
                      .filter(
                        (o) =>
                          (o.state === "succeeded" ||
                            (o.kind === "refund" &&
                              o.state === "failed" &&
                              r.reason === "refund_in_progress")) &&
                          typeof o.result?.query_started_at === "string" &&
                          new Date(
                            /[Zz]|[+-]\d\d:\d\d$/.test(
                              o.result.query_started_at,
                            )
                              ? o.result.query_started_at
                              : o.result.query_started_at + "Z",
                          ) >=
                            new Date(
                              /[Zz]|[+-]\d\d:\d\d$/.test(r.created_at)
                                ? r.created_at
                                : r.created_at + "Z",
                            ),
                      )
                      .map((o) => (
                        <button
                          className="button secondary"
                          key={o.id}
                          disabled={action.busy || action.uncertain}
                          onClick={() => prepare("resolve", r.id, o.id)}
                        >
                          Revisar evidencia ·{" "}
                          {o.kind === "refund" ? "devolución" : "consulta"} ·{" "}
                          {localTime(o.created_at, m.timezone)}
                        </button>
                      ))}
                </div>
              ))}
          </section>
          <section>
            <h3>Acciones financieras</h3>
            <p className="source-note">
              Una solicitud aceptada puede seguir pendiente. El historial indica
              lo que está confirmado.
            </p>
            {permissions.some(
              (p) => p !== "finance.read" && p.startsWith("finance."),
            ) && (
              <label>
                Motivo de la acción
                <textarea
                  aria-label="Motivo de la acción financiera"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  maxLength={500}
                />
              </label>
            )}
            {h.capabilities.lookup && (
              <button
                className="button secondary"
                disabled={action.busy || action.uncertain}
                onClick={() => prepare("lookup")}
              >
                Consultar pago con el proveedor
              </button>
            )}
            {h.capabilities.inspect_refund && (
              <>
                <label>
                  ID de devolución del proveedor
                  <input
                    aria-label="ID de devolución del proveedor"
                    inputMode="numeric"
                    value={reference}
                    onChange={(e) => setReference(e.target.value)}
                    maxLength={20}
                  />
                </label>
                <button
                  className="button secondary"
                  disabled={action.busy || action.uncertain}
                  onClick={() => prepare("inspect")}
                >
                  Consultar devolución del proveedor
                </button>
              </>
            )}
            {h.capabilities.refund && !refundIntent && (
              <button
                className="button secondary"
                disabled={action.busy || action.uncertain}
                onClick={() => prepare("refund")}
              >
                Solicitar devolución completa
              </button>
            )}
            {refundIntent && (
              <p>
                Ya existe una solicitud de devolución para este pedido. Consulta
                su estado en el historial.
              </p>
            )}
            {!h.capabilities.refund && (
              <p className="source-note">
                {reasons[h.capabilities.refund_block_reason] ||
                  "La devolución no está disponible para este pedido o tus permisos."}
              </p>
            )}
          </section>
          <section>
            <h3>Solicitudes y resultados</h3>
            {!h.operations.length && (
              <p>No hay operaciones financieras registradas.</p>
            )}
            {h.operations.map((o) => (
              <article className="finance-record" key={o.id}>
                <strong>
                  {o.kind === "refund"
                    ? "Solicitud de devolución completa"
                    : "Consulta al proveedor"}
                </strong>
                <p>{state[o.state] || "Estado por revisar"}</p>
                <p>{o.reason}</p>
                <small>{localTime(o.created_at, m.timezone)}</small>
                <Evidence value={o.result} currency={m.order.currency} />
              </article>
            ))}
          </section>
          {!!m.refunds.length && (
            <section>
              <h3>Distribución de devoluciones confirmadas</h3>
              <p className="source-note">
                Este registro ajusta la fidelización; no realiza otra devolución
                de dinero. Los importes no se reparten automáticamente.
              </p>
              {m.refunds.map((r) => (
                <AllocationForm
                  key={r.id + JSON.stringify(m.allocation.allocations)}
                  refund={r}
                  context={m.allocation}
                  canWrite={permissions.includes("finance.resolve")}
                  csrf={csrf}
                  business={business}
                  refresh={refresh}
                />
              ))}
            </section>
          )}
          <section>
            <h3>Registro de acciones</h3>
            {!h.audit.length && <p>No hay acciones financieras registradas.</p>}
            {h.audit.map((a) => (
              <details className="finance-record" key={a.id}>
                <summary>
                  {localTime(a.created_at, m.timezone)} · {a.reason}
                </summary>
                <p>Responsable: {a.actor_id}</p>
                <Evidence value={a.evidence} currency={m.order.currency} />
              </details>
            ))}
          </section>
          <Dialog.Root
            open={!!pending}
            onOpenChange={(open) => {
              if (!open && !action.busy) setPending(null);
            }}
          >
            <Dialog.Portal>
              <Dialog.Backdrop className="backdrop" />
              <Dialog.Popup className="action-dialog">
                <Dialog.Title>
                  {pending?.action === "refund"
                    ? "Confirmar devolución completa"
                    : pending?.action === "resolve"
                      ? "Resolver con esta evidencia"
                      : "Confirmar consulta al proveedor"}
                </Dialog.Title>
                <Dialog.Description>
                  Pedido #{m.order.public_code}
                  {pending?.action === "refund" &&
                  m.full_refund_amount_minor !== null
                    ? ` · ${amount(m.full_refund_amount_minor, m.full_refund_currency || m.order.currency)}`
                    : ""}
                  . {pending?.reason}
                </Dialog.Description>
                <label className="confirm-cash">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={(e) => setChecked(e.target.checked)}
                  />
                  He revisado el pedido, el motivo y la acción.
                </label>
                <div className="dialog-actions">
                  <button
                    className="button secondary"
                    disabled={action.busy}
                    onClick={() => setPending(null)}
                  >
                    Volver
                  </button>
                  <button
                    className="button primary"
                    disabled={!checked || action.busy || action.uncertain}
                    onClick={async () => {
                      if (!pending) return;
                      const value = pending;
                      const body =
                        value.action === "resolve"
                          ? {
                              operation_id: value.operation,
                              reason: value.reason,
                            }
                          : {
                              idempotency_key: value.requestKey,
                              reason: value.reason,
                              ...(value.action === "inspect"
                                ? { refund_reference: value.reference }
                                : {}),
                            };
                      const result = await action.perform(
                        root +
                          (value.action === "resolve"
                            ? "/resolve/" + encodeURIComponent(value.review!)
                            : value.action === "refund"
                              ? "/refund"
                              : "/lookup"),
                        body,
                      );
                      setPending(null);
                      if (result) {
                        retained.current = null;
                        await refresh();
                      }
                    }}
                  >
                    Confirmar
                  </button>
                </div>
              </Dialog.Popup>
            </Dialog.Portal>
          </Dialog.Root>
        </div>
      )}
    </aside>
  );
}

function Evidence({
  value,
  currency,
}: {
  value: Record<string, unknown> | null;
  currency: string;
}) {
  if (!value) return null;
  return (
    <div className="source-note">
      {typeof value.status === "string" && (
        <p>Estado verificado: {pay[value.status] || value.status}</p>
      )}
      {typeof value.amount_minor === "number" && (
        <p>
          Importe:{" "}
          {amount(
            value.amount_minor,
            typeof value.currency === "string" ? value.currency : currency,
          )}
        </p>
      )}
      {typeof value.provider_reference === "string" && (
        <p>Referencia de pago: {value.provider_reference}</p>
      )}
      {typeof value.refund_reference === "string" && (
        <p>Referencia de devolución: {value.refund_reference}</p>
      )}
      {typeof value.refund_status === "string" && (
        <p>
          Estado reportado de devolución: {value.refund_status}. Esta
          observación requiere revisión; no confirma una devolución en este
          sistema.
        </p>
      )}
      {!!value.error && (
        <p>El proveedor no dio una confirmación verificable.</p>
      )}
    </div>
  );
}

function AllocationForm({
  refund,
  context,
  canWrite,
  csrf,
  business,
  refresh,
}: {
  refund: Metadata["refunds"][number];
  context: Allocation;
  canWrite: boolean;
  csrf: string;
  business: string;
  refresh: () => Promise<void>;
}) {
  const recorded = context.allocations.find(
      (a) => a.refund_id === refund.id,
    )?.document,
    op = useOperation(csrf);
  const [confirmed, setConfirmed] = useState(false);
  return (
    <form
      className="finance-record"
      aria-label={"Distribución de devolución " + refund.reference}
      onSubmit={async (e) => {
        e.preventDefault();
        const form = new FormData(e.currentTarget);
        try {
          const lines = Object.fromEntries(
            context.lines.map((line) => [
              line.id,
              minor(String(form.get(line.id) || "0"), refund.currency),
            ]),
          );
          const fee = minor(String(form.get("fee") || "0"), refund.currency);
          if (
            Object.values(lines).reduce((a, b) => a + b, fee) !==
            refund.amount_minor
          ) {
            op.setMessage(
              "La distribución debe sumar exactamente el importe confirmado.",
            );
            return;
          }
          const result = await op.perform(
            `/api/finance/restaurants/${encodeURIComponent(business)}/loyalty-refunds/${encodeURIComponent(refund.id)}/allocation`,
            { lines, delivery_fee_minor: fee },
          );
          if (result) await refresh();
        } catch (error) {
          op.setMessage(
            error instanceof Error ? error.message : "Revisa los importes.",
          );
        }
      }}
    >
      <h4>
        {amount(refund.amount_minor, refund.currency)} · {refund.reference}
      </h4>
      {context.blocker && <p>{context.blocker}</p>}
      {recorded && <p>Distribución registrada. Este registro es inmutable.</p>}
      <fieldset
        disabled={
          !canWrite ||
          !!recorded ||
          !!context.blocker ||
          op.busy ||
          op.uncertain
        }
        className="allocation-fields"
      >
        {context.lines.map((line) => (
          <label key={line.id}>
            {line.quantity} × {line.name}
            <input
              aria-label={"Distribución para " + line.name}
              name={line.id}
              inputMode="decimal"
              defaultValue={
                recorded
                  ? editableMoney(recorded.lines[line.id] || 0, refund.currency)
                  : ""
              }
            />
            {line.remaining_minor !== null && (
              <small>
                Disponible para asignar:{" "}
                {amount(line.remaining_minor, refund.currency)}
              </small>
            )}
          </label>
        ))}
        <label>
          Parte correspondiente a la entrega
          <input
            name="fee"
            aria-label="Distribución para la entrega"
            inputMode="decimal"
            defaultValue={
              recorded
                ? editableMoney(recorded.delivery_fee_minor, refund.currency)
                : ""
            }
          />
        </label>
        <p className="source-note">
          Disponible: productos{" "}
          {amount(context.remaining_food_minor, refund.currency)} · entrega{" "}
          {amount(context.remaining_delivery_fee_minor, refund.currency)}.
          {context.basis === "baseline" &&
            " La validación de productos usa el total histórico, sin inventar un reparto por línea."}
        </p>
        {!recorded && canWrite && !context.blocker && (
          <>
            <label className="check-label">
              <input
                type="checkbox"
                checked={confirmed}
                onChange={(e) => setConfirmed(e.target.checked)}
              />
              He revisado la distribución de esta devolución confirmada.
            </label>
            <button
              className="button secondary"
              disabled={!confirmed || op.busy}
            >
              Registrar distribución
            </button>
          </>
        )}
      </fieldset>
      <OperationNotice message={op.message} />
      {op.uncertain && (
        <button type="button" className="button secondary" onClick={refresh}>
          Comprobar distribución
        </button>
      )}
    </form>
  );
}
