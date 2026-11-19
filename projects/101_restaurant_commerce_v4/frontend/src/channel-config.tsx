import { AccountConnection, ProviderTabs } from "./account-connections";
import { useState } from "react";
import { RefreshCw } from "lucide-react";
import { api, endpoint, useResource, Failure, Loading } from "./ui";
import { OperationNotice, useOperation } from "./operations-ui";
import "./growth-channels.css";

export type ChannelConfig = {
  scope: string;
  state: string;
  sender: Record<string, string | number | boolean | null> | null;
  sender_digest: string;
  templates?: Template[];
  customers: { id: string; name: string | null; phone: string | null }[];
};
type Template = {
  id: string;
  provider_id: string;
  name: string;
  language: string;
  status: string;
  body?: string;
  footer?: string;
  category?: string;
  source?: string;
  expires_at?: string;
  digest: string;
};
export type Readiness = {
  scope: string;
  live_enabled: boolean;
  provider_test_enabled: boolean;
  channels: Record<
    string,
    { state: string; blockers: string[]; [key: string]: unknown }
  >;
};
type Props = {
  business: string;
  csrf: string;
  permissions: string[];
  demo: boolean;
  params: URLSearchParams;
  navigate: (changes: Record<string, string | null>, push?: boolean) => void;
};
const status: Record<string, string> = {
  unconfigured: "Sin configurar",
  unverified: "Sin verificar",
  international_long_code: "Número internacional",
  short_code: "Código corto",
  available: "Disponibles",
  unavailable: "No disponibles",
  unknown: "Desconocido",
  UNKNOWN: "Desconocida",
  GREEN: "Alta",
  YELLOW: "Media",
  RED: "Baja",
  simulation_only: "Solo simulación",
  configured_inactive: "Configurado, sin envío real",
  UNVERIFIED: "Sin verificar",
  READY: "Listo para simulación",
  RESTRICTED: "Restringido",
  APPROVED: "Aprobada",
  PENDING: "Pendiente",
  PAUSED: "Pausada",
  DISABLED: "Deshabilitada",
  REJECTED: "Rechazada",
  UNSUPPORTED: "Formato no compatible",
  MISSING: "No encontrada en la última revisión",
  SYNC_REQUIRED: "Requiere actualizar",
};
export function ReadinessSummary({ data }: { data: Readiness }) {
  return (
    <section className="work-surface readiness-summary">
      <h2>Estado de los canales</h2>
      <p>
        La configuración guardada y una simulación no habilitan envíos reales.
      </p>
      {Object.entries(data.channels).map(([key, value]) => (
        <div key={key}>
          <h3>{key === "whatsapp" ? "WhatsApp" : "SMS"}</h3>
          <ul>
            {value.blockers.map((b) => (
              <li key={b}>{blocker(b)}</li>
            ))}
          </ul>
          {!value.blockers.length && (
            <p>
              Disponible para revisión; requiere autorización específica antes
              de enviar.
            </p>
          )}
        </div>
      ))}
    </section>
  );
}
export function blocker(value: string) {
  const labels: Record<string, string> = {
    shared_contact_limit: "Ya se alcanzó el límite de contacto compartido",
    simulation_is_not_provider_verification:
      "La simulación no verifica una conexión real",
    sender_unconfigured: "Falta configurar el remitente",
    real_provider_unconfigured: "Falta la conexión autorizada con el proveedor",
    current_provider_observation_required:
      "Falta una observación vigente del proveedor",
    phone_waba_binding_not_verified:
      "Falta verificar la relación entre la cuenta y el número",
    current_account_allowance_review_required:
      "Falta revisar el cupo de la cuenta",
    current_price_review_required: "Falta verificar el precio actual",
    public_webhook_receipt_verification_required:
      "Falta verificar la recepción de eventos del proveedor",
    colombia_route_and_registration_review_required:
      "Falta verificar la ruta y su registro para Colombia",
    inbound_and_receipt_capability_verification_required:
      "Falta verificar mensajes entrantes y recibos",
    separate_exact_message_authorization_and_activation_required:
      "El mensaje requiere una autorización y activación separadas",
    provider_test_campaign_required:
      "La campaña debe pertenecer al entorno de prueba del proveedor",
    single_recipient_campaign_required:
      "La prueba requiere un solo destinatario",
    test_cost_unknown_or_over_limit:
      "El costo es desconocido o supera el límite",
  };
  return labels[value] || value.replaceAll("_", " ");
}
export function ChannelConnections(props: Props) {
  return ["whatsapp", "sms"].includes(props.params.get("provider") || "") ? (
    <PhoneConnections {...props} />
  ) : (
    <AccountConnection {...props} />
  );
}
export function PhoneConnections(props: Props) {
  const { business, csrf, permissions, demo, params, navigate } = props,
    provider = params.get("provider") === "sms" ? "sms" : "whatsapp",
    root = endpoint(business);
  const config = useResource<ChannelConfig>(root + "/" + provider),
    ready = useResource<Readiness>(root + "/campaigns/provider-readiness");
  const [notice, setNotice] = useState("");
  const [current, setCurrent] = useState<ChannelConfig>(),
    [revision, setRevision] = useState(0),
    [confirm, setConfirm] = useState<string | null>(null),
    op = useOperation(csrf);
  const value = current || config.data,
    canWrite = permissions.includes("growth.write");
  async function refresh() {
    try {
      setCurrent(await api<ChannelConfig>(root + "/" + provider));
      setRevision((n) => n + 1);
      ready.retry();
      op.checked();
    } catch {
      op.setMessage(
        "No pudimos actualizar la configuración. Conserva tus cambios.",
      );
    }
  }
  return (
    <div className="page growth-channel-page">
      <section className="page-heading">
        <div>
          <h1>Conexiones</h1>
          <p>Remitentes, plantillas y evidencia de disponibilidad.</p>
        </div>
        <button
          className="button secondary"
          onClick={refresh}
          disabled={op.busy}
        >
          <RefreshCw size={16} />
          Descartar cambios y actualizar
        </button>
      </section>
      <ProviderTabs params={params} navigate={navigate} />
      <OperationNotice message={notice} />
      <OperationNotice message={op.message} />
      {config.error && !value ? (
        <Failure message={config.error} retry={config.retry} />
      ) : !value ? (
        <Loading />
      ) : (
        <>
          <p className="channel-state">
            <span className="badge">{status[value.state] || value.state}</span>{" "}
            · Entorno: {value.scope}
          </p>
          <SenderForm
            key={business + provider + revision + value.sender_digest}
            provider={provider}
            data={value}
            root={root}
            csrf={csrf}
            canWrite={canWrite}
            refresh={refresh}
            saved={(next) => {
              setCurrent(next);
              setNotice(
                "Remitente guardado. La disponibilidad real conserva sus comprobaciones pendientes.",
              );
              ready.retry();
            }}
          />
          {provider === "whatsapp" && (
            <>
              <section className="work-surface template-list">
                <h2>Plantillas</h2>
                {!value.templates?.length && (
                  <p>No hay plantillas registradas.</p>
                )}
                {value.templates?.map((t) => (
                  <article className="catalogue-item" key={t.id}>
                    <h3>
                      {t.name} · {t.language}
                    </h3>
                    <span className="badge">
                      {status[t.status] || t.status}
                    </span>
                    <p className="message-copy">
                      {t.body ||
                        "Esta definición no contiene un cuerpo compatible."}
                    </p>
                    {t.footer && <p>{t.footer}</p>}
                    <p className="source-note">
                      {t.source} ·{" "}
                      {t.expires_at
                        ? new Date(t.expires_at).toLocaleString("es-CO")
                        : "Sin vigencia compatible"}
                    </p>
                    {demo &&
                      value.scope === "test" &&
                      canWrite &&
                      t.body &&
                      [
                        "APPROVED",
                        "PENDING",
                        "PAUSED",
                        "DISABLED",
                        "REJECTED",
                      ].includes(t.status) && (
                        <TemplateForm
                          key={t.digest + t.status}
                          template={t}
                          root={root}
                          csrf={csrf}
                          saved={() => {
                            config.retry();
                            setCurrent(undefined);
                          }}
                        />
                      )}
                  </article>
                ))}
              </section>
              {demo && value.scope === "test" && canWrite && (
                <TemplateForm
                  root={root}
                  csrf={csrf}
                  saved={() => {
                    config.retry();
                    setCurrent(undefined);
                  }}
                />
              )}
              {canWrite && value.scope !== "test" && (
                <section className="work-surface provider-probes">
                  <h2>Revisar con el proveedor</h2>
                  <p>
                    Estas acciones consultan la conexión existente. No envían
                    mensajes.
                  </p>
                  {[
                    ["sync", "Actualizar plantillas"],
                    ["probe", "Revisar cuenta y plantillas"],
                  ].map(([key, title]) => (
                    <button
                      key={key}
                      className="button secondary"
                      disabled={op.busy || op.uncertain}
                      onClick={() => setConfirm(key)}
                    >
                      {title}
                    </button>
                  ))}
                  {confirm && (
                    <div className="operation-notice">
                      <p>
                        Se consultará la cuenta autorizada para este negocio.
                      </p>
                      <button
                        className="button secondary"
                        onClick={() => setConfirm(null)}
                        disabled={op.busy}
                      >
                        Volver
                      </button>
                      <button
                        className="button primary"
                        disabled={op.busy || op.uncertain}
                        onClick={async () => {
                          const result = await op.perform(
                            root +
                              (confirm === "sync"
                                ? "/whatsapp/sync"
                                : "/campaigns/provider-readiness/whatsapp/probe"),
                          );
                          setConfirm(null);
                          if (result) await refresh();
                        }}
                      >
                        Confirmar consulta
                      </button>
                    </div>
                  )}
                </section>
              )}
            </>
          )}
        </>
      )}
      {ready.error ? (
        <Failure message={ready.error} retry={ready.retry} />
      ) : ready.data ? (
        <ReadinessSummary data={ready.data} />
      ) : (
        <Loading />
      )}
    </div>
  );
}
type Spec = {
  key: string;
  label: string;
  kind?: "number" | "price" | "date" | "check";
  options?: string[];
  initial?: string | number | boolean;
  testOnly?: boolean;
};
const common: Spec[] = [
  { key: "link_origin", label: "Origen de los enlaces (sin ruta)" },
  {
    key: "status",
    label: "Estado declarado",
    options: ["UNVERIFIED", "READY", "RESTRICTED"],
    initial: "UNVERIFIED",
    testOnly: true,
  },
  { key: "source", label: "Fuente de la información" },
  {
    key: "expires_at",
    label: "Vigencia · hora local de este dispositivo",
    kind: "date",
  },
  {
    key: "unit_cost_microusd",
    label: "Precio por mensaje · USD (vacío: desconocido)",
    kind: "price",
    testOnly: true,
  },
];
const waFields: Spec[] = [
  { key: "phone_id", label: "Identificador del número" },
  { key: "waba_id", label: "Identificador de la cuenta de WhatsApp" },
  { key: "version", label: "Versión de la conexión" },
  { key: "display_phone", label: "Número visible" },
  { key: "support_owner", label: "Responsable de soporte" },
  {
    key: "quality",
    label: "Calidad declarada",
    options: ["UNKNOWN", "GREEN", "YELLOW", "RED"],
    initial: "UNKNOWN",
    testOnly: true,
  },
  {
    key: "allowance",
    label: "Cupo declarado",
    kind: "number",
    initial: 0,
    testOnly: true,
  },
  ...common,
];
const smsFields: Spec[] = [
  { key: "account_sid", label: "Identificador de la cuenta SMS" },
  { key: "sender", label: "Número o código remitente" },
  {
    key: "route",
    label: "Ruta",
    options: ["unverified", "international_long_code", "short_code"],
    initial: "unverified",
  },
  {
    key: "inbound_supported",
    label: "La ruta permite recibir respuestas",
    kind: "check",
    initial: false,
    testOnly: true,
  },
  {
    key: "delivery_receipts",
    label: "Recibos de entrega",
    options: ["unknown", "available", "unavailable"],
    initial: "unknown",
    testOnly: true,
  },
  {
    key: "max_segments",
    label: "Máximo de segmentos por mensaje",
    kind: "number",
    initial: 1,
  },
  ...common,
];
function localInput(iso: unknown) {
  if (typeof iso !== "string") return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? ""
    : new Date(d.getTime() - d.getTimezoneOffset() * 60000)
        .toISOString()
        .slice(0, 16);
}
function SenderForm({
  provider,
  data,
  root,
  csrf,
  canWrite,
  refresh,
  saved,
}: {
  provider: string;
  data: ChannelConfig;
  root: string;
  csrf: string;
  canWrite: boolean;
  refresh: () => Promise<void>;
  saved: (d: ChannelConfig) => void;
}) {
  const op = useOperation(csrf),
    fields = provider === "whatsapp" ? waFields : smsFields;
  return (
    <form
      className="work-surface channel-form"
      aria-label="Configuración del remitente"
      onSubmit={async (e) => {
        e.preventDefault();
        const form = new FormData(e.currentTarget),
          body: Record<string, unknown> = {
            expected_digest: data.sender_digest,
          };
        for (const field of fields) {
          if (field.testOnly && data.scope !== "test") {
            body[field.key] = data.sender?.[field.key] ?? field.initial ?? null;
            continue;
          }
          const raw = String(form.get(field.key) || "");
          body[field.key] =
            field.kind === "check"
              ? form.has(field.key)
              : field.kind === "number"
                ? Number(raw)
                : field.kind === "price"
                  ? raw === ""
                    ? null
                    : Math.round(Number(raw) * 1e6)
                  : field.kind === "date"
                    ? new Date(raw).toISOString()
                    : raw;
        }
        const result = await op.perform<ChannelConfig>(
          root + "/" + provider + "/sender",
          body,
          "PUT",
        );
        if (result) saved(result);
      }}
    >
      <h2>Remitente de {provider === "whatsapp" ? "WhatsApp" : "SMS"}</h2>
      <p className="source-note">
        Los identificadores se guardan sin claves de acceso. En configuración
        real, los estados declarados quedan sin verificar hasta revisar
        evidencia del proveedor.
      </p>
      <fieldset disabled={!canWrite || op.busy || op.uncertain}>
        <div className="channel-fields">
          {fields.map((f) => (
            <label
              key={f.key}
              className={f.kind === "check" ? "check-label" : ""}
            >
              {f.kind !== "check" && f.label}
              {f.options ? (
                <select
                  name={f.key}
                  disabled={f.testOnly && data.scope !== "test"}
                  defaultValue={String(data.sender?.[f.key] ?? f.initial ?? "")}
                >
                  {f.options.map((o) => (
                    <option key={o} value={o}>
                      {status[o] || o}
                    </option>
                  ))}
                </select>
              ) : f.kind === "check" ? (
                <>
                  <input
                    type="checkbox"
                    name={f.key}
                    disabled={f.testOnly && data.scope !== "test"}
                    defaultChecked={Boolean(data.sender?.[f.key] ?? f.initial)}
                  />
                  {f.label}
                </>
              ) : (
                <input
                  name={f.key}
                  type={
                    f.kind === "date"
                      ? "datetime-local"
                      : f.kind === "price" || f.kind === "number"
                        ? "number"
                        : "text"
                  }
                  disabled={f.testOnly && data.scope !== "test"}
                  min={f.kind === "number" && f.key === "max_segments" ? 1 : 0}
                  max={
                    f.key === "max_segments"
                      ? 10
                      : f.key === "allowance"
                        ? 100000
                        : undefined
                  }
                  step={f.kind === "price" ? "0.000001" : undefined}
                  maxLength={500}
                  required={f.kind !== "price"}
                  defaultValue={
                    f.kind === "date"
                      ? localInput(data.sender?.[f.key])
                      : f.kind === "price"
                        ? data.sender?.[f.key] == null
                          ? ""
                          : Number(data.sender[f.key]) / 1e6
                        : String(data.sender?.[f.key] ?? f.initial ?? "")
                  }
                />
              )}
            </label>
          ))}
        </div>
        {canWrite && (
          <button className="button primary" disabled={op.busy}>
            Guardar remitente
          </button>
        )}
      </fieldset>
      <OperationNotice message={op.message} />
      {(op.message || op.uncertain) && (
        <button
          type="button"
          className="button secondary"
          disabled={op.busy}
          onClick={refresh}
        >
          Comprobar configuración
        </button>
      )}
    </form>
  );
}
function TemplateForm({
  template,
  root,
  csrf,
  saved,
}: {
  template?: Template;
  root: string;
  csrf: string;
  saved: () => void;
}) {
  const op = useOperation(csrf);
  return (
    <details className="work-surface template-editor">
      <summary>
        {template
          ? "Editar plantilla de simulación"
          : "Añadir plantilla de simulación"}
      </summary>
      <form
        className="channel-form"
        aria-label={
          template
            ? "Editar plantilla " + template.name
            : "Nueva plantilla de simulación"
        }
        onSubmit={async (e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget),
            body = Object.fromEntries(
              [
                "provider_id",
                "name",
                "language",
                "status",
                "body",
                "footer",
                "source",
              ].map((k) => [k, String(f.get(k) || "")]),
            );
          const result = await op.perform(root + "/whatsapp/templates", {
            ...body,
            category: "MARKETING",
            expires_at: new Date(String(f.get("expires_at"))).toISOString(),
          });
          if (result) saved();
        }}
      >
        <fieldset disabled={op.busy || op.uncertain}>
          <div className="channel-fields">
            {[
              ["provider_id", "Identificador de la plantilla"],
              ["name", "Nombre de la plantilla"],
              ["language", "Idioma"],
              ["source", "Fuente"],
            ].map(([key, label]) => (
              <label key={key}>
                {label}
                <input
                  name={key}
                  defaultValue={String(template?.[key as keyof Template] || "")}
                  required
                  maxLength={300}
                />
              </label>
            ))}
            <label>
              Estado
              <select
                name="status"
                defaultValue={template?.status || "PENDING"}
              >
                {["PENDING", "APPROVED", "PAUSED", "DISABLED", "REJECTED"].map(
                  (s) => (
                    <option key={s} value={s}>
                      {status[s]}
                    </option>
                  ),
                )}
              </select>
            </label>
            <label>
              Vigencia · hora local de este dispositivo
              <input
                type="datetime-local"
                name="expires_at"
                defaultValue={localInput(template?.expires_at)}
                required
              />
            </label>
          </div>
          <label>
            Texto de la plantilla
            <textarea
              name="body"
              defaultValue={template?.body || ""}
              required
              maxLength={1024}
            />
          </label>
          <label>
            Pie de la plantilla
            <input
              name="footer"
              defaultValue={template?.footer || ""}
              required
              maxLength={60}
            />
          </label>
          <p>
            Parámetros consecutivos: {"{{1}}"} hasta {"{{5}}"}. El enlace de
            pedido y la opción de baja se mantienen.
          </p>
          <button className="button secondary" disabled={op.busy}>
            Guardar plantilla de simulación
          </button>
        </fieldset>
        <OperationNotice message={op.message} />
      </form>
    </details>
  );
}
