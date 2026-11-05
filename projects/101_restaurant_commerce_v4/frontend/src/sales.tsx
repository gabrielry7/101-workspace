import { useEffect, useRef, useState } from "react";
import { Dialog } from "@base-ui/react/dialog";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronLeft,
  ChevronRight,
  Clock3,
  ExternalLink,
  PackageCheck,
  RefreshCw,
  Search,
  ShoppingBag,
  Truck,
  X,
} from "lucide-react";
import {
  api,
  endpoint,
  amount,
  date,
  count,
  useResource,
  Failure,
  Loading,
} from "./ui";
import "./sales.css";
import { periodQuery } from "./workspace-views";

type Row = {
  id: string;
  public_code: string;
  status: string;
  payment_status: string;
  fulfillment_type: string;
  total_minor: number;
  currency: string;
  created_at: string;
  version: number;
  customer_name: string | null;
};
type Listing = {
  items: Row[];
  count: number;
  counts: Record<string, number>;
  review_count: number;
};
type Action = {
  status: string;
  allowed: boolean;
  reason: string | null;
  confirmation: string | null;
};
type Detail = Row & {
  customer_phone: string;
  notes: string | null;
  source_channel: string;
  subtotal_minor: number;
  discount_minor: number;
  delivery_fee_minor: number;
  reconciliation_required: boolean;
  identity_verified: boolean;
  items: {
    name: string;
    quantity: number;
    line_total_minor: number;
    modifiers: { option_name: string; group_name: string }[];
  }[];
  payments: {
    provider: string;
    status: string;
    amount_minor: number;
    currency: string;
  }[];
  delivery: null | { status: string };
  actions: Action[];
  money: {
    scope: string;
    currency: string;
    captured_minor: number;
    refunded_minor: number;
    net_minor: number;
  }[];
};
type Props = {
  initialScroll: number;
  rememberScroll: (value: number) => void;
  business: string;
  permissions: string[];
  csrf: string;
  params: URLSearchParams;
  navigate: (changes: Record<string, string | null>, push?: boolean) => void;
};
const statusName: Record<string, string> = {
  awaiting_payment: "Esperando pago",
  placed: "Por aceptar",
  accepted: "Aceptado",
  preparing: "En preparación",
  ready: "Listo",
  completed: "Entregado",
  cancelled: "Cancelado",
};
const payName: Record<string, string> = {
  paid: "Pagado",
  unpaid: "Sin pagar",
  pending: "Pendiente",
  refunded: "Devuelto",
  failed: "Fallido",
};
const actionName: Record<string, string> = {
  accepted: "Aceptar pedido",
  preparing: "Empezar preparación",
  ready: "Marcar listo",
  completed: "Confirmar entrega",
  cancelled: "Cancelar pedido",
};
const reasonName: Record<string, string> = {
  "An order with a refund intent cannot advance fulfillment":
    "Hay una devolución en revisión. Resuélvela antes de continuar.",
  "Payment reconciliation is required before fulfillment":
    "Este pago necesita revisión antes de preparar el pedido.",
  "Order cannot advance before payment is confirmed":
    "El pago todavía no está confirmado.",
  "Delivery orders complete only after the courier marks them delivered":
    "El transportador debe confirmar la entrega primero.",
  "Paid orders require a refund workflow before cancellation":
    "Este pedido ya está pagado. Gestiona la devolución desde operaciones.",
  "Order cannot be cancelled after courier pickup":
    "El pedido ya fue recogido por el transportador.",
  "Cancel the dispatched delivery before cancelling the order":
    "Cancela primero el envío desde operaciones.",
};
function Status({
  value,
  payment = false,
}: {
  value: string;
  payment?: boolean;
}) {
  return (
    <span className={`badge order-status status-${value}`}>
      <span aria-hidden="true" />
      {(payment ? payName : statusName)[value] || value}
    </span>
  );
}
const timeFormatter = new Intl.DateTimeFormat("es-CO", {
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "America/Bogota",
});

export function SalesWorkspace({
  business,
  permissions,
  csrf,
  params,
  navigate,
  initialScroll,
  rememberScroll,
}: Props) {
  const query = params.get("q") || "";
  const status = params.get("status") || "active";
  const offset = Math.max(0, Number(params.get("offset")) || 0);
  const selected = params.get("order");
  const [search, setSearch] = useState(query);
  const scroll = useRef<HTMLDivElement>(null);
  const previousScroll = useRef(0);
  const returnFocus = useRef<HTMLAnchorElement | null>(null);
  const previousSelected = useRef(selected);
  useEffect(() => setSearch(query), [query]);
  useEffect(() => {
    if (search === query) return;
    const timer = setTimeout(
      () => navigate({ q: search.trim(), offset: null, order: null }),
      180,
    );
    return () => clearTimeout(timer);
  }, [search, query]);
  const list = useResource<Listing>(
    `${endpoint(business)}/sales?q=${encodeURIComponent(query)}&status=${status}&offset=${offset}&limit=25&${periodQuery(params)}`,
  );
  useEffect(() => {
    if (!selected && previousSelected.current) {
      requestAnimationFrame(() => {
        if (scroll.current) scroll.current.scrollTop = previousScroll.current;
        returnFocus.current?.focus({ preventScroll: true });
      });
    }
    previousSelected.current = selected;
  }, [selected]);
  const restored = useRef(false);
  useEffect(() => {
    if (list.data && !restored.current) {
      restored.current = true;
      requestAnimationFrame(() => {
        if (scroll.current) scroll.current.scrollTop = initialScroll;
      });
    }
  }, [list.data]);
  const active = Object.entries(list.data?.counts || {})
    .filter(([s]) => !["completed", "cancelled"].includes(s))
    .reduce((sum, [, n]) => sum + n, 0);
  function close() {
    if (history.state?.customerWorkspace) history.back();
    else navigate({ order: null });
  }
  return (
    <div className={`sales-workspace ${selected ? "sale-selected" : ""}`}>
      <div className="page">
        <section className="page-heading">
          <div>
            <h1>Ventas</h1>
            <p>Los pedidos, del primer paso a la entrega.</p>
          </div>
          <button className="button secondary" onClick={list.retry}>
            <RefreshCw size={16} />
            Actualizar
          </button>
        </section>
        <section className="sales-summary" aria-label="Estado de los pedidos">
          <div>
            <span>
              <ShoppingBag size={17} />
              En curso
            </span>
            <strong>{list.data ? count(active) : "—"}</strong>
          </div>
          <div>
            <span>
              <PackageCheck size={17} />
              Listos para entregar
            </span>
            <strong>
              {list.data ? count(list.data.counts.ready || 0) : "—"}
            </strong>
          </div>
          <div>
            <span>
              <Clock3 size={17} />
              Pagos por revisar · actuales
            </span>
            <strong>{list.data ? count(list.data.review_count) : "—"}</strong>
          </div>
        </section>
        <section
          className="customer-surface"
          aria-label="Directorio de pedidos"
        >
          <div className="surface-heading">
            <h2>
              Pedidos <span>{list.data ? count(list.data.count) : "…"}</span>
            </h2>
            <a
              className="legacy-link"
              href={`/admin?business_id=${encodeURIComponent(business)}`}
            >
              Operaciones completas
              <ExternalLink size={13} />
            </a>
          </div>
          <div className="toolbar">
            <div className="tabs" aria-label="Filtrar pedidos">
              {[
                ["active", "En curso"],
                ["ready", "Listos"],
                ["all", "Todos"],
              ].map(([value, label]) => (
                <button
                  key={value}
                  aria-pressed={status === value}
                  className={status === value ? "selected" : ""}
                  onClick={() =>
                    navigate({
                      status: value === "active" ? null : value,
                      offset: null,
                      order: null,
                    })
                  }
                >
                  {label}
                </button>
              ))}
            </div>
            <div className="search-controls">
              <label className="search">
                <Search size={17} />
                <input
                  type="search"
                  value={search}
                  aria-label="Buscar pedido por código"
                  placeholder="Buscar código de pedido"
                  onChange={(e) => setSearch(e.target.value)}
                />
                {search && (
                  <button
                    aria-label="Limpiar búsqueda de pedidos"
                    onClick={() => {
                      setSearch("");
                      navigate({ q: null, offset: null });
                    }}
                  >
                    <X size={16} />
                  </button>
                )}
              </label>
              <label className="filter">
                <span className="sr-only">Estado del pedido</span>
                <select
                  aria-label="Estado del pedido"
                  value={status}
                  onChange={(e) =>
                    navigate({
                      status: e.target.value,
                      offset: null,
                      order: null,
                    })
                  }
                >
                  <option value="active">En curso</option>
                  <option value="all">Todos</option>
                  {Object.entries(statusName).map(([key, label]) => (
                    <option key={key} value={key}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </div>
          <div
            className="list-scroll sales-scroll"
            ref={scroll}
            onScroll={(e) => rememberScroll(e.currentTarget.scrollTop)}
            data-testid="sales-list"
          >
            {list.error ? (
              <Failure message={list.error} retry={list.retry} />
            ) : !list.data ? (
              <Loading />
            ) : !list.data.count ? (
              <div className="state">
                <PackageCheck size={30} />
                <h3>
                  {query ? "No encontramos ese pedido" : "Todo al día por aquí"}
                </h3>
                <p>
                  {query
                    ? "Prueba con otro código o cambia el filtro."
                    : "Los pedidos de este estado aparecerán aquí."}
                </p>
                <button
                  className="button secondary"
                  onClick={() => {
                    setSearch("");
                    navigate({ q: null, status: "all", offset: null });
                  }}
                >
                  Ver todos los pedidos
                </button>
              </div>
            ) : (
              <table className="sales-table">
                <thead>
                  <tr>
                    <th>Pedido</th>
                    <th>Estado</th>
                    <th>Entrega</th>
                    <th>Total</th>
                    <th>Pago</th>
                  </tr>
                </thead>
                <tbody>
                  {list.data.items.map((o) => (
                    <tr
                      key={o.id}
                      className={o.id === selected ? "current" : ""}
                    >
                      <td>
                        <a
                          className="sale-link"
                          href={`?${new URLSearchParams({ ...Object.fromEntries(params), business, order: o.id })}`}
                          onClick={(e) => {
                            if (
                              e.ctrlKey ||
                              e.metaKey ||
                              e.shiftKey ||
                              e.altKey
                            )
                              return;
                            e.preventDefault();
                            previousScroll.current =
                              scroll.current?.scrollTop || 0;
                            returnFocus.current = e.currentTarget;
                            navigate({ order: o.id }, true);
                          }}
                        >
                          <strong>#{o.public_code}</strong>
                          <span>{o.customer_name || "Cliente sin nombre"}</span>
                          <small>
                            {date(o.created_at)} ·{" "}
                            {timeFormatter.format(new Date(o.created_at))}
                          </small>
                        </a>
                      </td>
                      <td>
                        <Status value={o.status} />
                        <span className="mobile-total">
                          {amount(o.total_minor, o.currency)}
                        </span>
                        <span className="mobile-payment">
                          {payName[o.payment_status] || o.payment_status} ·{" "}
                          {o.fulfillment_type === "delivery"
                            ? "Domicilio"
                            : "Recogida"}
                        </span>
                      </td>
                      <td>
                        <span className="fulfillment">
                          {o.fulfillment_type === "delivery" ? (
                            <Truck size={15} />
                          ) : (
                            <ShoppingBag size={15} />
                          )}
                          <span>
                            {o.fulfillment_type === "delivery"
                              ? "Domicilio"
                              : "Recogida"}
                          </span>
                        </span>
                      </td>
                      <td className="sale-total">
                        {amount(o.total_minor, o.currency)}
                      </td>
                      <td>
                        <Status value={o.payment_status} payment />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          <footer className="table-footer">
            <span aria-live="polite">
              {list.data
                ? `${list.data.count ? offset + 1 : 0}–${Math.min(offset + 25, list.data.count)} de ${list.data.count} pedidos`
                : "Cargando…"}
            </span>
            <div>
              <button
                className="icon-button"
                aria-label="Pedidos anteriores"
                disabled={!offset || !list.data}
                onClick={() =>
                  navigate({
                    offset: String(Math.max(0, offset - 25)),
                    order: null,
                  })
                }
              >
                <ChevronLeft size={18} />
              </button>
              <span>Página {Math.floor(offset / 25) + 1}</span>
              <button
                className="icon-button"
                aria-label="Pedidos siguientes"
                disabled={!list.data || offset + 25 >= list.data.count}
                onClick={() =>
                  navigate({ offset: String(offset + 25), order: null })
                }
              >
                <ChevronRight size={18} />
              </button>
            </div>
          </footer>
        </section>
      </div>
      {selected && (
        <SaleDetail
          key={business + selected}
          business={business}
          id={selected}
          csrf={csrf}
          canOperate={permissions.includes("operations.write")}
          close={close}
          changed={list.retry}
        />
      )}
    </div>
  );
}

function SaleDetail({
  business,
  id,
  csrf,
  canOperate,
  close,
  changed,
}: {
  business: string;
  id: string;
  csrf: string;
  canOperate: boolean;
  close: () => void;
  changed: () => void;
}) {
  const url = `${endpoint(business)}/sales/${encodeURIComponent(id)}`;
  const resource = useResource<Detail>(url);
  const [current, setCurrent] = useState<Detail>();
  const [confirmation, setConfirmation] = useState<Action | null>(null);
  const [busy, setBusy] = useState(false);
  const [cash, setCash] = useState(false);
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState("");
  const [uncertain, setUncertain] = useState(false);
  const heading = useRef<HTMLHeadingElement>(null);
  const pending = useRef(false);
  useEffect(() => {
    if (resource.data) setCurrent(resource.data);
  }, [resource.data]);
  useEffect(() => {
    if (current) heading.current?.focus();
  }, [current?.id]);
  const d = current;
  async function prepare(action: Action) {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setMessage("");
    try {
      const fresh = await api<Detail>(url);
      setCurrent(fresh);
      if (fresh.version !== d?.version) {
        setMessage("El pedido cambió. Revisa la información actualizada.");
        return;
      }
      const now = fresh.actions.find(
        (a) => a.status === action.status && a.allowed,
      );
      if (!now) {
        setMessage("Esta acción ya no está disponible. Revisa el pedido.");
        return;
      }
      setCash(false);
      setReason("");
      if (now.confirmation || now.status === "cancelled") setConfirmation(now);
      else await commit(now, fresh);
    } catch (e) {
      setMessage(
        e instanceof Error ? e.message : "No se pudo revisar el pedido.",
      );
    } finally {
      setBusy(false);
      pending.current = false;
    }
  }
  async function commit(action: Action, order: Detail) {
    try {
      await api(`/api/operator/orders/${encodeURIComponent(id)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", "X-101-CSRF": csrf },
        body: JSON.stringify({
          status: action.status,
          expected_version: order.version,
          reason:
            action.status === "cancelled"
              ? reason
              : action.confirmation === "cash_received"
                ? "Efectivo recibido y pedido entregado; confirmado por el operador."
                : "Acción confirmada desde Ventas.",
        }),
        signal: AbortSignal.timeout(15000),
      });
      setConfirmation(null);
      setCurrent(await api<Detail>(url));
      setMessage("Pedido actualizado.");
      changed();
    } catch (e) {
      setConfirmation(null);
      setUncertain(true);
      setMessage(
        e instanceof Error && "status" in e && e.status === 409
          ? "El pedido cambió. Actualiza antes de decidir de nuevo."
          : "No se confirmó la actualización. Comprueba el estado antes de intentar otra acción.",
      );
    }
  }
  async function submit() {
    if (!confirmation || !d || pending.current) return;
    pending.current = true;
    setBusy(true);
    try {
      await commit(confirmation, d);
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }
  return (
    <aside className="detail sale-detail" aria-label="Detalle del pedido">
      <div className="detail-top">
        <button className="back-link" onClick={close}>
          <ArrowLeft size={17} />
          Pedidos
        </button>
        <button
          className="icon-button"
          aria-label="Cerrar pedido"
          onClick={close}
        >
          <X size={20} />
        </button>
      </div>
      {resource.error && !d ? (
        <Failure message={resource.error} retry={resource.retry} />
      ) : !d ? (
        <Loading />
      ) : (
        <div className="detail-body">
          <span className="eyebrow">
            {date(d.created_at)} ·{" "}
            {timeFormatter.format(new Date(d.created_at))}
          </span>
          <h2 ref={heading} tabIndex={-1}>
            Pedido #{d.public_code}
          </h2>
          <div className="order-badges">
            <Status value={d.status} />
            <Status value={d.payment_status} payment />
          </div>
          <div className="sale-customer">
            <strong>{d.customer_name || "Cliente sin nombre"}</strong>
            <span>{d.customer_phone || "Sin teléfono registrado"}</span>
            <small>
              {d.identity_verified
                ? "Identidad verificada"
                : "Pedido como invitado"}
            </small>
          </div>
          <div className="fulfillment-strip">
            {d.fulfillment_type === "delivery" ? (
              <Truck size={19} />
            ) : (
              <ShoppingBag size={19} />
            )}
            <span>
              {d.fulfillment_type === "delivery"
                ? "Entrega a domicilio"
                : "Recogida en el negocio"}
            </span>
          </div>
          {message && (
            <div
              className={`action-notice ${uncertain ? "attention" : ""}`}
              role="status"
            >
              {message}
              {uncertain && (
                <button
                  className="button secondary"
                  onClick={async () => {
                    try {
                      setCurrent(await api<Detail>(url));
                      setUncertain(false);
                      setMessage(
                        "Estado actualizado. Revisa el pedido antes de continuar.",
                      );
                      changed();
                    } catch {
                      setMessage(
                        "No se pudo comprobar el estado. Inténtalo cuando vuelva la conexión.",
                      );
                    }
                  }}
                >
                  Comprobar estado
                </button>
              )}
            </div>
          )}
          <section className="detail-section action-section">
            <div className="section-title">
              <h3>Siguiente paso</h3>
            </div>
            {!canOperate ? (
              <p className="detail-note">
                Tu acceso permite consultar este pedido. Una persona con permiso
                de operación puede actualizarlo.
              </p>
            ) : uncertain ? (
              <p className="detail-note">
                Las acciones están pausadas hasta comprobar el resultado.
              </p>
            ) : d.actions.length ? (
              <>
                <div className="order-actions">
                  {d.actions
                    .filter((a) => a.allowed)
                    .map((a) => (
                      <button
                        key={a.status}
                        className={`button ${a.status === "cancelled" ? "secondary cancel-action" : "primary"}`}
                        disabled={busy}
                        onClick={() => prepare(a)}
                      >
                        {busy
                          ? "Comprobando…"
                          : a.confirmation === "cash_received"
                            ? "Confirmar cobro y entrega"
                            : actionName[a.status]}
                        {a.status !== "cancelled" && <ArrowRight size={15} />}
                      </button>
                    ))}
                </div>
                {Array.from(
                  new Set(
                    d.actions
                      .filter((a) => !a.allowed && a.status !== "cancelled")
                      .map((a) => a.reason),
                  ),
                ).map((r) => (
                  <p key={r} className="detail-note">
                    {reasonName[r || ""] ||
                      "Revisa este pedido en operaciones antes de continuar."}
                  </p>
                ))}
              </>
            ) : (
              <p className="detail-note">Este pedido ya está cerrado.</p>
            )}
          </section>
          <section className="detail-section">
            <div className="section-title">
              <h3>Contenido del pedido</h3>
            </div>
            {d.items.length ? (
              d.items.map((item, i) => (
                <div className="sale-item" key={i}>
                  <span className="quantity">{item.quantity}×</span>
                  <div>
                    <strong>{item.name}</strong>
                    {item.modifiers.map((m, j) => (
                      <small key={j}>
                        {m.group_name}: {m.option_name}
                      </small>
                    ))}
                  </div>
                  <strong>{amount(item.line_total_minor, d.currency)}</strong>
                </div>
              ))
            ) : (
              <p className="detail-note">
                Este registro no conserva líneas de productos.
              </p>
            )}
            <dl className="sale-totals">
              <div>
                <dt>Subtotal</dt>
                <dd>{amount(d.subtotal_minor, d.currency)}</dd>
              </div>
              {d.discount_minor > 0 && (
                <div>
                  <dt>Descuentos</dt>
                  <dd>−{amount(d.discount_minor, d.currency)}</dd>
                </div>
              )}
              {d.delivery_fee_minor > 0 && (
                <div>
                  <dt>Domicilio</dt>
                  <dd>{amount(d.delivery_fee_minor, d.currency)}</dd>
                </div>
              )}
              <div className="grand-total">
                <dt>Total del pedido</dt>
                <dd>{amount(d.total_minor, d.currency)}</dd>
              </div>
            </dl>
            {d.notes && (
              <div className="order-note">
                <strong>Nota del cliente</strong>
                <p>{d.notes}</p>
              </div>
            )}
          </section>
          <section className="detail-section">
            <div className="section-title">
              <h3>Pago y devoluciones</h3>
            </div>
            {d.money.length ? (
              d.money.map((m) => (
                <div className="money" key={m.scope + m.currency}>
                  <span className="eyebrow">
                    {m.scope === "test"
                      ? "SIMULACIÓN"
                      : m.scope === "cash"
                        ? "EFECTIVO"
                        : "REGISTRO DEL PROVEEDOR"}{" "}
                    · {m.currency}
                  </span>
                  <dl>
                    <div>
                      <dt>Capturado</dt>
                      <dd>{amount(m.captured_minor, m.currency)}</dd>
                    </div>
                    <div>
                      <dt>Devuelto</dt>
                      <dd>{amount(m.refunded_minor, m.currency)}</dd>
                    </div>
                    <div>
                      <dt>Capturado menos devuelto</dt>
                      <dd>{amount(m.net_minor, m.currency)}</dd>
                    </div>
                  </dl>
                </div>
              ))
            ) : (
              <p className="detail-note">Aún no hay un pago confirmado.</p>
            )}
            <p className="detail-note">
              El total del pedido y el dinero recibido se muestran por separado.
            </p>
            <a
              className="legacy-link"
              href={`/admin?business_id=${encodeURIComponent(business)}`}
            >
              Abrir operaciones completas
              <ExternalLink size={14} />
            </a>
          </section>
        </div>
      )}
      <Dialog.Root
        open={!!confirmation}
        onOpenChange={(open) => {
          if (!open && !busy) setConfirmation(null);
        }}
      >
        <Dialog.Portal>
          <Dialog.Backdrop className="backdrop" />
          <Dialog.Popup className="action-dialog">
            <Dialog.Title>
              {confirmation?.confirmation === "cash_received"
                ? "Confirmar efectivo y entrega"
                : actionName[confirmation?.status || ""]}
            </Dialog.Title>
            <Dialog.Description>
              {confirmation?.confirmation === "cash_received"
                ? `Confirma que recibiste ${d ? amount(d.total_minor, d.currency) : ""} en efectivo y entregaste el pedido. Esto registrará el pago como recibido.`
                : confirmation?.status === "cancelled"
                  ? "El pedido dejará de prepararse. Esta acción no realiza una devolución de dinero."
                  : `Actualizarás el pedido #${d?.public_code} a “${statusName[confirmation?.status || ""]}”.`}
            </Dialog.Description>
            {confirmation?.confirmation === "cash_received" && (
              <label className="confirm-cash">
                <input
                  type="checkbox"
                  checked={cash}
                  onChange={(e) => setCash(e.target.checked)}
                />
                Recibí el efectivo y entregué el pedido.
              </label>
            )}
            {confirmation?.status === "cancelled" && (
              <label className="cancel-reason">
                Motivo de cancelación
                <textarea
                  maxLength={500}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
              </label>
            )}
            <div className="dialog-actions">
              <button
                className="button secondary"
                disabled={busy}
                onClick={() => setConfirmation(null)}
              >
                Volver
              </button>
              <button
                className="button primary"
                disabled={
                  busy ||
                  (confirmation?.confirmation === "cash_received" && !cash) ||
                  (confirmation?.status === "cancelled" && !reason.trim())
                }
                onClick={submit}
              >
                {busy ? "Guardando…" : "Confirmar"}
                <Check size={16} />
              </button>
            </div>
          </Dialog.Popup>
        </Dialog.Portal>
      </Dialog.Root>
    </aside>
  );
}
