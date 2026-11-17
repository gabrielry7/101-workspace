import { useEffect, useRef, useState } from "react";
import { endpoint } from "./ui";
type Job = {
  title: string;
  id: string;
  kind: string;
  state: string;
  reason: string | null;
  pack_id: string | null;
  result_revision: string | null;
  attempt_count: number;
  attempts: any[];
  cost: any;
  effort: any[];
};
const states: Record<string, string> = {
  queued: "En cola",
  running: "Preparando",
  succeeded: "Listo",
  uncertain: "Resultado del modelo sin confirmar",
  failed: "No se pudo terminar",
  needs_input: "Necesita revisión",
  superseded: "Los datos cambiaron",
};
const reasons: Record<string, string> = {
  local_processing_failed:
    "No pudimos procesar el archivo. Puedes reintentar este paso.",
  source_deleted_or_revoked:
    "La foto se retiró. Selecciona otra para continuar.",
  asset_expired: "Revisa el permiso de la foto o elige otra.",
  reference_only_asset: "Este material solo está autorizado como referencia.",
  fact_expired: "Actualiza los datos vencidos antes de preparar otra versión.",
  job_inputs_changed:
    "Cambió la información del trabajo. Prepara una nueva versión.",
  revision_conflict: "Ya existe una versión más reciente.",
  job_authorization_revoked: "Cambió el acceso de quien pidió este trabajo.",
  model_outcome_unknown:
    "No se repetirá automáticamente una solicitud con resultado incierto.",
  proposal_response_needs_review:
    "Se recibió una respuesta que necesita revisión. No se cobrará otra solicitud automáticamente.",
  proposal_context_changed:
    "Cambió la información del negocio. Prepara otra propuesta con los datos actuales.",
  attempt_limit:
    "El trabajo alcanzó el límite de intentos. Contacta al equipo de 101.",
};
export function ProductionJobs({
  business,
  csrf,
  asset,
  activeJob,
  onState,
  onComplete,
}: {
  business: string;
  csrf: string;
  asset: string;
  activeJob: string | null;
  onState: (v: boolean) => void;
  onComplete: (id: string) => Promise<void>;
}) {
  const [effortSeconds, setEffortSeconds] = useState(""),
    [effortRole, setEffortRole] = useState("owner"),
    [effortKey, setEffortKey] = useState(() => crypto.randomUUID());
  const [jobs, setJobs] = useState<Job[]>([]),
    [error, setError] = useState(""),
    [refresh, setRefresh] = useState(0),
    [expanded, setExpanded] = useState<string | null>(null);
  const callback = useRef(onComplete),
    stateCallback = useRef(onState),
    handled = useRef(new Set<string>());
  callback.current = onComplete;
  stateCallback.current = onState;
  const root = endpoint(business) + "/social/jobs";
  useEffect(() => {
    let stopped = false,
      timer: ReturnType<typeof setTimeout>;
    const controller = new AbortController();
    async function poll() {
      try {
        const r = await fetch(root, { signal: controller.signal });
        const data = await r.json();
        if (!r.ok)
          throw new Error(
            typeof data.detail === "string"
              ? data.detail
              : "No se pudo cargar el trabajo.",
          );
        if (stopped) return;
        setJobs(data.jobs);
        setError("");
        const selected = data.jobs.find((j: Job) => j.id === activeJob),
          pending = data.jobs.some((j: Job) =>
            ["queued", "running"].includes(j.state),
          );
        stateCallback.current(
          !!selected && ["queued", "running"].includes(selected.state),
        );
        if (
          selected?.state === "succeeded" &&
          selected.pack_id &&
          !handled.current.has(selected.id)
        ) {
          await callback.current(selected.pack_id);
          handled.current.add(selected.id);
        }
        if (pending)
          timer = setTimeout(() => {
            if (document.visibilityState === "visible") void poll();
          }, 700);
      } catch (e) {
        if (!stopped) {
          setError(String(e));
          timer = setTimeout(() => void poll(), 3000);
        }
      }
    }
    const visible = () => {
      if (document.visibilityState === "visible") {
        clearTimeout(timer);
        void poll();
      }
    };
    document.addEventListener("visibilitychange", visible);
    void poll();
    return () => {
      stopped = true;
      controller.abort();
      clearTimeout(timer);
      document.removeEventListener("visibilitychange", visible);
    };
  }, [root, activeJob, refresh]);
  async function retry(id: string) {
    try {
      const r = await fetch(root + "/" + id + "/retry", {
        method: "POST",
        headers: { "X-101-CSRF": csrf },
      });
      const body = await r.json();
      if (!r.ok) throw new Error(reasons[body.detail] || body.detail);
      setRefresh((v) => v + 1);
    } catch (e) {
      setError(String(e));
    }
  }
  async function inspect() {
    try {
      const r = await fetch(root, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-101-CSRF": csrf },
        body: JSON.stringify({ kind: "inspect_asset", asset_id: asset }),
      });
      const body = await r.json();
      if (!r.ok) throw new Error(reasons[body.detail] || body.detail);
      setRefresh((v) => v + 1);
    } catch (e) {
      setError(String(e));
    }
  }
  async function recordEffort(id: string) {
    try {
      const r = await fetch(root + "/" + id + "/effort", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-101-CSRF": csrf },
        body: JSON.stringify({
          request_id: effortKey,
          role: effortRole,
          seconds: Number(effortSeconds),
        }),
      });
      const b = await r.json();
      if (!r.ok) throw new Error(b.detail);
      setEffortKey(crypto.randomUUID());
      setEffortSeconds("");
      setRefresh((v) => v + 1);
    } catch (e) {
      setError(String(e));
    }
  }
  if (!jobs.length && !error && !asset) return null;
  return (
    <section className="production-jobs" aria-label="Preparación de contenido">
      <h2>Preparación de contenido</h2>
      {asset && (
        <button
          type="button"
          className="button secondary"
          onClick={() => void inspect()}
        >
          Revisar el archivo seleccionado
        </button>
      )}
      {error && <p role="alert">{error}</p>}
      {jobs.slice(0, 10).map((j) => (
        <article key={j.id} className="production-job">
          <div>
            <strong>
              {j.kind === "photo_render"
                ? "Preparar fotografía y texto"
                : j.kind === "video_render"
                  ? "Preparar montaje de vídeo"
                  : j.kind === "subtitle_manual"
                    ? "Guardar subtítulos manuales"
                    : j.kind === "speech_transcribe"
                      ? "Transcripción de la respuesta"
                      : j.kind === "proposal_generate"
                        ? "Preparar propuesta"
                        : "Revisar archivo"}
            </strong>
            <p>{j.title}</p>
            <p role="status">
              {states[j.state] || j.state} · {j.attempt_count}{" "}
              {j.attempt_count === 1 ? "intento" : "intentos"}
            </p>
            {j.reason && (
              <p>
                {reasons[j.reason] ||
                  "Revisa los datos y permisos antes de continuar."}
              </p>
            )}
          </div>
          <div className="production-actions">
            {j.state === "succeeded" && j.pack_id && (
              <button
                type="button"
                className="button secondary"
                onClick={() => void callback.current(j.pack_id!)}
              >
                Abrir resultado
              </button>
            )}
            {j.state === "failed" && j.kind !== "proposal_generate" && (
              <button
                type="button"
                className="button secondary"
                onClick={() => void retry(j.id)}
              >
                Reintentar este paso
              </button>
            )}
            <button
              type="button"
              className="button secondary"
              aria-expanded={expanded === j.id}
              onClick={() => setExpanded(expanded === j.id ? null : j.id)}
            >
              Ver actividad
            </button>
          </div>
          {expanded === j.id && (
            <div className="production-activity">
              <p>
                Costo externo estimado:{" "}
                {j.cost.provider_microusd == null
                  ? "sin confirmar"
                  : `${(j.cost.provider_microusd / 1_000_000).toFixed(6)} USD`}
                . Costo de procesamiento y almacenamiento: sin calcular.
              </p>
              {!j.attempts.length && (
                <p>
                  Esperando un trabajador disponible. Puedes volver más tarde.
                </p>
              )}
              {j.attempts.map((a) => (
                <p key={a.number}>
                  Intento {a.number} ·{" "}
                  {a.state === "interrupted"
                    ? "Interrumpido; se recuperará"
                    : states[a.state] || a.state}
                  {a.usage.checkpoint_reused
                    ? " · reutilizó el archivo preparado"
                    : ""}
                  {a.usage.elapsed_ms != null
                    ? ` · ${a.usage.elapsed_ms} ms`
                    : ""}
                </p>
              ))}
              {j.kind === "inspect_asset" && j.state === "succeeded" && (
                <img
                  className="inspection-preview"
                  src={root + "/" + j.id + "/preview"}
                  alt="Copia reducida de la fotografía para revisión"
                />
              )}
              <div className="effort-fields">
                <label>
                  Tiempo dedicado (segundos)
                  <input
                    type="number"
                    min={1}
                    max={86400}
                    value={effortSeconds}
                    onChange={(e) => setEffortSeconds(e.target.value)}
                  />
                </label>
                <label>
                  Quién dedicó ese tiempo
                  <select
                    value={effortRole}
                    onChange={(e) => setEffortRole(e.target.value)}
                  >
                    <option value="owner">Negocio</option>
                    <option value="reviewer">Revisión de 101</option>
                  </select>
                </label>
                <button
                  type="button"
                  className="button secondary"
                  disabled={
                    !effortSeconds ||
                    Number(effortSeconds) < 1 ||
                    Number(effortSeconds) > 86400
                  }
                  onClick={() => void recordEffort(j.id)}
                >
                  Registrar tiempo
                </button>
              </div>
              {j.effort.map((e, i) => (
                <p key={i}>
                  {e.role === "owner"
                    ? "Tiempo del negocio"
                    : "Tiempo de revisión"}
                  : {e.seconds} s · registrado manualmente
                </p>
              ))}
            </div>
          )}
        </article>
      ))}
    </section>
  );
}
