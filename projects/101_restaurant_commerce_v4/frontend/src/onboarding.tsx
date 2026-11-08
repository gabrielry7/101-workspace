import { useEffect, useRef, useState } from "react";
import { Dialog } from "@base-ui/react/dialog";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronRight,
  ExternalLink,
  Layers,
  Plus,
  RefreshCw,
  Search,
  X,
} from "lucide-react";
import { date, Failure, Loading } from "./ui";
import { parseBusinesses, csvCell } from "./onboarding-contract";
import "./onboarding.css";

type Resource = {
  status: string;
  code?: string;
  error?: string;
  next_action?: string;
  hostname?: string;
  domain?: string;
  website_id?: string;
  dns?: { type: string; name: string; content: string };
  ownership_verification?: { type?: string; name?: string; value?: string };
  validation_records?: { txt_name?: string; txt_value?: string }[];
};
type Setup = {
  business_id: string;
  slug: string;
  status: string;
  configuration: {
    name: string;
    owner_id: string;
    custom_hostname?: string;
    currency: string;
    timezone: string;
  };
  resources: Record<string, Resource>;
  attempts: number;
  next_attempt_at?: string;
  lease_until?: string;
  history?: { action: string; at: string; actor: string }[];
};
type Directory = {
  items: Setup[];
  count: number;
  offset: number;
  limit: number;
};
type Owner = { id: string; username: string };
type Command = {
  request_key: string;
  name: string;
  slug: string;
  owner_id: string;
  custom_hostname?: string;
  currency: string;
  timezone: string;
};
type Outcome = { result?: Setup; error?: string; next_action?: string };
type Ledger = { requests: Command[]; outcomes?: Outcome[] };
const states: Record<string, string> = {
  ready: "Listo",
  queued: "En cola",
  pending: "Pendiente",
  suspended: "Suspendido",
  pending_dns_tls: "Verificar dominio",
  pending_platform: "Configurar plataforma",
  error: "Revisar",
  running: "En curso",
};
const stages: Record<string, string> = {
  commerce: "Sitio y acceso",
  analytics: "Analítica",
  managed_domain: "Enlace 101",
  custom_domain: "Dominio propio",
};
const codeText: Record<string, string> = {
  idempotency_conflict:
    "Reintenta los datos originales o inicia una nueva solicitud.",
  reservation_conflict: "El enlace, dominio o negocio ya está reservado.",
  owner_missing: "Elige una cuenta activa para el propietario.",
  request_conflict: "La solicitud ya existe con otros datos.",
  slug_conflict: "Este enlace ya está en uso.",
  domain_conflict: "El dominio ya está asociado. Revisa su propietario.",
  owner_not_found: "Elige una cuenta activa para el propietario.",
  busy_or_suspended: "Hay una operación en curso o el negocio está suspendido.",
  cloudflare_setup_pending:
    "Falta conectar la configuración compartida de dominios.",
  umami_setup_pending: "Falta habilitar la analítica de la plataforma.",
  provider_http_401: "Revisa el acceso del servicio de analítica.",
  managed_routing_pending: "Falta configurar el dominio compartido de 101.",
};
function message(code: string, action?: string) {
  return (
    codeText[code] || action || "Revisa la configuración y vuelve a intentar."
  );
}
class AdminError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch("/api/101/" + path, {
    credentials: "same-origin",
    ...init,
  });
  if (!response.ok) {
    if (response.status === 401)
      window.dispatchEvent(new Event("session-expired"));
    const body = await response.json().catch(() => ({}));
    throw new AdminError(
      response.status,
      response.status === 401
        ? "Tu sesión terminó. Vuelve a entrar."
        : response.status === 403
          ? "Solo un administrador de 101 puede gestionar negocios."
          : response.status === 422
            ? "Revisa los datos de la solicitud."
            : message(body.detail?.code, body.detail?.next_action),
    );
  }
  return response.json();
}
// Poll only this mounted view. Keep confirmed data during refresh; discard data on key changes.
function useLive<T>(path: string | null, revision = 0) {
  const [state, setState] = useState<{
    key: string | null;
    data?: T;
    error?: string;
  }>({ key: null });
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (!path) {
      setState({ key: null });
      return;
    }
    const abort = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const load = async () => {
      try {
        const data = await request<T>(path, { signal: abort.signal });
        if (!abort.signal.aborted) setState({ key: path, data });
      } catch (e) {
        if (!abort.signal.aborted)
          setState((old) => ({
            key: path,
            data:
              !(e instanceof AdminError && [401, 403].includes(e.status)) &&
              old.key === path
                ? old.data
                : undefined,
            error: (e as Error).message,
          }));
      } finally {
        if (!abort.signal.aborted) timer = setTimeout(load, 5000);
      }
    };
    load();
    return () => {
      abort.abort();
      clearTimeout(timer);
    };
  }, [path, revision, tick]);
  return {
    ...(state.key === path ? state : {}),
    retry: () => setTick((x) => x + 1),
  };
}
function Badge({ value }: { value: string }) {
  return (
    <span
      className={`setup-badge ${value === "ready" ? "is-ready" : value === "suspended" ? "is-suspended" : ""}`}
    >
      {value === "ready" && <Check size={13} />}
      {states[value] || "Pendiente"}
    </span>
  );
}
function siteURL(row: Setup) {
  const host = row.resources.managed_domain?.hostname;
  if (
    !host ||
    row.resources.managed_domain?.status !== "ready" ||
    row.status === "suspended"
  )
    return null;
  return host.endsWith(".localhost") &&
    ["localhost", "127.0.0.1"].includes(location.hostname)
    ? `http://${host}:${location.port}`
    : `https://${host}`;
}
export function OnboardingView({
  csrf,
  actor,
  params,
  navigate,
}: {
  csrf: string;
  actor: string;
  params: URLSearchParams;
  navigate: (changes: Record<string, string | null>, push?: boolean) => void;
}) {
  const [mode, setMode] = useState<"single" | "bulk" | null>(null),
    [revision, refresh] = useState(0);
  const [search, setSearch] = useState(params.get("setup_q") || "");
  const query = params.get("setup_q") || "",
    filter = params.get("setup_state") || "all",
    selected = params.get("setup");
  const offset = Math.max(0, Number(params.get("setup_offset")) || 0);
  const list = useLive<Directory>(
    `admin/businesses?q=${encodeURIComponent(query)}&state=${encodeURIComponent(filter)}&offset=${offset}`,
    revision,
  );
  const detail = useLive<Setup>(
    selected ? `admin/businesses/${encodeURIComponent(selected)}` : null,
    revision,
  );
  useEffect(() => {
    setSearch(query);
  }, [query]);
  useEffect(() => {
    if (search === query) return;
    const timer = setTimeout(
      () => navigate({ setup_q: search.trim(), setup_offset: null }),
      200,
    );
    return () => clearTimeout(timer);
  }, [search, query]);
  useEffect(() => {
    if (selected && matchMedia("(max-width:650px)").matches) {
      requestAnimationFrame(() =>
        document.querySelector<HTMLElement>(".setup-detail-title")?.focus(),
      );
    }
  }, [selected]);
  return (
    <div className="page new-view onboarding">
      <section className="view-heading">
        <div>
          <span className="eyebrow">ADMINISTRACIÓN 101</span>
          <h1>Negocios</h1>
          <p>Crea espacios independientes y sigue su puesta en marcha.</p>
        </div>
        <div className="setup-actions">
          <button className="button secondary" onClick={() => setMode("bulk")}>
            <Layers size={17} />
            Crear varios
          </button>
          <button className="button primary" onClick={() => setMode("single")}>
            <Plus size={17} />
            Crear negocio
          </button>
        </div>
      </section>
      <div className={`setup-layout ${selected ? "with-selection" : ""}`}>
        <section
          className="work-surface setup-directory"
          aria-label="Negocios de 101"
        >
          <div className="section-heading">
            <h2>
              Directorio{" "}
              <span className="number-chip">{list.data?.count ?? "…"}</span>
            </h2>
            <button
              className="icon-button"
              aria-label="Actualizar negocios"
              onClick={list.retry}
            >
              <RefreshCw size={17} />
            </button>
          </div>
          <div className="setup-toolbar">
            <label className="setup-search">
              <Search size={17} />
              <span className="sr-only">Buscar negocios</span>
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Buscar por nombre o enlace"
              />
            </label>
            <label>
              <span className="sr-only">Estado de configuración</span>
              <select
                value={filter}
                onChange={(e) =>
                  navigate({
                    setup_state:
                      e.target.value === "all" ? null : e.target.value,
                    setup_offset: null,
                  })
                }
              >
                <option value="all">Todos los estados</option>
                {["queued", "pending", "ready", "suspended"].map((s) => (
                  <option key={s} value={s}>
                    {states[s]}
                  </option>
                ))}
              </select>
            </label>
          </div>
          {list.error && <Failure message={list.error} retry={list.retry} />}
          {!list.data && !list.error && <Loading />}
          {list.data && (
            <>
              <div className="setup-list">
                {list.data.items.length ? (
                  list.data.items.map((row) => (
                    <button
                      className={`setup-row ${selected === row.business_id ? "selected" : ""}`}
                      key={row.business_id}
                      onClick={() => navigate({ setup: row.business_id }, true)}
                      aria-pressed={selected === row.business_id}
                    >
                      <span className="setup-monogram" aria-hidden="true">
                        {row.configuration.name.slice(0, 1)}
                      </span>
                      <span className="setup-row-name">
                        <strong>{row.configuration.name}</strong>
                        <small>
                          {row.resources.managed_domain?.hostname || row.slug}
                        </small>
                      </span>
                      <Badge value={row.status} />
                      <ChevronRight size={17} />
                    </button>
                  ))
                ) : (
                  <div className="setup-empty">
                    <Layers size={28} />
                    <h3>
                      {query || filter !== "all"
                        ? "Sin coincidencias"
                        : "Tu próximo negocio empieza aquí"}
                    </h3>
                    <p>
                      {query || filter !== "all"
                        ? "Prueba otro nombre o estado."
                        : "Crea el primero y sigue cada paso desde este espacio."}
                    </p>
                  </div>
                )}
              </div>
              <div className="setup-pagination">
                <span>
                  {list.data.count
                    ? `${offset + 1}–${Math.min(offset + list.data.limit, list.data.count)} de ${list.data.count}`
                    : "0 negocios"}
                </span>
                <button
                  className="icon-button"
                  aria-label="Negocios anteriores"
                  disabled={offset === 0}
                  onClick={() =>
                    navigate({
                      setup_offset: String(
                        Math.max(0, offset - list.data!.limit),
                      ),
                    })
                  }
                >
                  <ArrowLeft size={17} />
                </button>
                <button
                  className="icon-button"
                  aria-label="Más negocios"
                  disabled={offset + list.data.limit >= list.data.count}
                  onClick={() =>
                    navigate({
                      setup_offset: String(offset + list.data!.limit),
                    })
                  }
                >
                  <ArrowRight size={17} />
                </button>
              </div>
            </>
          )}
        </section>
        {selected && (
          <aside
            className="work-surface setup-detail"
            aria-label="Configuración del negocio"
          >
            <button
              className="setup-back button secondary"
              onClick={() => navigate({ setup: null })}
            >
              <ArrowLeft size={16} />
              Volver al directorio
            </button>
            <div className="section-heading">
              <h2 className="setup-detail-title" tabIndex={-1}>
                Configuración
              </h2>
              <button
                className="icon-button"
                aria-label="Cerrar configuración"
                onClick={() => navigate({ setup: null })}
              >
                <X size={18} />
              </button>
            </div>
            {detail.error && (
              <Failure message={detail.error} retry={detail.retry} />
            )}
            {detail.data ? (
              <SetupDetail
                key={selected}
                row={detail.data}
                csrf={csrf}
                changed={() => refresh((x) => x + 1)}
              />
            ) : (
              !detail.error && <Loading />
            )}
          </aside>
        )}
      </div>
      <Dialog.Root
        open={mode !== null}
        onOpenChange={(open) => {
          if (!open) setMode(null);
        }}
      >
        <Dialog.Portal>
          <Dialog.Backdrop className="backdrop" />
          <Dialog.Popup className="setup-dialog">
            <Dialog.Title>
              {mode === "bulk" ? "Crear varios negocios" : "Crear negocio"}
            </Dialog.Title>
            <Dialog.Description>
              Cada negocio tendrá su propio sitio, propietario y analítica.
            </Dialog.Description>
            <Dialog.Close
              className="icon-button setup-dialog-close"
              aria-label="Cerrar creación"
            >
              <X size={20} />
            </Dialog.Close>
            {mode && (
              <CreateForm
                key={mode + actor}
                mode={mode}
                actor={actor}
                csrf={csrf}
                completed={(id) => {
                  refresh((x) => x + 1);
                  navigate({ setup: id }, true);
                }}
                close={() => setMode(null)}
              />
            )}
          </Dialog.Popup>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
function SetupDetail({
  row,
  csrf,
  changed,
}: {
  row: Setup;
  csrf: string;
  changed: () => void;
}) {
  const [busy, setBusy] = useState(""),
    [error, setError] = useState("");
  const url = siteURL(row);
  async function act(action: string) {
    setBusy(action);
    setError("");
    try {
      await request(`businesses/${row.business_id}/${action}`, {
        method: "POST",
        headers: { "X-101-CSRF": csrf },
      });
      changed();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  return (
    <div className="setup-detail-body">
      <h3>{row.configuration.name}</h3>
      <p className="setup-slug">{row.slug}</p>
      <Badge value={row.status} />
      {url && (
        <a
          className="button secondary setup-visit"
          href={url}
          target="_blank"
          rel="noreferrer"
        >
          Abrir sitio <ExternalLink size={15} />
        </a>
      )}
      <dl className="setup-facts">
        <div>
          <dt>Moneda</dt>
          <dd>{row.configuration.currency}</dd>
        </div>
        <div>
          <dt>Zona horaria</dt>
          <dd>{row.configuration.timezone}</dd>
        </div>
        <div>
          <dt>Intentos</dt>
          <dd>{row.attempts}</dd>
        </div>
      </dl>
      <div className="setup-stages">
        {Object.entries(stages)
          .filter(
            ([key]) =>
              key !== "custom_domain" || row.configuration.custom_hostname,
          )
          .map(([key, title]) => {
            const resource = row.resources[key];
            return (
              <section key={key}>
                <div>
                  <h4>{title}</h4>
                  <Badge value={resource?.status || "queued"} />
                </div>
                {resource?.hostname && <p>{resource.hostname}</p>}
                {resource?.domain && <p>{resource.domain}</p>}
                {resource?.status !== "ready" && resource?.next_action && (
                  <p className="setup-next">
                    {message(
                      resource.code || resource.error || "",
                      resource.next_action,
                    )}
                  </p>
                )}
                {resource?.dns && (
                  <dl className="setup-dns">
                    <dt>Registro DNS solicitado</dt>
                    <dd>
                      <code>
                        {resource.dns.type} {resource.dns.name} →{" "}
                        {resource.dns.content}
                      </code>
                    </dd>
                  </dl>
                )}
                {resource?.ownership_verification && (
                  <p className="setup-next">
                    Verificación:{" "}
                    <code>
                      {resource.ownership_verification.type}{" "}
                      {resource.ownership_verification.name}{" "}
                      {resource.ownership_verification.value}
                    </code>
                  </p>
                )}
                {resource?.validation_records?.map((record, i) => (
                  <p className="setup-next" key={i}>
                    <code>
                      {record.txt_name} {record.txt_value}
                    </code>
                  </p>
                ))}
              </section>
            );
          })}
      </div>
      {row.next_attempt_at && row.status === "pending" && (
        <p className="caption">
          Revisión automática prevista:{" "}
          {new Date(row.next_attempt_at).toLocaleString("es-CO")}. Los cambios
          de DNS pueden seguir pendientes.
        </p>
      )}
      {error && (
        <p role="alert" className="form-error">
          {error}
        </p>
      )}
      <div className="setup-actions">
        <button
          className="button primary"
          disabled={!!busy || row.status === "suspended"}
          onClick={() => act("reconcile")}
        >
          <RefreshCw size={16} />
          {busy === "reconcile" ? "Revisando…" : "Reintentar configuración"}
        </button>
        <button
          className="button secondary"
          disabled={!!busy}
          onClick={() => act(row.status === "suspended" ? "resume" : "suspend")}
        >
          {busy && busy !== "reconcile"
            ? "Guardando…"
            : row.status === "suspended"
              ? "Reanudar"
              : "Suspender"}
        </button>
      </div>
      <p className="caption">
        Suspender desactiva el acceso por dominio. Los registros y recursos se
        conservan.
      </p>
      <details className="setup-history">
        <summary>Historial de configuración</summary>
        <ol>
          {row.history?.map((event, i) => (
            <li key={i}>
              <strong>
                {stages[event.action] ||
                  (
                    {
                      requested: "Solicitud creada",
                      suspend: "Suspendido",
                      resume: "Reanudado",
                    } as Record<string, string>
                  )[event.action] ||
                  event.action}
              </strong>
              <span>{date(event.at)}</span>
            </li>
          ))}
        </ol>
      </details>
    </div>
  );
}
function readLedger(key: string): Ledger | null {
  try {
    const data = JSON.parse(sessionStorage.getItem(key) || "null");
    return Array.isArray(data?.requests) && data.requests.length > 0
      ? data
      : null;
  } catch {
    return null;
  }
}
function CreateForm({
  mode,
  actor,
  csrf,
  completed,
  close,
}: {
  mode: "single" | "bulk";
  actor: string;
  csrf: string;
  completed: (id: string) => void;
  close: () => void;
}) {
  const key = `101:onboarding:${actor}:${mode}`;
  const [ledger, setLedger] = useState<Ledger | null>(() => readLedger(key));
  const [owner, setOwner] = useState(""),
    [ownerSearch, setOwnerSearch] = useState(""),
    [name, setName] = useState(""),
    [slug, setSlug] = useState(""),
    [domain, setDomain] = useState(""),
    [csv, setCSV] = useState(""),
    [currency, setCurrency] = useState("COP"),
    [zone, setZone] = useState("America/Bogota");
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const mounted = useRef(true);
  useEffect(
    () => () => {
      mounted.current = false;
    },
    [],
  );
  const owners = useLive<Owner[]>(
    ledger ? null : `admin/owners?q=${encodeURIComponent(ownerSearch)}`,
  );
  const chosen = owners.data?.find((item) => item.id === owner);
  const ownerLabel = useRef<Owner | null>(null);
  if (chosen) ownerLabel.current = chosen;
  function save(next: Ledger | null) {
    // Persist before submitting, so a lost response or reload retains exact request keys/payloads.
    if (next) sessionStorage.setItem(key, JSON.stringify(next));
    else sessionStorage.removeItem(key);
    setLedger(next);
  }
  async function submit() {
    setError("");
    let pending = ledger;
    try {
      if (!pending) {
        if (!owner)
          throw Error("Selecciona una cuenta activa para el propietario.");
        const drafts = parseBusinesses(
          mode === "bulk" ? csv : [name, slug, domain].map(csvCell).join(","),
        );
        pending = {
          requests: drafts.map((draft) => ({
            ...draft,
            request_key: crypto.randomUUID(),
            owner_id: owner,
            currency,
            timezone: zone,
          })),
        };
        save(pending);
      }
      setBusy(true);
      const outcomes = await request<Outcome[]>("businesses/bulk", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-101-CSRF": csrf },
        body: JSON.stringify(pending.requests),
      });
      const next = { ...pending, outcomes };
      sessionStorage.setItem(key, JSON.stringify(next));
      if (mounted.current) {
        setLedger(next);
        const first = outcomes.find((row) => row.result)?.result;
        if (first) completed(first.business_id);
      }
    } catch (e) {
      if (mounted.current)
        setError(
          e instanceof TypeError
            ? "No se confirmó la respuesta. Reintenta la misma solicitud."
            : (e as Error).message,
        );
    } finally {
      if (mounted.current) setBusy(false);
    }
  }
  const allCreated =
    ledger?.outcomes?.length === ledger?.requests.length &&
    ledger?.outcomes?.every((row) => !!row.result);
  return (
    <form
      className="setup-form"
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      {ledger ? (
        <>
          <div className="setup-retained">
            <strong>
              Solicitud conservada · {ledger.requests.length}{" "}
              {ledger.requests.length === 1 ? "negocio" : "negocios"}
            </strong>
            <p>
              Reintentar usa los mismos datos y evita crear duplicados. Los
              negocios ya creados se conservan.
            </p>
          </div>
          <ul className="setup-outcomes">
            {ledger.requests.map((command, i) => {
              const outcome = ledger.outcomes?.[i];
              return (
                <li key={command.request_key}>
                  <span>
                    <strong>{command.name}</strong>
                    <small>{command.slug}</small>
                  </span>
                  {outcome?.result ? (
                    <button
                      type="button"
                      className="back-link"
                      onClick={() => {
                        completed(outcome.result!.business_id);
                        close();
                      }}
                    >
                      Ver configuración <ArrowRight size={14} />
                    </button>
                  ) : (
                    <span>
                      {outcome?.error
                        ? message(outcome.error, outcome.next_action)
                        : "Sin confirmar"}
                    </span>
                  )}
                </li>
              );
            })}
          </ul>
        </>
      ) : (
        <>
          <label>
            Buscar propietario
            <input
              value={ownerSearch}
              onChange={(e) => setOwnerSearch(e.target.value)}
              placeholder="Nombre de usuario"
            />
          </label>
          <label>
            Propietario
            <select
              required
              value={owner}
              onChange={(e) => setOwner(e.target.value)}
            >
              <option value="">Selecciona una cuenta activa</option>
              {owner && !chosen && ownerLabel.current && (
                <option value={owner}>{ownerLabel.current.username}</option>
              )}
              {owners.data?.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.username}
                </option>
              ))}
            </select>
          </label>
          {owners.error && (
            <p role="alert" className="form-error">
              {owners.error}
            </p>
          )}
          {mode === "single" ? (
            <>
              <label>
                Nombre del negocio
                <input
                  required
                  maxLength={200}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </label>
              <label>
                Enlace 101
                <input
                  required
                  minLength={2}
                  maxLength={50}
                  pattern="[a-z0-9]+(-[a-z0-9]+)*"
                  value={slug}
                  onChange={(e) => setSlug(e.target.value)}
                  placeholder="mi-negocio"
                />
                <small>Único en 101. Usa minúsculas, números y guiones.</small>
              </label>
              <label>
                Dominio propio <span className="caption">opcional</span>
                <input
                  value={domain}
                  onChange={(e) => setDomain(e.target.value)}
                  placeholder="tienda.ejemplo.com"
                />
                <small>
                  Si requiere DNS o verificación, lo verás como pendiente.
                </small>
              </label>
            </>
          ) : (
            <label>
              Negocios, uno por línea
              <textarea
                required
                rows={7}
                value={csv}
                onChange={(e) => setCSV(e.target.value)}
                placeholder={
                  "nombre,enlace,dominio\nTienda Uno,tienda-uno,\nTienda Dos,tienda-dos,tienda.ejemplo.com"
                }
              />
              <small>
                CSV: nombre, enlace, dominio opcional. Máximo 100; todos se
                asignan al propietario elegido.
              </small>
            </label>
          )}
          <div className="setup-form-pair">
            <label>
              Moneda
              <input
                required
                minLength={3}
                maxLength={3}
                pattern="[A-Z]{3}"
                value={currency}
                onChange={(e) => setCurrency(e.target.value.toUpperCase())}
              />
            </label>
            <label>
              Zona horaria
              <input
                required
                value={zone}
                onChange={(e) => setZone(e.target.value)}
              />
            </label>
          </div>
        </>
      )}
      {error && (
        <p role="alert" className="form-error">
          {error}
        </p>
      )}
      <div className="setup-form-actions">
        {ledger && (
          <button
            className="button secondary"
            type="button"
            disabled={busy}
            onClick={() => {
              try {
                save(null);
                setError("");
              } catch {
                setError("El navegador no permite guardar solicitudes.");
              }
            }}
          >
            {allCreated ? "Nueva solicitud" : "Descartar solicitud local"}
          </button>
        )}
        <button
          className="button primary"
          type={allCreated ? "button" : "submit"}
          disabled={busy}
          onClick={
            allCreated
              ? () => {
                  save(null);
                  close();
                }
              : undefined
          }
        >
          {busy
            ? "Creando…"
            : allCreated
              ? "Finalizar"
              : ledger
                ? "Reintentar misma solicitud"
                : mode === "bulk"
                  ? "Crear negocios"
                  : "Crear negocio"}
          {!busy && <ArrowRight size={16} />}
        </button>
      </div>
    </form>
  );
}
