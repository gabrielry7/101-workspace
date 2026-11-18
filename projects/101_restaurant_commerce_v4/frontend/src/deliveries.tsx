import { useEffect, useRef, useState } from "react";
import { Dialog } from "@base-ui/react/dialog";
import { RefreshCw, X, ArrowLeft, ArrowRight } from "lucide-react";
import { api, endpoint, amount, useResource, Failure, Loading } from "./ui";
import { OperationNotice, useOperation } from "./operations-ui";
import { periodQuery } from "./workspace-views";
import "./operations-workspace.css";

const states: Record<string, string> = {
  quoted: "Por despachar",
  requested: "Solicitada",
  courier_assigned: "Transportador asignado",
  picked_up: "En camino",
  delivered: "Entregada",
  cancelled: "Cancelada",
  failed: "Fallida",
};
const verbs: Record<string, string> = {
  dispatch: "Solicitar transportador",
  cancel: "Cancelar entrega",
  picked_up: "Simular recogida",
  delivered: "Simular entrega",
};
type Delivery = {
  id: string;
  order_id: string;
  order_public_code: string;
  version: number;
  order_version: number;
  status: string;
  order_status: string;
  order_payment_status: string;
  currency: string;
  fee_minor: number;
  provider: string;
  provider_available: boolean;
  provider_delivery_reference: string | null;
  destination_address: string;
  destination_city: string;
  destination_instructions: string | null;
  courier_name: string | null;
  courier_phone: string | null;
  estimated_pickup_at: string | null;
  estimated_dropoff_at: string | null;
  tracking_url: string | null;
  actions: string[];
  timezone: string;
  payment_review: boolean;
  refund_intent: boolean;
  cancellation_requested: boolean;
  dispatch_pending: boolean;
};
type Props = {
  business: string;
  csrf: string;
  permissions: string[];
  params: URLSearchParams;
  navigate: (changes: Record<string, string | null>, push?: boolean) => void;
};
function stamp(value: string | null, zone: string) {
  return value
    ? new Intl.DateTimeFormat("es-CO", {
        timeZone: zone,
        dateStyle: "medium",
        timeStyle: "short",
      }).format(
        new Date(/[Zz]|[+-]\d\d:\d\d$/.test(value) ? value : value + "Z"),
      )
    : "Sin confirmar";
}
export function trackingLink(
  value: string | null,
  origins: string[] | undefined,
) {
  if (!value || /[\\\u0000-\u0020\u007f]/.test(value)) return null;
  try {
    const url = new URL(value, location.origin);
    return url.protocol === "https:" &&
      !url.username &&
      !url.password &&
      origins?.includes(url.origin)
      ? url.href
      : null;
  } catch {
    return null;
  }
}
export function DeliveryWorkspace({
  business,
  csrf,
  permissions,
  params,
  navigate,
}: Props) {
  const status = params.get("delivery_status") || "active",
    offset = Math.max(0, Number(params.get("delivery_offset")) || 0),
    selected = params.get("delivery");
  const root = endpoint(business) + "/sales-deliveries";
  const list = useResource<{ items: Delivery[]; count: number }>(
    `${root}?status=${encodeURIComponent(status)}&offset=${offset}&limit=25&${periodQuery(params)}`,
  );
  useEffect(() => {
    const timer = setInterval(() => {
      if (!document.hidden) list.retry();
    }, 15000);
    return () => clearInterval(timer);
  }, [business, status, offset, params.toString()]);
  return (
    <div
      className={`sales-workspace operations-panel ${selected ? "sale-selected" : ""}`}
    >
      <div className="page">
        <section className="page-heading">
          <div>
            <h1>Entregas</h1>
            <p>Del pedido preparado a la llegada del transportador.</p>
          </div>
          <button className="button secondary" onClick={list.retry}>
            <RefreshCw size={16} />
            Actualizar
          </button>
        </section>
        <section className="customer-surface">
          <div className="surface-heading">
            <h2>
              Entregas <span>{list.data?.count ?? "…"}</span>
            </h2>
          </div>
          <div className="toolbar">
            <label className="reservation-filter">
              Estado de la entrega
              <select
                aria-label="Estado de la entrega"
                value={status}
                onChange={(e) =>
                  navigate({
                    delivery_status: e.target.value,
                    delivery_offset: null,
                    delivery: null,
                  })
                }
              >
                <option value="active">Pendientes y en curso</option>
                <option value="all">Todas</option>
                {Object.entries(states).map(([k, v]) => (
                  <option value={k} key={k}>
                    {v}
                  </option>
                ))}
              </select>
            </label>
          </div>
          {list.error ? (
            <Failure message={list.error} retry={list.retry} />
          ) : !list.data ? (
            <Loading />
          ) : !list.data.items.length ? (
            <div className="state">
              <h3>No hay entregas en esta vista</h3>
            </div>
          ) : (
            <div className="list-scroll operation-rows">
              {list.data.items.map((d) => (
                <a
                  className={`operation-row ${selected === d.id ? "selected" : ""}`}
                  key={d.id}
                  href={`/workspace/sales?${new URLSearchParams({ ...Object.fromEntries(params), delivery: d.id })}`}
                  onClick={(e) => {
                    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey)
                      return;
                    e.preventDefault();
                    navigate({ delivery: d.id }, true);
                  }}
                >
                  <span>
                    <strong>#{d.order_public_code}</strong>
                    <small>{d.destination_address}</small>
                  </span>
                  <span>
                    <strong>{states[d.status]}</strong>
                    <small>{d.destination_city}</small>
                  </span>
                  <span>{amount(d.fee_minor, d.currency)}</span>
                </a>
              ))}
            </div>
          )}
          {list.data && (
            <div className="table-footer">
              <span>{list.data.count} entregas</span>
              <div className="pagination">
                <button
                  className="icon-button"
                  aria-label="Entregas anteriores"
                  disabled={!offset}
                  onClick={() =>
                    navigate({
                      delivery_offset: String(Math.max(0, offset - 25)),
                      delivery: null,
                    })
                  }
                >
                  <ArrowLeft size={17} />
                </button>
                <button
                  className="icon-button"
                  aria-label="Más entregas"
                  disabled={offset + 25 >= list.data.count}
                  onClick={() =>
                    navigate({
                      delivery_offset: String(offset + 25),
                      delivery: null,
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
        <DeliveryDetail
          key={business + selected}
          id={selected}
          root={root}
          csrf={csrf}
          canOperate={permissions.includes("operations.write")}
          changed={list.retry}
          close={() => {
            if (history.state?.customerWorkspace) history.back();
            else navigate({ delivery: null });
          }}
        />
      )}
    </div>
  );
}
function DeliveryDetail({
  id,
  root,
  csrf,
  canOperate,
  close,
  changed,
}: {
  id: string;
  root: string;
  csrf: string;
  canOperate: boolean;
  close: () => void;
  changed: () => void;
}) {
  const resource = useResource<Delivery>(root + "/" + encodeURIComponent(id));
  const policy = useResource<{ tracking_origins: string[] }>(
    "/api/browser-policy",
  );
  const [current, setCurrent] = useState<Delivery>(),
    [pending, setPending] = useState<{ action: string; data: Delivery } | null>(
      null,
    ),
    [checked, setChecked] = useState(false);
  const op = useOperation(csrf),
    d = current || resource.data;
  async function check(explicit = true) {
    try {
      const data = await api<Delivery>(root + "/" + encodeURIComponent(id));
      setCurrent(data);
      changed();
      if (
        !op.uncertain ||
        (d &&
          (data.version !== d.version ||
            data.order_version !== d.order_version))
      ) {
        if (explicit) op.checked();
      } else
        op.setMessage(
          "Todavía no vemos un cambio confirmado. No hemos repetido la solicitud.",
        );
    } catch {
      op.setMessage(
        "No pudimos comprobar el estado. Vuelve a intentarlo cuando tengas conexión.",
      );
    }
  }
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    if (d) heading.current?.focus({ preventScroll: true });
  }, [d?.id]);
  const link = trackingLink(
    d?.tracking_url || null,
    policy.data?.tracking_origins,
  );
  return (
    <aside
      className="detail sale-detail operation-detail"
      aria-label="Detalle de entrega"
    >
      <div className="detail-top">
        <button
          className="icon-button"
          aria-label="Cerrar entrega"
          onClick={close}
        >
          <X size={19} />
        </button>
      </div>
      {resource.error && !d ? (
        <Failure message={resource.error} retry={resource.retry} />
      ) : !d ? (
        <Loading />
      ) : (
        <div className="detail-body">
          <span className="eyebrow">Pedido #{d.order_public_code}</span>
          <h2 ref={heading} tabIndex={-1}>
            Entrega #{d.order_public_code}
          </h2>
          <span className="badge">{states[d.status]}</span>
          <p>
            {d.destination_address}
            <br />
            {d.destination_city}
          </p>
          {d.destination_instructions && <p>{d.destination_instructions}</p>}
          <dl>
            <div>
              <dt>Transportador</dt>
              <dd>{d.courier_name || "Sin asignar"}</dd>
            </div>
            <div>
              <dt>Teléfono del transportador</dt>
              <dd>{d.courier_phone || "Sin confirmar"}</dd>
            </div>
            <div>
              <dt>Recogida estimada</dt>
              <dd>{stamp(d.estimated_pickup_at, d.timezone)}</dd>
            </div>
            <div>
              <dt>Llegada estimada</dt>
              <dd>{stamp(d.estimated_dropoff_at, d.timezone)}</dd>
            </div>
            <div>
              <dt>Costo de entrega</dt>
              <dd>{amount(d.fee_minor, d.currency)}</dd>
            </div>
            <div>
              <dt>Referencia del proveedor</dt>
              <dd>{d.provider_delivery_reference || "Sin despachar"}</dd>
            </div>
          </dl>
          {link ? (
            <a
              className="button secondary"
              href={link}
              target="_blank"
              rel="noopener noreferrer"
            >
              Ver seguimiento del proveedor
            </a>
          ) : (
            <p className="source-note">
              {d.provider === "simulated_delivery"
                ? "El seguimiento de esta demostración se muestra aquí."
                : "No hay un enlace de seguimiento autorizado disponible."}
            </p>
          )}
          {!d.provider_available && (
            <p className="operation-notice">
              La conexión con este proveedor de entregas está pendiente.
            </p>
          )}
          {d.payment_review && (
            <p className="operation-notice">
              El pago necesita revisión antes de despachar.
            </p>
          )}
          {d.refund_intent && (
            <p className="operation-notice">
              Hay una solicitud de devolución. Revisa el pago antes de
              despachar.
            </p>
          )}
          {d.dispatch_pending && (
            <p className="operation-notice">
              Hay una solicitud de transportador sin confirmar. Se requiere
              revisar con el proveedor; no la repetiremos automáticamente.
            </p>
          )}
          {d.cancellation_requested && d.status !== "cancelled" && (
            <p>
              Cancelación solicitada. El estado todavía no confirma que se haya
              cancelado.
            </p>
          )}
          <OperationNotice message={op.message} />
          <section>
            <h3>Acciones</h3>
            {!canOperate ? (
              <p>Tu acceso permite consultar las entregas.</p>
            ) : (
              <div className="order-actions">
                {d.actions.map((action) => (
                  <button
                    className="button secondary"
                    key={action}
                    disabled={op.busy || op.uncertain}
                    onClick={() => {
                      setPending({ action, data: d });
                      setChecked(false);
                    }}
                  >
                    {verbs[action]}
                  </button>
                ))}
              </div>
            )}
            <button
              className="button secondary"
              disabled={op.busy}
              onClick={() => check()}
            >
              <RefreshCw size={16} />
              {op.uncertain ? "Comprobar estado" : "Actualizar estado"}
            </button>
          </section>
          <Dialog.Root
            open={!!pending}
            onOpenChange={(open) => {
              if (!open && !op.busy) setPending(null);
            }}
          >
            <Dialog.Portal>
              <Dialog.Backdrop className="backdrop" />
              <Dialog.Popup className="action-dialog">
                <Dialog.Title>{pending && verbs[pending.action]}</Dialog.Title>
                <Dialog.Description>
                  {pending?.action === "cancel"
                    ? "Cancelar la entrega no cancela el pedido ni devuelve dinero."
                    : pending?.action === "dispatch"
                      ? "Se solicitará el transportador para este pedido."
                      : "Este cambio solo simula el estado de la entrega."}
                </Dialog.Description>
                <label className="confirm-cash">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={(e) => setChecked(e.target.checked)}
                  />
                  Confirmo la acción para el pedido #
                  {pending?.data.order_public_code}.
                </label>
                <div className="dialog-actions">
                  <button
                    className="button secondary"
                    disabled={op.busy}
                    onClick={() => setPending(null)}
                  >
                    Volver
                  </button>
                  <button
                    className="button primary"
                    disabled={!checked || op.busy || op.uncertain}
                    onClick={async () => {
                      if (!pending) return;
                      const { action, data } = pending;
                      const body = {
                        expected_version: data.version,
                        expected_order_version: data.order_version,
                      };
                      const result = await op.perform<Delivery>(
                        ["dispatch", "cancel"].includes(action)
                          ? `/api/operator/orders/${encodeURIComponent(data.order_id)}/delivery/${action}`
                          : `/api/operator/deliveries/${encodeURIComponent(id)}/status`,
                        ["dispatch", "cancel"].includes(action)
                          ? body
                          : { ...body, status: action },
                        ["dispatch", "cancel"].includes(action)
                          ? "POST"
                          : "PATCH",
                      );
                      setPending(null);
                      if (result) {
                        setCurrent({ ...data, ...result, actions: [] });
                        await check(false);
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
