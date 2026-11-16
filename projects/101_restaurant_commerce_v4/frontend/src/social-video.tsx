import { useEffect, useState } from "react";
import { endpoint } from "./ui";

export const videoErrors: Record<string, string> = {
  video_tools_unavailable:
    "El equipo de 101 debe habilitar el procesamiento de vídeo.",
  video_record_vertically: "Graba esta toma en vertical y vuelve a subirla.",
  video_record_higher_resolution:
    "Esta toma tiene poca resolución. Usa al menos 720 × 1280 en la cámara.",
  video_hdr_record_in_sdr:
    "Esta toma está en HDR. Desactiva HDR en la cámara y grábala en SDR.",
  video_decode_failed_rerecord:
    "No podemos leer esta toma completa. Prueba el archivo original o grábala otra vez.",
  video_duration_or_framerate_limit:
    "Usa una toma de 1–30 segundos, grabada hasta a 60 fps.",
  video_trim_out_of_bounds:
    "El corte termina después del archivo. Revisa los tiempos de esa toma.",
  video_guide_context_changed:
    "Cambió el texto o la información del negocio. Guarda una nueva guía con los datos actuales.",
  media_processing_time_limit:
    "Esta toma tarda demasiado en procesarse. Prueba una toma más breve en SDR.",
  video_shot_mismatch:
    "Esta toma pertenece a otro plano. Selecciona una toma de este espacio.",
  video_output_changed:
    "El archivo preparado necesita regenerarse antes de aprobarlo.",
  video_source_changed:
    "Cambió un archivo de origen. Selecciona una toma autorizada.",
  source_deleted_or_revoked: "Una toma se retiró. Selecciona otra autorizada.",
  asset_expired: "Renueva el permiso del material o elige otra toma.",
  reference_only_asset: "Este material solo puede usarse como referencia.",
  watch_and_listen_to_complete_video:
    "Mira y escucha el vídeo completo antes de marcarlo como listo.",
};
const shotIds = ["detail", "process", "finish"];
type Cut = {
  asset_id: string;
  source_in: number;
  source_out: number;
  focal_x: number;
  focal_y: number;
  audio_mode: string;
};

export function SocialVideo({
  business,
  csrf,
  pack,
  disabled,
  onJob,
  onDirty,
}: {
  business: string;
  csrf: string;
  pack: any;
  disabled: boolean;
  onJob: (id: string) => void;
  onDirty: (v: boolean) => void;
}) {
  const root = endpoint(business) + "/social";
  const [open, setOpen] = useState(false),
    [shoot, setShoot] = useState<any>(null);
  const [cuts, setCuts] = useState<Record<string, Cut>>({}),
    [changed, setChanged] = useState(false);
  const [rights, setRights] = useState(""),
    [expiry, setExpiry] = useState("");
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [pendingUploads, setPendingUploads] = useState<
    Record<string, { id: string; key: string }>
  >({});
  const [progress, setProgress] = useState<Record<string, string>>({});
  const [attempt, setAttempt] = useState(() => crypto.randomUUID());
  async function request(path: string, method = "GET", body?: unknown) {
    const r = await fetch(root + path, {
      method,
      headers: { "Content-Type": "application/json", "X-101-CSRF": csrf },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const d = await r.json();
    if (!r.ok)
      throw new Error(
        videoErrors[d.detail] ||
          (typeof d.detail === "string"
            ? d.detail
            : "Revisa los tiempos, el encuadre y las tres tomas de la guía."),
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
  function dirty(value: boolean) {
    setChanged(value);
    onDirty(value);
  }
  function defaults(s: any) {
    const saved =
      pack.document.brief.video?.shoot_id === s.id
        ? pack.document.brief.video
        : null;
    const next: Record<string, Cut> = {};
    for (const id of shotIds) {
      const old = saved?.clips.find((c: any) => c.shot_id === id);
      const take =
        s.takes.find((t: any) => t.id === old?.asset_id) ||
        s.takes.filter((t: any) => t.shot_id === id).at(-1);
      if (take)
        next[id] =
          old?.asset_id === take.id
            ? { ...old }
            : {
                asset_id: take.id,
                source_in: 0,
                source_out: Math.min(4000, take.media.duration_ms),
                focal_x: 0.5,
                focal_y: 0.5,
                audio_mode: "preserve_natural_sound",
              };
    }
    setCuts(next);
    setShoot(s);
    dirty(false);
  }
  useEffect(() => {
    if (!open) return;
    let stopped = false;
    void request("/packs/" + pack.id + "/shoots")
      .then((d) => {
        if (stopped) return;
        const selected =
          d.shoots.find(
            (s: any) => s.id === pack.document.brief.video?.shoot_id,
          ) || d.shoots.at(-1);
        if (selected) defaults(selected);
        else {
          setShoot(null);
          setCuts({});
          dirty(false);
        }
      })
      .catch((e) => {
        if (!stopped) setError(String(e));
      });
    return () => {
      stopped = true;
    };
  }, [open, pack.id, pack.digest]);
  function update(id: string, change: Partial<Cut>) {
    setCuts((old) => ({ ...old, [id]: { ...old[id], ...change } }));
    setAttempt(crypto.randomUUID());
    dirty(true);
  }
  async function upload(id: string, file: File) {
    if (!rights.trim() || !expiry)
      throw new Error(
        "Indica el permiso de las tomas y su fecha de revisión antes de subirlas.",
      );
    if (file.size > 64 * 1024 * 1024)
      throw new Error(
        "Cada toma puede pesar hasta 64 MB. Usa un fragmento más breve.",
      );
    const bytes = await file.arrayBuffer();
    const hash = Array.from(
      new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)),
    )
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
    const key =
      "101-video:" +
      business +
      ":" +
      shoot.id +
      ":" +
      id +
      ":" +
      hash +
      ":" +
      expiry +
      ":" +
      rights;
    let uid = localStorage.getItem(key),
      state: any = null;
    if (uid) {
      try {
        state = await request("/uploads/" + uid);
      } catch {
        uid = null;
        localStorage.removeItem(key);
      }
    }
    if (!uid) {
      state = await request("/uploads", "POST", {
        media_kind: "video",
        shoot_id: shoot.id,
        shot_id: id,
        sha256: hash,
        total: file.size,
        rights_statement: rights,
        expires_at: expiry + "T23:59:59Z",
        permitted_use: "production",
        fixture: pack.document.fixture,
      });
      uid = state.id;
      localStorage.setItem(key, uid!);
    }
    setPendingUploads((old) => ({ ...old, [id]: { id: uid!, key } }));
    if (!state.asset_id) {
      for (let offset = state.received; offset < bytes.byteLength;) {
        const chunk = new Uint8Array(bytes.slice(offset, offset + 262144));
        let binary = "";
        for (const b of chunk) binary += String.fromCharCode(b);
        state = await request("/uploads/" + uid, "PUT", {
          offset,
          data_base64: btoa(binary),
        });
        offset = state.received;
        setProgress((old) => ({
          ...old,
          [id]: Math.round((offset / bytes.byteLength) * 100) + "% recibido",
        }));
      }
      setProgress((old) => ({
        ...old,
        [id]: "Comprobando el archivo completo…",
      }));
      state = await request("/uploads/" + uid + "/complete", "POST");
    }
    localStorage.removeItem(key);
    setPendingUploads((old) => {
      const next = { ...old };
      delete next[id];
      return next;
    });
    const s = await request("/shoots/" + shoot.id);
    setShoot(s);
    const take = s.takes.find(
      (t: any) => t.id === (state.asset_id || state.id),
    );
    update(id, {
      asset_id: take.id,
      source_in: 0,
      source_out: Math.min(4000, take.media.duration_ms),
      focal_x: 0.5,
      focal_y: 0.5,
      audio_mode: "preserve_natural_sound",
    });
    setProgress((old) => ({
      ...old,
      [id]: "Toma recibida. Puedes revisarla o reemplazarla.",
    }));
  }
  async function render() {
    let start = 0;
    const clips = shotIds.map((id) => {
      const c = cuts[id];
      const out = { ...c, shot_id: id, timeline_start: start };
      start += c.source_out - c.source_in;
      return out;
    });
    const j = await request("/packs/" + pack.id + "/video", "POST", {
      request_id: attempt,
      expected_revision: pack.revision,
      timeline: { shoot_id: shoot.id, clips },
      confirmed: true,
    });
    onJob(j.id);
  }
  const total =
    Object.values(cuts).reduce((n, c) => n + c.source_out - c.source_in, 0) /
    1000;
  return (
    <details
      className="social-video"
      open={open}
      onToggle={(e) => setOpen(e.currentTarget.open)}
    >
      <summary>Preparar un vídeo con tus tomas</summary>
      {open && (
        <div>
          <h2>Una secuencia de tu producto o proceso</h2>
          <p>
            Usaremos el texto y los datos de esta publicación. Graba tres planos
            reales; después podrás elegir las tomas y ajustar el corte.
          </p>
          {error && <p role="alert">{error}</p>}
          <fieldset disabled={busy || disabled || pack.stale}>
            {!shoot ? (
              <button
                type="button"
                className="button secondary"
                onClick={() =>
                  void run(async () =>
                    defaults(
                      await request("/shoots", "POST", {
                        request_id: crypto.randomUUID(),
                        pack_id: pack.id,
                        expected_revision: pack.revision,
                      }),
                    ),
                  )
                }
              >
                Crear guía de grabación
              </button>
            ) : (
              <>
                <p className="video-guidance">{shoot.guidance}</p>
                <details>
                  <summary>Permiso del material</summary>
                  <label>
                    Permiso para usar estas tomas
                    <input
                      value={rights}
                      minLength={8}
                      maxLength={600}
                      onChange={(e) => setRights(e.target.value)}
                      placeholder="Son nuestras tomas y podemos usarlas en redes"
                    />
                  </label>
                  <label>
                    Revisar el permiso de las tomas
                    <input
                      type="date"
                      value={expiry}
                      onChange={(e) => setExpiry(e.target.value)}
                    />
                  </label>
                  <p>
                    Conservaremos las tomas originales. Subirlas hoy no indica
                    cuándo se grabaron.
                  </p>
                </details>
                <ol className="video-shots">
                  {shoot.shots.map((shot: any) => {
                    const takes = shoot.takes.filter(
                        (t: any) => t.shot_id === shot.id,
                      ),
                      cut = cuts[shot.id];
                    const selected = takes.find(
                      (t: any) => t.id === cut?.asset_id,
                    );
                    return (
                      <li key={shot.id} className="video-shot">
                        <h3>{shot.title}</h3>
                        <p>{shot.instruction}</p>
                        <p className="video-purpose">
                          {shot.purpose} · 5–10 segundos · vertical · sonido
                          ambiente
                        </p>
                        <label>
                          Subir toma: {shot.title}
                          <input
                            type="file"
                            accept="video/mp4,video/quicktime,.mov"
                            onChange={(e) => {
                              const file = e.target.files?.[0];
                              if (file) void run(() => upload(shot.id, file));
                              e.target.value = "";
                            }}
                          />
                        </label>
                        {progress[shot.id] && (
                          <p role="status">{progress[shot.id]}</p>
                        )}
                        {pendingUploads[shot.id] && (
                          <button
                            type="button"
                            className="button secondary"
                            onClick={() =>
                              void run(async () => {
                                const u = pendingUploads[shot.id];
                                await request("/uploads/" + u.id, "DELETE");
                                localStorage.removeItem(u.key);
                                setPendingUploads((old) => {
                                  const n = { ...old };
                                  delete n[shot.id];
                                  return n;
                                });
                                setProgress((old) => ({
                                  ...old,
                                  [shot.id]:
                                    "Subida cancelada. Puedes elegir otro archivo.",
                                }));
                              })
                            }
                          >
                            Cancelar subida: {shot.title}
                          </button>
                        )}
                        {!selected && (
                          <div>
                            <svg
                              className="video-framing"
                              viewBox="0 0 90 160"
                              role="img"
                              aria-label={
                                "Ejemplo de encuadre vertical: " + shot.title
                              }
                            >
                              <rect
                                x="1"
                                y="1"
                                width="88"
                                height="158"
                                rx="9"
                                fill="none"
                                stroke="currentColor"
                              />
                              <rect
                                x="15"
                                y="28"
                                width="60"
                                height="104"
                                rx="3"
                                fill="none"
                                stroke="currentColor"
                                strokeDasharray="4 4"
                              />
                              <path d="M36 10h18" stroke="currentColor" />
                            </svg>
                            <p className="video-illustration">
                              Guía de encuadre: deja espacio alrededor de la
                              acción. Es una ilustración, no material del
                              negocio.
                            </p>
                            <p>Falta esta toma.</p>
                          </div>
                        )}
                        {selected && (
                          <>
                            <label>
                              Toma elegida: {shot.title}
                              <select
                                aria-label={"Toma elegida: " + shot.title}
                                value={cut.asset_id}
                                onChange={(e) => {
                                  const t = takes.find(
                                    (t: any) => t.id === e.target.value,
                                  );
                                  update(shot.id, {
                                    asset_id: t.id,
                                    source_in: 0,
                                    source_out: Math.min(
                                      4000,
                                      t.media.duration_ms,
                                    ),
                                  });
                                }}
                              >
                                {takes.map((t: any, i: number) => (
                                  <option key={t.id} value={t.id}>
                                    Toma {i + 1} ·{" "}
                                    {(t.media.duration_ms / 1000).toFixed(1)} s
                                    {t.fixture ? " · prueba" : ""}
                                  </option>
                                ))}
                              </select>
                            </label>
                            <video
                              className="video-take"
                              controls
                              preload="none"
                              poster={
                                root + "/video/takes/" + selected.id + "/poster"
                              }
                              src={
                                root +
                                "/video/takes/" +
                                selected.id +
                                "/analysis"
                              }
                              aria-label={"Revisar toma: " + shot.title}
                            />
                            <p>
                              Vista de análisis: primeros cinco segundos.
                              Original: {selected.media.width} ×{" "}
                              {selected.media.height} ·{" "}
                              {selected.media.has_audio
                                ? "con sonido"
                                : "sin audio; se conservará el silencio"}
                              .
                            </p>
                            <div className="video-controls">
                              <label>
                                Desde (s): {shot.title}
                                <input
                                  type="number"
                                  step=".1"
                                  min="0"
                                  max={selected.media.duration_ms / 1000}
                                  value={cut.source_in / 1000}
                                  onChange={(e) =>
                                    update(shot.id, {
                                      source_in: Math.round(
                                        Number(e.target.value) * 1000,
                                      ),
                                    })
                                  }
                                />
                              </label>
                              <label>
                                Hasta (s): {shot.title}
                                <input
                                  type="number"
                                  step=".1"
                                  min=".5"
                                  max={selected.media.duration_ms / 1000}
                                  value={cut.source_out / 1000}
                                  onChange={(e) =>
                                    update(shot.id, {
                                      source_out: Math.round(
                                        Number(e.target.value) * 1000,
                                      ),
                                    })
                                  }
                                />
                              </label>
                              <label>
                                Encuadre horizontal: {shot.title}
                                <input
                                  type="range"
                                  min="0"
                                  max="1"
                                  step=".05"
                                  value={cut.focal_x}
                                  onChange={(e) =>
                                    update(shot.id, {
                                      focal_x: Number(e.target.value),
                                    })
                                  }
                                />
                              </label>
                              <label>
                                Encuadre vertical: {shot.title}
                                <input
                                  type="range"
                                  min="0"
                                  max="1"
                                  step=".05"
                                  value={cut.focal_y}
                                  onChange={(e) =>
                                    update(shot.id, {
                                      focal_y: Number(e.target.value),
                                    })
                                  }
                                />
                              </label>
                              <label>
                                Sonido: {shot.title}
                                <select
                                  aria-label={"Sonido: " + shot.title}
                                  value={cut.audio_mode}
                                  onChange={(e) =>
                                    update(shot.id, {
                                      audio_mode: e.target.value,
                                    })
                                  }
                                >
                                  <option value="preserve_natural_sound">
                                    Conservar sonido ambiente
                                  </option>
                                  <option value="mute">
                                    Silenciar esta toma
                                  </option>
                                </select>
                              </label>
                            </div>
                          </>
                        )}
                        <details>
                          <summary>No puedo grabar este plano</summary>
                          <p>
                            Puedes usar otra toma real del mismo plano o
                            continuar con la publicación estática. No
                            inventaremos la toma que falta.
                          </p>
                        </details>
                      </li>
                    );
                  })}
                </ol>
                <p>
                  Duración elegida: {total.toFixed(1)} s. Cada plano puede durar
                  entre 0,5 y 6 segundos; el montaje completo, hasta 18
                  segundos.
                </p>
                <p>
                  Esta receta no transcribe ni añade música. Revisa el encuadre
                  y conserva el significado de cualquier voz que se escuche.
                </p>
                <button
                  type="button"
                  className="button primary"
                  disabled={shotIds.some((id) => !cuts[id]) || !changed}
                  onClick={() => void run(render)}
                >
                  Preparar montaje
                </button>
                {changed && (
                  <button
                    type="button"
                    className="button secondary"
                    onClick={() => defaults(shoot)}
                  >
                    Descartar ajustes de vídeo
                  </button>
                )}
                <button
                  type="button"
                  className="button secondary"
                  onClick={() =>
                    void run(async () =>
                      defaults(
                        await request("/shoots", "POST", {
                          request_id: crypto.randomUUID(),
                          pack_id: pack.id,
                          expected_revision: pack.revision,
                        }),
                      ),
                    )
                  }
                >
                  Crear otra guía con los datos actuales
                </button>
              </>
            )}
          </fieldset>
          {busy && (
            <p role="status">
              Procesando el archivo. Mantén esta página abierta durante la
              subida; si se interrumpe, vuelve a seleccionar el mismo archivo
              para continuar.
            </p>
          )}
        </div>
      )}
    </details>
  );
}
