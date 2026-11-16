import { useEffect, useRef, useState } from "react";
import { endpoint } from "./ui";
const labels: Record<string, string> = {
  technical: "Calidad técnica",
  factual: "Exactitud de los datos",
  craft: "Composición y claridad",
  brand_fit: "Estilo del negocio",
  purpose: "Cumple el propósito",
};
const verdicts: Record<string, string> = {
  no_concern_detected: "Sin problema detectado dentro de esta comprobación",
  needs_changes: "Necesita cambios",
  uncertain: "Necesita revisión humana",
};
const messages: Record<string, string> = {
  creative_review_revision_changed:
    "Cambió la versión. Comprueba la pieza actual.",
  creative_review_context_changed:
    "Cambió la información de esta pieza. Prepara otra comprobación.",
  creative_review_model_not_enabled:
    "La revisión visual con modelo no está habilitada para este negocio.",
  creative_review_media_permission_required:
    "Confirma el permiso para procesar esta imagen con el proveedor configurado.",
  creative_review_video_needs_temporal_review:
    "El vídeo necesita una revisión completa de imagen y sonido. Una portada no basta.",
  model_outcome_unknown:
    "La respuesta del modelo quedó sin confirmar. No repetiremos la llamada automáticamente.",
  creative_review_response_needs_review:
    "Llegó una respuesta que necesita revisión. No se volverá a solicitar automáticamente.",
  research_source_unavailable:
    "Una fuente se retiró o venció. Revisa la investigación antes de continuar.",
};

export function SocialAutoReview({
  business,
  csrf,
  pack,
  dirty,
}: {
  business: string;
  csrf: string;
  pack: any;
  dirty: boolean;
}) {
  const [data, setData] = useState<any>(null),
    [mode, setMode] = useState("rules"),
    [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [selected, setSelected] = useState("");
  const [feedbackChoice, setFeedbackChoice] = useState(""),
    [feedbackKind, setFeedbackKind] = useState("model_misread"),
    [feedbackReason, setFeedbackReason] = useState("");
  const requestId = useRef(crypto.randomUUID()),
    feedbackId = useRef(crypto.randomUUID());
  const root = endpoint(business) + "/social";
  const active =
    data?.reviews.find((r: any) => r.id === selected) ||
    data?.reviews.find((r: any) => !r.stale && r.digest === pack.digest);
  async function request(path: string, method = "GET", body?: unknown) {
    const r = await fetch(root + path, {
      method,
      headers: { "Content-Type": "application/json", "X-101-CSRF": csrf },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const d = await r.json();
    if (!r.ok)
      throw new Error(
        messages[d.detail] ||
          "No se pudo comprobar esta pieza. Revisa sus datos, permisos y versión.",
      );
    return d;
  }
  async function run(fn: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(String(e).replace(/^Error: /, ""));
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    setMode("rules");
    setConsent(false);
    setSelected("");
    setFeedbackChoice("");
    setFeedbackReason("");
    requestId.current = crypto.randomUUID();
  }, [root, pack.id, pack.digest]);
  useEffect(() => {
    let stopped = false,
      timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const d = await request("/packs/" + pack.id + "/automated-reviews");
        if (stopped) return;
        setData(d);
        if (d.reviews.some((r: any) => ["queued", "running"].includes(r.state)))
          timer = setTimeout(() => void poll(), 900);
      } catch (e) {
        if (!stopped) setError(String(e));
      }
    }
    void poll();
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [root, pack.id, pack.digest, pack.stale, selected]);
  async function check() {
    const r = await request(
      "/packs/" + pack.id + "/automated-reviews",
      "POST",
      {
        request_id: requestId.current,
        digest: pack.digest,
        mode,
        media_processing_confirmed: consent,
      },
    );
    setSelected(r.id);
    setFeedbackChoice("");
    setFeedbackReason("");
    requestId.current = crypto.randomUUID();
    setData(await request("/packs/" + pack.id + "/automated-reviews"));
  }
  return (
    <section
      className="social-auto-review"
      aria-label="Comprobaciones de preparación"
    >
      <h3>Comprobaciones de preparación</h3>
      <p>
        Las comprobaciones automáticas ayudan a detectar problemas. La revisión
        por criterios y la aprobación final siguen siendo tuyas.
      </p>
      {error && <p role="alert">{error}</p>}
      <fieldset
        disabled={
          busy ||
          dirty ||
          pack.stale ||
          active?.state === "running" ||
          active?.state === "queued"
        }
      >
        <label>
          Tipo de comprobación
          <select
            aria-label="Tipo de comprobación"
            value={mode}
            onChange={(e) => {
              setMode(e.target.value);
              setConsent(false);
              requestId.current = crypto.randomUUID();
            }}
          >
            <option value="rules">Comprobaciones locales · sin modelo</option>
            {data?.model_enabled && !pack.document.video_output && (
              <option value="model">
                Revisión visual con el modelo configurado
              </option>
            )}
          </select>
        </label>
        {mode === "model" && (
          <label className="social-check">
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
            />
            Podemos enviar esta imagen preparada y sus datos al proveedor de
            análisis configurado, dentro del presupuesto autorizado.
          </label>
        )}
        <button
          type="button"
          className="button secondary"
          disabled={mode === "model" && !consent}
          onClick={() => void run(check)}
        >
          Comprobar esta versión
        </button>
      </fieldset>
      {!data?.model_enabled && (
        <p>
          La revisión visual con modelo aún no está habilitada. Las reglas
          locales no juzgan el gusto ni predicen resultados.
        </p>
      )}
      {pack.document.video_output && (
        <p>
          Para el vídeo, revisa toda la secuencia y el sonido. La comprobación
          local no evalúa su narrativa.
        </p>
      )}
      {active && (
        <div className="auto-review-result">
          {active.stale || pack.stale ? (
            <p role="status">
              Esta comprobación corresponde a una versión o fuentes que
              cambiaron.
            </p>
          ) : (
            <>
              <p role="status">
                {active.state === "queued"
                  ? "Comprobación en cola"
                  : active.state === "running"
                    ? "Comprobando"
                    : active.output
                      ? active.mode === "model"
                        ? "Sugerencias del modelo · sin validación de calidad todavía"
                        : "Comprobaciones locales terminadas"
                      : "Necesita revisión antes de continuar"}
              </p>
              {active.reason && (
                <p>
                  {messages[active.reason] ||
                    "Revisa los datos o permisos de esta pieza. No repetiremos una solicitud de modelo automáticamente."}
                </p>
              )}
              {active.output?.criteria.map((c: any) => (
                <article key={c.criterion}>
                  <h4>{labels[c.criterion]}</h4>
                  <p>{verdicts[c.verdict]}</p>
                  <p>{c.reason}</p>
                  <p>
                    <strong>Siguiente paso:</strong> {c.suggestion}
                  </p>
                  {c.evidence?.length > 0 && (
                    <details>
                      <summary>Ver evidencia de esta sugerencia</summary>
                      {c.evidence.map((e: any, i: number) => (
                        <p key={i}>
                          {e.surface === "image"
                            ? `Región de la imagen: x ${e.region.x}, y ${e.region.y}, ancho ${e.region.width}, alto ${e.region.height}.`
                            : e.quote}
                          {e.fact_id ? " · dato " + e.fact_id : ""}
                        </p>
                      ))}
                      <p>
                        Confianza declarada por el modelo: {c.confidence}. No
                        está calibrada.
                      </p>
                    </details>
                  )}
                </article>
              ))}
              {active.output && (
                <p>
                  Resultado comercial y posición en búsquedas: sin medir. No hay
                  una puntuación global de calidad.
                </p>
              )}
            </>
          )}
          <details className="auto-review-activity">
            <summary>Actividad y coste de la comprobación</summary>
            <p>
              {active.activity.attempt_count} intentos · coste externo{" "}
              {active.activity.cost.provider_microusd === null
                ? "sin confirmar"
                : (active.activity.cost.provider_microusd / 1000000).toFixed(
                    6,
                  ) + " USD"}
              . Cómputo y almacenamiento: sin calcular.
            </p>
            <p>Esta comprobación no publica ni aprueba contenido.</p>
          </details>
          {active.output && !active.stale && (
            <details className="auto-review-feedback">
              <summary>¿Fue útil esta comprobación?</summary>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  void run(async () => {
                    await request(
                      "/automated-reviews/" + active.id + "/feedback",
                      "POST",
                      {
                        request_id: feedbackId.current,
                        choice: feedbackChoice,
                        kind: feedbackKind,
                        reason: feedbackReason,
                      },
                    );
                    feedbackId.current = crypto.randomUUID();
                    setFeedbackReason("");
                    setFeedbackChoice("");
                    setData(
                      await request("/packs/" + pack.id + "/automated-reviews"),
                    );
                  });
                }}
              >
                <fieldset disabled={busy || dirty}>
                  <label>
                    Tu evaluación
                    <select
                      aria-label="Tu evaluación de la comprobación"
                      required
                      value={feedbackChoice}
                      onChange={(e) => setFeedbackChoice(e.target.value)}
                    >
                      <option value="">Elegir</option>
                      <option value="helpful">Útil</option>
                      <option value="not_helpful">Poco útil</option>
                      <option value="disagree">No estoy de acuerdo</option>
                      <option value="insufficient_context">
                        Falta contexto
                      </option>
                    </select>
                  </label>
                  <label>
                    Tipo de corrección
                    <select
                      aria-label="Tipo de corrección de la comprobación"
                      value={feedbackKind}
                      onChange={(e) => setFeedbackKind(e.target.value)}
                    >
                      <option value="model_misread">
                        Interpretó mal la pieza
                      </option>
                      <option value="factual_correction">
                        Corrección de un dato
                      </option>
                      <option value="brand_preference">
                        Preferencia del negocio
                      </option>
                      <option value="strategy">Cambio de propósito</option>
                      <option value="technical">Problema técnico</option>
                    </select>
                  </label>
                  <label>
                    Por qué
                    <input
                      required
                      maxLength={1000}
                      value={feedbackReason}
                      onChange={(e) => setFeedbackReason(e.target.value)}
                    />
                  </label>
                  <button className="button secondary">
                    Guardar evaluación
                  </button>
                </fieldset>
              </form>
              <p>
                No usaremos una corrección de precio como preferencia de estilo
                ni entrenaremos un modelo compartido por guardar esta
                evaluación.
              </p>
              {active.feedback.map((f: any) => (
                <p key={f.id}>
                  {
                    (
                      {
                        helpful: "Útil",
                        not_helpful: "Poco útil",
                        disagree: "No estoy de acuerdo",
                        insufficient_context: "Falta contexto",
                      } as any
                    )[f.request.choice]
                  }
                  : {f.request.reason} ·{" "}
                  {
                    (
                      {
                        factual_correction: "Corrección de un dato",
                        brand_preference: "Preferencia del negocio",
                        strategy: "Cambio de propósito",
                        technical: "Problema técnico",
                        model_misread: "Interpretó mal la pieza",
                      } as any
                    )[f.request.kind]
                  }
                </p>
              ))}
            </details>
          )}
        </div>
      )}
    </section>
  );
}
