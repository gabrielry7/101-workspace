import { useState } from "react";

type Caption = { start: string; end: string; text: string };
export function ManualSubtitles({
  asset,
  request,
  disabled,
  onSaved,
  onDirty,
}: {
  asset: string;
  request: (path: string, method?: string, body?: unknown) => Promise<any>;
  disabled: boolean;
  onSaved: (value: any) => void;
  onDirty: () => void;
}) {
  const [captions, setCaptions] = useState<Caption[]>([
    { start: "", end: "", text: "" },
  ]);
  const [confirmed, setConfirmed] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [requestId, setRequestId] = useState(() => crypto.randomUUID());
  function update(index: number, value: Partial<Caption>) {
    setCaptions((old) =>
      old.map((c, i) => (i === index ? { ...c, ...value } : c)),
    );
    setConfirmed(false);
    setRequestId(crypto.randomUUID());
    onDirty();
  }
  const complete = captions.every(
    (c) =>
      c.text.trim() &&
      c.start !== "" &&
      c.end !== "" &&
      Number(c.start) < Number(c.end),
  );
  async function save() {
    setBusy(true);
    setError("");
    try {
      const value = await request(
        `/video/takes/${asset}/manual-subtitles`,
        "POST",
        {
          request_id: requestId,
          confirmed,
          segments: captions.map((c, index) => ({
            index,
            text: c.text,
            start: Math.round(Number(c.start) * 1000),
            end: Math.round(Number(c.end) * 1000),
          })),
        },
      );
      onSaved(value);
      onDirty();
    } catch (e) {
      setError(String(e).replace(/^Error: /, ""));
    } finally {
      setBusy(false);
    }
  }
  return (
    <details className="manual-subtitles">
      <summary>Escribir subtítulos con sus tiempos</summary>
      <p>
        Escucha la respuesta original y escribe lo que se oye, en frases breves.
        Indica cuándo empieza y termina cada frase.
      </p>
      <p>
        Usa segundos desde el inicio de la toma original. Deja las frases en
        orden, sin superponerlas. Después podrás corregir texto y tiempos sin
        cambiar el vídeo.
      </p>
      {error && <p role="alert">{error}</p>}
      <fieldset disabled={disabled || busy}>
        {captions.map((c, i) => (
          <div className="manual-caption" key={i}>
            <label>
              Texto del subtítulo {i + 1}
              <input
                aria-label={`Texto del subtítulo ${i + 1}`}
                maxLength={64}
                value={c.text}
                onChange={(e) => update(i, { text: e.target.value })}
              />
            </label>
            <div className="speech-times">
              <label>
                Desde (s), subtítulo {i + 1}
                <input
                  aria-label={`Desde (s), subtítulo ${i + 1}`}
                  type="number"
                  min="0"
                  max="30"
                  step=".01"
                  value={c.start}
                  onChange={(e) => update(i, { start: e.target.value })}
                />
              </label>
              <label>
                Hasta (s), subtítulo {i + 1}
                <input
                  aria-label={`Hasta (s), subtítulo ${i + 1}`}
                  type="number"
                  min=".08"
                  max="30"
                  step=".01"
                  value={c.end}
                  onChange={(e) => update(i, { end: e.target.value })}
                />
              </label>
            </div>
            {captions.length > 1 && (
              <button
                type="button"
                className="button secondary"
                onClick={() => {
                  setCaptions((old) => old.filter((_, j) => i !== j));
                  setConfirmed(false);
                  setRequestId(crypto.randomUUID());
                  onDirty();
                }}
              >
                Quitar subtítulo {i + 1}
              </button>
            )}
          </div>
        ))}
        <button
          type="button"
          className="button secondary"
          disabled={captions.length >= 40}
          onClick={() => {
            setCaptions((old) => [...old, { start: "", end: "", text: "" }]);
            setConfirmed(false);
            setRequestId(crypto.randomUUID());
            onDirty();
          }}
        >
          Añadir otro subtítulo
        </button>
        <label className="speech-meaning">
          <input
            type="checkbox"
            checked={confirmed}
            onChange={(e) => setConfirmed(e.target.checked)}
          />
          Escuché la toma completa y confirmé el texto y los tiempos.
        </label>
        <button
          type="button"
          className="button primary"
          disabled={!complete || !confirmed}
          onClick={() => void save()}
        >
          {busy ? "Guardando…" : "Guardar subtítulos manuales"}
        </button>
      </fieldset>
    </details>
  );
}
