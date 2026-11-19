import { useEffect, useState } from "react";
import { api, endpoint, useResource, Failure, Loading } from "./ui";
import { OperationNotice, useOperation } from "./operations-ui";
import {
  ReadinessSummary,
  blocker,
  type ChannelConfig,
  type Readiness,
} from "./channel-config";
import type { Draft, Meta, Preview } from "./campaign-workspace";

export function PhoneCampaignFields({
  business,
  form,
  change,
}: {
  business: string;
  form: Draft;
  change: (d: Draft) => void;
}) {
  const data = useResource<ChannelConfig>(
    form.channel !== "email" ? endpoint(business) + "/" + form.channel : null,
  );
  const templates = data.data?.templates || [],
    t = templates.find((t) => t.id === form.whatsapp_template_id),
    count = t?.body ? new Set(t.body.match(/\{\{\d+\}\}/g) || []).size : 0;
  useEffect(() => {
    if (data.data?.sender && !form.sender)
      change({
        ...form,
        sender: String(
          data.data.sender[
            form.channel === "whatsapp" ? "phone_id" : "sender"
          ] || "",
        ),
      });
  }, [data.data]);
  return (
    <>
      {data.error ? (
        <Failure message={data.error} retry={data.retry} />
      ) : !data.data ? (
        <Loading />
      ) : (
        <>
          <a
            href={`/workspace/connections?business=${encodeURIComponent(business)}&provider=${form.channel}`}
          >
            Configurar este canal
          </a>
          {!data.data.sender && (
            <p className="action-notice">
              Falta configurar el remitente. Puedes hacerlo en Conexiones.
            </p>
          )}
          <label>
            Remitente del canal
            <input
              value={form.sender}
              onChange={(e) => change({ ...form, sender: e.target.value })}
              required
              maxLength={320}
            />
          </label>
          <small>
            Usa el identificador de número de WhatsApp o el remitente SMS de la
            configuración.
          </small>
          {form.channel === "whatsapp" ? (
            <>
              <label>
                Plantilla de WhatsApp
                <select
                  aria-label="Plantilla de WhatsApp"
                  required
                  value={form.whatsapp_template_id || ""}
                  onChange={(e) => {
                    const t = templates.find((t) => t.id === e.target.value);
                    if (!t) return;
                    const n = new Set(t.body?.match(/\{\{\d+\}\}/g) || []).size;
                    change({
                      ...form,
                      whatsapp_template_id: t.id,
                      whatsapp_parameters: Array.from({ length: n }, () => ""),
                      content: {
                        ...form.content,
                        subject: form.content.subject || t.name,
                        title: form.content.title || t.name,
                        body: t.body || form.content.body,
                        terms: t.footer || form.content.terms,
                      },
                    });
                  }}
                >
                  <option value="">Elige una plantilla registrada</option>
                  {templates.map((t) => (
                    <option
                      key={t.id}
                      value={t.id}
                      disabled={!t.body || t.status !== "APPROVED"}
                    >
                      {t.name} · {t.language} · {t.status}
                    </option>
                  ))}
                </select>
              </label>
              {t && (
                <>
                  <p className="message-copy">{t.body}</p>
                  <p>{t.footer}</p>
                  {Array.from({ length: count }, (_, i) => (
                    <label key={i}>
                      Parámetro {i + 1}
                      <input
                        aria-label={`Parámetro ${i + 1}`}
                        value={form.whatsapp_parameters[i] || ""}
                        required
                        maxLength={500}
                        onChange={(e) => {
                          const values = [...form.whatsapp_parameters];
                          values[i] = e.target.value;
                          change({ ...form, whatsapp_parameters: values });
                        }}
                      />
                    </label>
                  ))}
                </>
              )}
              <p className="source-note">
                El mensaje enviado usa esta plantilla y sus parámetros. Asunto y
                título identifican la campaña. El enlace para pedir y la opción
                de baja se conservan.
              </p>
            </>
          ) : (
            <p className="source-note">
              SMS incluye el cuerpo, las condiciones, la marca y los enlaces
              completos de pedido y baja. La revisión calcula segmentos y costo
              por destinatario; no se calcula solo con el texto escrito aquí.
            </p>
          )}
        </>
      )}
    </>
  );
}
export function CampaignBusinessTools({
  business,
  csrf,
  canWrite,
  meta,
  changed,
  open,
  setOpen,
}: {
  business: string;
  csrf: string;
  canWrite: boolean;
  meta: Meta;
  changed: () => void;
  open: boolean;
  setOpen: (value: boolean) => void;
}) {
  const readiness = useResource<Readiness>(
      endpoint(business) + "/campaigns/provider-readiness",
    ),
    op = useOperation(csrf),
    [confirm, setConfirm] = useState(false);
  return (
    <details
      className="work-surface campaign-business-tools"
      open={open}
      onToggle={(e) => setOpen(e.currentTarget.open)}
    >
      <summary>Estado de canales y control de envíos</summary>
      <p>
        Los envíos están {meta.paused ? "pausados" : "sin pausa"} para este
        negocio.
      </p>
      <p className="source-note">
        Al procesar trabajos durante una pausa, los pendientes vencidos pueden
        quedar omitidos. Reanudar no vuelve a enviar trabajos omitidos.
      </p>
      {canWrite && (
        <button
          className="button secondary"
          disabled={op.busy || op.uncertain}
          onClick={() => setConfirm(true)}
        >
          {meta.paused ? "Reanudar envíos" : "Pausar envíos"}
        </button>
      )}
      {confirm && (
        <div className="operation-notice">
          <p>
            {meta.paused
              ? "Se quitará la pausa. Los trabajos omitidos conservarán su estado."
              : "Se pausarán los envíos de todas las campañas y respuestas de este negocio."}
          </p>
          <button
            className="button secondary"
            disabled={op.busy}
            onClick={() => setConfirm(false)}
          >
            Volver
          </button>
          <button
            className="button primary"
            disabled={op.busy || op.uncertain}
            onClick={async () => {
              const result = await op.perform(
                endpoint(business) + "/campaigns/pause",
                { paused: !meta.paused },
              );
              setConfirm(false);
              if (result) {
                changed();
                op.setMessage("Estado de envíos guardado.");
              }
            }}
          >
            Confirmar cambio de envíos
          </button>
        </div>
      )}
      <button
        className="button secondary"
        disabled={op.busy}
        onClick={async () => {
          try {
            await api(endpoint(business) + "/campaigns");
            changed();
            readiness.retry();
            op.checked();
          } catch {
            op.setMessage("No pudimos comprobar el estado de envíos.");
          }
        }}
      >
        Comprobar control de envíos
      </button>
      <OperationNotice message={op.message} />
      {readiness.error ? (
        <Failure message={readiness.error} retry={readiness.retry} />
      ) : readiness.data ? (
        <ReadinessSummary data={readiness.data} />
      ) : (
        <Loading />
      )}
      <a
        href={`/workspace/connections?business=${encodeURIComponent(business)}&provider=whatsapp`}
      >
        Ver remitentes y plantillas
      </a>
    </details>
  );
}
type Review = {
  id: string;
  state: string;
  send_authorized?: boolean;
  document: {
    message: { text: string };
    recipient: { name: string; destination: string };
    revision_digest: string;
    campaign_id: string;
    expires_at: string;
    max_cost_microusd: number;
    estimated_cost_microusd: number | null;
    blockers: string[];
    send_authorized: false;
  };
};
export function ProviderTestReview({
  business,
  csrf,
  canWrite,
  preview,
  meta,
  params,
  navigate,
}: {
  business: string;
  csrf: string;
  canWrite: boolean;
  preview: Preview;
  meta: Meta;
  params: URLSearchParams;
  navigate: (changes: Record<string, string | null>) => void;
}) {
  const root = endpoint(business) + "/campaigns/provider-test-reviews",
    id = params.get("test_review"),
    saved = useResource<Review>(
      id ? root + "/" + encodeURIComponent(id) : null,
    ),
    op = useOperation(csrf),
    [review, setReview] = useState<Review>(),
    [confirm, setConfirm] = useState(false);
  const candidate = review || saved.data;
  const d =
    candidate?.document.campaign_id === preview.id ? candidate : undefined;
  return (
    <details
      className="work-surface provider-test-review"
      open={id ? true : undefined}
    >
      <summary>Preparar revisión de una prueba limitada</summary>
      {candidate && !d && (
        <p role="alert">
          Esta revisión pertenece a otra campaña. Abre la campaña
          correspondiente.
        </p>
      )}
      <p>
        Guarda una revisión para un destinatario y una versión exacta. No
        autoriza ni envía el mensaje.
      </p>
      {canWrite && (
        <form
          className="channel-form"
          onSubmit={async (e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            if (!confirm) return;
            const result = await op.perform<Review>(root, {
              campaign_id: preview.id,
              customer_id: String(f.get("customer")),
              revision_digest: preview.digest,
              max_cost_microusd: Math.round(Number(f.get("cost")) * 1e6),
              recipient_authorization_source: String(f.get("source")),
              expires_at: new Date(String(f.get("expiry"))).toISOString(),
            });
            if (result) {
              setReview(result);
              setConfirm(false);
              navigate({ test_review: result.id });
            }
          }}
        >
          <fieldset disabled={op.busy || op.uncertain}>
            <label>
              Destinatario de la revisión
              <select name="customer" required>
                {preview.audience.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name || p.destination || p.id}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Fuente de autorización del destinatario
              <input name="source" required minLength={10} maxLength={500} />
            </label>
            <label>
              Límite de costo · USD
              <input
                type="number"
                name="cost"
                min={0}
                max={10}
                step="0.000001"
                required
              />
            </label>
            <label>
              Vence · hora local de este dispositivo
              <input type="datetime-local" name="expiry" required />
            </label>
            <p className="source-note">
              Debe vencer dentro de las 24 horas posteriores al reloj del
              entorno: {new Date(meta.clock).toLocaleString("es-CO")}.
            </p>
            <label className="review-check">
              <input
                type="checkbox"
                checked={confirm}
                onChange={(e) => setConfirm(e.target.checked)}
              />
              Revisé la versión, el destinatario y el límite. Esto no envía.
            </label>
            <button className="button secondary" disabled={!confirm || op.busy}>
              Preparar revisión limitada
            </button>
          </fieldset>
        </form>
      )}
      <OperationNotice message={op.message} />
      {saved.error && (
        <Failure message={saved.error} retry={saved.retry} />
      )}{" "}
      {d && (
        <article className="test-review-result">
          <h3>
            {d.state === "stale"
              ? "Revisión desactualizada"
              : "Prueba bloqueada"}
          </h3>
          <p>Envío autorizado: no.</p>
          <p>
            {d.document.recipient.name} · {d.document.recipient.destination}
          </p>
          <p className="message-copy">{d.document.message.text}</p>
          <small>Versión: {d.document.revision_digest}</small>
          <p>
            Vigencia: {new Date(d.document.expires_at).toLocaleString("es-CO")}
          </p>
          <ul>
            {d.document.blockers.map((b) => (
              <li key={b}>{blocker(b)}</li>
            ))}
          </ul>
          <button
            className="button secondary"
            onClick={async () => {
              try {
                setReview(await api<Review>(root + "/" + d.id));
                op.checked();
              } catch {
                op.setMessage("No pudimos comprobar la revisión.");
              }
            }}
          >
            Comprobar revisión limitada
          </button>
        </article>
      )}
    </details>
  );
}
