import { ManualOutbox } from "./growth-workspace";
import { ChannelInbox } from "./channel-inbox";
import {
  CampaignBusinessTools,
  PhoneCampaignFields,
  ProviderTestReview,
} from "./campaign-channel-controls";
import type { ChannelConfig } from "./channel-config";
import { ApiError } from "./ui";
import { useEffect, useRef, useState } from "react";
import {
  EmailChassisControls,
  type EmailChassis,
} from "./email-chassis-controls";
import {
  ArrowLeft,
  ArrowRight,
  Plus,
  Mail,
  Megaphone,
  Check,
  RefreshCw,
  Search,
  X,
  CalendarDays,
} from "lucide-react";
import {
  api,
  endpoint,
  date,
  amount,
  count,
  useResource,
  Loading,
  Failure,
} from "./ui";
import {
  PageHeading,
  PeriodPicker,
  currentPeriod,
  workspaceHref,
  type ViewProps,
} from "./workspace-views";
type Person = {
  id: string;
  name: string | null;
  email: string | null;
  phone: string | null;
};
export type Meta = {
  scope: string;
  paused: boolean;
  clock: string;
  sender: string;
  customers: Person[];
  channels: Record<string, string>;
};
type EmailDesign = {
  template_id: string;
  image_url?: string | null;
  image_alt?: string;
  cta_label?: string;
  chassis?: EmailChassis | null;
};
type TemplateCatalog = {
  templates: { id: string; name: string; available: boolean }[];
};
export type Draft = {
  channel: string;
  promotion_code: string | null;
  whatsapp_template_id: string | null;
  whatsapp_parameters: string[];
  email_design?: EmailDesign | null;
  sender: string;
  content: { subject: string; title: string; body: string; terms: string };
  customer_ids: string[];
  scheduled_at: string;
  expires_at: string;
  scope: string;
  budget_microusd: number;
};
export type Preview = {
  render_error?: string | null;
  id: string;
  state: string;
  digest: string;
  approved: boolean;
  document: Draft;
  eligible: number;
  excluded: number;
  estimated_cost_microusd: number | null;
  audience: {
    id: string;
    name: string | null;
    destination: string | null;
    status: string;
    reasons: string[];
    sms_segments?: number;
    sms_encoding?: string;
    sms_cost_microusd?: number | null;
  }[];
  email: { text: string };
  simulation_clock: string;
};
type Summary = {
  id: string;
  subject: string;
  state: string;
  channel: string;
  scope: string;
  scheduled_at: string;
  audience_count: number;
};
type Report = {
  queued: number;
  provider_accepted: number;
  provider_reported_delivery: number;
  unknown: number;
  receipt_missing: number;
  tracked_visits: number;
  scanner_visits: number;
  paid_orders: number;
  captured_revenue: number;
  refunds: number;
  net_revenue: number;
  currency: string;
  delivery_cost_microusd: number | null;
  read_signals: number | "unavailable";
  sms?: {
    estimated_submitted_segments: number;
    estimated_delivery_cost_microusd: number | null;
    provider_status_counts: Record<string, number>;
    route_receipt_support: string[];
    cost_note: string;
  };
  scope: string;
  deliveries: {
    id: string;
    state: string;
    reason: string | null;
    customer_id: string;
    message_id: string | null;
    tracking_url: string;
    unsubscribe_url: string;
  }[];
};
const channelState = (value: string) =>
  ({
    unconfigured: "sin configurar",
    simulation_only: "solo simulación",
    configured_inactive: "configurado, sin envío real",
  })[value] || "requiere revisión";
const states: Record<string, string> = {
  draft: "Borrador",
  approved: "Aprobada",
  scheduled: "Programada",
  cancelled: "Cancelada",
};
const reasons: Record<string, string> = {
  rne_missing_or_stale: "Falta una revisión RNE vigente",
  destination_suppressed: "Dirección bloqueada para marketing",
  unsubscribed: "Baja confirmada",
  consent_missing: "Sin permiso registrado",
  outside_sending_hours: "Fuera del horario de envío",
  campaign_cancelled: "Campaña cancelada",
  shared_contact_limit: "Ya recibió un mensaje dentro del límite de contacto",
  outside_colombia_sending_hours: "Fuera del horario de envío en Colombia",
  missing_or_invalid_destination: "Falta una dirección válida",
  rne_excluded: "Excluido por RNE",
  colombian_holiday: "Festivo en Colombia",
  business_paused: "Envíos pausados para el negocio",
  permission_missing: "Sin permiso registrado",
  permission_withdrawn: "Permiso retirado",
  permission_suppressed: "Contacto suprimido",
  missing_destination: "Sin dirección",
  rne_stale: "Revisión RNE vencida",
  registry_stale: "Revisión RNE vencida",
  duplicate_destination: "Dirección repetida",
  permission_unknown: "Permiso sin confirmar",
};
const deliveryStates: Record<string, string> = {
  queued: "En cola",
  sending: "En proceso",
  accepted: "Aceptado",
  delivered: "Entrega reportada",
  read: "Lectura reportada",
  unknown: "Resultado desconocido",
  skipped: "Omitido",
  failed: "Fallido",
  bounced: "Rebotado",
  complaint: "Queja recibida",
  rejected: "Rechazado",
};
function explainReason(value: string) {
  return value
    .split(",")
    .map((r) => reasons[r] || r.replaceAll("_", " "))
    .join(" · ");
}
function cost(value: number | null) {
  return value === null
    ? "Sin estimación"
    : new Intl.NumberFormat("es-CO", {
        style: "currency",
        currency: "USD",
        minimumFractionDigits: 4,
      }).format(value / 1000000) + " USD";
}
function localTime(iso: string) {
  return new Date(new Date(iso).getTime() - 5 * 3600000)
    .toISOString()
    .slice(0, 16);
}
function freshDraft(m: Meta): Draft {
  return {
    channel: "email",
    promotion_code: null,
    whatsapp_template_id: null,
    whatsapp_parameters: [],
    email_design: { template_id: "matte" },
    sender: m.sender || "",
    content: { subject: "", title: "", body: "", terms: "" },
    customer_ids: [],
    scheduled_at: m.clock,
    expires_at: new Date(new Date(m.clock).getTime() + 86400000).toISOString(),
    scope: m.scope,
    budget_microusd: 1000000,
  };
}
async function mutate(
  path: string,
  csrf: string,
  method: string,
  body?: unknown,
) {
  const r = await fetch(path, {
    method,
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", "X-101-CSRF": csrf },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(15000),
  });
  if (!r.ok) {
    const d = await r.json().catch(() => ({}));
    const known: Record<string, string> = {
      email_renderer_unavailable:
        "No está disponible la preparación del diseño. Puedes usar Clásico anterior o intentarlo de nuevo.",
      email_render_failed:
        "No se pudo preparar el diseño. Revisa la imagen o inténtalo de nuevo.",
      renderer_revision_changed:
        "El diseño cambió. Guarda una versión nueva y vuelve a revisarla.",
      preview_changed:
        "La campaña cambió. Actualiza antes de guardar el diseño.",
      revision_changed: "La versión cambió. Vuelve a revisar la campaña.",
      valid_approval_required: "Esta versión necesita aprobación.",
      campaign_expired:
        "La campaña venció. Cambia las fechas y vuelve a aprobar.",
      live_send_not_enabled: "El envío real no está habilitado.",
    };
    if (r.status === 401) window.dispatchEvent(new Event("session-expired"));
    const error = new ApiError(r.status);
    error.message =
      known[d.detail] ||
      (r.status < 500 && typeof d.detail === "string"
        ? d.detail.slice(0, 300)
        : "No se confirmó la acción. Comprueba el estado antes de continuar.");
    throw error;
  }
  return r.json();
}
export function CampaignWorkspace(
  props: ViewProps & { csrf: string; permissions: string[]; demo: boolean },
) {
  const view = props.params.get("view") || "campaigns";
  return (
    <>
      <div
        className="tabs sales-views channel-tabs"
        aria-label="Secciones de campañas"
      >
        {[
          ["campaigns", "Campañas"],
          ["outbox", "Mensajes manuales"],
          ["inbox", "Conversaciones"],
        ].map(([key, title]) => (
          <button
            key={key}
            className={view === key ? "selected" : ""}
            aria-pressed={view === key}
            onClick={() =>
              props.navigate(
                {
                  view: key,
                  campaign: null,
                  conversation: null,
                  test_review: null,
                },
                true,
              )
            }
          >
            {title}
          </button>
        ))}
      </div>
      {view === "outbox" ? (
        <ManualOutbox {...props} />
      ) : view === "inbox" ? (
        <ChannelInbox {...props} />
      ) : (
        <CampaignView {...props} />
      )}
    </>
  );
}
export function CampaignView(
  props: ViewProps & { csrf: string; permissions: string[]; demo: boolean },
) {
  const { business, params, navigate, csrf, permissions, demo } = props;
  const base = endpoint(business) + "/campaigns";
  const meta = useResource<Meta>(base);
  const id = params.get("campaign");
  const canWrite = permissions.includes("growth.write");
  const query = params.get("q") || "",
    state = params.get("state") || "all",
    offset = Number(params.get("offset")) || 0;
  const [search, setSearch] = useState(query);
  const [toolsOpen, setToolsOpen] = useState(false);
  useEffect(() => setSearch(query), [query]);
  const selectedPeriod = currentPeriod(params);
  const list = useResource<{ items: Summary[]; count: number }>(
    `${endpoint(business)}/workspace/campaigns?${new URLSearchParams({ date_from: selectedPeriod.from, date_to: selectedPeriod.to })}&q=${encodeURIComponent(query)}&state=${state}&offset=${offset}`,
  );
  function open(next: string | null) {
    navigate({ campaign: next, test_review: null }, true);
  }
  if (meta.error)
    return (
      <div className="page new-view">
        <PageHeading title="Campañas" />
        <Failure message={meta.error} retry={meta.retry} />
        <a
          className="legacy-link"
          href={`/workspace/connections?business=${encodeURIComponent(business)}&provider=google`}
        >
          Revisar conexiones
        </a>
      </div>
    );
  if (!meta.data)
    return (
      <div className="page new-view">
        <PageHeading title="Campañas" />
        <Loading />
      </div>
    );
  return (
    <div className="page new-view campaign-view">
      {id ? (
        <CampaignDetail
          key={business + id}
          {...props}
          id={id}
          meta={meta.data}
          canWrite={canWrite}
          close={() => navigate({ campaign: null })}
          saved={(next) => {
            navigate({ campaign: next });
            list.retry();
          }}
        />
      ) : (
        <>
          <PageHeading
            title="Campañas"
            description="Escribe, revisa y programa."
          >
            <button
              className="button primary"
              disabled={!canWrite}
              onClick={() => open("new")}
            >
              <Plus size={17} />
              Crear campaña
            </button>
          </PageHeading>
          <CampaignBusinessTools
            business={business}
            csrf={csrf}
            canWrite={canWrite}
            meta={meta.data}
            changed={meta.retry}
            open={toolsOpen}
            setOpen={setToolsOpen}
          />
          <div className="campaign-toolbar">
            <PeriodPicker {...props} />
            <div className="channel-status">
              <span>
                <Mail size={16} />
                Email ·{" "}
                {meta.data.scope === "test"
                  ? "simulación"
                  : "envío no activado"}
              </span>
              <span>
                WhatsApp · {channelState(meta.data.channels.whatsapp)}
              </span>
              <span>SMS · {channelState(meta.data.channels.sms)}</span>
            </div>
          </div>
          {meta.data.paused && (
            <div className="demo-notice">
              Los envíos de este negocio están pausados.
            </div>
          )}
          <section className="work-surface">
            <div className="section-heading">
              <h2>
                Campañas{" "}
                <span className="number-chip">{list.data?.count ?? "—"}</span>
              </h2>
              <span className="caption">Creadas en el periodo</span>
            </div>
            <div className="campaign-filters">
              <div className="tabs">
                {["all", "draft", "scheduled"].map((s) => (
                  <button
                    key={s}
                    aria-pressed={s === state}
                    className={s === state ? "selected" : ""}
                    onClick={() => navigate({ state: s, offset: null })}
                  >
                    {s === "all"
                      ? "Todas"
                      : s === "draft"
                        ? "Borradores"
                        : "Programadas"}
                  </button>
                ))}
              </div>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  navigate({ q: search, offset: null });
                }}
                className="search"
              >
                <Search size={16} />
                <input
                  aria-label="Buscar campañas"
                  placeholder="Buscar en campañas"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
                <button type="submit" aria-label="Buscar">
                  <ArrowRight size={16} />
                </button>
              </form>
            </div>
            {list.error ? (
              <Failure message={list.error} retry={list.retry} />
            ) : !list.data ? (
              <Loading />
            ) : list.data.items.length ? (
              <div className="campaign-directory">
                {list.data.items.map((c) => (
                  <a
                    key={c.id}
                    className="campaign-row"
                    href={workspaceHref("campaigns", business, params, {
                      campaign: c.id,
                    })}
                    onClick={(e) => {
                      if (!e.metaKey && !e.ctrlKey) {
                        e.preventDefault();
                        open(c.id);
                      }
                    }}
                  >
                    <span className="item-icon kind-campaign">
                      <Megaphone size={20} />
                    </span>
                    <div>
                      <strong>{c.subject}</strong>
                      <small>
                        {c.channel === "email" ? "Email" : c.channel} ·{" "}
                        {c.audience_count} contactos ·{" "}
                        {c.scope === "test" ? "Simulación" : c.scope}
                      </small>
                    </div>
                    <span className={"badge campaign-" + c.state}>
                      {states[c.state] || c.state}
                    </span>
                    <span className="campaign-date">
                      <CalendarDays size={14} />
                      {date(c.scheduled_at)}
                    </span>
                    <ArrowRight size={17} />
                  </a>
                ))}
              </div>
            ) : (
              <div className="quiet-empty">
                <Megaphone />
                <h3>
                  {query
                    ? "No encontramos campañas"
                    : "Todavía no hay campañas aquí"}
                </h3>
                <p>
                  {query
                    ? "Prueba otra búsqueda o cambia las fechas."
                    : "Crea un borrador para empezar."}
                </p>
                {canWrite && (
                  <button
                    className="button secondary"
                    onClick={() => open("new")}
                  >
                    Crear campaña
                  </button>
                )}
              </div>
            )}
            <footer className="table-footer">
              <span>{list.data?.count || 0} campañas</span>
              <div>
                <button
                  className="button secondary"
                  disabled={!offset}
                  onClick={() =>
                    navigate({ offset: String(Math.max(0, offset - 25)) })
                  }
                >
                  Anterior
                </button>
                <button
                  className="button secondary"
                  disabled={!list.data || offset + 25 >= list.data.count}
                  onClick={() => navigate({ offset: String(offset + 25) })}
                >
                  Siguiente
                </button>
              </div>
            </footer>
          </section>
          <p className="data-footnote">
            Las campañas reales requieren activación aparte. La aprobación de
            esta pantalla autoriza una simulación.
          </p>
          <a
            className="legacy-link"
            href={`/workspace/connections?business=${encodeURIComponent(business)}&provider=google`}
          >
            Conexiones de este negocio <ArrowRight size={14} />
          </a>
        </>
      )}
    </div>
  );
}
function CampaignDetail(
  props: ViewProps & {
    id: string;
    csrf: string;
    meta: Meta;
    demo: boolean;
    canWrite: boolean;
    close: () => void;
    saved: (id: string) => void;
  },
) {
  const { id, business, csrf, meta, canWrite, close, saved, demo } = props,
    base = endpoint(business) + "/campaigns";
  const resource = useResource<Preview>(id === "new" ? null : base + "/" + id);
  const templates = useResource<TemplateCatalog>(base + "/email-templates");
  const [viewDesign, setViewDesign] = useState<string | null>(null);
  const [d, setD] = useState<Preview>();
  const unsavedDesign =
    !!viewDesign &&
    viewDesign !== (d?.document.email_design?.template_id || "legacy");
  const alternate = useResource<{ text: string }>(
    id !== "new" && unsavedDesign
      ? base +
          "/" +
          id +
          "/email-content?template_id=" +
          encodeURIComponent(viewDesign)
      : null,
  );
  const [form, setForm] = useState<Draft>(() => freshDraft(meta));
  const [uncertain, setUncertain] = useState(false);
  const wa = useResource<ChannelConfig>(
      base.replace(/\/campaigns$/, "/whatsapp"),
    ),
    sms = useResource<ChannelConfig>(base.replace(/\/campaigns$/, "/sms"));
  const promotions = useResource<
    { code: string; name: string; enabled: boolean }[]
  >(endpoint(business) + "/promotions");
  const [editing, setEditing] = useState(id === "new");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const pending = useRef(false);
  const [audienceSearch, setAudienceSearch] = useState("");
  const [checked, setChecked] = useState(false);
  const [confirmCancel, setConfirmCancel] = useState(false);
  const report = useResource<Report>(
    id === "new"
      ? null
      : base + "/" + id + "/report?scope=" + (d?.document.scope || meta.scope),
  );
  useEffect(() => {
    if (resource.data) {
      setD(resource.data);
      setViewDesign(null);
      const doc = resource.data.document;
      setForm({
        channel: doc.channel,
        promotion_code: doc.promotion_code ?? null,
        whatsapp_template_id: doc.whatsapp_template_id ?? null,
        whatsapp_parameters: doc.whatsapp_parameters || [],
        email_design: doc.email_design
          ? (Object.fromEntries(
              Object.entries(doc.email_design).filter(
                ([k]) => k !== "template_version",
              ),
            ) as EmailDesign)
          : { template_id: "legacy" },
        sender: doc.sender,
        content: doc.content,
        customer_ids: doc.customer_ids,
        scheduled_at: doc.scheduled_at,
        expires_at: doc.expires_at,
        scope: doc.scope,
        budget_microusd: doc.budget_microusd,
      });
    }
  }, [resource.data]);
  async function run(action: () => Promise<void>) {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setMessage("");
    try {
      await action();
    } catch (e) {
      if (!(e instanceof ApiError && e.status < 500)) setUncertain(true);
      setMessage(
        e instanceof Error
          ? e.message
          : "No se confirmó la acción. Actualiza antes de intentarlo de nuevo.",
      );
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }
  async function refresh() {
    const next = await api<Preview>(base + "/" + id);
    setD(next);
    setUncertain(false);
    setChecked(false);
    report.retry();
  }
  async function act(name: string) {
    await mutate(
      base + "/" + id + "/" + name,
      csrf,
      "POST",
      name === "cancel" ? undefined : { digest: d!.digest },
    );
    await refresh();
    setMessage(
      name === "approve"
        ? "Versión aprobada para simulación."
        : name === "schedule"
          ? "Campaña programada."
          : "Campaña cancelada.",
    );
    setConfirmCancel(false);
  }
  function content(key: keyof Draft["content"], value: string) {
    setForm({ ...form, content: { ...form.content, [key]: value } });
  }
  if (resource.error)
    return <Failure message={resource.error} retry={resource.retry} />;
  if (id !== "new" && !d) return <Loading />;
  const people = meta.customers.filter((p) =>
    (p.name || p.email || p.phone || "")
      .toLowerCase()
      .includes(audienceSearch.toLowerCase()),
  );
  return (
    <>
      <button className="back-link" onClick={close}>
        <ArrowLeft size={16} />
        Campañas
      </button>
      <PageHeading
        title={id === "new" ? "Nueva campaña" : d!.document.content.subject}
        description={
          editing
            ? "Guarda una versión para revisar el mensaje y los destinatarios."
            : `${states[d!.state]} · ${meta.scope === "test" ? "Simulación" : meta.scope}`
        }
      >
        {!editing && (
          <div className="heading-actions">
            <button
              className="button secondary"
              onClick={() => run(refresh)}
              disabled={busy}
            >
              <RefreshCw size={16} />
              Actualizar
            </button>
            {canWrite && !uncertain && (
              <button
                className="button secondary"
                onClick={() => {
                  setEditing(true);
                  setChecked(false);
                }}
              >
                Editar
              </button>
            )}
          </div>
        )}
      </PageHeading>
      {message && (
        <div className="action-notice" role="status">
          {message}
        </div>
      )}
      {uncertain && (
        <div className="action-notice" role="status">
          No recibimos confirmación. Comprueba el estado guardado antes de
          repetir una acción.
          <button
            className="button secondary"
            disabled={busy}
            onClick={() => (id === "new" ? close() : run(refresh))}
          >
            Comprobar campaña guardada
          </button>
        </div>
      )}
      {editing ? (
        <form
          className="campaign-editor"
          onSubmit={(e) => {
            e.preventDefault();
            run(async () => {
              const next = await mutate(
                base + (id === "new" ? "" : "/" + id),
                csrf,
                id === "new" ? "POST" : "PUT",
                form,
              );
              setD(next);
              setEditing(false);
              setChecked(false);
              saved(next.id);
            });
          }}
        >
          <section className="work-surface editor-copy">
            <div className="section-heading">
              <h2>Mensaje</h2>
              <span className="badge">
                {form.channel === "email"
                  ? "Email"
                  : form.channel === "whatsapp"
                    ? "WhatsApp"
                    : "SMS"}
              </span>
            </div>
            <div className="form-fields">
              <label>
                Canal
                <select
                  aria-label="Canal de la campaña"
                  value={form.channel}
                  onChange={(e) => {
                    const channel = e.target.value;
                    setForm({
                      ...form,
                      channel,
                      email_design:
                        channel === "email" ? { template_id: "matte" } : null,
                      sender:
                        channel === "email"
                          ? meta.sender
                          : String(
                              (channel === "whatsapp"
                                ? wa.data?.sender?.phone_id
                                : sms.data?.sender?.sender) || "",
                            ),
                      whatsapp_template_id:
                        channel === "whatsapp"
                          ? form.whatsapp_template_id
                          : null,
                      whatsapp_parameters:
                        channel === "whatsapp" ? form.whatsapp_parameters : [],
                    });
                  }}
                >
                  <option value="email">Email</option>
                  <option value="whatsapp">WhatsApp</option>
                  <option value="sms">SMS</option>
                </select>
              </label>
              {form.channel === "email" ? (
                <>
                  <label>
                    Diseño del correo
                    <select
                      aria-label="Diseño del correo"
                      value={form.email_design?.template_id || "legacy"}
                      onChange={(e) =>
                        setForm({
                          ...form,
                          email_design: {
                            ...form.email_design,
                            template_id: e.target.value,
                            chassis:
                              e.target.value === "legacy"
                                ? undefined
                                : form.email_design?.chassis,
                          },
                        })
                      }
                    >
                      {(
                        templates.data?.templates || [
                          {
                            id: "legacy",
                            name: "Clásico anterior",
                            available: true,
                          },
                        ]
                      ).map((t) => (
                        <option key={t.id} value={t.id} disabled={!t.available}>
                          {t.name}
                          {t.available ? "" : " · no disponible"}
                        </option>
                      ))}
                    </select>
                  </label>
                  {form.email_design?.template_id !== "legacy" && (
                    <EmailChassisControls
                      value={form.email_design?.chassis}
                      change={(chassis) =>
                        setForm({
                          ...form,
                          email_design: { ...form.email_design!, chassis },
                        })
                      }
                    />
                  )}
                  {form.email_design?.template_id !== "legacy" && (
                    <details>
                      <summary>Imagen y botón · opcional</summary>
                      <div className="form-fields">
                        <label>
                          Imagen del correo · URL
                          <input
                            type="url"
                            value={form.email_design?.image_url || ""}
                            onChange={(e) =>
                              setForm({
                                ...form,
                                email_design: {
                                  ...form.email_design!,
                                  image_url: e.target.value || null,
                                },
                              })
                            }
                            placeholder="https://tu-negocio.com/foto.jpg"
                          />
                        </label>
                        <label>
                          Descripción de la imagen
                          <input
                            maxLength={200}
                            value={form.email_design?.image_alt || ""}
                            onChange={(e) =>
                              setForm({
                                ...form,
                                email_design: {
                                  ...form.email_design!,
                                  image_alt: e.target.value,
                                },
                              })
                            }
                          />
                        </label>
                        <label>
                          Texto del botón
                          <input
                            maxLength={80}
                            value={
                              form.email_design?.cta_label ||
                              "Ver la carta y pedir →"
                            }
                            onChange={(e) =>
                              setForm({
                                ...form,
                                email_design: {
                                  ...form.email_design!,
                                  cta_label: e.target.value,
                                },
                              })
                            }
                          />
                        </label>
                      </div>
                    </details>
                  )}
                  <label>
                    Remitente
                    <input
                      value={form.sender}
                      onChange={(e) =>
                        setForm({ ...form, sender: e.target.value })
                      }
                      required
                      type="email"
                    />
                  </label>
                </>
              ) : (
                <PhoneCampaignFields
                  business={business}
                  form={form}
                  change={setForm}
                />
              )}
              <label>
                Asunto
                <input
                  value={form.content.subject}
                  onChange={(e) => content("subject", e.target.value)}
                  required
                  maxLength={180}
                  placeholder="Lo primero que van a leer"
                />
              </label>
              <label>
                Título del mensaje
                <input
                  value={form.content.title}
                  onChange={(e) => content("title", e.target.value)}
                  required
                  maxLength={180}
                />
              </label>
              {form.channel !== "whatsapp" && (
                <label>
                  Mensaje
                  <textarea
                    value={form.content.body}
                    onChange={(e) => content("body", e.target.value)}
                    required
                    maxLength={4000}
                    rows={7}
                    placeholder="Escribe como hablarías con tus clientes."
                  />
                </label>
              )}
              <label>
                Condiciones y vigencia
                <textarea
                  value={form.content.terms}
                  onChange={(e) => content("terms", e.target.value)}
                  required
                  maxLength={1000}
                  rows={3}
                />
              </label>
            </div>
          </section>
          <div className="editor-side">
            <section className="work-surface">
              <div className="section-heading">
                <h2>Destinatarios</h2>
                <span className="number-chip">{form.customer_ids.length}</span>
              </div>
              <div className="form-fields">
                <input
                  aria-label="Buscar destinatarios"
                  placeholder="Buscar contacto"
                  value={audienceSearch}
                  onChange={(e) => setAudienceSearch(e.target.value)}
                />
                <div className="audience-picker">
                  {people.map((p) => (
                    <label key={p.id}>
                      <input
                        type="checkbox"
                        checked={form.customer_ids.includes(p.id)}
                        onChange={(e) =>
                          setForm({
                            ...form,
                            customer_ids: e.target.checked
                              ? [...form.customer_ids, p.id]
                              : form.customer_ids.filter((i) => i !== p.id),
                          })
                        }
                      />
                      <span>
                        <strong>{p.name || "Sin nombre"}</strong>
                        <small>
                          {(form.channel === "email" ? p.email : p.phone) ||
                            "Sin contacto para este canal"}
                        </small>
                      </span>
                    </label>
                  ))}
                </div>
                <p className="caption">
                  Hasta 500 contactos existentes. La revisión separa quién puede
                  recibirlo y quién queda fuera.
                </p>
              </div>
            </section>
            <section className="work-surface">
              <div className="section-heading">
                <h2>Cuándo y cuánto</h2>
              </div>
              <div className="form-fields">
                <label>
                  Programar · hora de Bogotá
                  <input
                    type="datetime-local"
                    value={localTime(form.scheduled_at)}
                    onChange={(e) => {
                      if (e.target.value)
                        setForm({
                          ...form,
                          scheduled_at: e.target.value + ":00-05:00",
                        });
                    }}
                    required
                  />
                </label>
                <label>
                  Vence · hora de Bogotá
                  <input
                    type="datetime-local"
                    value={localTime(form.expires_at)}
                    onChange={(e) => {
                      if (e.target.value)
                        setForm({
                          ...form,
                          expires_at: e.target.value + ":00-05:00",
                        });
                    }}
                    required
                  />
                </label>
                <label>
                  Promoción existente · opcional
                  <select
                    aria-label="Promoción existente"
                    value={form.promotion_code || ""}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        promotion_code: e.target.value || null,
                      })
                    }
                  >
                    <option value="">Sin promoción asociada</option>
                    {promotions.data?.map((p) => (
                      <option key={p.code} value={p.code}>
                        {p.code} · {p.name}
                        {p.enabled ? "" : " · deshabilitada"}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Presupuesto máximo · USD
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="0.01"
                    value={form.budget_microusd / 1000000}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        budget_microusd: Math.round(
                          Number(e.target.value) * 1000000,
                        ),
                      })
                    }
                    required
                  />
                </label>
                <p className="caption">
                  {meta.scope === "test"
                    ? "Simulación. No se enviarán mensajes reales."
                    : "Este entorno no tiene activación de envío real."}
                </p>
              </div>
            </section>
          </div>
          <div className="editor-submit">
            <p>Guardar una edición invalida la aprobación anterior.</p>
            <button
              className="button primary"
              disabled={
                busy || uncertain || !canWrite || !form.customer_ids.length
              }
            >
              Guardar y revisar <ArrowRight size={16} />
            </button>
            {id !== "new" && (
              <button
                type="button"
                className="button secondary"
                onClick={() => {
                  setEditing(false);
                  resource.retry();
                }}
              >
                Volver a la versión guardada
              </button>
            )}
          </div>
        </form>
      ) : (
        <>
          <div className="campaign-review">
            <section className="work-surface email-preview">
              <div className="section-heading">
                <h2>
                  {unsavedDesign ? "Vista de otro diseño" : "Mensaje guardado"}
                </h2>
                <span className="caption">
                  {d!.document.channel === "email"
                    ? "HTML + texto"
                    : "Contenido del canal"}
                </span>
              </div>
              {d!.render_error && (
                <p className="action-notice" role="alert">
                  El diseño no está disponible. Puedes editar la campaña y
                  elegir Clásico anterior, o intentarlo de nuevo.
                </p>
              )}
              {d!.document.channel === "email" && (
                <div className="form-fields email-design-controls">
                  <label>
                    Probar otro diseño
                    <select
                      aria-label="Probar otro diseño"
                      value={
                        viewDesign ||
                        d!.document.email_design?.template_id ||
                        "legacy"
                      }
                      disabled={busy || uncertain}
                      onChange={(e) => {
                        setViewDesign(e.target.value);
                        setChecked(false);
                      }}
                    >
                      {templates.data?.templates.map((t) => (
                        <option key={t.id} value={t.id} disabled={!t.available}>
                          {t.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  {viewDesign &&
                    viewDesign !==
                      (d!.document.email_design?.template_id || "legacy") && (
                      <>
                        <p role="status">
                          Vista de prueba. La campaña y su aprobación siguen con
                          el diseño guardado.
                        </p>
                        {canWrite && (
                          <button
                            type="button"
                            className="button secondary"
                            disabled={busy || uncertain}
                            onClick={() =>
                              run(async () => {
                                const next = await mutate(
                                  base + "/" + id + "/design",
                                  csrf,
                                  "POST",
                                  {
                                    digest: d!.digest,
                                    email_design: {
                                      ...form.email_design,
                                      template_id: viewDesign,
                                    },
                                  },
                                );
                                setD(next);
                                setViewDesign(null);
                                setChecked(false);
                                saved(next.id);
                                resource.retry();
                                setMessage(
                                  "Diseño guardado en una nueva versión. Revisa y aprueba de nuevo.",
                                );
                              })
                            }
                          >
                            Guardar este diseño
                          </button>
                        )}
                      </>
                    )}
                  {alternate.error && <p role="alert">{alternate.error}</p>}
                </div>
              )}
              {d!.document.channel === "email" ? (
                <iframe
                  key={d!.digest + String(viewDesign)}
                  src={
                    base +
                    "/" +
                    id +
                    "/email" +
                    (unsavedDesign
                      ? "?template_id=" + encodeURIComponent(viewDesign)
                      : "")
                  }
                  sandbox="allow-same-origin"
                  title="Vista previa del correo"
                />
              ) : (
                <p className="panel-note message-copy">{d!.email.text}</p>
              )}
              <details className="plain-preview">
                <summary>Versión de texto</summary>
                <pre>{alternate.data?.text || d!.email.text}</pre>
              </details>
            </section>
            <div className="review-side">
              <section className="work-surface review-summary">
                <h2>
                  {d!.state === "draft" || d!.state === "approved"
                    ? "Antes de programar"
                    : "Elegibilidad actual"}
                </h2>
                {d!.state === "scheduled" && (
                  <p className="caption">
                    Se revisa de nuevo antes de cada envío. El historial está en
                    Resultados.
                  </p>
                )}
                <dl>
                  <div>
                    <dt>Pueden recibirlo</dt>
                    <dd>{d!.eligible}</dd>
                  </div>
                  <div>
                    <dt>Excluidos</dt>
                    <dd>{d!.excluded}</dd>
                  </div>
                  <div>
                    <dt>Coste estimado</dt>
                    <dd>{cost(d!.estimated_cost_microusd)}</dd>
                  </div>
                  <div>
                    <dt>Presupuesto</dt>
                    <dd>{cost(d!.document.budget_microusd)}</dd>
                  </div>
                  <div>
                    <dt>Programación</dt>
                    <dd>
                      {localTime(d!.document.scheduled_at).replace("T", " ")}
                      <small>Bogotá</small>
                    </dd>
                  </div>
                  <div>
                    <dt>Vencimiento</dt>
                    <dd>
                      {localTime(d!.document.expires_at).replace("T", " ")}
                    </dd>
                  </div>
                </dl>
                <p className="caption">Remitente: {d!.document.sender}</p>
                <p className="caption">
                  {meta.scope === "test"
                    ? "El reloj de prueba es " +
                      localTime(d!.simulation_clock).replace("T", " ") +
                      "."
                    : "Envío real no activado."}
                </p>
                {canWrite && d!.state === "draft" && (
                  <>
                    <label className="review-check">
                      <input
                        type="checkbox"
                        checked={checked}
                        disabled={unsavedDesign || !!d!.render_error}
                        onChange={(e) => setChecked(e.target.checked)}
                      />
                      Revisé el mensaje, destinatarios, fechas y presupuesto de
                      esta versión.
                    </label>
                    <button
                      className="button primary"
                      disabled={
                        busy ||
                        uncertain ||
                        !checked ||
                        meta.scope !== "test" ||
                        unsavedDesign ||
                        !!d!.render_error
                      }
                      onClick={() => run(() => act("approve"))}
                    >
                      <Check size={16} />
                      Aprobar simulación
                    </button>
                  </>
                )}
                {canWrite && d!.approved && d!.state === "approved" && (
                  <button
                    className="button primary"
                    disabled={
                      busy || uncertain || unsavedDesign || !!d!.render_error
                    }
                    onClick={() => run(() => act("schedule"))}
                  >
                    <CalendarDays size={16} />
                    Programar
                  </button>
                )}
                {canWrite && d!.state !== "cancelled" && (
                  <button
                    className="button secondary"
                    disabled={busy || uncertain}
                    onClick={() => setConfirmCancel(true)}
                  >
                    Cancelar campaña
                  </button>
                )}
                {confirmCancel && (
                  <div
                    className="cancel-inline"
                    role="group"
                    aria-label="Confirmar cancelación"
                  >
                    <p>
                      Se detendrán los envíos pendientes. Los ya enviados no se
                      pueden retirar.
                    </p>
                    <button
                      className="button secondary"
                      disabled={busy || uncertain}
                      onClick={() => run(() => act("cancel"))}
                    >
                      Sí, cancelar campaña
                    </button>
                    <button
                      className="back-link"
                      onClick={() => setConfirmCancel(false)}
                    >
                      Volver
                    </button>
                  </div>
                )}
                {!canWrite && (
                  <p className="caption">
                    Tu acceso permite consultar. La aprobación requiere permiso
                    de campañas.
                  </p>
                )}
              </section>
              <section className="work-surface audience-review">
                <div className="section-heading">
                  <h2>Destinatarios</h2>
                </div>
                <div>
                  {d!.audience.map((p) => (
                    <div className="audience-result" key={p.id}>
                      <strong>{p.name || "Sin nombre"}</strong>
                      <small>{p.destination || "Sin dirección"}</small>
                      <span
                        className={
                          "badge " + (p.status === "allowed" ? "verified" : "")
                        }
                      >
                        {p.status === "allowed"
                          ? "Elegible"
                          : p.status === "unknown"
                            ? "Sin confirmar"
                            : "Excluido"}
                      </span>
                      {p.sms_segments !== undefined && (
                        <small>
                          {p.sms_segments} segmentos · {p.sms_encoding} ·{" "}
                          {cost(p.sms_cost_microusd ?? null)}
                        </small>
                      )}
                      {p.reasons.map((reason) => (
                        <small key={reason}>
                          {reasons[reason] || reason.replaceAll("_", " ")}
                        </small>
                      ))}
                    </div>
                  ))}
                </div>
              </section>
            </div>
          </div>
          {d!.document.channel !== "email" && (
            <ProviderTestReview
              key={business + id + (props.params.get("test_review") || "")}
              business={business}
              csrf={csrf}
              canWrite={canWrite}
              preview={d!}
              meta={meta}
              params={props.params}
              navigate={props.navigate}
            />
          )}
          <section className="work-surface campaign-report">
            <div className="section-heading">
              <h2>Resultados</h2>
              <span className="caption">
                Toda la campaña ·{" "}
                {meta.scope === "test" ? "simulación" : meta.scope} ·{" "}
                {report.data?.currency || ""}
              </span>
            </div>
            {report.error ? (
              <Failure message={report.error} retry={report.retry} />
            ) : !report.data ? (
              <Loading />
            ) : (
              <>
                <div className="report-grid">
                  {[
                    ["En cola", report.data.queued],
                    [
                      meta.scope === "test"
                        ? "Aceptados por simulador"
                        : "Aceptados por proveedor",
                      report.data.provider_accepted,
                    ],
                    [
                      "Entrega reportada",
                      report.data.provider_reported_delivery,
                    ],
                    ["Visitas al enlace", report.data.tracked_visits],
                    ["Visitas de escáner", report.data.scanner_visits],
                    [
                      "Lecturas reportadas",
                      report.data.read_signals === "unavailable"
                        ? "No disponibles"
                        : report.data.read_signals,
                    ],
                    [
                      "Costo registrado · USD",
                      cost(report.data.delivery_cost_microusd),
                    ],
                    ["Pedidos pagados", report.data.paid_orders],
                    [
                      "Capturado menos devuelto",
                      amount(report.data.net_revenue, report.data.currency),
                    ],
                  ].map(([label, value]) => (
                    <div key={label}>
                      <span>{label}</span>
                      <strong>{value}</strong>
                    </div>
                  ))}
                </div>
                <p className="panel-note">
                  Capturado{" "}
                  {amount(report.data.captured_revenue, report.data.currency)} ·
                  Devuelto {amount(report.data.refunds, report.data.currency)} ·{" "}
                  {report.data.unknown} resultados desconocidos ·{" "}
                  {report.data.receipt_missing} sin recibo de entrega. Una
                  visita no prueba que sea una persona.
                </p>
                {d!.document.channel === "sms" && report.data.sms && (
                  <section className="sms-report-detail">
                    <h3>Detalle de SMS</h3>
                    <p>
                      {report.data.sms.estimated_submitted_segments} segmentos
                      sometidos · estimación{" "}
                      {cost(report.data.sms.estimated_delivery_cost_microusd)}
                    </p>
                    <p>
                      Recibos de la ruta:{" "}
                      {report.data.sms.route_receipt_support.join(", ") ||
                        "Sin datos"}
                      .
                    </p>
                    {Object.entries(report.data.sms.provider_status_counts).map(
                      ([state, n]) => (
                        <p key={state}>
                          {state}: {n}
                        </p>
                      ),
                    )}
                    <p className="source-note">
                      Estos estados son históricos y no se suman entre sí. El
                      precio usa la tarifa guardada; no verifica la factura del
                      proveedor. En simulación no se incurre en costo.
                    </p>
                  </section>
                )}
                {demo && meta.scope === "test" && canWrite && (
                  <div className="simulation-actions">
                    <span className="badge">Solo demostración</span>
                    <button
                      className="button secondary"
                      disabled={busy || uncertain}
                      onClick={() =>
                        run(async () => {
                          await mutate(
                            base + "/simulate/dispatch",
                            csrf,
                            "POST",
                          );
                          await refresh();
                          setMessage(
                            "Se procesaron los trabajos vencidos del negocio, en simulación.",
                          );
                        })
                      }
                    >
                      Procesar pendientes del negocio
                    </button>
                    <button
                      className="button secondary"
                      disabled={busy || uncertain}
                      onClick={() =>
                        run(async () => {
                          await mutate(
                            base + "/" + id + "/simulate-receipt",
                            csrf,
                            "POST",
                          );
                          await refresh();
                          setMessage("Recibos simulados registrados.");
                        })
                      }
                    >
                      Simular recibos de entrega
                    </button>
                  </div>
                )}
                {report.data.deliveries.length > 0 && (
                  <details className="delivery-details">
                    <summary>Ver entregas y enlaces</summary>
                    {report.data.deliveries.map((j) => (
                      <div className="delivery-row" key={j.id}>
                        <span>
                          {deliveryStates[j.state] || j.state}
                          {j.reason ? " · " + explainReason(j.reason) : ""}
                        </span>
                        <small>
                          Contacto: {j.customer_id} · Referencia:{" "}
                          {j.message_id || "Sin confirmar"}
                        </small>
                        {demo && (
                          <>
                            <a href={j.tracking_url}>
                              Abrir pedido de prueba <ArrowRight size={14} />
                            </a>
                            <a href={j.unsubscribe_url}>Retirar permiso</a>
                          </>
                        )}
                      </div>
                    ))}
                  </details>
                )}
              </>
            )}
          </section>
        </>
      )}
    </>
  );
}
