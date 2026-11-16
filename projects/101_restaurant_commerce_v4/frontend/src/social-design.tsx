import { useEffect, useState } from "react";
import { endpoint } from "./ui";
import type { BusinessContext } from "./social-context";
export type Layer = {
  id: string;
  fact_id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  size: number;
  line_height: number;
  tracking: number;
  align: string;
};
export type DesignSpec = {
  schema_version: "1";
  preset_version: "1";
  layout: string;
  canvas: { width: 1080; height: 1350 };
  styles: { background: string; foreground: string; font_id: string };
  photo: { x: number; y: number; width: number; height: number };
  layers: Layer[];
};
export const ownedLayerId = (role: string) => "design_owned_" + role;
const names: Record<string, string> = {
  headline: "Título",
  detail: "Información",
  price: "Precio",
};
export function designError(detail: any): string {
  if (typeof detail !== "string")
    return "Revisa los campos y vuelve a intentar.";
  const reviewMessages:Record<string,string>={structured_review_required:'Guarda una revisión completa de esta versión antes de aprobarla.',review_not_ready:'Resuelve los cambios pedidos antes de aprobar.',review_version_changed:'La versión cambió. Abre la versión actual para revisarla.',approval_changed:'La versión cambió. Vuelve a revisarla.',comparison_brief_mismatch:'Estas versiones tienen datos, objetivos o referencias diferentes. Compara alternativas del mismo contexto.',comparison_context_changed:'Cambió o venció el contexto de esta comparación. Prepara otra.',comparison_output_changed:'Cambió un archivo de la comparación. Vuelve a abrir las versiones.',distinct_comparison_required:'Elige dos versiones con imágenes o textos diferentes.',comparison_already_voted:'Esta elección ya se guardó y no se puede reemplazar.',source_deleted_or_revoked:'La fotografía ya no está autorizada. Selecciona otra.',technical_review_blocked:'Hay un problema con el archivo. Prepara una nueva versión.',export_output_changed:'Cambió el archivo exportado. Prepara otra versión y revísala.'};
  if (!detail.startsWith("design:")) return reviewMessages[detail]||detail;
  const [, role, code] = detail.split(":");
  const labels: Record<string, string> = {
    ...names,
    canvas: "Diseño",
    photo: "Fotografía",
  };
  const messages: Record<string, string> = {
    text_overflow:
      "el texto no cabe. Reduce su tamaño, amplía el espacio o acorta el texto.",
    unsupported_character:
      "hay un carácter que esta fuente no puede mostrar. Usa otra redacción.",
    contrast: "el texto y el fondo necesitan más contraste.",
    overlap: "este elemento se superpone con otro. Revisa sus posiciones.",
    safe_region: "el texto sale del margen seguro.",
    out_of_bounds: "el elemento sale del lienzo.",
    unresolved_fact: "selecciona un dato confirmado para el texto.",
    source_resolution:
      "la fotografía no tiene suficiente resolución para este encuadre.",
    font_missing_or_changed:
      "la fuente no está disponible. Contacta al equipo de 101.",
  };
  return `${labels[role] || role}: ${messages[code] || "revisa los ajustes antes de continuar."}`;
}
export function SocialDesign({
  business,
  csrf,
  value,
  onChange,
  context,
  custom,
  onCustom,
  onPriceChange,
}: {
  business: string;
  csrf: string;
  value: DesignSpec | null;
  onChange: (v: DesignSpec | null) => void;
  context: BusinessContext | null;
  custom: Record<string, string>;
  onCustom: (role: string, value: string) => void;
  onPriceChange: (id: string, value: string) => Promise<void>;
}) {
  const [options, setOptions] = useState<any>(null),
    [error, setError] = useState(""),
    [price, setPrice] = useState(""),
    [confirmed, setConfirmed] = useState(false),
    [busy, setBusy] = useState(false);
  const [expanded, setExpanded] = useState(!!value);
  const root = endpoint(business) + "/social";
  useEffect(() => {
    let stop = false;
    void fetch(root + "/design/options", { headers: { "X-101-CSRF": csrf } })
      .then(async (r) => {
        const d = await r.json();
        if (!r.ok) throw new Error(designError(d.detail));
        if (!stop) setOptions(d);
      })
      .catch((e) => {
        if (!stop) setError(String(e));
      });
    return () => {
      stop = true;
    };
  }, [root]);
  const moneyId = value?.layers.find((l) => l.id === "price")?.fact_id;
  const current = context?.facts.find(
    (f) =>
      f.id === moneyId &&
      f.kind === "money" &&
      f.current_status === "confirmed",
  );
  useEffect(() => {
    setPrice(current?.value || "");
    setConfirmed(false);
  }, [current?.value, moneyId]);
  const facts =
    context?.facts.filter((f) => f.current_status === "confirmed") || [];
  function choose(layout: string) {
    if (layout === "photo_only") {
      onChange(null);
      return;
    }
    const p = structuredClone(options.presets[layout]);
    if (value) p.styles = { ...value.styles };
    for (const l of p.layers) {
      l.fact_id =
        value?.layers.find((v) => v.id === l.id)?.fact_id ||
        (l.id === "headline" ? ownedLayerId(l.id) : "");
    }
    onChange(p);
  }
  const editableLayers: Layer[] =
    value && options
      ? options.presets[value.layout].layers.map((l: Layer) => ({
          ...l,
          ...value.layers.find((v) => v.id === l.id),
        }))
      : value?.layers || [];
  function layerPatch(id: string, patch: Partial<Layer>) {
    if (value)
      onChange({
        ...value,
        layers: editableLayers.map((l) =>
          l.id === id ? { ...l, ...patch } : l,
        ),
      });
  }
  async function updatePrice() {
    if (!current) return;
    setBusy(true);
    setError("");
    try {
      await onPriceChange(current.id, price);
      setConfirmed(false);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <details
      id="social-design-editor"
      className="social-design-editor"
      open={expanded}
      onToggle={(e) => setExpanded(e.currentTarget.open)}
    >
      <summary>Diseño de la imagen</summary>
      <p>
        Elige una composición. Los textos se guardan separados de la fotografía.
      </p>
      {error && <p role="alert">{error}</p>}
      <label>
        Composición
        <select
          aria-label="Composición"
          value={value?.layout || "photo_only"}
          disabled={!options}
          onChange={(e) => choose(e.target.value)}
        >
          <option value="photo_only">Solo fotografía</option>
          <option value="photo_first">Fotografía protagonista</option>
          <option value="information">Tarjeta informativa</option>
        </select>
      </label>
      {value && (
        <>
          <div className="design-colors">
            <label>
              Color del fondo
              <input
                type="color"
                aria-label="Color del fondo"
                value={value.styles.background}
                onChange={(e) =>
                  onChange({
                    ...value,
                    styles: { ...value.styles, background: e.target.value },
                  })
                }
              />
            </label>
            <label>
              Color del texto
              <input
                type="color"
                aria-label="Color del texto"
                value={value.styles.foreground}
                onChange={(e) =>
                  onChange({
                    ...value,
                    styles: { ...value.styles, foreground: e.target.value },
                  })
                }
              />
            </label>
          </div>
          <label>
            Fuente de la publicación
            <select
              aria-label="Fuente de la publicación"
              value={value.styles.font_id}
              onChange={(e) =>
                onChange({
                  ...value,
                  styles: { ...value.styles, font_id: e.target.value },
                })
              }
            >
              {options?.fonts.map((f: any) => (
                <option key={f.id} value={f.id}>
                  {f.family} · {f.style}
                </option>
              ))}
            </select>
          </label>
          <p>
            Inter Regular es la fuente disponible en esta primera versión. Los
            acentos y la legibilidad se comprueban al preparar la imagen.
          </p>
          {editableLayers.map((layer) => (
            <fieldset key={layer.id} className="design-layer">
              <legend>{names[layer.id]}</legend>
              <label>
                {names[layer.id]} · dato o texto
                <select
                  aria-label={`${names[layer.id]} · dato o texto`}
                  value={layer.fact_id}
                  onChange={(e) =>
                    layerPatch(layer.id, { fact_id: e.target.value })
                  }
                >
                  <option value="">
                    {layer.id === "headline"
                      ? "Seleccionar dato"
                      : "No mostrar"}
                  </option>
                  {layer.id !== "price" && (
                    <option value={ownedLayerId(layer.id)}>
                      Escribir un texto que puedo confirmar
                    </option>
                  )}
                  {facts.map((f) => (
                    <option value={f.id} key={f.id}>
                      {f.text}
                    </option>
                  ))}
                </select>
              </label>
              {layer.fact_id === ownedLayerId(layer.id) && (
                <label>
                  {names[layer.id]} de la imagen
                  <textarea
                    aria-label={`${names[layer.id]} de la imagen`}
                    rows={2}
                    maxLength={300}
                    required={layer.id === "headline"}
                    value={custom[layer.id] || ""}
                    onChange={(e) => onCustom(layer.id, e.target.value)}
                  />
                </label>
              )}
              {layer.fact_id && layer.fact_id !== ownedLayerId(layer.id) && (
                <p className="design-source">
                  {facts.find((f) => f.id === layer.fact_id)?.text ||
                    "Este dato cambió. Revisa la publicación con los datos actuales."}
                </p>
              )}
              {layer.fact_id && (
                <>
                  <div className="design-controls">
                    <label>
                      {names[layer.id]} · tamaño
                      <input
                        type="number"
                        min={24}
                        max={100}
                        aria-label={`${names[layer.id]} · tamaño`}
                        value={layer.size}
                        onChange={(e) =>
                          layerPatch(layer.id, { size: Number(e.target.value) })
                        }
                      />
                    </label>
                    <label>
                      {names[layer.id]} · alineación
                      <select
                        aria-label={`${names[layer.id]} · alineación`}
                        value={layer.align}
                        onChange={(e) =>
                          layerPatch(layer.id, { align: e.target.value })
                        }
                      >
                        <option value="left">Izquierda</option>
                        <option value="center">Centro</option>
                        <option value="right">Derecha</option>
                      </select>
                    </label>
                  </div>
                  <details className="design-geometry">
                    <summary>
                      Ajustar espacio de {names[layer.id].toLowerCase()}
                    </summary>
                    <div className="design-controls">
                      {[
                        ["x", "Posición X", 0, 1080],
                        ["y", "Posición Y", 0, 1350],
                        ["width", "Ancho", 32, 1080],
                        ["height", "Alto", 32, 1350],
                        ["tracking", "Espacio entre letras", 0, 3],
                        ["line_height", "Espacio entre líneas", 1.05, 1.6],
                      ].map(([key, label, min, max]) => (
                        <label key={String(key)}>
                          {names[layer.id]} · {label}
                          <input
                            type="number"
                            min={Number(min)}
                            max={Number(max)}
                            step={key === "line_height" ? 0.05 : 1}
                            value={(layer as any)[key]}
                            onChange={(e) =>
                              layerPatch(layer.id, {
                                [String(key)]: Number(e.target.value),
                              })
                            }
                          />
                        </label>
                      ))}
                    </div>
                  </details>
                </>
              )}
            </fieldset>
          ))}
          {current && (
            <div className="design-price-correction">
              <p>
                Para cambiar el precio, actualiza el dato del negocio. Las
                versiones anteriores conservan el valor que usaron.
              </p>
              <label>
                Nuevo precio confirmado · {current.currency}
                <input
                  type="number"
                  min={0}
                  step="0.01"
                  aria-label={`Nuevo precio confirmado · ${current.currency}`}
                  value={price}
                  onChange={(e) => {
                    setPrice(e.target.value);
                    setConfirmed(false);
                  }}
                />
              </label>
              <label className="social-check">
                <input
                  type="checkbox"
                  checked={confirmed}
                  onChange={(e) => setConfirmed(e.target.checked)}
                />
                Confirmo este nuevo precio.
              </label>
              <button
                type="button"
                className="button secondary"
                disabled={
                  busy || !confirmed || !price || price === current.value
                }
                onClick={() => void updatePrice()}
              >
                Actualizar precio del negocio
              </button>
            </div>
          )}
          <details className="design-geometry">
            <summary>Ajustar espacio de la fotografía</summary>
            <div className="design-controls">
              {[
                ["x", "Posición X", 0, 1080],
                ["y", "Posición Y", 0, 1350],
                ["width", "Ancho", 32, 1080],
                ["height", "Alto", 32, 1350],
              ].map(([key, label, min, max]) => (
                <label key={String(key)}>
                  Fotografía · {label}
                  <input
                    type="number"
                    min={Number(min)}
                    max={Number(max)}
                    value={(value.photo as any)[key]}
                    onChange={(e) =>
                      onChange({
                        ...value,
                        photo: {
                          ...value.photo,
                          [String(key)]: Number(e.target.value),
                        },
                      })
                    }
                  />
                </label>
              ))}
            </div>
          </details>
          <p>
            La imagen se prepara en 1080 × 1350. El texto debe caber, mantener
            contraste y respetar los márgenes. Guardar una nueva versión vuelve
            a pedir revisión.
          </p>
        </>
      )}
    </details>
  );
}

const changeNames: Record<string, string> = {
  initial: "Primera versión",
  caption: "Texto de la publicación",
  composition: "Composición",
  layout: "Familia de diseño",
  styles: "Colores o tipografía",
  canvas: "Lienzo",
  "photo.asset_id": "Fotografía",
  "photo.focal_x": "Encuadre horizontal",
  "photo.focal_y": "Encuadre vertical",
  "photo.frame_or_source": "Marco o archivo de fotografía",
  brief_or_review: "Información o revisión",
};
function changeName(value: string) {
  const [type, role, field] = value.split(".");
  if(type==="video") {
    if(role==="added") return "Se añadió el montaje";
    if(role==="removed") return "Se volvió a una imagen";
    return "Vídeo · "+({detail:"producto",process:"proceso",finish:"resultado"} as any)[role]+": "+({asset_id:"otra toma",source_in:"inicio del corte",source_out:"fin del corte",focal_x:"encuadre horizontal",focal_y:"encuadre vertical",audio_mode:"sonido"} as any)[field];
  }
  return (
    changeNames[value] ||
    (type === "text"
      ? "Texto: "
      : type === "layout"
        ? "Espacio: "
        : type === "removed"
          ? "Se retiró: "
          : "") + (names[role] || value)
  );
}
export function SocialHistory({
  business,
  pack,
  revision,
}: {
  business: string;
  pack: string;
  revision: number;
}) {
  const [history, setHistory] = useState<any[]>([]),
    [view, setView] = useState<number | null>(null),
    [cursor, setCursor] = useState<number | null>(null),
    [error, setError] = useState("");
  const root = endpoint(business) + "/social/packs/" + pack;
  async function fetchHistory(before?: number) {
    const r = await fetch(
      root + "/history" + (before ? "?before_revision=" + before : ""),
    );
    const d = await r.json();
    if (!r.ok) throw new Error(designError(d.detail));
    return d;
  }
  useEffect(() => {
    let stop = false;
    setHistory([]);
    setView(null);
    void fetchHistory()
      .then((d) => {
        if (!stop) {
          setHistory(d.revisions);
          setCursor(d.before_revision);
        }
      })
      .catch((e) => {
        if (!stop) setError(String(e));
      });
    return () => {
      stop = true;
    };
  }, [root, revision]);
  return (
    <details className="social-design-history">
      <summary>Historial de versiones</summary>
      {error && <p role="alert">{error}</p>}
      {history.map((h) => (
        <article key={h.revision}>
          <h3>
            Versión {h.revision}
            {h.current ? " · actual" : ""}
          </h3>
          <p>{h.changes.map(changeName).join(" · ")}</p>
          {h.review_summary&&<p>Revisión: {({ready:'lista para aprobar',changes_requested:'cambios pedidos',rejected:'descartada'} as any)[h.review_summary.outcome]} · {h.review_summary.reason}</p>}
          <p>
            {h.historically_approved
              ? "Esta versión recibió aprobación."
              : "Sin aprobación registrada."}{" "}
            Las versiones anteriores no autorizan una nueva publicación.
          </p>
          <button
            type="button"
            className="button secondary"
            onClick={() => setView(view === h.revision ? null : h.revision)}
          >
            {view === h.revision ? "Cerrar vista" : h.media_kind==="video"?"Ver vídeo y texto":"Ver imagen y texto"}{" "}
            {h.revision}
          </button>
          {view === h.revision && (
            <>
              {h.media_kind==="video"&&<video className="video-preview" controls preload="none" aria-label={"Vídeo histórico de la versión "+h.revision} src={root+"/revisions/"+h.revision+"/video"}/>}
              <img
                className="social-image"
                src={root + "/revisions/" + h.revision + "/image"}
                alt={"Imagen histórica de la versión " + h.revision}
                onError={(e) => {
                  e.currentTarget.hidden = true;
                  setError(
                    "Esta fotografía ya no está disponible con su permiso actual.",
                  );
                }}
              />
              <p className="social-caption">{h.caption}</p>
            </>
          )}
        </article>
      ))}
      {cursor && (
        <button
          className="button secondary"
          type="button"
          onClick={() =>
            void fetchHistory(cursor)
              .then((d) => {
                setHistory((old) => [...old, ...d.revisions]);
                setCursor(d.before_revision);
              })
              .catch((e) => setError(String(e)))
          }
        >
          Ver versiones anteriores
        </button>
      )}
    </details>
  );
}
