import { useEffect, useState } from "react";
import { Dialog } from "@base-ui/react/dialog";
import { RefreshCw } from "lucide-react";
import { api, endpoint, useResource, Failure, Loading } from "./ui";
import { useOperation, OperationNotice } from "./operations-ui";
import "./growth-channels.css";
export type ConnectionProps = {
  business: string;
  csrf: string;
  permissions: string[];
  demo: boolean;
  params: URLSearchParams;
  navigate: (changes: Record<string, string | null>, push?: boolean) => void;
};
export const providers = [
  ["google", "Google"],
  ["instagram", "Instagram"],
  ["whatsapp", "WhatsApp"],
  ["sms", "SMS"],
];
export function ProviderTabs({
  params,
  navigate,
}: Pick<ConnectionProps, "params" | "navigate">) {
  const selected = params.get("provider") || "google";
  return (
    <div className="tabs channel-tabs" aria-label="Proveedores de conexión">
      {providers.map(([key, name]) => (
        <button
          key={key}
          className={selected === key ? "selected" : ""}
          aria-pressed={selected === key}
          onClick={() => navigate({ provider: key }, true)}
        >
          {name}
        </button>
      ))}
    </div>
  );
}
const states: Record<string, string> = {
  unconfigured: "Falta configurar la conexión",
  disconnected: "Sin conexión",
  authorizing: "Esperando autorización",
  exchanging: "Comprobando acceso",
  access_denied: "Autorización cancelada",
  discovering: "Buscando recursos",
  choose_location: "Elige el recurso correcto",
  syncing: "Actualizando datos",
  connected: "Conectado",
  partial: "Datos parciales",
  sync_error: "No se pudo actualizar",
  reconnect_required: "Vuelve a conectar",
  disconnecting: "Revocación pendiente",
};
const reasons: Record<string, string> = {
  provider_access_denied:
    "El proveedor no permite consultar estos datos con el acceso actual.",
  provider_temporarily_unavailable:
    "El proveedor no está disponible. Las lecturas se reintentan de forma limitada.",
  reconnect_required: "El permiso venció o fue retirado.",
  revoke_in_google_account:
    "El acceso local se eliminó. Retira también el permiso en tu cuenta de Google.",
  revoke_in_instagram_settings:
    "El acceso local se eliminó. Retira también el permiso en la configuración de Instagram.",
  account_selection_limit:
    "La cuenta supera el límite de recursos de esta versión.",
  provider_network_error: "No se pudo contactar al proveedor.",
  authorization_expired: "La autorización venció.",
  permission_or_field_unavailable:
    "No disponible con los permisos o campos actuales.",
  outside_probe_limit: "Fuera del límite de esta importación.",
};
const reason = (r: string) =>
  reasons[r] || "Esta información no está disponible con el acceso actual.";
type Doc = {
  state: string;
  mode?: string;
  verification?: string;
  assets: {
    key: string;
    name?: string;
    account?: { name: string; accountName?: string };
    location?: { name: string; title?: string };
  }[];
  snapshot: any;
  selected?: string;
  error?: string;
  last_success?: string;
  cache_expires_at?: string;
  job?: { state: string; attempts: number };
  capabilities?: Record<string, unknown>;
};
export function AccountConnection(props: ConnectionProps) {
  const { business, params, csrf, permissions } = props,
    provider = params.get("provider") === "instagram" ? "instagram" : "google",
    label = provider === "google" ? "Google" : "Instagram";
  const statusRoot = endpoint(business) + "/connections",
    root =
      provider === "google"
        ? statusRoot + "/google"
        : endpoint(business) + "/social/instagram";
  const resource = useResource<Record<string, Doc>>(statusRoot),
    op = useOperation(csrf),
    [notice, setNotice] = useState(""),
    [selected, setSelected] = useState(""),
    [command, setCommand] = useState<string | null>(null),
    [reviewed, setReviewed] = useState(false);
  const d = resource.data?.[provider],
    canWrite = permissions.includes("settings.write");
  useEffect(() => {
    if (
      !d ||
      !["discovering", "exchanging", "syncing", "disconnecting"].includes(
        d.state,
      )
    )
      return;
    const t = setTimeout(resource.retry, 1500);
    return () => clearTimeout(t);
  }, [d?.state, d?.job?.attempts, business, provider]);
  async function check() {
    try {
      await api(statusRoot);
      resource.retry();
      op.checked();
    } catch {
      op.setMessage(
        "No pudimos comprobar el estado. No repitas una acción sin revisarlo.",
      );
    }
  }
  async function act(name: string) {
    const out = await op.perform<{ url?: string }>(
      root + "/" + name,
      name === "select"
        ? provider === "google"
          ? { location: selected }
          : { account_id: selected }
        : undefined,
    );
    setCommand(null);
    if (out?.url) {
      location.assign(out.url);
      return;
    }
    if (out) {
      setNotice("Solicitud guardada. Revisa el estado de la conexión.");
      resource.retry();
    }
  }
  const pending =
    !!d &&
    [
      "authorizing",
      "exchanging",
      "discovering",
      "syncing",
      "disconnecting",
    ].includes(d.state);
  return (
    <div className="page growth-channel-page account-connections">
      <section className="page-heading">
        <div>
          <h1>Conexiones</h1>
          <p>Autoriza la cuenta y confirma el recurso de este negocio.</p>
        </div>
        <button className="button secondary" disabled={op.busy} onClick={check}>
          <RefreshCw size={16} />
          Comprobar estado
        </button>
      </section>
      <ProviderTabs {...props} />
      <OperationNotice
        message={
          (op.message === "Wait one minute before refreshing"
            ? "Espera un minuto antes de actualizar."
            : op.message) || notice
        }
      />
      {resource.error ? (
        <Failure message={resource.error} retry={resource.retry} />
      ) : !d ? (
        <Loading />
      ) : (
        <>
          <section className="work-surface account-status">
            <h2>{label}</h2>
            <p role="status" className="connection-state">
              {states[d.state] || "Estado pendiente de revisión"}
            </p>
            <p className="source-note">
              {d.mode === "test" || d.verification === "fixture"
                ? "Simulación · datos ficticios. No verifica una conexión real."
                : d.state === "unconfigured"
                  ? "La conexión no está configurada en este entorno. No hay una cuenta conectada."
                  : "Solo lectura. Los datos disponibles dependen de los permisos y límites del proveedor."}
            </p>
            {d.error && <p>{reason(d.error)}</p>}
            {d.job && (
              <p className="source-note">
                Trabajo:{" "}
                {(
                  {
                    done: "completado",
                    pending: "pendiente",
                    running: "procesando",
                    failed: "fallido",
                  } as Record<string, string>
                )[d.job.state] || d.job.state}{" "}
                · intentos: {d.job.attempts}
              </p>
            )}
            {canWrite && (
              <div className="account-actions">
                <button
                  className="button primary"
                  disabled={
                    op.busy ||
                    op.uncertain ||
                    pending ||
                    d.state === "unconfigured"
                  }
                  onClick={() => act("authorize")}
                >
                  {d.state === "disconnected"
                    ? "Conectar " + label
                    : "Volver a conectar " + label}
                </button>
                {[
                  "connected",
                  "partial",
                  "sync_error",
                  "choose_location",
                ].includes(d.state) && (
                  <button
                    className="button secondary"
                    disabled={op.busy || op.uncertain}
                    onClick={() => act("refresh")}
                  >
                    Actualizar datos
                  </button>
                )}
                {provider === "google" &&
                  [
                    "connected",
                    "partial",
                    "sync_error",
                    "choose_location",
                  ].includes(d.state) && (
                    <button
                      className="button secondary"
                      disabled={op.busy || op.uncertain}
                      onClick={() => act("refresh?discover=true")}
                    >
                      Buscar ubicaciones
                    </button>
                  )}
                {!["unconfigured", "disconnected"].includes(d.state) && (
                  <button
                    className="button secondary"
                    disabled={
                      op.busy || op.uncertain || d.state === "exchanging"
                    }
                    onClick={() => {
                      setCommand("disconnect");
                      setReviewed(false);
                    }}
                  >
                    Desconectar {label}
                  </button>
                )}
              </div>
            )}
            {d.state === "choose_location" && (
              <>
                {d.assets.length ? (
                  <form
                    className="channel-form"
                    onSubmit={(e) => {
                      e.preventDefault();
                      setCommand("select");
                      setReviewed(false);
                    }}
                  >
                    <label>
                      Recurso del negocio
                      <select
                        aria-label="Recurso del negocio"
                        required
                        value={selected}
                        disabled={!canWrite || op.busy || op.uncertain}
                        onChange={(e) => setSelected(e.target.value)}
                      >
                        <option value="">Elige un recurso autorizado</option>
                        {d.assets.map((a) => (
                          <option key={a.key} value={a.key}>
                            {a.location?.title || a.name || a.key}
                            {a.account
                              ? " · " +
                                (a.account.accountName || a.account.name)
                              : ""}
                          </option>
                        ))}
                      </select>
                    </label>
                    {canWrite && (
                      <button
                        className="button primary"
                        disabled={!selected || op.busy || op.uncertain}
                      >
                        Confirmar recurso
                      </button>
                    )}
                  </form>
                ) : (
                  <p>
                    No hay recursos disponibles en la lista vigente. Comprueba
                    los permisos o vuelve a buscar.
                  </p>
                )}
              </>
            )}
          </section>
          {d.snapshot ? (
            <section className="work-surface connection-snapshot">
              <p className="source-note">
                Última lectura correcta:{" "}
                {d.last_success
                  ? new Date(d.last_success).toLocaleString("es-CO")
                  : "No disponible"}
                .{" "}
                {d.cache_expires_at &&
                  "Caché vigente hasta " +
                    new Date(d.cache_expires_at).toLocaleString("es-CO") +
                    "."}
              </p>
              {provider === "google" ? (
                <GoogleSnapshot snapshot={d.snapshot} />
              ) : (
                <InstagramSnapshot snapshot={d.snapshot} />
              )}
            </section>
          ) : (
            <p className="source-note">
              No hay datos vigentes para mostrar. Un permiso concedido no
              garantiza cobertura completa.
            </p>
          )}
          <p className="source-note">
            Facebook, TikTok, Search Console y GA4 no tienen una conexión
            implementada en esta pantalla. La configuración de WhatsApp y SMS
            conserva sus propios permisos y requisitos.
          </p>
        </>
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
              {command === "disconnect"
                ? "Desconectar " + label
                : "Confirmar recurso"}
            </Dialog.Title>
            <Dialog.Description>
              {command === "disconnect"
                ? "Se eliminarán los datos locales de esta conexión y se cancelarán sus trabajos pendientes. La retirada del permiso en el proveedor puede requerir otro paso."
                : "Se importarán los datos del recurso autorizado " +
                  selected +
                  ". Confirma que corresponde a este negocio."}
            </Dialog.Description>
            <label className="review-check">
              <input
                type="checkbox"
                checked={reviewed}
                onChange={(e) => setReviewed(e.target.checked)}
              />
              Revisé el negocio y el alcance de esta acción.
            </label>
            <div className="dialog-actions">
              <button
                className="button secondary"
                disabled={op.busy}
                onClick={() => setCommand(null)}
              >
                Volver
              </button>
              <button
                className="button primary"
                disabled={!reviewed || op.busy || op.uncertain}
                onClick={() => act(command!)}
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
function GoogleSnapshot({ snapshot: s }: { snapshot: any }) {
  const sections = s.sections || {},
    listing = sections.listing || {},
    reviews = sections.reviews?.reviews || [];
  const metrics = (sections.metrics?.multiDailyMetricTimeSeries || []).flatMap(
    (g: any) =>
      (g.dailyMetricTimeSeries || []).flatMap((series: any) =>
        (series.timeSeries?.datedValues || []).map((p: any) => ({
          metric: series.dailyMetric,
          ...p,
        })),
      ),
  );
  const names: Record<string, string> = {
    WEBSITE_CLICKS: "Clics al sitio web",
    CALL_CLICKS: "Clics para llamar",
    BUSINESS_DIRECTION_REQUESTS: "Solicitudes de indicaciones",
  };
  return (
    <>
      <h2>{listing.title || "Ubicación seleccionada"}</h2>
      <p>
        {[
          ...(listing.storefrontAddress?.addressLines || []),
          listing.storefrontAddress?.locality,
        ]
          .filter(Boolean)
          .join(", ")}
      </p>
      <p>Teléfono: {listing.phoneNumbers?.primaryPhone || "No disponible"}</p>
      <p>Sitio: {listing.websiteUri || "No disponible"}</p>
      {Object.entries(s.errors || {}).map(([key, value]) => (
        <p key={key} role="status">
          {(
            {
              listing: "Ficha",
              metrics: "Actividad",
              reviews: "Reseñas",
            } as Record<string, string>
          )[key] || key}
          : {reason(String(value))}
        </p>
      ))}
      <h3>Actividad disponible</h3>
      <p>
        Periodo solicitado: {s.period?.start} — {s.period?.end}. Los clics para
        llamar no son llamadas completadas ni ventas.
      </p>
      {metrics.length ? (
        <div className="connection-table">
          <table>
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Medida</th>
                <th>Valor</th>
              </tr>
            </thead>
            <tbody>
              {metrics.map((p: any, i: number) => (
                <tr key={i}>
                  <td>
                    {p.date?.year}-{String(p.date?.month).padStart(2, "0")}-
                    {String(p.date?.day).padStart(2, "0")}
                  </td>
                  <td>{names[p.metric] || p.metric}</td>
                  <td>{p.value ?? "No disponible"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p>No se devolvieron valores disponibles para este periodo.</p>
      )}
      <h3>Reseñas</h3>
      <p>
        Última página accesible: {reviews.length} reseñas, hasta 50. No es un
        archivo completo.
      </p>
      {reviews.map((r: any, i: number) => (
        <article className="catalogue-item" key={r.reviewId || i}>
          <strong>{r.reviewer?.displayName || "Autor no disponible"}</strong>
          <p>
            {(
              {
                ONE: "1",
                TWO: "2",
                THREE: "3",
                FOUR: "4",
                FIVE: "5",
              } as Record<string, string>
            )[r.starRating] || "No disponible"}{" "}
            / 5 ·{" "}
            {r.updateTime
              ? new Date(r.updateTime).toLocaleString("es-CO")
              : "Fecha no disponible"}
          </p>
          <p>{r.comment || "Sin comentario"}</p>
          {r.reviewReply && (
            <p>Respuesta del negocio: {r.reviewReply.comment}</p>
          )}
        </article>
      ))}
    </>
  );
}
function InstagramSnapshot({ snapshot: s }: { snapshot: any }) {
  return (
    <>
      <h2>Publicaciones importadas</h2>
      <p>
        {s.coverage?.posts} publicaciones · {s.coverage?.requests} solicitudes
        de un máximo de {s.coverage?.maximum_requests}.{" "}
        {s.coverage?.has_more
          ? "Hay más publicaciones fuera de esta importación."
          : "Se llegó al final de la lista accesible."}
      </p>
      <p>
        Alcance, ventas y tráfico de búsqueda no disponibles. Los textos son
        históricos: confirma ofertas y precios antes de reutilizarlos.
      </p>
      <div className="catalogue-grid">
        {s.posts?.map((p: any) => (
          <article className="catalogue-item" key={p.id}>
            <h3>
              {(
                {
                  IMAGE: "Fotografía",
                  VIDEO: "Video",
                  CAROUSEL_ALBUM: "Carrusel",
                } as Record<string, string>
              )[p.format] || p.format}
            </h3>
            <p>{p.published_at_native || "Fecha no disponible"}</p>
            <small>
              Precisión:{" "}
              {(
                {
                  day: "solo día",
                  second: "segundos",
                  minute: "minutos",
                  unknown: "desconocida",
                } as Record<string, string>
              )[p.timestamp_precision] || p.timestamp_precision}
              . UTC: {p.published_at_utc || "No disponible"}
            </small>
            <p className="message-copy">{p.caption || "Sin texto"}</p>
            {["likes", "comments"].map((m) => (
              <p key={m}>
                {m === "likes" ? "Me gusta" : "Comentarios"}:{" "}
                {p.metrics?.[m]?.value ?? "No disponible"}
                {p.metrics?.[m]?.reason && " · " + reason(p.metrics[m].reason)}
              </p>
            ))}
          </article>
        ))}
      </div>
    </>
  );
}
