import { useEffect, useRef, useState } from "react";
import { Dialog } from "@base-ui/react/dialog";
import { ArrowLeft, ArrowRight, RefreshCw, X } from "lucide-react";
import { api, endpoint, useResource, Failure, Loading } from "./ui";
import { OperationNotice, useOperation } from "./operations-ui";
import type { ChannelConfig } from "./channel-config";
import "./growth-channels.css";

type Props = {
  business: string;
  csrf: string;
  permissions: string[];
  demo: boolean;
  params: URLSearchParams;
  navigate: (changes: Record<string, string | null>, push?: boolean) => void;
};
type Conversation = {
  id: string;
  destination: string;
  scope: string;
  state: string;
  assigned_name: string | null;
  opted_out: boolean;
  last_inbound_at: string | null;
  service_window_open: boolean;
  reply_allowed: boolean;
};
type Incoming = {
  id: string;
  scope: string;
  received_at: string;
  provider_at?: string;
  document: {
    text?: string;
    destination?: string;
    from?: string;
    kind?: string;
    at?: string;
    [key: string]: unknown;
  };
};
type Detail = Conversation & {
  messages: Incoming[];
  message_count: number;
  reply_count: number;
  replies: {
    id: string;
    body: string;
    state: string;
    reason: string | null;
    actor: string;
    provider_id: string | null;
    created_at: string;
  }[];
};
const states: Record<string, string> = {
  queued: "En cola",
  sending: "En proceso",
  accepted: "Aceptada por simulador",
  delivered: "Entrega reportada",
  read: "Lectura reportada",
  unknown: "Resultado desconocido",
  skipped: "Omitida",
  failed: "Fallida",
  waiting_for_customer: "Esperando al cliente",
  assigned: "Asignada",
};
function time(iso: string | null) {
  if (!iso) return "Sin fecha";
  return new Date(
    /[Zz]|[+-]\d\d:\d\d$/.test(iso) ? iso : iso + "Z",
  ).toLocaleString("es-CO");
}
export function ChannelInbox(props: Props) {
  const { business, csrf, permissions, demo, params, navigate } = props,
    root = endpoint(business),
    channel = params.get("channel") === "sms" ? "sms" : "whatsapp",
    offset = Math.max(0, Number(params.get("inbox_offset")) || 0),
    scope = params.get("inbox_scope") || "all",
    selected = channel === "whatsapp" ? params.get("conversation") : null;
  const config = useResource<ChannelConfig>(root + "/" + channel),
    list = useResource<{ items: (Conversation | Incoming)[]; count: number }>(
      `${root}/channel-workspace/inbox?channel=${channel}&scope=${scope}&offset=${offset}`,
    ),
    op = useOperation(csrf),
    canWrite = permissions.includes("growth.write");
  const [simulation, setSimulation] = useState(false),
    [command, setCommand] = useState<string | null>(null),
    [customer, setCustomer] = useState(""),
    [text, setText] = useState(""),
    [checked, setChecked] = useState(false);
  const request = useRef<string | null>(null);
  async function refresh() {
    try {
      await api(
        `${root}/channel-workspace/inbox?channel=${channel}&scope=${scope}&offset=${offset}`,
      );
      list.retry();
      config.retry();
      op.checked();
    } catch {
      op.setMessage(
        "No pudimos comprobar el historial. No repitas una acción sin revisarlo.",
      );
    }
  }
  return (
    <div
      className={`sales-workspace channel-inbox ${selected ? "sale-selected" : ""}`}
    >
      <div className="page growth-channel-page">
        <section className="page-heading">
          <div>
            <h1>Conversaciones</h1>
            <p>
              Mensajes recibidos y respuestas registradas, separados por canal.
            </p>
          </div>
          <button
            className="button secondary"
            disabled={op.busy}
            onClick={refresh}
          >
            <RefreshCw size={16} />
            Actualizar historial
          </button>
        </section>
        <div className="tabs channel-tabs" aria-label="Canal de conversaciones">
          {["whatsapp", "sms"].map((key) => (
            <button
              key={key}
              aria-pressed={channel === key}
              className={channel === key ? "selected" : ""}
              onClick={() => {
                setCommand(null);
                setCustomer("");
                setText("");
                setSimulation(false);
                request.current = null;
                navigate(
                  {
                    channel: key,
                    conversation: null,
                    inbox_offset: null,
                    message_offset: null,
                    reply_offset: null,
                  },
                  true,
                );
              }}
            >
              {key === "whatsapp" ? "WhatsApp" : "SMS"}
            </button>
          ))}
        </div>
        <label className="channel-filter">
          Entorno del historial
          <select
            value={scope}
            onChange={(e) =>
              navigate({
                inbox_scope: e.target.value,
                inbox_offset: null,
                conversation: null,
              })
            }
          >
            {[
              ["all", "Todos"],
              ["test", "Simulación"],
              ["provider_test", "Prueba del proveedor"],
              ["live", "Real"],
            ].map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <p className="source-note">
          Una conversación conserva identificadores del canal; no confirma la
          identidad de una persona.{" "}
          {channel === "sms" &&
            "SMS conserva el historial y las bajas; este sistema todavía no permite responder por SMS."}
        </p>
        <OperationNotice message={op.message} />
        {list.error ? (
          <Failure message={list.error} retry={list.retry} />
        ) : !list.data ? (
          <Loading />
        ) : (
          <section className="work-surface inbox-list">
            {!list.data.items.length && <p>No hay mensajes en esta vista.</p>}
            {list.data.items.map((item) =>
              "destination" in item ? (
                <a
                  className="inbox-row"
                  href={`?business=${encodeURIComponent(business)}&view=inbox&channel=whatsapp&conversation=${encodeURIComponent(item.id)}`}
                  key={item.id}
                  onClick={(e) => {
                    if (!e.metaKey && !e.ctrlKey) {
                      e.preventDefault();
                      navigate(
                        {
                          conversation: item.id,
                          message_offset: null,
                          reply_offset: null,
                        },
                        true,
                      );
                    }
                  }}
                >
                  <strong>{item.destination}</strong>
                  <small>
                    {states[item.state] || item.state} · {item.scope}
                  </small>
                  <small>{time(item.last_inbound_at)}</small>
                  {item.opted_out && (
                    <span className="badge">Baja registrada</span>
                  )}
                </a>
              ) : (
                <article className="inbox-row" key={item.id}>
                  <strong>
                    {String(
                      item.document.destination ||
                        item.document.from ||
                        "Remitente sin identificar",
                    )}
                  </strong>
                  <p className="message-copy">
                    {String(
                      item.document.text || "Mensaje sin texto compatible",
                    )}
                  </p>
                  <small>
                    Recibido: {time(item.received_at)} · {item.scope}
                  </small>
                  <small>No hay hora original del proveedor disponible.</small>
                </article>
              ),
            )}
            <Pager
              offset={offset}
              count={list.data.count}
              label="conversaciones"
              change={(value) =>
                navigate({ inbox_offset: String(value), conversation: null })
              }
            />
          </section>
        )}
        {demo && config.data?.scope === "test" && canWrite && (
          <details
            className="work-surface inbox-simulation"
            open={simulation}
            onToggle={(e) => setSimulation(e.currentTarget.open)}
          >
            <summary>Pruebas de mensajes · solo simulación</summary>
            <div className="channel-form">
              <label>
                Contacto de prueba
                <select
                  aria-label="Contacto de prueba"
                  value={customer}
                  onChange={(e) => {
                    setCustomer(e.target.value);
                    request.current = null;
                  }}
                >
                  <option value="">Elige un contacto existente</option>
                  {config.data.customers?.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name || c.phone || "Sin nombre"}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Mensaje entrante de prueba
                <textarea
                  aria-label="Mensaje entrante de prueba"
                  value={text}
                  maxLength={channel === "sms" ? 1600 : 2000}
                  onChange={(e) => {
                    setText(e.target.value);
                    request.current = null;
                  }}
                />
              </label>
              <p>
                BAJA/STOP retiran el permiso; HELP y otros mensajes no lo
                renuevan.
              </p>
              <button
                className="button secondary"
                disabled={!customer || !text.trim() || op.busy || op.uncertain}
                onClick={() => {
                  setCommand("inbound");
                  setChecked(false);
                }}
              >
                Registrar mensaje de prueba
              </button>
              {channel === "whatsapp" && (
                <button
                  className="button secondary"
                  disabled={op.busy || op.uncertain}
                  onClick={() => {
                    setCommand("dispatch");
                    setChecked(false);
                  }}
                >
                  Procesar respuestas de prueba
                </button>
              )}
            </div>
          </details>
        )}
        <Dialog.Root
          open={!!command}
          onOpenChange={(open) => {
            if (!open && !op.busy) setCommand(null);
          }}
        >
          <Dialog.Portal>
            <Dialog.Backdrop className="backdrop" />
            <Dialog.Popup className="action-dialog">
              <Dialog.Title>
                {command === "dispatch"
                  ? "Procesar respuestas de prueba"
                  : "Registrar mensaje de prueba"}
              </Dialog.Title>
              <Dialog.Description>
                {command === "dispatch"
                  ? "Solo se procesarán las respuestas pendientes de este negocio; las campañas no se procesan aquí."
                  : `Se registrará este mensaje ficticio: ${text}`}
              </Dialog.Description>
              <label className="review-check">
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={(e) => setChecked(e.target.checked)}
                />
                Revisé la acción y su alcance.
              </label>
              <div className="dialog-actions">
                <button
                  className="button secondary"
                  onClick={() => setCommand(null)}
                  disabled={op.busy}
                >
                  Volver
                </button>
                <button
                  className="button primary"
                  disabled={!checked || op.busy || op.uncertain}
                  onClick={async () => {
                    if (!request.current) request.current = crypto.randomUUID();
                    const result = await op.perform(
                      command === "dispatch"
                        ? root + "/channel-workspace/simulate-replies"
                        : root + "/" + channel + "/simulate-inbound",
                      command === "dispatch"
                        ? undefined
                        : {
                            customer_id: customer,
                            text,
                            ...(channel === "whatsapp"
                              ? { request_key: request.current }
                              : {}),
                          },
                    );
                    setCommand(null);
                    if (result) {
                      request.current = null;
                      list.retry();
                      op.setMessage(
                        "Simulación registrada. Revisa los estados en el historial.",
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
      {selected && (
        <ConversationDetail
          key={business + selected}
          {...props}
          id={selected}
          changed={list.retry}
          close={() => navigate({ conversation: null })}
        />
      )}
    </div>
  );
}
function Pager({
  offset,
  count,
  label,
  change,
}: {
  offset: number;
  count: number;
  label: string;
  change: (n: number) => void;
}) {
  return (
    <div className="table-footer">
      <span>
        {count} {label}
      </span>
      <div className="pagination">
        <button
          className="icon-button"
          aria-label={label + " anteriores"}
          disabled={!offset}
          onClick={() => change(Math.max(0, offset - 25))}
        >
          <ArrowLeft size={16} />
        </button>
        <button
          className="icon-button"
          aria-label={"Más " + label}
          disabled={offset + 25 >= count}
          onClick={() => change(offset + 25)}
        >
          <ArrowRight size={16} />
        </button>
      </div>
    </div>
  );
}
function ConversationDetail({
  id,
  business,
  csrf,
  permissions,
  params,
  navigate,
  changed,
  close,
}: Props & { id: string; changed: () => void; close: () => void }) {
  const mo = Math.max(0, Number(params.get("message_offset")) || 0),
    ro = Math.max(0, Number(params.get("reply_offset")) || 0),
    root = endpoint(business),
    url = `${root}/channel-workspace/conversations/${encodeURIComponent(id)}?offset=${mo}&reply_offset=${ro}`;
  const resource = useResource<Detail>(url),
    op = useOperation(csrf),
    [current, setCurrent] = useState<{ url: string; value: Detail }>(),
    [body, setBody] = useState(""),
    [pending, setPending] = useState<string | null>(null),
    [checked, setChecked] = useState(false),
    request = useRef<{ body: string; key: string } | null>(null),
    heading = useRef<HTMLHeadingElement>(null),
    d = current?.url === url ? current.value : resource.data;
  useEffect(() => {
    if (d) heading.current?.focus({ preventScroll: true });
  }, [d?.id]);
  async function refresh() {
    try {
      setCurrent({ url, value: await api<Detail>(url) });
      op.checked();
      changed();
    } catch {
      op.setMessage(
        "No pudimos comprobar la conversación. Conserva la respuesta sin repetirla.",
      );
    }
  }
  return (
    <aside
      className="detail sale-detail operation-detail conversation-detail"
      aria-label="Detalle de conversación"
    >
      <div className="detail-top">
        <button
          className="icon-button"
          aria-label="Cerrar conversación"
          onClick={close}
        >
          <X size={18} />
        </button>
      </div>
      {resource.error && !d ? (
        <Failure message={resource.error} retry={resource.retry} />
      ) : !d ? (
        <Loading />
      ) : (
        <div className="detail-body">
          <h2 ref={heading} tabIndex={-1}>
            {d.destination}
          </h2>
          <span className="badge">{d.scope}</span>
          <p>
            {d.assigned_name ? `Asignada a ${d.assigned_name}` : "Sin asignar"}
          </p>
          <p>
            {d.opted_out
              ? "Baja registrada. No se permiten respuestas."
              : d.service_window_open
                ? "Ventana de respuesta abierta."
                : "La ventana de respuesta está cerrada."}
          </p>
          <p className="source-note">
            Último mensaje entrante: {time(d.last_inbound_at)}. La hora mostrada
            usa la zona local de este dispositivo.
          </p>
          <button
            className="button secondary"
            disabled={op.busy}
            onClick={refresh}
          >
            <RefreshCw size={16} />
            {op.uncertain ? "Comprobar respuesta" : "Actualizar conversación"}
          </button>
          <OperationNotice message={op.message} />
          <section>
            <h3>Mensajes recibidos</h3>
            {d.messages.map((m) => (
              <article className="conversation-message" key={m.id}>
                <p className="message-copy">
                  {String(m.document.text || "Mensaje sin texto compatible")}
                </p>
                <small>Proveedor: {time(m.provider_at || null)}</small>
                <small>Recibido: {time(m.received_at)}</small>
              </article>
            ))}
            <Pager
              offset={mo}
              count={d.message_count}
              label="mensajes recibidos"
              change={(n) => navigate({ message_offset: String(n) })}
            />
          </section>
          <section>
            <h3>Respuestas</h3>
            {!d.replies.length && <p>No hay respuestas registradas.</p>}
            {d.replies.map((r) => (
              <article className="conversation-message" key={r.id}>
                <p className="message-copy">{r.body}</p>
                <strong>{states[r.state] || r.state}</strong>
                {r.reason && <p>{r.reason.replaceAll("_", " ")}</p>}
                <small>
                  {time(r.created_at)} · {r.actor}
                </small>
                {r.provider_id && <small>Referencia: {r.provider_id}</small>}
              </article>
            ))}
            <Pager
              offset={ro}
              count={d.reply_count}
              label="respuestas"
              change={(n) => navigate({ reply_offset: String(n) })}
            />
          </section>
          {permissions.includes("growth.write") && d.reply_allowed ? (
            <form
              className="channel-form"
              onSubmit={(e) => {
                e.preventDefault();
                setPending(body);
                setChecked(false);
              }}
            >
              <label>
                Respuesta de prueba
                <textarea
                  required
                  maxLength={2000}
                  value={body}
                  disabled={op.busy || op.uncertain}
                  onChange={(e) => setBody(e.target.value)}
                />
              </label>
              <p>
                Se asignará a tu usuario y quedará en cola de simulación.
                Registrar la respuesta no confirma su entrega.
              </p>
              <button
                className="button primary"
                disabled={!body.trim() || op.busy || op.uncertain}
              >
                Revisar respuesta
              </button>
            </form>
          ) : (
            <p className="source-note">
              La respuesta requiere acceso autorizado, entorno de prueba,
              remitente vigente, ventana abierta y ausencia de baja. Las
              respuestas reales permanecen deshabilitadas.
            </p>
          )}
          <Dialog.Root
            open={pending !== null}
            onOpenChange={(open) => {
              if (!open && !op.busy) setPending(null);
            }}
          >
            <Dialog.Portal>
              <Dialog.Backdrop className="backdrop" />
              <Dialog.Popup className="action-dialog">
                <Dialog.Title>Confirmar respuesta de prueba</Dialog.Title>
                <Dialog.Description>
                  {d.destination}: {pending}
                </Dialog.Description>
                <label className="review-check">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={(e) => setChecked(e.target.checked)}
                  />
                  Revisé el destinatario y el texto.
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
                      if (pending === null) return;
                      if (!request.current || request.current.body !== pending)
                        request.current = {
                          body: pending,
                          key: crypto.randomUUID(),
                        };
                      const result = await op.perform(
                        `${root}/whatsapp/conversations/${encodeURIComponent(id)}/reply`,
                        { body: pending, request_key: request.current.key },
                      );
                      setPending(null);
                      if (result) {
                        setBody("");
                        request.current = null;
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
