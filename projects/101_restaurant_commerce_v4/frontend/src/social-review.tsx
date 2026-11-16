import { useEffect, useState } from "react";
import { endpoint } from "./ui";
import { designError } from "./social-design";
const labels: Record<string, string> = {
  technical: "Calidad técnica",
  factual: "Exactitud de los datos",
  craft: "Composición y claridad",
  brand_fit: "Estilo del negocio",
  purpose: "Cumple el propósito",
};
const descriptions: Record<string, string> = {
  technical:
    "Imagen legible, sin recortes incorrectos ni errores de exportación.",
  factual:
    "El texto y la fotografía describen lo que realmente ofrece el negocio.",
  craft: "La imagen, la jerarquía y el texto funcionan juntos.",
  brand_fit:
    "La presentación y la voz coinciden con las referencias del negocio.",
  purpose: "Responde la pregunta y deja claro el siguiente paso adecuado.",
};
const statuses: Record<string, string> = {
  ready_for_review: "Por revisar",
  changes_requested: "Cambios pedidos",
  rejected: "Descartado",
  ready_to_approve: "Listo para aprobar",
  approved: "Aprobado",
  needs_input: "Datos o material pendientes",
};
const choices: Record<string, string> = {
  a: "A",
  b: "B",
  tie: "Empate",
  both_unacceptable: "Ninguna sirve",
  insufficient_context: "Falta contexto",
};
const tagLabels: Record<string, string> = {
  crowded_type: "Demasiado texto",
  weak_hierarchy: "Jerarquía débil",
  awkward_crop: "Encuadre incómodo",
  unnatural_color: "Color artificial",
  generic_copy: "Texto genérico",
  unclear_action: "Siguiente paso poco claro",
  brand_mismatch: "No encaja con el negocio",
  clear_message: "Mensaje claro",
  balanced_layout: "Composición equilibrada",
  natural_appearance: "Apariencia natural",
  useful_explanation: "Explicación útil",
  other: "Otro motivo",
};
function useRequest(business: string, csrf: string) {
  return async (path: string, method = "GET", body?: unknown) => {
    const r = await fetch(endpoint(business) + "/social" + path, {
      method,
      headers: { "Content-Type": "application/json", "X-101-CSRF": csrf },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const d = await r.json();
    if (!r.ok) throw new Error(designError(d.detail));
    return d;
  };
}
export function SocialReviewQueue({
  business,
  csrf,
  refreshKey,
  onOpen,
}: {
  business: string;
  csrf: string;
  refreshKey: string;
  onOpen: (id: string) => void;
}) {
  const request = useRequest(business, csrf),
    [items, setItems] = useState<any[]>([]),
    [cursor, setCursor] = useState<string | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [filter, setFilter] = useState("pending");
  const visible = items.filter(
    (p) =>
      filter === "all" ||
      (filter === "pending" ? p.status !== "approved" : p.status === filter),
  );
  async function load(next = false) {
    setBusy(true);
    try {
      const d = await request(
        "/review-queue" +
          (next && cursor ? "?cursor=" + encodeURIComponent(cursor) : ""),
      );
      setItems((old) => (next ? [...old, ...d.items] : d.items));
      setCursor(d.next_cursor);
      setError("");
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    void load();
  }, [business, refreshKey]);
  return (
    <section className="production-jobs review-queue">
      <h2>Publicaciones por revisar</h2>
      <p>
        Abre un trabajo para revisar su versión actual y los cambios pendientes.
      </p>
      <label className="review-queue-filter">
        Mostrar trabajos
        <select
          aria-label="Mostrar trabajos"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        >
          <option value="pending">Pendientes</option>
          <option value="all">Todos</option>
          <option value="changes_requested">Cambios pedidos</option>
          <option value="approved">Aprobados</option>
        </select>
      </label>
      {error && <p role="alert">{error}</p>}
      {!visible.length && !busy && (
        <p>
          {items.length
            ? "No hay trabajos de este estado en esta página."
            : "No hay trabajos guardados todavía."}
        </p>
      )}
      <div className="review-queue-items">
        {visible.map((p) => (
          <button
            type="button"
            className="review-queue-item"
            key={p.id}
            onClick={() => onOpen(p.id)}
          >
            <span>{p.title}</span>
            <small>
              Versión {p.revision} · {statuses[p.status]}
            </small>
          </button>
        ))}
      </div>
      {cursor && (
        <button
          type="button"
          className="button secondary"
          disabled={busy}
          onClick={() => void load(true)}
        >
          Ver más trabajos
        </button>
      )}
    </section>
  );
}
export function SocialReview({
  business,
  csrf,
  pack,
  dirty,
  onChanged,
}: {
  business: string;
  csrf: string;
  pack: any;
  dirty: boolean;
  onChanged: () => Promise<void>;
}) {
  const request = useRequest(business, csrf),
    [data, setData] = useState<any>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [criteria, setCriteria] = useState<
      Record<string, { verdict: string; reason: string }>
    >({}),
    [reason, setReason] = useState(""),
    [outcome, setOutcome] = useState("ready");
  async function refresh() {
    setData(await request("/packs/" + pack.id + "/reviews"));
  }
  useEffect(() => {
    setData(null);
    setCriteria({});
    setReason("");
    setError("");
    setOutcome("ready");
    void refresh().catch((e) => setError(String(e)));
  }, [pack.id, pack.digest, pack.review_state]);
  async function run(fn: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  const assessment = data?.events
      .filter((e: any) => e.kind === "assessment")
      .at(-1),
    blocked = busy || dirty || pack.stale;
  return (
    <section
      className="structured-review"
      aria-label="Revisión de esta versión"
    >
      <h3>Revisión de esta versión</h3>
      {error && <p role="alert">{error}</p>}
      {data && (
        <>
          <p className="review-status" role="status">
            {statuses[data.state]}
          </p>
          <p>
            Comprobación del archivo:{" "}
            {data.technical.status === "passed"
              ? "correcta"
              : "necesita corrección"}
            . El sistema no decide si la imagen es apropiada para tu negocio.
          </p>
          {data.legacy_approval && (
            <p>
              Aprobación anterior: se guardó antes de la revisión por criterios.
              No hay juicios detallados registrados.
            </p>
          )}
          <details
            open={!pack.approved && !assessment}
            className="review-assessment"
          >
            <summary>Revisar por criterios</summary>
            <p>
              Evalúa cada aspecto por separado. Explica cualquier problema o
              duda.
            </p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void run(async () => {
                  await request("/packs/" + pack.id + "/reviews", "POST", {
                    request_id: crypto.randomUUID(),
                    digest: pack.digest,
                    outcome,
                    reason,
                    ...criteria,
                  });
                  await refresh();
                  await onChanged();
                });
              }}
            >
              <fieldset disabled={blocked}>
                {Object.entries(labels).map(([key, label]) => (
                  <div className="review-criterion" key={key}>
                    <label>
                      {label}
                      <select
                        required
                        aria-label={label}
                        value={criteria[key]?.verdict || ""}
                        onChange={(e) =>
                          setCriteria((old) => ({
                            ...old,
                            [key]: {
                              verdict: e.target.value,
                              reason: old[key]?.reason || "",
                            },
                          }))
                        }
                      >
                        <option value="">Elige una evaluación</option>
                        <option value="acceptable">Está bien</option>
                        <option value="needs_changes">Necesita cambios</option>
                        <option value="uncertain">Tengo dudas</option>
                      </select>
                    </label>
                    <p>{descriptions[key]}</p>
                    <label>
                      Nota: {label.toLowerCase()}
                      <input
                        maxLength={600}
                        required={
                          !!criteria[key]?.verdict &&
                          criteria[key]?.verdict !== "acceptable"
                        }
                        value={criteria[key]?.reason || ""}
                        onChange={(e) =>
                          setCriteria((old) => ({
                            ...old,
                            [key]: {
                              verdict: old[key]?.verdict || "",
                              reason: e.target.value,
                            },
                          }))
                        }
                      />
                    </label>
                  </div>
                ))}
                <label>
                  Decisión de revisión
                  <select
                    value={outcome}
                    onChange={(e) => setOutcome(e.target.value)}
                  >
                    <option value="ready">Listo para aprobar</option>
                    <option value="changes_requested">Pedir cambios</option>
                    <option value="rejected">Descartar esta versión</option>
                  </select>
                </label>
                <label>
                  Motivo de la decisión
                  <textarea
                    required
                    maxLength={1200}
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    placeholder="Qué funciona o qué debemos corregir"
                  />
                </label>
                <p>
                  Guardar otra revisión deja sin efecto la aprobación anterior
                  de esta versión.
                </p>
                <button
                  className="button secondary"
                  disabled={
                    outcome === "ready" &&
                    Object.keys(labels).some(
                      (k) => criteria[k]?.verdict !== "acceptable",
                    )
                  }
                >
                  Guardar revisión
                </button>
              </fieldset>
            </form>
          </details>
          {assessment && (
            <div className="review-saved">
              <p>
                Última revisión:{" "}
                {
                  (
                    {
                      ready: "lista para aprobar",
                      changes_requested: "cambios pedidos",
                      rejected: "versión descartada",
                    } as any
                  )[assessment.outcome]
                }
              </p>
              <p>{assessment.reason}</p>
              {Object.keys(labels).map((key) => (
                <p key={key}>
                  <strong>{labels[key]}:</strong>{" "}
                  {
                    (
                      {
                        acceptable: "está bien",
                        needs_changes: "necesita cambios",
                        uncertain: "con dudas",
                      } as any
                    )[assessment[key].verdict]
                  }
                  {assessment[key].reason ? " · " + assessment[key].reason : ""}
                </p>
              ))}
            </div>
          )}
          <p>
            Resultado comercial: sin medir. Una aprobación de diseño no
            demuestra ventas ni alcance.
          </p>
          <button
            className="button primary"
            disabled={
              blocked ||
              pack.approved ||
              !assessment ||
              assessment.outcome !== "ready" ||
              data.technical.status !== "passed"
            }
            onClick={() =>
              void run(async () => {
                await request("/packs/" + pack.id + "/approve", "POST", {
                  digest: pack.digest,
                  review_id: assessment.id,
                });
                await refresh();
                await onChanged();
              })
            }
          >
            {pack.approved ? "Versión aprobada" : "Aprobar esta versión"}
          </button>
          {pack.approved && !dirty && (
            <p>
              <a
                href={
                  endpoint(business) + "/social/packs/" + pack.id + "/export"
                }
              >
                Descargar foto, texto y archivo editable
              </a>
            </p>
          )}
          {data.events.length > 0 && (
            <details className="review-events">
              <summary>Historial de decisiones de esta versión</summary>
              {data.events.map((e: any) => (
                <p key={e.id}>
                  {new Date(e.at * 1000).toLocaleString("es-CO")} ·{" "}
                  {e.kind === "approval"
                    ? "Aprobación final"
                    : (
                        {
                          ready: "Lista para aprobar",
                          changes_requested: "Cambios pedidos",
                          rejected: "Descartada",
                        } as any
                      )[e.outcome]}{" "}
                  · {e.reason || "Aprobación para exportación manual"} ·{" "}
                  {e.actor_id}
                </p>
              ))}
            </details>
          )}
        </>
      )}
      <SocialComparison
        key={pack.digest}
        business={business}
        csrf={csrf}
        pack={pack}
        dirty={dirty}
      />
    </section>
  );
}
function SocialComparison({
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
  const request = useRequest(business, csrf),
    [history, setHistory] = useState<any[]>([]),
    [prior, setPrior] = useState<any[]>([]),
    [pair, setPair] = useState<any>(null),
    [first, setFirst] = useState(""),
    [second, setSecond] = useState(""),
    [criterion, setCriterion] = useState("brand_fit"),
    [choice, setChoice] = useState(""),
    [reason, setReason] = useState(""),
    [tags, setTags] = useState<string[]>([]),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [more, setMore] = useState<number | null>(null);
  async function loadHistory(before?: number) {
    const d = await request(
      "/packs/" +
        pack.id +
        "/history" +
        (before ? "?before_revision=" + before : ""),
    );
    setHistory((old) => (before ? [...old, ...d.revisions] : d.revisions));
    setMore(d.before_revision);
  }
  useEffect(() => {
    void Promise.all([
      loadHistory(),
      request("/packs/" + pack.id + "/comparisons").then((d) =>
        setPrior(d.comparisons),
      ),
    ]).catch((e) => setError(String(e)));
  }, [pack.id, pack.digest]);
  async function run(fn: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <details className="review-comparison">
      <summary>Comparar dos alternativas</summary>
      <p>
        Compara versiones del mismo trabajo con el mismo objetivo, datos y
        referencias. El orden A/B se asigna al azar. Tu elección queda privada
        en este negocio; no aprueba la publicación.
      </p>
      {error && <p role="alert">{error}</p>}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void run(async () => {
            const a = history.find((r) => r.revision === Number(first)),
              b = history.find((r) => r.revision === Number(second));
            setPair(
              await request("/packs/" + pack.id + "/comparisons", "POST", {
                request_id: crypto.randomUUID(),
                a_revision: a.revision,
                b_revision: b.revision,
                a_digest: a.digest,
                b_digest: b.digest,
                criterion,
              }),
            );
            setChoice("");
            setReason("");
            setTags([]);
          });
        }}
      >
        <fieldset disabled={busy || dirty || pack.stale}>
          {[
            ["Primera versión", first, setFirst],
            ["Segunda versión", second, setSecond],
          ].map(([label, value, set]: any) => (
            <label key={label}>
              {label}
              <select
                required
                aria-label={label}
                value={value}
                onChange={(e) => set(e.target.value)}
              >
                <option value="">Seleccionar versión</option>
                {history.map((r) => (
                  <option key={r.revision} value={r.revision}>
                    Versión {r.revision}
                  </option>
                ))}
              </select>
            </label>
          ))}
          <label>
            Aspecto a comparar
            <select
              value={criterion}
              onChange={(e) => setCriterion(e.target.value)}
            >
              {["craft", "brand_fit", "purpose"].map((k) => (
                <option key={k} value={k}>
                  {labels[k]}
                </option>
              ))}
            </select>
          </label>
          <button
            className="button secondary"
            disabled={!first || !second || first === second}
          >
            Preparar comparación
          </button>
          {more && (
            <button
              type="button"
              className="button secondary"
              onClick={() => void run(() => loadHistory(more))}
            >
              Ver versiones anteriores
            </button>
          )}
        </fieldset>
      </form>
      {pair && (
        <div className="review-pair">
          <h4>¿Cuál encaja mejor? · {labels[pair.criterion]}</h4>
          <div className="review-pair-images">
            {["a", "b"].map((side) => (
              <article key={side}>
                <h4>{side.toUpperCase()}</h4>
                <img
                  src={
                    endpoint(business) +
                    "/social/packs/" +
                    pack.id +
                    "/revisions/" +
                    pair[side].revision +
                    "/image"
                  }
                  alt={"Alternativa " + side.toUpperCase()}
                />
                <p>{pair[side].caption}</p>
              </article>
            ))}
          </div>
          {pair.vote ? (
            <p role="status">
              Elección guardada: {choices[pair.vote.choice]} ·{" "}
              {pair.vote.reason}
            </p>
          ) : (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void run(async () => {
                  const saved = await request(
                    "/comparisons/" + pair.id + "/vote",
                    "POST",
                    {
                      request_id: crypto.randomUUID(),
                      context_sha256: pair.context_sha256,
                      choice,
                      reason,
                      tags,
                    },
                  );
                  setPair(saved);
                  setPrior((old) => [
                    saved,
                    ...old.filter((p) => p.id !== saved.id),
                  ]);
                });
              }}
            >
              <fieldset disabled={busy || dirty || pack.stale}>
                <label>
                  Tu elección
                  <select
                    required
                    aria-label="Tu elección"
                    value={choice}
                    onChange={(e) => setChoice(e.target.value)}
                  >
                    <option value="">Seleccionar</option>
                    {Object.entries(choices).map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Motivo de tu elección
                  <textarea
                    required
                    maxLength={1000}
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                  />
                </label>
                <fieldset className="review-tags">
                  <legend>Razones específicas · opcional, máximo seis</legend>
                  {Object.entries(tagLabels).map(([key, label]) => (
                    <label key={key} className="social-check">
                      <input
                        type="checkbox"
                        checked={tags.includes(key)}
                        disabled={!tags.includes(key) && tags.length >= 6}
                        onChange={(e) =>
                          setTags((old) =>
                            e.target.checked
                              ? [...old, key]
                              : old.filter((t) => t !== key),
                          )
                        }
                      />
                      {label}
                    </label>
                  ))}
                </fieldset>
                <button className="button secondary">Guardar elección</button>
              </fieldset>
            </form>
          )}
        </div>
      )}
      {prior.length > 0 && (
        <details>
          <summary>Comparaciones guardadas</summary>
          {prior.map((p) => (
            <p key={p.id}>
              {labels[p.criterion]} ·{" "}
              {p.vote
                ? `${choices[p.vote.choice]}: ${p.vote.reason}`
                : "Sin elección guardada"}
            </p>
          ))}
        </details>
      )}
    </details>
  );
}
