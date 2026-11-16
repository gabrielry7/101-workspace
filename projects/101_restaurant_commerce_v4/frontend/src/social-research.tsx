import { useEffect, useState } from "react";
import { endpoint } from "./ui";
import type { CreativeBoard } from "./social-creative";

export type ResearchSelection = {
  version_id: string;
  post_ids: string[];
  search_ids: string[];
  question_id: string | null;
};
const errors: Record<string, string> = {
  research_revision_conflict:
    "La investigación cambió en otra ventana. Vuelve a cargar antes de guardar.",
  research_reference_missing:
    "Guarda primero la referencia y el grupo de comparación en «Referencias, voz y preguntas».",
  research_reference_changed:
    "La referencia cambió. Revisa esta observación y vuelve a guardarla.",
  research_source_unavailable:
    "La fuente se retiró o venció. Revísala antes de usarla.",
  research_question_unavailable:
    "Guarda o actualiza primero la pregunta que corresponde a esta búsqueda.",
  research_evidence_changed:
    "Cambió la evidencia seleccionada. Revisa la investigación actual.",
};
const groups: Record<string, string> = {
  local_competitor: "Alternativa local",
  remote_comparable: "Negocio similar en otro lugar",
  creative_reference: "Referencia creativa",
  own_brand: "Ejemplo del negocio",
};
function dateLater() {
  return new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10);
}
function localNow() {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 19);
}
function base() {
  return {
    id: "",
    source: "",
    source_url: null,
    permission: "",
    allowed_use: "internal_reference_only",
    model_processing_allowed: false,
    fixture: false,
    observed_at: new Date().toISOString(),
    valid_until: dateLater() + "T23:59:59Z",
    status: "active",
  };
}
function newPost() {
  return {
    ...base(),
    reference_id: "",
    account_key: "",
    platform: "instagram",
    format: "photo",
    subject: "",
    opening: "",
    sequence: "",
    visible_text: "",
    caption_excerpt: "",
    visual_treatment: "",
    customer_action: "",
    duration_ms: null,
    sound: "unknown",
    paid_support: "unknown",
    distribution_evidence: "",
    published_at: null,
    publication_day: null,
    timestamp_precision: "unknown",
    timezone: null,
    observation: "",
    hypothesis: "",
    alternatives: "",
    adaptation: "",
    metrics: [] as any[],
  };
}
function newSearch() {
  return {
    ...base(),
    question_id: "",
    platform: "instagram",
    locale: "",
    geography: "",
    source_kind: "manual_research",
    observation_context: "",
    observation: "",
    sampled_position: null,
  };
}
const postKeys = Object.keys(newPost()),
  searchKeys = Object.keys(newSearch());
function clean(row: any, kind: string) {
  return Object.fromEntries(
    (kind === "posts" ? postKeys : searchKeys).map((k) => [k, row[k]]),
  );
}

export function SocialResearch({
  business,
  csrf,
  creative,
  fixture,
  onUse,
  onChanged,
}: {
  business: string;
  csrf: string;
  creative: CreativeBoard | null;
  fixture: boolean;
  onUse: (r: ResearchSelection) => void;
  onChanged: () => Promise<void>;
}) {
  const [open, setOpen] = useState(false),
    [board, setBoard] = useState<any>(null),
    [post, setPost] = useState<any>(null),
    [search, setSearch] = useState<any>(null);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [confirmed, setConfirmed] = useState(false);
  const [selectedPosts, setSelectedPosts] = useState<string[]>([]),
    [selectedSearch, setSelectedSearch] = useState("");
  const [observed, setObserved] = useState(localNow()),
    [expiry, setExpiry] = useState(dateLater());
  const root = endpoint(business) + "/social/research";
  async function request(method = "GET", body?: unknown) {
    const r = await fetch(root, {
      method,
      headers: { "Content-Type": "application/json", "X-101-CSRF": csrf },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const d = await r.json();
    if (!r.ok)
      throw new Error(
        errors[d.detail] ||
          "Revisa las fuentes, fechas, permisos y el momento real en que se midieron los datos.",
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
    if (open) void run(async () => setBoard(await request()));
  }, [open, root]);
  function begin(kind: string, row?: any) {
    setPost(
      kind === "posts"
        ? row
          ? clean(row, kind)
          : { ...newPost(), id: crypto.randomUUID(), fixture }
        : null,
    );
    setSearch(
      kind === "searches"
        ? row
          ? clean(row, kind)
          : { ...newSearch(), id: crypto.randomUUID(), fixture }
        : null,
    );
    setConfirmed(false);
    setObserved(
      row
        ? new Date(
            new Date(row.observed_at).getTime() -
              new Date(row.observed_at).getTimezoneOffset() * 60000,
          )
            .toISOString()
            .slice(0, 19)
        : localNow(),
    );
    setExpiry(row?.valid_until?.slice(0, 10) || dateLater());
  }
  async function save(kind: string, item: any) {
    const payload = {
      expected_revision: board.revision,
      posts: board.posts.map((p: any) => clean(p, "posts")),
      searches: board.searches.map((p: any) => clean(p, "searches")),
      reason:
        item.status === "withdrawn"
          ? "Retirada explícita de una observación"
          : "Observación y permiso revisados por el usuario",
      confirmed: true,
    };
    payload[kind as "posts" | "searches"] = [
      ...payload[kind as "posts" | "searches"].filter(
        (p: any) => p.id !== item.id,
      ),
      item,
    ];
    const result = await request("PUT", payload);
    setBoard(result);
    setPost(null);
    setSearch(null);
    setConfirmed(false);
    setSelectedPosts((old) =>
      old.filter((id) =>
        result.posts.some((p: any) => p.id === id && p.status === "active"),
      ),
    );
    if (
      result.searches.find((p: any) => p.id === selectedSearch)?.status !==
      "active"
    )
      setSelectedSearch("");
    await onChanged();
  }
  const item = post || search,
    kind = post ? "posts" : "searches";
  function change(k: string, value: any) {
    if (post) setPost((p: any) => ({ ...p, [k]: value }));
    else
      setSearch((p: any) => ({
        ...p,
        [k]: value,
        ...(k === "source_kind"
          ? {
              sampled_position:
                value === "sampled_search" ? p.sampled_position : null,
              source_url: value === "hypothesis" ? null : p.source_url,
            }
          : {}),
      }));
    setConfirmed(false);
  }
  function metric(i: number, k: string, value: any) {
    setPost((p: any) => ({
      ...p,
      metrics: p.metrics.map((m: any, n: number) =>
        n === i ? { ...m, [k]: value } : m,
      ),
    }));
    setConfirmed(false);
  }
  function use() {
    const chosen = board.searches.find((s: any) => s.id === selectedSearch);
    onUse({
      version_id: board.id,
      post_ids: selectedPosts,
      search_ids: chosen ? [chosen.id] : [],
      question_id: chosen?.question_id || null,
    });
  }
  return (
    <details
      className="social-context social-research"
      open={open}
      onToggle={(e) => setOpen(e.currentTarget.open)}
    >
      <summary>Investigación y búsquedas</summary>
      {open && (
        <>
          <h2>Qué observamos y qué podemos probar</h2>
          <p>
            Guarda ejemplos ordinarios y destacados, sus fuentes y una
            adaptación con material propio. Esta selección manual no representa
            todo el historial de una cuenta ni verifica sus ventas.
          </p>
          {error && <p role="alert">{error}</p>}
          {board && (
            <>
              <div className="research-actions">
                <button
                  type="button"
                  className="button secondary"
                  disabled={busy || !creative?.references.length}
                  onClick={() => begin("posts")}
                >
                  Añadir publicación de referencia
                </button>
                <button
                  type="button"
                  className="button secondary"
                  disabled={busy || !creative?.questions.length}
                  onClick={() => begin("searches")}
                >
                  Añadir observación de búsqueda
                </button>
              </div>
              {!creative?.references.length && (
                <p>
                  Empieza por guardar las cuentas o referencias y su grupo en
                  «Referencias, voz y preguntas».
                </p>
              )}
              {!creative?.questions.length && (
                <p>
                  Para investigar búsquedas, guarda primero una pregunta y los
                  datos que la responden.
                </p>
              )}
              {item && (
                <form
                  className="research-editor"
                  onSubmit={(e) => {
                    e.preventDefault();
                    void run(async () => {
                      const v = {
                        ...item,
                        observed_at:
                          item.observed_at &&
                          new Date(
                            new Date(item.observed_at).getTime() -
                              new Date(item.observed_at).getTimezoneOffset() *
                                60000,
                          )
                            .toISOString()
                            .slice(0, 19) === observed
                            ? item.observed_at
                            : new Date(observed).toISOString(),
                        valid_until: expiry + "T23:59:59Z",
                      };
                      await save(kind, v);
                    });
                  }}
                >
                  <h3>
                    {post
                      ? "Publicación observada"
                      : "Búsqueda o pregunta observada"}
                  </h3>
                  <fieldset disabled={busy}>
                    {post ? (
                      <>
                        <label>
                          Referencia o cuenta
                          <select
                            aria-label="Referencia o cuenta"
                            required
                            value={post.reference_id}
                            onChange={(e) =>
                              change("reference_id", e.target.value)
                            }
                          >
                            <option value="">
                              Seleccionar referencia guardada
                            </option>
                            {creative?.references
                              .filter((r) => r.status === "active")
                              .map((r) => (
                                <option key={r.id} value={r.id}>
                                  {r.title} · {groups[r.purpose]}
                                </option>
                              ))}
                          </select>
                        </label>
                        <label>
                          Cuenta observada
                          <input
                            aria-label="Cuenta observada"
                            required
                            maxLength={100}
                            value={post.account_key}
                            onChange={(e) =>
                              change("account_key", e.target.value)
                            }
                            placeholder="Nombre o @ tal como aparece"
                          />
                        </label>
                        <label>
                          Asunto de la publicación
                          <input
                            aria-label="Asunto de la publicación"
                            required
                            maxLength={300}
                            value={post.subject}
                            onChange={(e) => change("subject", e.target.value)}
                          />
                        </label>
                      </>
                    ) : (
                      <label>
                        Pregunta que investigamos
                        <select
                          aria-label="Pregunta que investigamos"
                          required
                          value={search.question_id}
                          onChange={(e) =>
                            change("question_id", e.target.value)
                          }
                        >
                          <option value="">
                            Seleccionar pregunta guardada
                          </option>
                          {creative?.questions
                            .filter((q) => q.status === "active")
                            .map((q) => (
                              <option key={q.id} value={q.id}>
                                {q.text}
                              </option>
                            ))}
                        </select>
                      </label>
                    )}
                    <div className="social-context-fields">
                      <label>
                        Plataforma
                        <select
                          aria-label="Plataforma observada"
                          value={item.platform}
                          onChange={(e) => change("platform", e.target.value)}
                        >
                          <option value="instagram">Instagram</option>
                          <option value="facebook">Facebook</option>
                          <option value="tiktok">TikTok</option>
                          {search && <option value="other">Otra</option>}
                        </select>
                      </label>
                      <label>
                        Fecha de la observación
                        <input
                          aria-label="Fecha de la observación"
                          required
                          type="datetime-local"
                          step="1"
                          value={observed}
                          onChange={(e) => {
                            setObserved(e.target.value);
                            setConfirmed(false);
                          }}
                        />
                      </label>
                    </div>
                    <label>
                      Fuente de esta observación
                      <textarea
                        aria-label="Fuente de esta observación"
                        required
                        maxLength={500}
                        value={item.source}
                        onChange={(e) => change("source", e.target.value)}
                        placeholder="Dónde y cómo lo observamos; exportación o apunte revisado"
                      />
                    </label>
                    <label>
                      Enlace de la fuente · opcional
                      <input
                        aria-label="Enlace de la fuente · opcional"
                        type="url"
                        value={item.source_url || ""}
                        onChange={(e) =>
                          change("source_url", e.target.value || null)
                        }
                        placeholder="https://…"
                      />
                    </label>
                    <label>
                      Qué observamos
                      <textarea
                        aria-label="Qué observamos"
                        required
                        maxLength={600}
                        value={item.observation}
                        onChange={(e) => change("observation", e.target.value)}
                      />
                    </label>
                    {post ? (
                      <>
                        <label>
                          Qué podría explicarlo · hipótesis
                          <textarea
                            aria-label="Qué podría explicarlo · hipótesis"
                            required
                            maxLength={600}
                            value={post.hypothesis}
                            onChange={(e) =>
                              change("hypothesis", e.target.value)
                            }
                          />
                        </label>
                        <label>
                          Otras explicaciones posibles
                          <textarea
                            aria-label="Otras explicaciones posibles"
                            required
                            maxLength={600}
                            value={post.alternatives}
                            onChange={(e) =>
                              change("alternatives", e.target.value)
                            }
                          />
                        </label>
                        <label>
                          Qué podríamos probar con nuestro material
                          <textarea
                            aria-label="Qué podríamos probar con nuestro material"
                            required
                            maxLength={600}
                            value={post.adaptation}
                            onChange={(e) =>
                              change("adaptation", e.target.value)
                            }
                          />
                        </label>
                        <details className="research-details">
                          <summary>
                            Formato, secuencia y fecha de publicación
                          </summary>
                          <label>
                            Formato observado
                            <select
                              aria-label="Formato observado"
                              value={post.format}
                              onChange={(e) => change("format", e.target.value)}
                            >
                              <option value="photo">Fotografía</option>
                              <option value="carousel">Carrusel</option>
                              <option value="video">Vídeo</option>
                            </select>
                          </label>
                          {[
                            ["opening", "Inicio o primera escena"],
                            ["sequence", "Secuencia"],
                            ["visual_treatment", "Tratamiento visual"],
                            ["visible_text", "Texto visible"],
                            [
                              "caption_excerpt",
                              "Fragmento del texto · solo referencia",
                            ],
                            ["customer_action", "Qué pide hacer al cliente"],
                          ].map(([k, label]) => (
                            <label key={k}>
                              {label}
                              <textarea
                                maxLength={
                                  k === "caption_excerpt"
                                    ? 1200
                                    : k === "sequence" || k === "visible_text"
                                      ? 800
                                      : 400
                                }
                                value={post[k]}
                                onChange={(e) => change(k, e.target.value)}
                              />
                            </label>
                          ))}
                          <label>
                            Duración observada (segundos) · opcional
                            <input
                              aria-label="Duración observada (segundos) · opcional"
                              type="number"
                              min=".001"
                              step=".001"
                              value={
                                post.duration_ms === null
                                  ? ""
                                  : post.duration_ms / 1000
                              }
                              onChange={(e) =>
                                change(
                                  "duration_ms",
                                  e.target.value
                                    ? Math.round(Number(e.target.value) * 1000)
                                    : null,
                                )
                              }
                            />
                          </label>
                          <label>
                            Sonido observado
                            <select
                              aria-label="Sonido observado"
                              value={post.sound}
                              onChange={(e) => change("sound", e.target.value)}
                            >
                              <option value="unknown">Sin identificar</option>
                              <option value="natural">Sonido ambiente</option>
                              <option value="speech">Voz</option>
                              <option value="music">Música</option>
                              <option value="silent">Silencio</option>
                            </select>
                          </label>
                          <label>
                            Precisión de la fecha
                            <select
                              aria-label="Precisión de la fecha"
                              value={post.timestamp_precision}
                              onChange={(e) => {
                                change("timestamp_precision", e.target.value);
                                setPost((p: any) => ({
                                  ...p,
                                  published_at: null,
                                  publication_day: null,
                                  timezone:
                                    e.target.value === "minute" ? "UTC" : null,
                                }));
                              }}
                            >
                              <option value="unknown">
                                No conocemos la fecha
                              </option>
                              <option value="day">Solo conocemos el día</option>
                              <option value="minute">
                                Hora y minuto de la fuente
                              </option>
                            </select>
                          </label>
                          {post.timestamp_precision === "day" && (
                            <label>
                              Día publicado
                              <input
                                aria-label="Día publicado"
                                required
                                type="date"
                                value={post.publication_day || ""}
                                onChange={(e) =>
                                  change(
                                    "publication_day",
                                    e.target.value || null,
                                  )
                                }
                              />
                            </label>
                          )}
                          {post.timestamp_precision === "minute" && (
                            <>
                              <label>
                                Hora publicada con su desfase
                                <input
                                  aria-label="Hora publicada con su desfase"
                                  required
                                  value={post.published_at || ""}
                                  onChange={(e) =>
                                    change(
                                      "published_at",
                                      e.target.value || null,
                                    )
                                  }
                                  placeholder="2026-11-15T18:37:00-05:00"
                                />
                              </label>
                              <label>
                                Zona horaria de esa hora
                                <input
                                  aria-label="Zona horaria de esa hora"
                                  required
                                  value={post.timezone || ""}
                                  onChange={(e) =>
                                    change("timezone", e.target.value)
                                  }
                                  placeholder="America/Bogota"
                                />
                              </label>
                              <p>
                                Conserva la hora real de la fuente. Un buen
                                resultado a una hora no demuestra que esa hora
                                lo causó.
                              </p>
                            </>
                          )}
                          <label>
                            Promoción pagada
                            <select
                              aria-label="Promoción pagada"
                              value={post.paid_support}
                              onChange={(e) =>
                                change("paid_support", e.target.value)
                              }
                            >
                              <option value="unknown">No lo sabemos</option>
                              <option value="organic_reported">
                                Orgánica según la fuente
                              </option>
                              <option value="paid_reported">
                                Pagada según la fuente
                              </option>
                            </select>
                          </label>
                          {post.paid_support !== "unknown" && (
                            <label>
                              Evidencia de distribución
                              <input
                                aria-label="Evidencia de distribución"
                                required
                                value={post.distribution_evidence}
                                maxLength={500}
                                onChange={(e) =>
                                  change(
                                    "distribution_evidence",
                                    e.target.value,
                                  )
                                }
                              />
                            </label>
                          )}
                        </details>
                        <details className="research-details">
                          <summary>Mediciones disponibles</summary>
                          <p>
                            Guarda el dato como se observó. Un total de hoy no
                            reconstruye el resultado de las primeras 24 horas.
                          </p>
                          {post.metrics.map((m: any, i: number) => (
                            <div key={i} className="research-metric">
                              <label>
                                Métrica {i + 1}
                                <select
                                  aria-label={"Métrica " + (i + 1)}
                                  value={m.metric}
                                  onChange={(e) =>
                                    metric(i, "metric", e.target.value)
                                  }
                                >
                                  <option value="likes">
                                    Me gusta públicos
                                  </option>
                                  <option value="comments">
                                    Comentarios públicos
                                  </option>
                                  <option value="views">
                                    Visualizaciones disponibles
                                  </option>
                                </select>
                              </label>
                              <label>
                                Disponibilidad {i + 1}
                                <select
                                  aria-label={"Disponibilidad " + (i + 1)}
                                  value={m.availability}
                                  onChange={(e) =>
                                    setPost((p: any) => ({
                                      ...p,
                                      metrics: p.metrics.map(
                                        (v: any, n: number) =>
                                          n === i
                                            ? {
                                                ...v,
                                                availability: e.target.value,
                                                value: null,
                                              }
                                            : v,
                                      ),
                                    }))
                                  }
                                >
                                  <option value="unavailable">
                                    No disponible
                                  </option>
                                  <option value="measured">
                                    Medido · cero es un valor válido
                                  </option>
                                </select>
                              </label>
                              {m.availability === "measured" ? (
                                <label>
                                  Valor medido {i + 1}
                                  <input
                                    required
                                    type="number"
                                    min="0"
                                    step="1"
                                    value={m.value ?? ""}
                                    onChange={(e) =>
                                      metric(
                                        i,
                                        "value",
                                        e.target.value === ""
                                          ? null
                                          : Number(e.target.value),
                                      )
                                    }
                                  />
                                </label>
                              ) : (
                                <label>
                                  Por qué falta {i + 1}
                                  <input
                                    required
                                    maxLength={300}
                                    value={m.reason}
                                    onChange={(e) =>
                                      metric(i, "reason", e.target.value)
                                    }
                                  />
                                </label>
                              )}
                              <label>
                                Definición de la métrica {i + 1}
                                <input
                                  required
                                  maxLength={300}
                                  value={m.definition}
                                  onChange={(e) =>
                                    metric(i, "definition", e.target.value)
                                  }
                                />
                              </label>
                              <label>
                                Momento del dato {i + 1}
                                <select
                                  aria-label={"Momento del dato " + (i + 1)}
                                  value={m.window}
                                  onChange={(e) =>
                                    metric(i, "window", e.target.value)
                                  }
                                >
                                  <option value="lifetime">
                                    Total observado · edad no comparable
                                  </option>
                                  <option value="24h">
                                    Alrededor de 24 horas
                                  </option>
                                  <option value="72h">
                                    Alrededor de 72 horas
                                  </option>
                                  <option value="7d">
                                    Alrededor de siete días
                                  </option>
                                </select>
                              </label>
                              <label>
                                Cuándo se midió {i + 1}
                                <input
                                  required
                                  type="datetime-local"
                                  step="1"
                                  value={new Date(
                                    new Date(m.observed_at).getTime() -
                                      new Date(
                                        m.observed_at,
                                      ).getTimezoneOffset() *
                                        60000,
                                  )
                                    .toISOString()
                                    .slice(0, 19)}
                                  onChange={(e) => {
                                    if (e.target.value)
                                      metric(
                                        i,
                                        "observed_at",
                                        new Date(e.target.value).toISOString(),
                                      );
                                  }}
                                />
                              </label>
                              <label>
                                Fuente de la medición {i + 1}
                                <input
                                  required
                                  maxLength={500}
                                  value={m.source_ref}
                                  onChange={(e) =>
                                    metric(i, "source_ref", e.target.value)
                                  }
                                />
                              </label>
                              <button
                                type="button"
                                className="button secondary"
                                onClick={() =>
                                  setPost((p: any) => ({
                                    ...p,
                                    metrics: p.metrics.filter(
                                      (_: any, n: number) => n !== i,
                                    ),
                                  }))
                                }
                              >
                                Quitar medición {i + 1}
                              </button>
                            </div>
                          ))}
                          <button
                            type="button"
                            className="button secondary"
                            disabled={post.metrics.length >= 9}
                            onClick={() =>
                              setPost((p: any) => ({
                                ...p,
                                metrics: [
                                  ...p.metrics,
                                  {
                                    metric: "likes",
                                    definition:
                                      "Recuento público de me gusta mostrado por la plataforma",
                                    value: null,
                                    availability: "unavailable",
                                    reason: "",
                                    window: "lifetime",
                                    observed_at: new Date(
                                      observed,
                                    ).toISOString(),
                                    source_ref: "",
                                  },
                                ],
                              }))
                            }
                          >
                            Añadir medición
                          </button>
                        </details>
                      </>
                    ) : (
                      <>
                        <label>
                          Origen de la observación
                          <select
                            aria-label="Origen de la observación"
                            value={search.source_kind}
                            onChange={(e) =>
                              change("source_kind", e.target.value)
                            }
                          >
                            <option value="manual_research">
                              Investigación manual
                            </option>
                            <option value="sampled_search">
                              Búsqueda muestreada
                            </option>
                            <option value="owner_export">
                              Exportación del dueño
                            </option>
                            <option value="customer_question">
                              Pregunta de cliente
                            </option>
                            <option value="hypothesis">
                              Hipótesis · sin demanda medida
                            </option>
                          </select>
                        </label>
                        <label>
                          Idioma y región de la búsqueda
                          <input
                            aria-label="Idioma y región de la búsqueda"
                            required
                            maxLength={30}
                            value={search.locale}
                            onChange={(e) => change("locale", e.target.value)}
                            placeholder="es-CO"
                          />
                        </label>
                        <label>
                          Lugar o área relevante · opcional
                          <input
                            aria-label="Lugar o área relevante · opcional"
                            maxLength={160}
                            value={search.geography}
                            onChange={(e) =>
                              change("geography", e.target.value)
                            }
                          />
                        </label>
                        <label>
                          Contexto de la observación
                          <textarea
                            aria-label="Contexto de la observación"
                            required
                            maxLength={600}
                            value={search.observation_context}
                            onChange={(e) =>
                              change("observation_context", e.target.value)
                            }
                            placeholder="Consulta, dispositivo, idioma y cómo se hizo la observación"
                          />
                        </label>
                        {search.source_kind === "sampled_search" && (
                          <label>
                            Posición en esa muestra · opcional
                            <input
                              aria-label="Posición en esa muestra · opcional"
                              type="number"
                              min="1"
                              max="200"
                              step="1"
                              value={search.sampled_position ?? ""}
                              onChange={(e) =>
                                change(
                                  "sampled_position",
                                  e.target.value
                                    ? Number(e.target.value)
                                    : null,
                                )
                              }
                            />
                          </label>
                        )}
                        <p>
                          Una muestra no es una posición universal. No hay
                          volumen de búsqueda ni tráfico medido en este
                          registro.
                        </p>
                      </>
                    )}
                    <label>
                      Permiso y uso de esta fuente
                      <textarea
                        aria-label="Permiso y uso de esta fuente"
                        required
                        minLength={8}
                        maxLength={600}
                        value={item.permission}
                        onChange={(e) => change("permission", e.target.value)}
                      />
                    </label>
                    <label>
                      Revisar esta observación antes de
                      <input
                        aria-label="Revisar esta observación antes de"
                        required
                        type="date"
                        value={expiry}
                        onChange={(e) => {
                          setExpiry(e.target.value);
                          setConfirmed(false);
                        }}
                      />
                    </label>
                    <label className="social-check">
                      <input
                        type="checkbox"
                        checked={item.model_processing_allowed}
                        onChange={(e) =>
                          change("model_processing_allowed", e.target.checked)
                        }
                      />
                      El permiso también permite enviar estos apuntes al
                      proveedor de análisis configurado. No autoriza publicar ni
                      entrenar un modelo compartido.
                    </label>
                    <label className="social-check">
                      <input
                        type="checkbox"
                        checked={confirmed}
                        onChange={(e) => setConfirmed(e.target.checked)}
                      />
                      Revisé la fuente, las fechas y el permiso de esta
                      observación.
                    </label>
                    <div className="research-actions">
                      <button className="button primary" disabled={!confirmed}>
                        Guardar observación
                      </button>
                      <button
                        type="button"
                        className="button secondary"
                        onClick={() => {
                          setPost(null);
                          setSearch(null);
                        }}
                      >
                        Cerrar sin guardar
                      </button>
                    </div>
                  </fieldset>
                </form>
              )}
              <div className="research-records">
                {board.posts.map((p: any) => {
                  const analysis = board.analysis.posts.find(
                      (a: any) => a.id === p.id,
                    ),
                    ref = creative?.references.find(
                      (r) => r.id === p.reference_id,
                    );
                  return (
                    <article key={"post:" + p.id}>
                      <h3>{p.subject}</h3>
                      <p>
                        {groups[ref?.purpose] || "Referencia pendiente"} ·{" "}
                        {p.account_key} · {p.format}
                        {p.fixture ? " · prueba" : ""}
                      </p>
                      <p>
                        <strong>Observación:</strong> {p.observation}
                      </p>
                      <p>
                        <strong>Hipótesis:</strong> {p.hypothesis}
                      </p>
                      <p>
                        <strong>Otras explicaciones:</strong> {p.alternatives}
                      </p>
                      <p>
                        <strong>Prueba propuesta:</strong> {p.adaptation}
                      </p>
                      {analysis?.comparisons.map((m: any) => (
                        <p key={m.metric + ":" + m.window}>
                          {m.metric} · {m.window}:{" "}
                          {m.value === null ? "no disponible" : m.value}
                          {m.relative_to_median !== null
                            ? " · " +
                              m.relative_to_median.toFixed(2) +
                              " veces la mediana comparable"
                            : " · sin comparación suficiente"}{" "}
                          · {m.sample_size} publicaciones de referencia
                          {m.range ? " · rango " + m.range.join("–") : ""}.{" "}
                          {m.reason === "zero_baseline_raw_values_only"
                            ? "La mediana es cero; no calculamos una razón."
                            : m.window === "lifetime"
                              ? "Los totales acumulados no son datos a la misma edad."
                              : "Comparación descriptiva; no demuestra qué causó el resultado."}
                        </p>
                      ))}
                      <p>
                        Fuente: {p.source} · observada{" "}
                        {new Date(p.observed_at).toLocaleString("es-CO")} ·
                        revisar {p.valid_until.slice(0, 10)}.
                      </p>
                      {p.source_url && (
                        <p>
                          <a
                            href={p.source_url}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Ver fuente
                          </a>
                        </p>
                      )}
                      {!analysis && (
                        <p>
                          Retirada, vencida o con una referencia que necesita
                          revisión.
                        </p>
                      )}
                      {analysis && (
                        <label className="social-check">
                          <input
                            type="checkbox"
                            checked={selectedPosts.includes(p.id)}
                            disabled={
                              busy ||
                              (!selectedPosts.includes(p.id) &&
                                selectedPosts.length >= 4)
                            }
                            onChange={(e) =>
                              setSelectedPosts((old) =>
                                e.target.checked
                                  ? [...old, p.id]
                                  : old.filter((id) => id !== p.id),
                              )
                            }
                          />
                          Usar evidencia: {p.subject}
                        </label>
                      )}
                      <button
                        type="button"
                        className="button secondary"
                        disabled={busy}
                        onClick={() => begin("posts", p)}
                      >
                        Editar observación: {p.subject}
                      </button>
                      {p.status === "active" && (
                        <button
                          type="button"
                          className="button secondary"
                          disabled={busy}
                          onClick={() =>
                            void run(() =>
                              save("posts", {
                                ...clean(p, "posts"),
                                status: "withdrawn",
                              }),
                            )
                          }
                        >
                          Retirar observación: {p.subject}
                        </button>
                      )}
                    </article>
                  );
                })}
              </div>
              <div className="research-records">
                {board.searches.map((s: any) => {
                  const q = creative?.questions.find(
                    (q) => q.id === s.question_id,
                  );
                  return (
                    <article key={"search:" + s.id}>
                      <h3>{q?.text || "Pregunta pendiente"}</h3>
                      <p>{s.observation}</p>
                      <p>
                        {s.platform} · {s.locale}
                        {s.geography ? " · " + s.geography : ""} ·{" "}
                        {s.observation_context}
                      </p>
                      {s.sampled_position && (
                        <p>
                          Posición {s.sampled_position} solo en esta muestra y
                          contexto.
                        </p>
                      )}
                      <p>
                        Fuente: {s.source} · sin volumen de búsqueda medido.
                      </p>
                      {s.status === "active" && (
                        <label className="social-check">
                          <input
                            type="radio"
                            name={"research-search-" + business}
                            checked={selectedSearch === s.id}
                            onChange={() => setSelectedSearch(s.id)}
                          />
                          Usar búsqueda: {q?.text}
                        </label>
                      )}
                      <button
                        type="button"
                        className="button secondary"
                        disabled={busy}
                        onClick={() => begin("searches", s)}
                      >
                        Editar búsqueda: {q?.text}
                      </button>
                      {s.status === "active" && (
                        <button
                          type="button"
                          className="button secondary"
                          disabled={busy}
                          onClick={() =>
                            void run(() =>
                              save("searches", {
                                ...clean(s, "searches"),
                                status: "withdrawn",
                              }),
                            )
                          }
                        >
                          Retirar búsqueda: {q?.text}
                        </button>
                      )}
                    </article>
                  );
                })}
              </div>
              {selectedSearch && (
                <button
                  type="button"
                  className="button secondary"
                  onClick={() => setSelectedSearch("")}
                >
                  Quitar búsqueda de la selección
                </button>
              )}
              <p>
                Las próximas propuestas deben explicar qué se observó, qué
                podría explicarlo y qué probaríamos con material propio. El
                resultado de una cuenta no demuestra ventas ni horarios ideales.
              </p>
              <button
                type="button"
                className="button primary"
                disabled={
                  busy ||
                  !board.id ||
                  (!selectedPosts.length && !selectedSearch)
                }
                onClick={use}
              >
                Preparar propuesta con esta evidencia
              </button>
            </>
          )}
        </>
      )}
    </details>
  );
}
