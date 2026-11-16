import { useEffect, useState } from "react";

type Binding = { transcript_id: string; revision: number; reviewed: true };
export function SocialSpeech({
  asset,
  saved,
  request,
  disabled,
  onChange,
  onDirty,
  onJob,
  errorMessage,
}: {
  asset: string;
  saved: Binding | null;
  request: (path: string, method?: string, body?: unknown) => Promise<any>;
  disabled: boolean;
  onChange: (value: Binding | null) => void;
  onDirty: () => void;
  onJob: (id: string) => void;
  errorMessage: (reason: string) => string;
}) {
  const [capability, setCapability] = useState<any>(null);
  const [transcript, setTranscript] = useState<any>(null);
  const [words, setWords] = useState<Record<number, string>>({});
  const [busy, setBusy] = useState(false),
    [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [reviewed, setReviewed] = useState(false);
  const [reason, setReason] = useState(
    "Corrección después de escuchar la toma original.",
  );
  const [attempt, setAttempt] = useState(() => crypto.randomUUID());
  function accept(t: any) {
    setTranscript(t);
    setWords(Object.fromEntries(t.words.map((w: any) => [w.index, w.text])));
    const same =
      saved?.transcript_id === t.id && saved?.revision === t.revision;
    setReviewed(!!same);
    if (!same) onChange(null);
  }
  useEffect(() => {
    let stop = false;
    setTranscript(null);
    setWords({});
    setReviewed(false);
    setPending(null);
    setError("");
    void request("/speech/capability")
      .then((d) => {
        if (!stop) setCapability(d);
      })
      .catch(() => {
        if (!stop) setCapability({ state: "blocked" });
      });
    void request(`/video/takes/${asset}/transcriptions`)
      .then((d) => {
        if (!stop && d.transcripts.length) accept(d.transcripts.at(-1));
      })
      .catch((e) => {
        if (!stop) setError(String(e));
      });
    return () => {
      stop = true;
    };
  }, [asset]);
  useEffect(() => {
    if (!pending) return;
    let stop = false;
    const tick = async () => {
      try {
        const j = await request(`/jobs/${pending}`);
        if (stop) return;
        if (j.state === "succeeded") {
          const t = await request(`/transcripts/${j.id}`);
          if (!stop) {
            accept(t);
            setPending(null);
          }
        } else if (!["queued", "running"].includes(j.state)) {
          setPending(null);
          setError(errorMessage(j.reason));
        }
      } catch (e) {
        if (!stop) {
          setPending(null);
          setError(String(e));
        }
      }
    };
    void tick();
    const timer = setInterval(() => void tick(), 1500);
    return () => {
      stop = true;
      clearInterval(timer);
    };
  }, [pending]);
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
  const changes =
    transcript?.words
      .filter((w: any) => words[w.index] !== w.text)
      .map((w: any) => ({ index: w.index, text: words[w.index] })) || [];
  return (
    <section className="speech-editor" aria-label="Transcripción y subtítulos">
      <h3>Tu respuesta, con subtítulos</h3>
      <p>
        Escucha la toma y revisa cada palabra, especialmente nombres, precios,
        condiciones y negaciones. La transcripción automática puede equivocarse.
        Las correcciones de texto no cambian lo que se escucha.
      </p>
      {error && <p role="alert">{error}</p>}
      {!transcript && capability?.state === "blocked" && (
        <p role="status">
          La transcripción necesita que 101 conecte el servicio de voz para este
          negocio. Tus tomas se conservan; puedes continuar con un montaje sin
          voz.
        </p>
      )}
      {!transcript && (
        <button
          type="button"
          className="button secondary"
          disabled={
            disabled || busy || !!pending || capability?.state !== "configured"
          }
          onClick={() =>
            void run(async () => {
              const j = await request(
                `/video/takes/${asset}/transcriptions`,
                "POST",
              );
              setPending(j.id);
              onJob(j.id);
            })
          }
        >
          {pending ? "Transcribiendo…" : "Transcribir respuesta en español"}
        </button>
      )}
      {transcript && (
        <>
          <p>
            Texto automático sin verificar · revisión {transcript.revision}. Los
            tiempos corresponden a la toma original.
          </p>
          <div className="speech-words">
            {transcript.words.map((w: any) => (
              <label key={w.index}>
                Palabra {w.index + 1} · {(w.start / 1000).toFixed(2)}–
                {(w.end / 1000).toFixed(2)} s{w.uncertain ? " · revisar" : ""}
                <input
                  aria-label={`Palabra ${w.index + 1}`}
                  value={words[w.index] || ""}
                  maxLength={64}
                  disabled={disabled || busy}
                  onChange={(e) => {
                    setWords((old) => ({ ...old, [w.index]: e.target.value }));
                    setReviewed(false);
                    onChange(null);
                    onDirty();
                    setAttempt(crypto.randomUUID());
                  }}
                />
              </label>
            ))}
          </div>
          <label className="speech-meaning">
            <input
              type="checkbox"
              checked={reviewed}
              disabled={disabled || busy}
              onChange={(e) => {
                setReviewed(e.target.checked);
                onDirty();
                onChange(
                  e.target.checked && !changes.length
                    ? {
                        transcript_id: transcript.id,
                        revision: transcript.revision,
                        reviewed: true,
                      }
                    : null,
                );
              }}
            />
            Revisé las palabras y conservan el significado de la voz, incluidas
            condiciones y negaciones.
          </label>
          {changes.length > 0 && (
            <>
              <label>
                Motivo de la corrección
                <input
                  value={reason}
                  maxLength={500}
                  onChange={(e) => setReason(e.target.value)}
                />
              </label>
              <button
                type="button"
                className="button secondary"
                disabled={
                  disabled ||
                  busy ||
                  !reviewed ||
                  reason.trim().length < 3 ||
                  changes.some((c: any) => !c.text.trim())
                }
                onClick={() =>
                  void run(async () => {
                    const t = await request(
                      `/transcripts/${transcript.id}/corrections`,
                      "POST",
                      {
                        request_id: attempt,
                        expected_revision: transcript.revision,
                        changes,
                        reason,
                        meaning_confirmed: true,
                      },
                    );
                    setTranscript(t);
                    setWords(
                      Object.fromEntries(
                        t.words.map((w: any) => [w.index, w.text]),
                      ),
                    );
                    setReviewed(true);
                    onChange({
                      transcript_id: t.id,
                      revision: t.revision,
                      reviewed: true,
                    });
                    onDirty();
                  })
                }
              >
                Guardar correcciones de palabras
              </button>
            </>
          )}
          <details>
            <summary>Texto original e historial</summary>
            <p>{transcript.machine.words.map((w: any) => w.text).join(" ")}</p>
            {transcript.history.map((h: any) => (
              <p key={h.revision}>
                Revisión {h.revision} · {h.reason}
              </p>
            ))}
          </details>
        </>
      )}
    </section>
  );
}
