import { useState } from "react";
import { Dialog } from "@base-ui/react/dialog";
import { ArrowLeft, ArrowRight, RefreshCw } from "lucide-react";
import { api, amount, endpoint, useResource, Failure, Loading } from "./ui";
import { OperationNotice, useOperation } from "./operations-ui";
import "./growth-channels.css";

type Props = {
  business: string;
  params: URLSearchParams;
  navigate: (changes: Record<string, string | null>, push?: boolean) => void;
};
type Context = {
  currency: string;
  currencies: string[];
  timezone: string;
  winback_days: number;
  analytics: Record<string, number | Record<string, number>>;
};
type Promotion = {
  id: string;
  code: string;
  name: string;
  discount_type: string;
  value: number;
  minimum_order_minor: number;
  maximum_discount_minor: number | null;
  starts_at: string | null;
  ends_at: string | null;
  per_customer_limit: number | null;
  total_redemption_limit: number | null;
  enabled: boolean;
};
type Reward = {
  id: string;
  name: string;
  description: string | null;
  points_cost: number;
  discount_minor: number;
  minimum_order_minor: number;
  enabled: boolean;
};
export function CustomerSections({ business, params, navigate }: Props) {
  const view = params.get("view") || "directory";
  return (
    <div
      className="tabs sales-views growth-tabs"
      aria-label="Secciones de clientes"
    >
      {[
        ["directory", "Directorio"],
        ["loyalty", "Fidelización"],
        ["promotions", "Promociones"],
        ["rewards", "Recompensas"],
        ["signup", "Registro"],
      ].map(([key, title]) => (
        <button
          key={key}
          className={view === key ? "selected" : ""}
          aria-pressed={view === key}
          onClick={() =>
            navigate(
              {
                view: key === "directory" ? null : key,
                customer: null,
                offset: null,
              },
              true,
            )
          }
        >
          {title}
        </button>
      ))}
    </div>
  );
}
export function Catalog({ business, params }: Props) {
  const promotions = params.get("view") === "promotions";
  const context = useResource<Context>(
    endpoint(business) + "/growth-workspace",
  );
  const rows = useResource<(Promotion | Reward)[]>(
    endpoint(business) + (promotions ? "/promotions" : "/rewards"),
  );
  return (
    <div className="page growth-channel-page">
      <section className="page-heading">
        <div>
          <h1>{promotions ? "Promociones" : "Recompensas"}</h1>
          <p>Condiciones y estado del catálogo existente.</p>
        </div>
        <button
          className="button secondary"
          onClick={() => {
            rows.retry();
            context.retry();
          }}
        >
          <RefreshCw size={16} />
          Actualizar
        </button>
      </section>
      {rows.error || context.error ? (
        <Failure
          message={rows.error || context.error!}
          retry={() => {
            rows.retry();
            context.retry();
          }}
        />
      ) : !rows.data || !context.data ? (
        <Loading />
      ) : (
        <section className="work-surface catalogue-grid">
          {!rows.data.length ? (
            <p>
              No hay {promotions ? "promociones" : "recompensas"} registradas.
            </p>
          ) : (
            rows.data.map((row) => (
              <article className="catalogue-item" key={row.id}>
                <h2>{row.name}</h2>
                <span className="badge">
                  {row.enabled ? "Habilitada" : "Deshabilitada"}
                </span>
                {"code" in row ? (
                  <>
                    <strong>{row.code}</strong>
                    <p>
                      {row.discount_type === "percent"
                        ? `${row.value / 100}%`
                        : amount(row.value, context.data!.currency)}{" "}
                      de descuento
                    </p>
                    <p>
                      Pedido mínimo:{" "}
                      {amount(row.minimum_order_minor, context.data!.currency)}
                    </p>
                    <p>
                      Descuento máximo:{" "}
                      {row.maximum_discount_minor === null
                        ? "Sin límite registrado"
                        : amount(
                            row.maximum_discount_minor,
                            context.data!.currency,
                          )}
                    </p>
                    <p>
                      Por cliente:{" "}
                      {row.per_customer_limit ?? "Sin límite registrado"} ·
                      Total:{" "}
                      {row.total_redemption_limit ?? "Sin límite registrado"}
                    </p>
                    <p>
                      Desde{" "}
                      {stamp(
                        row.starts_at,
                        context.data!.timezone,
                        "sin fecha inicial",
                      )}{" "}
                      hasta{" "}
                      {stamp(
                        row.ends_at,
                        context.data!.timezone,
                        "sin fecha final",
                      )}
                      .
                    </p>
                    <small>
                      Habilitada no significa vigente: al comprar se comprueban
                      fechas, límites y condiciones.
                    </small>
                  </>
                ) : (
                  <>
                    <p>{row.description}</p>
                    <p>
                      {row.points_cost} puntos →{" "}
                      {amount(row.discount_minor, context.data!.currency)}
                    </p>
                    <p>
                      Pedido mínimo:{" "}
                      {amount(row.minimum_order_minor, context.data!.currency)}
                    </p>
                    <small>
                      El saldo y las condiciones se comprueban al usarla.
                    </small>
                  </>
                )}
              </article>
            ))
          )}
        </section>
      )}
    </div>
  );
}
export function GrowthReport({ business }: Props) {
  const r = useResource<Context>(endpoint(business) + "/growth-workspace"),
    d = r.data,
    a = d?.analytics;
  return (
    <div className="page growth-channel-page">
      <section className="page-heading">
        <div>
          <h1>Comercio y clientes</h1>
          <p>
            Histórico de pedidos completados que actualmente figuran pagados.
          </p>
        </div>
        <button className="button secondary" onClick={r.retry}>
          <RefreshCw size={16} />
          Actualizar
        </button>
      </section>
      {r.error ? (
        <Failure message={r.error} retry={r.retry} />
      ) : !d || !a ? (
        <Loading />
      ) : (
        <>
          <p className="source-note">
            Incluye los canales registrados. Las cifras monetarias conservan el
            cálculo original y no descuentan devoluciones parciales; no son el
            balance diario ni el reporte mensual.
          </p>
          <section className="report-grid work-surface">
            {[
              ["Pedidos completados", "completed_orders"],
              ["Clientes con pedidos", "unique_customers"],
              ["Clientes que repiten", "repeat_customers"],
              ["Miembros de fidelización", "loyalty_members"],
              ["Puntos disponibles", "loyalty_points_outstanding"],
              ["Promociones usadas", "promotion_redemptions"],
              ["Mensajes manuales en cola", "queued_messages"],
              ["Mensajes suprimidos", "suppressed_messages"],
              ["Clientes sin compra reciente", "dormant_customers"],
            ].map(([title, key]) => (
              <div key={key}>
                <span>{title}</span>
                <strong>{Number(a[key]).toLocaleString("es-CO")}</strong>
              </div>
            ))}
            <div>
              <span>Clientes que repiten / clientes con pedidos</span>
              <strong>
                {(Number(a.repeat_customer_rate) * 100).toLocaleString(
                  "es-CO",
                  { maximumFractionDigits: 1 },
                )}
                %
              </strong>
            </div>
            {d.currencies.length <= 1 ? (
              [
                ["Importe de pedidos pagados", "net_revenue_minor"],
                ["Productos, sin entrega", "food_net_revenue_minor"],
                ["Entrega", "delivery_fees_minor"],
                ["Ticket promedio", "average_order_value_minor"],
                ["Subtotal antes de descuentos", "gross_revenue_minor"],
                ["Descuentos", "discount_minor"],
              ].map(([title, key]) => (
                <div key={key}>
                  <span>{title}</span>
                  <strong>
                    {amount(Number(a[key]), d.currencies[0] || d.currency)}
                  </strong>
                </div>
              ))
            ) : (
              <p>
                Hay varias monedas. El cálculo original no permite comparar
                estos importes juntos.
              </p>
            )}
          </section>
          <section className="work-surface channel-report">
            <h2>Pedidos por canal registrado</h2>
            {Object.entries(
              a.channel_order_counts as Record<string, number>,
            ).map(([channel, n]) => (
              <p key={channel}>
                {channel}: {n}
              </p>
            ))}
            <p className="source-note">
              “Sin compra reciente” usa {d.winback_days} días. Un contacto no
              equivale a un pedido adicional causado por marketing.
            </p>
          </section>
        </>
      )}
    </div>
  );
}
type Message = {
  id: string;
  channel: string;
  purpose: string;
  message_kind: string;
  destination: string;
  body: string;
  scheduled_at: string;
  status: string;
  suppression_reason: string | null;
  sent_at: string | null;
};
const states: Record<string, string> = {
  queued: "En cola",
  handed_off: "Preparado para envío manual",
  suppressed: "Suprimido",
  sent: "Enviado — registro histórico",
  failed: "Fallido",
};
function stamp(value: string | null, zone: string, empty = "Sin confirmar") {
  return value
    ? new Intl.DateTimeFormat("es-CO", {
        timeZone: zone,
        dateStyle: "medium",
        timeStyle: "short",
      }).format(
        new Date(/[Zz]|[+-]\d\d:\d\d$/.test(value) ? value : value + "Z"),
      )
    : empty;
}
export function ManualOutbox({
  business,
  params,
  navigate,
  csrf,
  permissions,
}: Props & { csrf: string; permissions: string[] }) {
  const root = endpoint(business),
    offset = Math.max(0, Number(params.get("outbox_offset")) || 0),
    status = params.get("outbox_status") || "all";
  const list = useResource<{ items: Message[]; count: number }>(
      `${root}/growth-workspace/outbox?status=${encodeURIComponent(status)}&offset=${offset}`,
    ),
    context = useResource<Context>(root + "/growth-workspace");
  const op = useOperation(csrf),
    canWrite = permissions.includes("growth.write");
  const [pending, setPending] = useState<Message | "plan" | null>(null),
    [checked, setChecked] = useState(false),
    [prepared, setPrepared] = useState<Message | null>(null),
    [limit, setLimit] = useState(100);
  const phone = prepared?.destination.replace(/^\+/, "");
  async function refresh() {
    try {
      await api(
        `${root}/growth-workspace/outbox?status=${encodeURIComponent(status)}&offset=${offset}`,
      );
      list.retry();
      context.retry();
      op.checked();
    } catch {
      op.setMessage(
        "No pudimos comprobar la bandeja. Conserva la solicitud sin repetirla.",
      );
    }
  }
  return (
    <div className="page growth-channel-page">
      <section className="page-heading">
        <div>
          <h1>Mensajes manuales</h1>
          <p>
            Planifica y prepara mensajes existentes para abrirlos en WhatsApp.
          </p>
        </div>
        <button
          className="button secondary"
          disabled={op.busy}
          onClick={refresh}
        >
          <RefreshCw size={16} />
          Comprobar bandeja
        </button>
      </section>
      <p className="source-note">
        Esta bandeja conserva los mensajes del sistema anterior. Preparar o
        abrir el mensaje no confirma que se haya enviado ni entregado.
      </p>
      <OperationNotice message={op.message} />
      {canWrite && (
        <section className="work-surface retention-plan">
          <h2>Invitar a volver</h2>
          <p>
            Usa la regla existente y los permisos vigentes. No se crea un plan
            al abrir esta página.
          </p>
          <label>
            Máximo de contactos
            <input
              type="number"
              min={1}
              max={1000}
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
            />
          </label>
          <button
            className="button secondary"
            disabled={op.busy || op.uncertain || limit < 1 || limit > 1000}
            onClick={() => {
              setPending("plan");
              setChecked(false);
            }}
          >
            Preparar plan de regreso
          </button>
        </section>
      )}
      <label className="channel-filter">
        Estado
        <select
          value={status}
          onChange={(e) =>
            navigate({ outbox_status: e.target.value, outbox_offset: null })
          }
        >
          <option value="all">Todos</option>
          {Object.entries(states).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>
      {list.error ? (
        <Failure message={list.error} retry={list.retry} />
      ) : !list.data ? (
        <Loading />
      ) : (
        <section className="work-surface manual-outbox">
          {!list.data.items.length && <p>No hay mensajes en esta vista.</p>}
          {list.data.items.map((m) => (
            <article className="outbox-message" key={m.id}>
              <span className="badge">{states[m.status] || m.status}</span>
              <h2>
                {m.message_kind === "winback"
                  ? "Invitación a volver"
                  : m.message_kind}
              </h2>
              <p>
                {m.destination} · {m.channel}
              </p>
              <p className="message-copy">{m.body}</p>
              <p>{stamp(m.scheduled_at, context.data?.timezone || "UTC")}</p>
              {m.suppression_reason && (
                <p>
                  Motivo:{" "}
                  {(
                    {
                      CURRENT_CHANNEL_PERMISSION_REQUIRED:
                        "El permiso actual del canal no autoriza este mensaje.",
                      WHATSAPP_OPT_IN_REQUIRED:
                        "Falta confirmar el permiso de WhatsApp.",
                      MARKETING_OPT_IN_REQUIRED:
                        "Falta confirmar el permiso de marketing.",
                      CONTACT_PHONE_REQUIRED: "Falta un teléfono de contacto.",
                      CONSENT_OR_RECIPIENT_CHANGED:
                        "El permiso o destinatario cambió. Revisa la información actual.",
                    } as Record<string, string>
                  )[m.suppression_reason] ||
                    "Este mensaje requiere revisión antes de prepararse."}
                </p>
              )}
              {m.sent_at && (
                <p>
                  Registro de envío:{" "}
                  {stamp(m.sent_at, context.data?.timezone || "UTC")}
                </p>
              )}
              {canWrite &&
                m.channel === "whatsapp" &&
                ["queued", "handed_off"].includes(m.status) && (
                  <button
                    className="button secondary"
                    disabled={op.busy || op.uncertain}
                    onClick={() => {
                      setPending(m);
                      setPrepared(null);
                      setChecked(false);
                    }}
                  >
                    Revisar y preparar mensaje
                  </button>
                )}
            </article>
          ))}
          <div className="table-footer">
            <span>{list.data.count} mensajes</span>
            <div className="pagination">
              <button
                className="icon-button"
                aria-label="Mensajes manuales anteriores"
                disabled={!offset}
                onClick={() =>
                  navigate({ outbox_offset: String(Math.max(0, offset - 25)) })
                }
              >
                <ArrowLeft size={17} />
              </button>
              <button
                className="icon-button"
                aria-label="Más mensajes manuales"
                disabled={offset + 25 >= list.data.count}
                onClick={() => navigate({ outbox_offset: String(offset + 25) })}
              >
                <ArrowRight size={17} />
              </button>
            </div>
          </div>
        </section>
      )}
      {prepared && phone && /^[0-9]{5,15}$/.test(phone) && (
        <section className="work-surface prepared-handoff">
          <h2>Mensaje autorizado para abrir</h2>
          <p>{prepared.destination}</p>
          <p className="message-copy">{prepared.body}</p>
          <a
            className="button primary"
            href={`https://wa.me/${phone}?text=${encodeURIComponent(prepared.body)}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            Abrir WhatsApp
          </a>
          <p>
            Revisa y envía desde WhatsApp. Aquí no se registra una entrega
            automática.
          </p>
        </section>
      )}
      <Dialog.Root
        open={!!pending}
        onOpenChange={(open) => {
          if (!open && !op.busy) setPending(null);
        }}
      >
        <Dialog.Portal>
          <Dialog.Backdrop className="backdrop" />
          <Dialog.Popup className="action-dialog">
            <Dialog.Title>
              {pending === "plan"
                ? "Preparar plan de regreso"
                : "Preparar mensaje manual"}
            </Dialog.Title>
            <Dialog.Description>
              {pending === "plan"
                ? `Se revisarán hasta ${limit} contactos con la regla existente. Se guardarán mensajes elegibles o motivos de supresión; no se enviarán mensajes.`
                : pending
                  ? `${pending.destination}: ${pending.body}`
                  : ""}
            </Dialog.Description>
            <label className="review-check">
              <input
                type="checkbox"
                checked={checked}
                onChange={(e) => setChecked(e.target.checked)}
              />
              Revisé el alcance y el mensaje.
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
                  const command = pending;
                  const result = await op.perform<Message | Message[]>(
                    command === "plan"
                      ? root + "/winback/plan"
                      : `/api/operator/outbox/${encodeURIComponent((command as Message).id)}/handoff`,
                    command === "plan" ? { limit } : undefined,
                  );
                  setPending(null);
                  if (result) {
                    if (!Array.isArray(result)) setPrepared(result);
                    list.retry();
                    context.retry();
                    op.setMessage(
                      Array.isArray(result)
                        ? `Plan preparado: ${result.length} registros. Revisa sus estados.`
                        : "Mensaje preparado; aún no se ha enviado.",
                    );
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
  );
}
