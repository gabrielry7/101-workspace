import { useEffect, useState } from "react";
import { endpoint } from "./ui";
const local = (value: string | Date, seconds = false) => {
  const date = new Date(value);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, seconds ? 19 : 16);
};
const iso = (value: string) => new Date(value).toISOString();
const awareLocal = (value: string) => {
  const d = new Date(value),
    m = -d.getTimezoneOffset(),
    sign = m >= 0 ? "+" : "-";
  return (
    value +
    ":00" +
    sign +
    String(Math.floor(Math.abs(m) / 60)).padStart(2, "0") +
    ":" +
    String(Math.abs(m) % 60).padStart(2, "0")
  );
};
const metricLabels: Record<string, string> = {
  qualified_inquiries: "Consultas de compra",
  orders: "Pedidos reportados",
  reach: "Alcance",
  views: "Visualizaciones",
  comments: "Comentarios",
  shares: "Compartidos",
  saves: "Guardados",
  watch_seconds: "Tiempo de reproducción",
  search_views: "Visualizaciones desde búsquedas",
  net_revenue_minor: "Ingresos netos reportados",
  owner_effort_seconds: "Tiempo del propietario",
};
const availability: Record<string, string> = {
  measured: "Medido",
  unavailable: "No disponible",
  not_yet_collected: "Por recoger",
};
const actionLabels: Record<string, string> = {
  repeat: "Repetir",
  modify: "Cambiar un elemento",
  stop: "Detener esta idea",
  collect_evidence: "Recoger información",
  inconclusive: "Mantener inconcluso",
};
const resultErrors: Record<string, string> = {
  approved_publication_version_required:
    "Revisa y aprueba la versión actual antes de registrar su publicación.",
  publication_before_approval:
    "La fecha declarada es anterior a la aprobación de esta versión. Revisa la fecha y la versión.",
  publication_time_in_future: "La publicación no puede tener una fecha futura.",
  publication_already_recorded:
    "Ese enlace o identificador ya está registrado. Corrige el registro existente.",
  publication_destination_mismatch:
    "La cuenta no coincide con el destino aprobado. Corrige el destino en una nueva versión.",
  publication_revision_changed:
    "El registro cambió. Ábrelo de nuevo antes de corregirlo.",
  learning_evidence_changed:
    "Cambió un dato citado. Revisa los resultados y guarda una nueva decisión.",
  learning_decision_superseded:
    "Hay una decisión posterior para esta publicación.",
  result_correction_conflict:
    "Ese dato ya tiene una corrección. Usa su versión actual.",
  observation_before_publication:
    "El periodo comienza antes de la fecha registrada de publicación.",
  observation_in_future:
    "La fecha de observación debe corresponder a un momento que ya pasó.",
  lifetime_window_mismatch:
    "El acumulado debe comenzar en la fecha de publicación.",
  learning_observation_required:
    "Guarda al menos un resultado, incluso si es un dato no disponible, antes de decidir.",
  publication_withdrawn:
    "Este registro está retirado. Conservamos su historial.",
  plan_primary_differs_from_brief:
    "La medida principal debe coincidir con el propósito aprobado.",
  prospective_review_must_be_future: "Elige una fecha futura para la revisión.",
};
export function SocialResults({
  business,
  csrf,
  initialPublicationId,
  pack,
  dirty,
  onChanged,
  onLearning,
}: {
  initialPublicationId?: string;
  business: string;
  csrf: string;
  pack: any;
  dirty: boolean;
  onChanged: () => Promise<void>;
  onLearning: (value: any) => void;
}) {
  const root = endpoint(business) + "/social";
  const [pubs, setPubs] = useState<any[]>([]),
    [plans, setPlans] = useState<any[]>([]),
    [selected, setSelected] = useState(initialPublicationId || ""),
    [report, setReport] = useState<any>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [editReceipt, setEditReceipt] = useState<any>(null),
    [platform, setPlatform] = useState(
      pack.document.brief.handoff?.platform === "unspecified"
        ? "instagram"
        : pack.document.brief.handoff?.platform || "instagram",
    ),
    [account, setAccount] = useState(
      pack.document.brief.handoff?.account_label || "",
    ),
    [link, setLink] = useState(""),
    [postId, setPostId] = useState(""),
    [published, setPublished] = useState(local(new Date())),
    [source, setSource] = useState(""),
    [receiptReason, setReceiptReason] = useState(""),
    [matched, setMatched] = useState(false),
    [withdrawn, setWithdrawn] = useState(false);
  const primary =
    pack.document.brief.primary_measure === "owner_effort"
      ? "owner_effort_seconds"
      : pack.document.brief.primary_measure;
  const [planQuestion, setPlanQuestion] = useState(""),
    [difference, setDifference] = useState(""),
    [reviewAt, setReviewAt] = useState(
      local(new Date(Date.now() + 7 * 86400000)),
    ),
    [planReason, setPlanReason] = useState("");
  const [metric, setMetric] = useState(primary),
    [status, setStatus] = useState(""),
    [value, setValue] = useState(""),
    [definition, setDefinition] = useState(""),
    [currency, setCurrency] = useState(""),
    [windowKind, setWindowKind] = useState("lifetime_snapshot"),
    [start, setStart] = useState(""),
    [end, setEnd] = useState(local(new Date(), true)),
    [observed, setObserved] = useState(local(new Date(), true)),
    [sourceKind, setSourceKind] = useState("owner_report"),
    [metricSource, setMetricSource] = useState(""),
    [metricReason, setMetricReason] = useState(""),
    [search, setSearch] = useState(false),
    [testData, setTestData] = useState(false),
    [correcting, setCorrecting] = useState<string | null>(null);
  const [role, setRole] = useState("owner"),
    [minutes, setMinutes] = useState(""),
    [activity, setActivity] = useState("review"),
    [effortSource, setEffortSource] = useState(""),
    [effortReason, setEffortReason] = useState("");
  const [action, setAction] = useState("inconclusive"),
    [decisionReason, setDecisionReason] = useState(""),
    [nextQuestion, setNextQuestion] = useState("");
  async function request(path: string, method = "GET", body?: unknown) {
    const res = await fetch(root + path, {
      method,
      headers: { "Content-Type": "application/json", "X-101-CSRF": csrf },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok)
      throw new Error(
        typeof data.detail === "string"
          ? resultErrors[data.detail] || data.detail
          : "Revisa los campos, las fechas y las fuentes.",
      );
    return data;
  }
  async function refresh(id = selected) {
    const d = await request("/packs/" + pack.id + "/publications");
    setPubs(d.publications);
    setPlans(d.plans);
    const current = id || d.publications[0]?.id || "";
    setSelected(current);
    if (current)
      setReport(await request("/publications/" + current + "/report"));
    else setReport(null);
  }
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
  useEffect(() => {
    void run(() => refresh(initialPublicationId || selected));
  }, [pack.id, pack.digest, initialPublicationId]);
  useEffect(() => {
    if (selected) {
      setCorrecting(null);
      setStatus("");
      setValue("");
      setEnd(local(new Date(), true));
      setObserved(local(new Date(), true));
      setEditReceipt(null);
    }
  }, [selected]);
  const pub = pubs.find((p) => p.id === selected),
    latestPlan = plans.filter((p) => p.request.digest === pack.digest).at(-1);
  function editPublication(p: any) {
    setEditReceipt(p);
    setPlatform(p.platform);
    setAccount(p.account);
    setLink(p.permalink);
    setPostId(p.provider_post_id);
    setPublished(local(p.published_at_utc));
    setSource(p.source_ref);
    setReceiptReason("");
    setMatched(false);
    setWithdrawn(p.status === "withdrawn");
    document
      .getElementById("manual-receipt")
      ?.scrollIntoView({ behavior: "smooth" });
  }
  function correctMetric(o: any) {
    const p = o.request;
    setCorrecting(o.id);
    setMetric(p.metric);
    setStatus(p.availability);
    setValue(p.value === null ? "" : String(p.value));
    setDefinition(p.definition);
    setCurrency(p.currency || "");
    setWindowKind(p.window_kind);
    setStart(local(p.window_start, true));
    setEnd(local(p.window_end, true));
    setObserved(local(p.observed_at, true));
    setSourceKind(p.source_kind);
    setMetricSource(p.source_ref);
    setMetricReason("");
    setSearch(p.search_specific);
    setTestData(p.test_data);
    document
      .getElementById("manual-metric")
      ?.scrollIntoView({ behavior: "smooth" });
  }
  return (
    <section className="production-jobs social-results" id="social-results">
      <h2>Publicación y resultados</h2>
      <p>
        Registra lo que publicaste y lo que pudiste observar. Son datos
        declarados por el negocio; no hay verificación automática de la
        plataforma.
      </p>
      {pack.document.fixture && (
        <p className="results-fixture">
          Material de prueba · los resultados también deben interpretarse como
          una demostración.
        </p>
      )}
      {error && <p role="alert">{error}</p>}
      <details className="results-plan">
        <summary>Qué queremos aprender</summary>
        <p>
          Una pregunta, un cambio a observar y una medida principal. Publicar en
          días distintos es una comparación observacional.
        </p>
        {latestPlan && (
          <div className="results-receipt">
            <p>{latestPlan.request.question}</p>
            <p>Cambio: {latestPlan.request.variant_difference}</p>
            <p>
              Revisión prevista:{" "}
              {new Date(latestPlan.request.review_at).toLocaleString("es-CO")}
            </p>
          </div>
        )}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void run(async () => {
              await request("/packs/" + pack.id + "/measurement-plan", "POST", {
                request_id: crypto.randomUUID(),
                digest: pack.digest,
                supersedes_id: latestPlan?.id || null,
                question: planQuestion,
                variant_difference: difference,
                primary_metric: primary,
                review_at: iso(reviewAt),
                reason: planReason,
              });
              await refresh();
            });
          }}
        >
          <fieldset disabled={busy || dirty || !pack.approved}>
            <label>
              Pregunta de la comparación
              <input
                required
                maxLength={500}
                value={planQuestion}
                onChange={(e) => setPlanQuestion(e.target.value)}
              />
            </label>
            <label>
              Diferencia que queremos observar
              <input
                required
                maxLength={500}
                value={difference}
                onChange={(e) => setDifference(e.target.value)}
                placeholder="Por ejemplo: explicar el siguiente paso con más claridad"
              />
            </label>
            <p>Medida principal: {metricLabels[primary]}.</p>
            <label>
              Cuándo revisar
              <input
                required
                type="datetime-local"
                value={reviewAt}
                onChange={(e) => setReviewAt(e.target.value)}
              />
            </label>
            <label>
              Motivo del plan
              <input
                required
                maxLength={600}
                value={planReason}
                onChange={(e) => setPlanReason(e.target.value)}
              />
            </label>
            <button className="button secondary">
              Guardar pregunta y revisión
            </button>
          </fieldset>
        </form>
        {!pack.approved && <p>Aprueba la versión para guardar su plan.</p>}
      </details>
      {pubs.length > 0 && (
        <label>
          Publicación registrada
          <select
            aria-label="Publicación registrada"
            value={selected}
            onChange={(e) => void run(() => refresh(e.target.value))}
          >
            {pubs.map((p) => (
              <option key={p.id} value={p.id}>
                {p.platform} · {p.account} · versión de contenido{" "}
                {p.revision_id.split(":").at(-1)}
                {p.status === "withdrawn" ? " · retirado" : ""}
              </option>
            ))}
          </select>
        </label>
      )}
      {pub && (
        <div className="results-receipt">
          <p>
            <strong>{pub.account}</strong> ·{" "}
            {new Date(pub.published_at_utc).toLocaleString("es-CO")} ·{" "}
            {pub.timezone} · precisión{" "}
            {pub.timestamp_precision === "minute"
              ? "de un minuto"
              : "de un segundo"}
          </p>
          <p>
            <a href={pub.permalink} target="_blank" rel="noreferrer">
              Abrir publicación declarada
            </a>
          </p>
          <p>
            Fuente: {pub.source_ref}. Registro manual{" "}
            {pub.fixture ? "de prueba" : ""}; cuenta y contenido sin
            verificación independiente.
          </p>
          <p>
            Contenido: versión {pub.revision_id.split(":").at(-1)}. Corrección
            del registro: {pub.revision}.
          </p>
          <button
            className="button secondary"
            disabled={busy}
            onClick={() => editPublication(pub)}
          >
            Corregir registro
          </button>
          {pub.status === "withdrawn" && (
            <p role="status">Registro retirado; el historial se conserva.</p>
          )}
        </div>
      )}
      <details
        className="results-receipt-form"
        open={!!editReceipt || undefined}
        id="manual-receipt"
      >
        <summary>
          {editReceipt
            ? "Corregir los datos de publicación"
            : "Registrar una publicación manual"}
        </summary>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void run(async () => {
              const data = {
                request_id: crypto.randomUUID(),
                digest: editReceipt
                  ? editReceipt.approval.binding.digest
                  : pack.digest,
                platform,
                account,
                permalink: link,
                provider_post_id: postId,
                published_at: awareLocal(published),
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                timestamp_precision: "minute",
                source_ref: source,
                matches_approved: matched,
                status: withdrawn ? "withdrawn" : "active",
                reason: receiptReason,
                ...(editReceipt
                  ? { expected_revision: editReceipt.revision }
                  : {}),
              };
              const saved = await request(
                editReceipt
                  ? "/publications/" + editReceipt.id
                  : "/packs/" + pack.id + "/publications",
                editReceipt ? "PUT" : "POST",
                data,
              );
              setEditReceipt(null);
              setMatched(false);
              await refresh(saved.id);
              await onChanged();
            });
          }}
        >
          <fieldset
            disabled={busy || dirty || (!editReceipt && !pack.approved)}
          >
            <div className="results-fields">
              <label>
                Plataforma publicada
                <select
                  aria-label="Plataforma publicada"
                  value={platform}
                  onChange={(e) => setPlatform(e.target.value)}
                >
                  <option value="instagram">Instagram</option>
                  <option value="facebook">Facebook</option>
                  <option value="tiktok">TikTok</option>
                </select>
              </label>
              <label>
                Cuenta publicada
                <input
                  required
                  maxLength={120}
                  value={account}
                  onChange={(e) => setAccount(e.target.value)}
                />
              </label>
            </div>
            <label>
              Enlace de la publicación
              <input
                required
                type="url"
                maxLength={500}
                value={link}
                onChange={(e) => setLink(e.target.value)}
              />
            </label>
            <label>
              Identificador de la plataforma · opcional
              <input
                maxLength={160}
                value={postId}
                onChange={(e) => setPostId(e.target.value)}
              />
            </label>
            <label>
              Fecha y hora publicadas
              <input
                required
                type="datetime-local"
                value={published}
                onChange={(e) => setPublished(e.target.value)}
              />
            </label>
            <p>
              Hora expresada en la zona de este dispositivo:{" "}
              {Intl.DateTimeFormat().resolvedOptions().timeZone}. No determina
              la ubicación del negocio.
            </p>
            <label>
              Fuente del registro
              <input
                required
                minLength={3}
                maxLength={500}
                value={source}
                onChange={(e) => setSource(e.target.value)}
                placeholder="Quién lo publicó y cómo comprobaste la fecha"
              />
            </label>
            <label>
              Motivo del registro o corrección
              <textarea
                aria-label="Motivo del registro o corrección"
                required
                maxLength={600}
                value={receiptReason}
                onChange={(e) => setReceiptReason(e.target.value)}
              />
            </label>
            {editReceipt && (
              <label className="social-check">
                <input
                  type="checkbox"
                  checked={withdrawn}
                  onChange={(e) => setWithdrawn(e.target.checked)}
                />
                Retirar este registro sin borrar su historial.
              </label>
            )}
            <label className="social-check">
              <input
                type="checkbox"
                checked={matched}
                onChange={(e) => setMatched(e.target.checked)}
              />
              La publicación usa esta versión aprobada y la cuenta indicada.
            </label>
            <button className="button secondary" disabled={!matched}>
              {editReceipt
                ? "Guardar corrección de publicación"
                : "Guardar publicación manual"}
            </button>
            {editReceipt && (
              <button
                type="button"
                className="button secondary"
                onClick={() => setEditReceipt(null)}
              >
                Cancelar corrección
              </button>
            )}
          </fieldset>
        </form>
      </details>
      {report && pub && (
        <div className="results-report">
          <h3>Lo que sabemos de esta publicación</h3>
          <div className="results-primary">
            <p>{metricLabels[report.primary.metric]}</p>
            <strong>
              {report.primary.value === null
                ? "Sin un dato comparable"
                : report.primary.value}
            </strong>
            <p>
              {availability[report.primary.availability]}
              {report.primary.definition
                ? " · " + report.primary.definition
                : ""}
            </p>
          </div>
          <p>
            Las cifras provienen de las fuentes que registres. Un pedido
            reportado no es una transacción conciliada; no sumamos atribuciones
            de distintas fuentes.
          </p>
          {report.plan && (
            <p>
              Pregunta: {report.plan.request.question}.{" "}
              {report.plan.timing === "prospective"
                ? "Declarada antes de la publicación."
                : report.plan.timing === "retrospective"
                  ? "Declarada después de la publicación."
                  : "La precisión de la hora no permite asegurar si se declaró antes de publicar."}{" "}
              {report.review_due
                ? "Llegó el momento previsto de revisión."
                : "La revisión prevista todavía no ha llegado."}
            </p>
          )}
          <details id="manual-metric" className="results-observation-form">
            <summary>
              {correcting ? "Corregir una observación" : "Añadir un resultado"}
            </summary>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void run(async () => {
                  await request(
                    "/publications/" + pub.id + "/observations",
                    "POST",
                    {
                      request_id: crypto.randomUUID(),
                      supersedes_id: correcting,
                      metric,
                      availability: status,
                      value: status === "measured" ? Number(value) : null,
                      currency:
                        metric === "net_revenue_minor" ? currency : null,
                      definition,
                      window_kind: windowKind,
                      window_start:
                        windowKind === "lifetime_snapshot"
                          ? pub.published_at_utc
                          : iso(start),
                      window_end: iso(end),
                      observed_at: iso(observed),
                      source_kind: sourceKind,
                      source_ref: metricSource,
                      reason: metricReason,
                      search_specific: search,
                      test_data: testData,
                    },
                  );
                  setCorrecting(null);
                  setValue("");
                  setStatus("");
                  await refresh();
                });
              }}
            >
              <fieldset disabled={busy || pub.status !== "active"}>
                <label>
                  Medida observada
                  <select
                    aria-label="Medida observada"
                    value={metric}
                    disabled={!!correcting}
                    onChange={(e) => setMetric(e.target.value)}
                  >
                    {Object.entries(metricLabels).map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Disponibilidad del dato
                  <select
                    required
                    aria-label="Disponibilidad del dato"
                    value={status}
                    onChange={(e) => setStatus(e.target.value)}
                  >
                    <option value="">Seleccionar</option>
                    {Object.entries(availability).map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
                {status === "measured" && (
                  <label>
                    Valor medido
                    {metric === "net_revenue_minor"
                      ? " · unidades monetarias menores"
                      : metric.includes("seconds")
                        ? " · segundos"
                        : ""}
                    <input
                      required
                      type="number"
                      min={metric === "net_revenue_minor" ? undefined : 0}
                      step="1"
                      value={value}
                      onChange={(e) => setValue(e.target.value)}
                    />
                  </label>
                )}
                {metric === "net_revenue_minor" && (
                  <label>
                    Moneda del ingreso
                    <input
                      required
                      pattern="[A-Z]{3}"
                      maxLength={3}
                      value={currency}
                      onChange={(e) =>
                        setCurrency(e.target.value.toUpperCase())
                      }
                      placeholder="COP"
                    />
                  </label>
                )}
                <label>
                  Qué cuenta exactamente esta medida
                  <textarea
                    aria-label="Qué cuenta exactamente esta medida"
                    required
                    minLength={3}
                    maxLength={500}
                    value={definition}
                    onChange={(e) => setDefinition(e.target.value)}
                  />
                </label>
                <label>
                  Tipo de periodo
                  <select
                    aria-label="Tipo de periodo"
                    value={windowKind}
                    onChange={(e) => setWindowKind(e.target.value)}
                  >
                    <option value="lifetime_snapshot">
                      Acumulado desde la publicación
                    </option>
                    <option value="period">Periodo específico</option>
                  </select>
                </label>
                {windowKind === "period" && (
                  <label>
                    Inicio del periodo
                    <input
                      required
                      type="datetime-local"
                      step="1"
                      value={start}
                      onChange={(e) => setStart(e.target.value)}
                    />
                  </label>
                )}
                <div className="results-fields">
                  <label>
                    Fin del periodo
                    <input
                      required
                      type="datetime-local"
                      step="1"
                      value={end}
                      onChange={(e) => setEnd(e.target.value)}
                    />
                  </label>
                  <label>
                    Cuándo observaste el dato
                    <input
                      required
                      type="datetime-local"
                      step="1"
                      value={observed}
                      onChange={(e) => setObserved(e.target.value)}
                    />
                  </label>
                </div>
                <label>
                  Origen del dato
                  <select
                    aria-label="Origen del dato"
                    value={sourceKind}
                    onChange={(e) => setSourceKind(e.target.value)}
                  >
                    <option value="owner_report">Conteo del negocio</option>
                    <option value="owner_entered_provider_export">
                      Dato de plataforma ingresado manualmente
                    </option>
                    <option value="owner_entered_first_party_report">
                      Reporte propio ingresado manualmente
                    </option>
                  </select>
                </label>
                <label>
                  Fuente de la observación
                  <input
                    required
                    minLength={3}
                    maxLength={500}
                    value={metricSource}
                    onChange={(e) => setMetricSource(e.target.value)}
                    placeholder="Reporte, captura o registro donde lo viste"
                  />
                </label>
                <label>
                  Motivo o limitación
                  <textarea
                    aria-label="Motivo o limitación"
                    required={status !== "measured" || !!correcting}
                    maxLength={600}
                    value={metricReason}
                    onChange={(e) => setMetricReason(e.target.value)}
                  />
                </label>
                {metric === "search_views" && (
                  <label className="social-check">
                    <input
                      type="checkbox"
                      checked={search}
                      onChange={(e) => setSearch(e.target.checked)}
                    />
                    La fuente distingue tráfico de búsqueda de las
                    recomendaciones.
                  </label>
                )}
                <label className="social-check">
                  <input
                    type="checkbox"
                    checked={testData}
                    onChange={(e) => setTestData(e.target.checked)}
                  />
                  Dato de prueba: excluir de las decisiones.
                </label>
                <button className="button secondary">
                  {correcting
                    ? "Guardar corrección del resultado"
                    : "Guardar resultado"}
                </button>
                {correcting && (
                  <button
                    type="button"
                    className="button secondary"
                    onClick={() => setCorrecting(null)}
                  >
                    Cancelar corrección del resultado
                  </button>
                )}
              </fieldset>
            </form>
          </details>
          <div className="results-observations">
            {report.observations.map((o: any) => (
              <article key={o.id}>
                <h4>
                  {metricLabels[o.request.metric]} ·{" "}
                  {o.request.value === null
                    ? availability[o.request.availability]
                    : o.request.value}
                </h4>
                <p>
                  {o.request.definition} ·{" "}
                  {
                    (
                      {
                        count: "conteo",
                        seconds: "segundos",
                        minor_currency: "unidades monetarias menores",
                      } as Record<string, string>
                    )[o.unit]
                  }
                  {o.request.currency ? " · " + o.request.currency : ""}
                </p>
                <p>
                  {new Date(o.request.window_start).toLocaleString("es-CO")} →{" "}
                  {new Date(o.request.window_end).toLocaleString("es-CO")} ·{" "}
                  {o.request.window_kind === "lifetime_snapshot"
                    ? "acumulado"
                    : "periodo"}
                </p>
                <p>
                  Fuente: {o.request.source_ref}. {o.request.reason}
                </p>
                {o.stale && (
                  <p>
                    El registro de publicación cambió; confirma o corrige esta
                    observación.
                  </p>
                )}
                {o.request.test_data && <p>Dato de prueba · excluido.</p>}
                <button
                  type="button"
                  className="button secondary"
                  onClick={() => {
                    correctMetric(o);
                    document.querySelector<HTMLDetailsElement>(
                      "#manual-metric",
                    )!.open = true;
                  }}
                >
                  Corregir este resultado
                </button>
              </article>
            ))}
          </div>
          <details className="results-effort">
            <summary>Tiempo y costo de producir este trabajo</summary>
            <p>
              Versiones guardadas: {report.production.revision_count}. Intentos
              de procesamiento: {report.production.attempt_count}.
            </p>
            <p>
              Costo externo registrado:{" "}
              {report.production.provider_microusd === null
                ? "sin registro completo"
                : report.production.provider_microusd / 1e6 + " USD"}
              . Cómputo, almacenamiento y total: sin precio completo.
            </p>
            <p>
              Tiempo en tareas: propietario{" "}
              {report.production.recorded_job_effort_seconds.owner ??
                "sin dato"}{" "}
              s; revisor{" "}
              {report.production.recorded_job_effort_seconds.reviewer ??
                "sin dato"}{" "}
              s.
            </p>
            <p>
              Tiempo adicional declarado: propietario{" "}
              {report.production.reported_activity_effort_seconds.owner ??
                "sin dato"}{" "}
              s; revisor{" "}
              {report.production.reported_activity_effort_seconds.reviewer ??
                "sin dato"}{" "}
              s. Estos registros se muestran separados para evitar sumarlos dos
              veces.
            </p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void run(async () => {
                  await request("/publications/" + pub.id + "/effort", "POST", {
                    request_id: crypto.randomUUID(),
                    role,
                    activity,
                    seconds: Math.round(Number(minutes) * 60),
                    source_ref: effortSource,
                    reason: effortReason,
                  });
                  await refresh();
                });
              }}
            >
              <fieldset disabled={busy}>
                <label>
                  Quién dedicó el tiempo
                  <select
                    aria-label="Quién dedicó el tiempo"
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                  >
                    <option value="owner">Propietario</option>
                    <option value="reviewer">Revisor</option>
                  </select>
                </label>
                <label>
                  Actividad realizada
                  <select
                    aria-label="Actividad realizada"
                    value={activity}
                    onChange={(e) => setActivity(e.target.value)}
                  >
                    <option value="capture">Captura de material</option>
                    <option value="upload">Carga</option>
                    <option value="review">Revisión</option>
                    <option value="revision">Corrección</option>
                    <option value="reporting">Registro de resultados</option>
                  </select>
                </label>
                <label>
                  Minutos dedicados
                  <input
                    required
                    type="number"
                    min="0"
                    max="1440"
                    step="0.1"
                    value={minutes}
                    onChange={(e) => setMinutes(e.target.value)}
                  />
                </label>
                <label>
                  Fuente del tiempo declarado
                  <input
                    required
                    minLength={3}
                    maxLength={500}
                    value={effortSource}
                    onChange={(e) => setEffortSource(e.target.value)}
                  />
                </label>
                <label>
                  Motivo del registro de tiempo
                  <input
                    required
                    maxLength={600}
                    value={effortReason}
                    onChange={(e) => setEffortReason(e.target.value)}
                  />
                </label>
                <button className="button secondary">
                  Guardar tiempo declarado
                </button>
              </fieldset>
            </form>
          </details>
          <div className="results-next">
            <h3>Qué hacemos después</h3>
            <p>{report.summary}</p>
            <p>
              Propuesta inicial: {actionLabels[report.suggested_action]}. Es una
              decisión a revisar, sin prueba de causalidad.
            </p>
            <details
              className="results-decision-form"
              open={!report.decisions.length || report.decisions.at(-1)?.stale}
            >
              <summary>Revisar la siguiente decisión</summary>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  void run(async () => {
                    await request(
                      "/publications/" + pub.id + "/decisions",
                      "POST",
                      {
                        request_id: crypto.randomUUID(),
                        evidence_digest: report.evidence_digest,
                        evidence_ids: [
                          ...new Set(
                            [
                              report.primary.event_id,
                              ...report.available_evidence_ids,
                            ].filter(Boolean),
                          ),
                        ].slice(0, 20),
                        action,
                        owner_reason: decisionReason,
                        next_question: nextQuestion,
                      },
                    );
                    await refresh();
                  });
                }}
              >
                <fieldset disabled={busy || pub.status !== "active"}>
                  <label>
                    Decisión para la siguiente ronda
                    <select
                      aria-label="Decisión para la siguiente ronda"
                      value={action}
                      onChange={(e) => setAction(e.target.value)}
                    >
                      {Object.entries(actionLabels).map(([key, label]) => (
                        <option key={key} value={key}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Por qué elegimos esta decisión
                    <textarea
                      aria-label="Por qué elegimos esta decisión"
                      required
                      minLength={3}
                      maxLength={800}
                      value={decisionReason}
                      onChange={(e) => setDecisionReason(e.target.value)}
                    />
                  </label>
                  <label>
                    Pregunta para el siguiente contenido
                    <input
                      required
                      minLength={3}
                      maxLength={300}
                      value={nextQuestion}
                      onChange={(e) => setNextQuestion(e.target.value)}
                    />
                  </label>
                  <button
                    className="button secondary"
                    disabled={
                      !report.observations.some(
                        (o: any) => !o.stale && !o.request.test_data,
                      )
                    }
                  >
                    Guardar siguiente decisión
                  </button>
                </fieldset>
              </form>
            </details>
            {report.decisions.map((d: any) => (
              <article className="results-decision" key={d.id}>
                <h4>{actionLabels[d.request.action]}</h4>
                <details>
                  <summary>Ver datos citados</summary>
                  <p>{d.summary}</p>
                </details>
                <p>{d.request.owner_reason}</p>
                <p>Siguiente pregunta: {d.request.next_question}</p>
                {d.stale ? (
                  <p>
                    Los datos citados cambiaron. Guarda una decisión con la
                    información actual.
                  </p>
                ) : ["repeat", "modify", "inconclusive"].includes(
                    d.request.action,
                  ) && d.id === report.decisions.at(-1)?.id ? (
                  <button
                    type="button"
                    className="button primary"
                    onClick={() =>
                      onLearning({
                        id: d.id,
                        summary: d.summary,
                        next_question: d.request.next_question,
                      })
                    }
                  >
                    Usar para el siguiente contenido
                  </button>
                ) : (
                  <p>Esta decisión no inicia otra producción.</p>
                )}
              </article>
            ))}
          </div>
          <details className="results-history">
            <summary>Historial de fuentes y correcciones</summary>
            <p>
              {report.record_count} registros de resultados. Las correcciones
              conservan el dato anterior.
            </p>
            {report.history.map((e: any) => (
              <p key={e.id}>
                {new Date(e.at * 1000).toLocaleString("es-CO")} ·{" "}
                {e.kind === "metric"
                  ? `${metricLabels[e.request.metric]}: ${e.request.value ?? availability[e.request.availability]}`
                  : e.kind === "effort"
                    ? "Tiempo declarado"
                    : actionLabels[e.request.action]}
                {e.supersedes_id ? " · corrige un registro anterior" : ""}
              </p>
            ))}
          </details>
        </div>
      )}
    </section>
  );
}
