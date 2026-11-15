import { useEffect, useRef, useState } from "react";
import { endpoint } from "./ui";
import type { BusinessContext } from "./social-context";
import type { CreativeBoard } from "./social-creative";
const sourceNames: Record<string, string> = {
  owner_suggestion: "Idea del negocio",
  customer_question: "Pregunta de cliente",
  hypothesis: "Hipótesis",
  manual_research: "Investigación manual",
  platform_observation: "Observación de plataforma",
};
const flags: Record<string, string> = {
  unsupported_number_or_price:
    "Hay un número o precio que no aparece en los datos seleccionados.",
  unsupported_currency: "La moneda no coincide con los datos.",
  qualification_missing: "Falta una condición o aclaración del negocio.",
  unresolved_placeholder: "Hay texto pendiente de completar.",
  claim_not_in_copy:
    "La relación entre el texto y sus fuentes necesita revisión.",
  unsupported_marketing_claim: "Hay una afirmación comercial sin respaldo.",
  claim_fact_not_in_context:
    "Una afirmación cita un dato que no está disponible.",
};
export function SocialProposals({
  business,
  csrf,
  context,
  creative,
  library,
  onProduction,
}: {
  business: string;
  csrf: string;
  context: BusinessContext | null;
  creative: CreativeBoard | null;
  library: any[];
  onProduction: (job: any) => void;
}) {
  const [items, setItems] = useState<any[]>([]),
    [enabled, setEnabled] = useState(false),
    [mode, setMode] = useState("preview"),
    [asset, setAsset] = useState(""),
    [ids, setIds] = useState<string[]>([]),
    [question, setQuestion] = useState(""),
    [topic, setTopic] = useState(""),
    [refs, setRefs] = useState<string[]>([]),
    [selected, setSelected] = useState(""),
    [choice, setChoice] = useState(""),
    [edited, setEdited] = useState(""),
    [reason, setReason] = useState(""),
    [kind, setKind] = useState("selection"),
    [claims, setClaims] = useState(false),
    [entire, setEntire] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const root = endpoint(business) + "/social/proposals";
  const requestId = useRef(crypto.randomUUID()),
    decisionId = useRef(crypto.randomUUID());
  const active = items.find((p) => p.id === selected),
    options = active?.output?.copy_options || [];
  async function request(path = "", method = "GET", body?: unknown) {
    const r = await fetch(root + path, {
      method,
      headers: { "Content-Type": "application/json", "X-101-CSRF": csrf },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const d = await r.json();
    if (!r.ok)
      throw new Error(
        (
          {
            proposal_claims_blocked:
              "El texto incluye información sin respaldo o perdió una condición. Corrígelo con los datos guardados.",
            proposal_context_changed:
              "Cambió la información del negocio. Prepara otra propuesta con los datos actuales.",
            proposal_locale_required:
              "Confirma el idioma y región del negocio antes de preparar la propuesta.",
            proposal_priority_required:
              "Confirma primero la prioridad del negocio.",
            proposal_fact_not_current:
              "Uno de los datos necesita confirmación o una fecha vigente.",
            proposal_model_not_enabled:
              "La generación con modelo no está habilitada para este negocio.",
            proposal_decision_superseded:
              "Ya existe una decisión más reciente. Revisa la propuesta guardada.",
          } as Record<string, string>
        )[d.detail] || "Revisa las respuestas y vuelve a intentar.",
      );
    return d;
  }
  async function refresh() {
    const d = await request();
    setItems(d.proposals);
    setEnabled(d.model_enabled);
  }
  useEffect(() => {
    let stop = false,
      timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const d = await request();
        if (stop) return;
        setItems(d.proposals);
        setEnabled(d.model_enabled);
        if (
          d.proposals.some((p: any) => ["queued", "running"].includes(p.state))
        )
          timer = setTimeout(() => {
            if (document.visibilityState === "visible") void poll();
          }, 800);
      } catch (e) {
        if (!stop) setError(String(e));
      }
    }
    const visible = () => {
      if (document.visibilityState === "visible") void poll();
    };
    document.addEventListener("visibilitychange", visible);
    void poll();
    return () => {
      stop = true;
      clearTimeout(timer);
      document.removeEventListener("visibilitychange", visible);
    };
  }, [root, selected]);
  useEffect(() => {
    setIds([]);
  }, [context?.id]);
  function changed() {
    requestId.current = crypto.randomUUID();
    setError("");
  }
  async function create(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const p = await request("", "POST", {
        request_id: requestId.current,
        mode,
        expected_context_revision: context?.revision || 0,
        expected_brand_revision: creative?.revision || 0,
        asset_id: asset,
        fact_ids: ids,
        question_id: question || null,
        question: topic,
        reference_ids: refs,
        location_id: context?.location_id || null,
      });
      await refresh();
      setSelected(p.id);
      setChoice("");
      setEdited("");
      setReason("");
      setClaims(false);
      setEntire(false);
      requestId.current = crypto.randomUUID();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  function pick(id: string) {
    setChoice(id);
    const c = options.find((v: any) => v.id === id);
    setEdited(
      c ? [c.opening, c.body, c.action].filter(Boolean).join("\n\n") : "",
    );
    setClaims(false);
    setEntire(false);
    decisionId.current = crypto.randomUUID();
  }
  async function decide(reject = false) {
    if (!active) return;
    setBusy(true);
    setError("");
    try {
      await request("/" + active.id + "/decisions", "POST", {
        request_id: decisionId.current,
        digest: active.digest,
        choice: reject ? "reject" : choice,
        edited_text: reject ? null : edited,
        reason_kind: kind,
        reason,
        reviewed_claims: claims,
        reviewed_entire_copy: entire,
      });
      await refresh();
      decisionId.current = crypto.randomUUID();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  async function produce(id: string) {
    setBusy(true);
    setError("");
    try {
      onProduction(
        await request("/" + active.id + "/produce", "POST", {
          decision_id: id,
        }),
      );
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <details className="social-context proposal-panel">
      <summary>Ideas y textos para publicar</summary>
      <p>
        Prepara una propuesta a partir de los datos, la voz y el material que
        selecciones.
      </p>
      {(!context?.brief?.objective || !context?.brief?.locale) && (
        <p>
          Primero confirma una prioridad y el idioma del negocio en «Información
          de tu negocio».
        </p>
      )}
      <details className="proposal-input" open={!active}>
        <summary>Datos para preparar la propuesta</summary>
        <form onSubmit={(e) => void create(e)} onChange={changed}>
          <div className="social-context-fields">
            <label>
              Cómo preparar la propuesta
              <select value={mode} onChange={(e) => setMode(e.target.value)}>
                <option value="preview">
                  Vista previa con plantilla · sin modelo
                </option>
                {enabled && (
                  <option value="model">
                    Generar con el modelo configurado
                  </option>
                )}
              </select>
            </label>
            <label>
              Fotografía para esta idea
              <select
                required
                value={asset}
                onChange={(e) => setAsset(e.target.value)}
              >
                <option value="">Seleccionar fotografía autorizada</option>
                {library
                  .filter((a) => a.permitted_use === "production")
                  .map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.fixture ? "Prueba · " : ""}
                      {a.id.slice(0, 8)}
                    </option>
                  ))}
              </select>
            </label>
          </div>
          {!enabled && (
            <p>
              La generación con modelo todavía no está habilitada para este
              negocio. La vista previa usa los datos tal como los confirmaste.
            </p>
          )}
          <fieldset className="proposal-facts">
            <legend>Datos que puede usar</legend>
            {context?.facts
              .filter((f) => f.current_status === "confirmed")
              .map((f) => (
                <label className="social-check" key={f.id}>
                  <input
                    type="checkbox"
                    checked={ids.includes(f.id)}
                    onChange={(e) =>
                      setIds((old) =>
                        e.target.checked
                          ? [...old, f.id]
                          : old.filter((i) => i !== f.id),
                      )
                    }
                  />
                  {f.text}
                </label>
              ))}
          </fieldset>
          <div className="social-context-fields">
            <label>
              Pregunta guardada para esta idea
              <select
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
              >
                <option value="">Proponer a partir de mi prioridad</option>
                {creative?.questions
                  .filter((q) => q.status === "active")
                  .map((q) => (
                    <option value={q.id} key={q.id}>
                      {q.text} · {sourceNames[q.source_kind]}
                    </option>
                  ))}
              </select>
            </label>
            {!question && (
              <label>
                Pregunta o tema · opcional
                <input
                  maxLength={300}
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                />
              </label>
            )}
          </div>
          {creative?.references.length ? (
            <fieldset className="proposal-facts">
              <legend>Referencias para revisar esta propuesta</legend>
              {creative.references
                .filter((r) => r.status === "active")
                .map((r) => (
                  <label className="social-check" key={r.id}>
                    <input
                      type="checkbox"
                      checked={refs.includes(r.id)}
                      onChange={(e) =>
                        setRefs((old) =>
                          e.target.checked
                            ? [...old, r.id]
                            : old.filter((i) => i !== r.id),
                        )
                      }
                    />
                    {r.title} · {r.reason}
                  </label>
                ))}
            </fieldset>
          ) : null}
          <button
            className="button primary"
            disabled={
              busy ||
              !ids.length ||
              ids.length > 12 ||
              !asset ||
              !context?.brief?.objective ||
              !context?.brief?.locale
            }
          >
            {busy ? "Preparando…" : "Preparar propuesta y dos textos"}
          </button>
        </form>
      </details>
      {error && <p role="alert">{error}</p>}
      {!!items.length && (
        <label>
          Propuestas guardadas
          <select
            value={selected}
            onChange={(e) => {
              setSelected(e.target.value);
              setChoice("");
              setEdited("");
              setReason("");
              setClaims(false);
              setEntire(false);
            }}
          >
            <option value="">Selecciona una propuesta</option>
            {items.map((p) => (
              <option value={p.id} key={p.id}>
                {p.output?.idea || "Propuesta en preparación"} ·{" "}
                {p.mode === "preview" ? "Plantilla" : "Modelo"}
              </option>
            ))}
          </select>
        </label>
      )}
      {active && (
        <section className="proposal-result" aria-label="Propuesta preparada">
          <p>
            {active.mode === "preview"
              ? "Vista previa con plantilla. No se llamó a un modelo."
              : "Texto generado con modelo. Requiere revisión del negocio."}
          </p>
          {active.stale && (
            <p role="status">
              Cambió información que usa esta propuesta. Prepara otra con los
              datos actuales.
            </p>
          )}
          {["queued", "running"].includes(active.state) && (
            <p role="status">
              {active.state === "queued"
                ? "En cola"
                : "Preparando la propuesta"}
              … Puedes volver más tarde.
            </p>
          )}
          {["failed", "needs_input", "uncertain", "superseded"].includes(
            active.state,
          ) && (
            <p role="status">
              {active.state === "uncertain"
                ? "No sabemos si el proveedor terminó la solicitud. No se repetirá automáticamente."
                : "Esta propuesta necesita revisión antes de continuar."}
            </p>
          )}
          {active.output && (
            <>
              <h3>{active.output.idea}</h3>
              <dl className="proposal-reason">
                <dt>Lo que sabemos</dt>
                <dd>{active.output.observation}</dd>
                <dt>Lo que queremos probar</dt>
                <dd>{active.output.hypothesis}</dd>
                <dt>Por qué lo proponemos</dt>
                <dd>{active.output.reason}</dd>
                <dt>Siguiente paso del cliente</dt>
                <dd>{active.output.customer_action}</dd>
                <dt>Qué mediremos</dt>
                <dd>
                  {
                    (
                      {
                        qualified_inquiries: "Consultas de compra",
                        orders: "Pedidos",
                        reach: "Alcance",
                        owner_effort: "Esfuerzo del negocio",
                      } as any
                    )[active.output.primary_measure]
                  }
                </dd>
              </dl>
              <p>
                Pregunta: {active.input.question.text} ·{" "}
                {sourceNames[active.input.question.source_kind]}. Sin volumen de
                búsqueda medido.
              </p>
              {active.output.missing_material.map((m: string, i: number) => (
                <p key={i}>Material pendiente: {m}</p>
              ))}
              <div className="proposal-options">
                {options.map((c: any) => (
                  <article key={c.id}>
                    <h4>
                      {c.id === "informational"
                        ? "Directo e informativo"
                        : "Conversado"}
                    </h4>
                    <p className="social-caption">
                      {[c.opening, c.body, c.action]
                        .filter(Boolean)
                        .join("\n\n")}
                    </p>
                    <details>
                      <summary>Afirmaciones y datos de respaldo</summary>
                      {c.claims.map((claim: any, i: number) => (
                        <div key={i}>
                          <p>{claim.text}</p>
                          {claim.fact_ids.map((id: string) => (
                            <p key={id}>
                              {active.input.facts.find((f: any) => f.id === id)
                                ?.text || "Dato no disponible"}
                            </p>
                          ))}
                        </div>
                      ))}
                      <p>
                        Citar un dato no demuestra por sí solo que el texto lo
                        respalde.
                      </p>
                    </details>
                    {active.review.options[c.id].blocking.map((f: string) => (
                      <p key={f} role="status">
                        {flags[f] || "Revisar esta afirmación."}
                      </p>
                    ))}
                    <button
                      type="button"
                      className="button secondary"
                      disabled={active.stale || busy}
                      aria-pressed={choice === c.id}
                      onClick={() => pick(c.id)}
                    >
                      Elegir{" "}
                      {c.id === "informational"
                        ? "texto informativo"
                        : "texto conversado"}
                    </button>
                  </article>
                ))}
              </div>
              {choice && (
                <div className="proposal-edit">
                  <label>
                    Texto elegido · puedes editarlo
                    <textarea
                      aria-label="Texto elegido · puedes editarlo"
                      rows={6}
                      maxLength={3000}
                      value={edited}
                      onChange={(e) => {
                        setEdited(e.target.value);
                        setClaims(false);
                        setEntire(false);
                        decisionId.current = crypto.randomUUID();
                      }}
                    />
                  </label>
                  <label className="social-check">
                    <input
                      type="checkbox"
                      checked={claims}
                      onChange={(e) => setClaims(e.target.checked)}
                    />
                    Comprobé cada afirmación contra los datos: precios,
                    condiciones y detalles.
                  </label>
                  <label className="social-check">
                    <input
                      type="checkbox"
                      checked={entire}
                      onChange={(e) => setEntire(e.target.checked)}
                    />
                    Revisé el texto completo y confirmé que no agrega datos sin
                    respaldo.
                  </label>
                </div>
              )}
              <label>
                Tipo de decisión
                <select value={kind} onChange={(e) => setKind(e.target.value)}>
                  <option value="selection">Elección de una opción</option>
                  <option value="factual_correction">Corrección factual</option>
                  <option value="style_preference">
                    Preferencia de estilo
                  </option>
                  <option value="strategy">Cambio de estrategia</option>
                </select>
              </label>
              <label>
                Motivo de la decisión
                <input
                  maxLength={500}
                  value={reason}
                  onChange={(e) => {
                    setReason(e.target.value);
                    decisionId.current = crypto.randomUUID();
                  }}
                />
              </label>
              <div className="proposal-actions">
                <button
                  type="button"
                  className="button primary"
                  disabled={
                    busy ||
                    active.stale ||
                    !choice ||
                    !edited ||
                    !reason.trim() ||
                    !claims ||
                    !entire
                  }
                  onClick={() => void decide()}
                >
                  Guardar texto revisado
                </button>
                <button
                  type="button"
                  className="button secondary"
                  disabled={busy || active.stale || !reason.trim()}
                  onClick={() => void decide(true)}
                >
                  Rechazar propuesta
                </button>
              </div>
              {active.decisions.map((d: any, i: number) => (
                <div className="proposal-decision" key={d.id}>
                  <p>
                    {d.choice === "reject"
                      ? "Propuesta rechazada"
                      : "Texto revisado guardado"}{" "}
                    · {d.reason}
                  </p>
                  {d.choice !== "reject" &&
                    i === active.decisions.length - 1 &&
                    !active.output.missing_material.length && (
                      <button
                        type="button"
                        className="button primary"
                        disabled={busy || active.stale}
                        onClick={() => void produce(d.id)}
                      >
                        Preparar publicación con este texto
                      </button>
                    )}
                </div>
              ))}
            </>
          )}
        </section>
      )}
    </details>
  );
}
