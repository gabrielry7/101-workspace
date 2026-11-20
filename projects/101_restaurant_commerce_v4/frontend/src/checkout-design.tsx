import { useEffect, useRef, useState } from "react";
import { api, endpoint, useResource, Failure, Loading } from "./ui";
import {
  checkoutProfile,
  CHECKOUT_ANATOMY,
  type CheckoutProfile,
} from "../../../../packages/101-checkout-chassis/checkout-chassis.js";
import { measureDesign } from "../../../../packages/101-checkout-chassis/vendor/measure.js";
import "./checkout-design.css";
type Saved = {
  revision: number;
  available: boolean;
  profile: CheckoutProfile;
  contract: {
    presets: Record<string, CheckoutProfile>;
    geometry: Record<string, [number, number]>;
    typography: Record<string, [number, number]>;
    fonts: Record<string, string>;
    surfaces: string[];
    colors: string[];
  };
};
const names: Record<string, string> = {
  panel: "Contenedor del pedido",
  card: "Producto en el pedido",
  stage: "Entrega o recogida",
  content: "Datos de contacto",
  story: "Nota y código",
  controls: "Botones",
  provider: "Confirmación y recuperación",
  dialog: "Opciones del producto",
  ink: "Texto",
  muted: "Texto de apoyo",
  canvas: "Campos",
  surface: "Superficie",
  line: "Bordes",
  accent: "Acción principal",
  onAccent: "Texto de la acción",
  soft: "Superficie secundaria",
  focus: "Foco del teclado",
  error: "Fondo de error",
  onError: "Texto de error",
  success: "Fondo de confirmación",
  onSuccess: "Texto de confirmación",
  maxWidth: "Ancho máximo de página",
  formWidth: "Ancho del pedido",
  gap: "Separación de columnas",
  inset: "Margen lateral",
  bodySize: "Texto",
  headingSize: "Título",
  labelSize: "Etiquetas",
  actionSize: "Botones",
};
export function CheckoutDesignView({
  business,
  csrf,
  permissions,
  storeUrl,
}: {
  business: string;
  csrf: string;
  permissions: string[];
  storeUrl?: string;
}) {
  const url = endpoint(business) + "/checkout-design",
    resource = useResource<Saved>(url),
    frame = useRef<HTMLIFrameElement>(null);
  const [saved, setSaved] = useState<Saved>(),
    [draft, setDraft] = useState<CheckoutProfile>(),
    [ready, setReady] = useState(false),
    [busy, setBusy] = useState(false),
    [message, setMessage] = useState(""),
    [error, setError] = useState(""),
    [piece, setPiece] = useState("panel"),
    [phone, setPhone] = useState(true),
    [measurement, setMeasurement] =
      useState<ReturnType<typeof measureDesign>>();
  const data = saved || resource.data,
    profile = draft || data?.profile,
    canWrite = permissions.includes("settings.write");
  const dirty =
    !!profile &&
    !!data &&
    JSON.stringify(profile) !== JSON.stringify(data.profile);
  const current = useRef(profile);
  current.current = profile;
  useEffect(() => {
    const receive = (e: MessageEvent) => {
      if (
        e.origin === location.origin &&
        e.source === frame.current?.contentWindow &&
        e.data?.type === "101:checkout-ready" &&
        e.data.business_id === business
      ) {
        setReady(true);
        const doc = frame.current?.contentDocument;
        const cart = doc?.getElementById("cart");
        if (cart) {
          const top =
            cart.getBoundingClientRect().top + (doc?.defaultView?.scrollY || 0);
          doc?.defaultView?.scrollTo(0, Math.max(0, top - 24));
        }
      }
    };
    window.addEventListener("message", receive);
    return () => window.removeEventListener("message", receive);
  }, [business]);
  useEffect(() => {
    if (!ready || !profile) return;
    frame.current?.contentWindow?.postMessage(
      { type: "101:checkout-preview", business_id: business, profile },
      location.origin,
    );
  }, [profile, ready]);
  function edit(next: CheckoutProfile) {
    try {
      setDraft(checkoutProfile(next));
      setError("");
      setMessage("");
      setMeasurement(undefined);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  function measure() {
    const doc = frame.current?.contentDocument;
    if (doc?.body) setMeasurement(measureDesign(doc.body, CHECKOUT_ANATOMY));
  }
  function number(
    group: "geometry" | "typography",
    key: string,
    bounds: [number, number],
  ) {
    if (!profile) return null;
    return (
      <label key={key}>
        {names[key]} (px)
        <input
          type="number"
          min={bounds[0]}
          max={bounds[1]}
          value={profile[group][key] ?? ""}
          placeholder="Original"
          onChange={(e) => {
            const values = { ...profile[group] };
            if (e.target.value === "") delete values[key];
            else values[key] = Number(e.target.value);
            edit({ ...profile, [group]: values });
          }}
        />
      </label>
    );
  }
  async function save() {
    if (!profile || !data) return;
    setBusy(true);
    setError("");
    try {
      const next = await api<Saved>(url, {
        method: "PUT",
        headers: { "Content-Type": "application/json", "X-101-CSRF": csrf },
        body: JSON.stringify({ expected_revision: data.revision, profile }),
      });
      setSaved({ ...data, ...next });
      setDraft(undefined);
      setMessage(
        "Diseño aplicado al checkout. Los pedidos conservan sus datos.",
      );
    } catch (e) {
      setError(
        (e as { status?: number }).status === 409
          ? "Otra persona cambió este diseño. Recarga para revisar su versión."
          : "No pudimos guardar el diseño. Tus cambios siguen aquí.",
      );
    } finally {
      setBusy(false);
    }
  }
  function download() {
    if (!profile) return;
    const value = {
      schema: "101-checkout-export-v1",
      profile,
      measurements: measurement || null,
    };
    const object = URL.createObjectURL(
      new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
    );
    const a = document.createElement("a");
    a.href = object;
    a.download = "checkout-design.json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(object), 1000);
  }
  async function upload(file?: File) {
    if (!file) return;
    try {
      if (file.size > 65536) throw Error("El archivo supera 64 KB.");
      const value = JSON.parse(await file.text());
      const imported = checkoutProfile(
        value.schema === "101-checkout-export-v1" ? value.profile : value,
      );
      setDraft(imported);
      setMeasurement(undefined);
      setError("");
      setMessage("Diseño importado para revisar. Aún no está aplicado.");
    } catch (e) {
      setError("No se importó el diseño: " + (e as Error).message);
    }
  }
  if (resource.error)
    return <Failure message={resource.error} retry={resource.retry} />;
  if (!data || !profile) return <Loading />;
  const surface = profile.bones.surfaces[piece] || {};
  return (
    <div className="page checkout-design">
      <section className="page-heading">
        <div>
          <span className="eyebrow">SITIO WEB</span>
          <h1>Checkout</h1>
          <p>La misma compra, con la identidad de tu negocio.</p>
        </div>
        <a
          className="button secondary"
          href={storeUrl || `/?business_id=${encodeURIComponent(business)}`}
          target="_blank"
          rel="noreferrer"
        >
          Abrir sitio
        </a>
      </section>
      <div className="checkout-design-status" role="status">
        {dirty
          ? "Cambios sin aplicar"
          : `Diseño actual · versión ${data.revision}`}
        {!data.available &&
          " · Guardado no disponible: falta instalar el almacenamiento."}
      </div>
      {error && (
        <p className="state error" role="alert">
          {error}
        </p>
      )}
      {message && (
        <p className="notice" role="status">
          {message}
        </p>
      )}
      <a
        className="button secondary checkout-preview-jump"
        href="#checkout-preview"
      >
        Ver vista previa
      </a>
      <div className="checkout-design-grid">
        <section
          className="panel checkout-design-controls"
          aria-label="Diseño del checkout"
        >
          <h2>Diseño</h2>
          <fieldset disabled={!canWrite || busy}>
            <legend className="sr-only">Apariencia del checkout</legend>
            <label>
              Punto de partida
              <select
                value=""
                onChange={(e) =>
                  edit(structuredClone(data.contract.presets[e.target.value]))
                }
              >
                <option value="" disabled>
                  Elegir un diseño…
                </option>
                <option value="source">Diseño actual de referencia</option>
                <option value="neutral">Chasis neutro</option>
                <option value="warm">Ejemplo cálido · demostración</option>
              </select>
            </label>
            <label>
              Distribución
              <select
                value={profile.layout}
                onChange={(e) =>
                  edit({
                    ...profile,
                    layout: e.target.value as CheckoutProfile["layout"],
                  })
                }
              >
                <option value="sidebar">Pedido junto al menú</option>
                <option value="stacked">Pedido debajo del menú</option>
              </select>
            </label>
            <details open>
              <summary>Espacios y tamaño</summary>
              <div className="checkout-field-grid">
                {Object.entries(data.contract.geometry).map(([key, bounds]) =>
                  number("geometry", key, bounds),
                )}
              </div>
            </details>
            <details>
              <summary>Colores</summary>
              <div className="checkout-field-grid">
                {data.contract.colors.map((key) => (
                  <label key={key}>
                    {names[key]}
                    <input
                      type="color"
                      value={
                        profile.colors[key] ||
                        data.contract.presets.neutral.colors[key]
                      }
                      onChange={(e) =>
                        edit({
                          ...profile,
                          colors: { ...profile.colors, [key]: e.target.value },
                        })
                      }
                    />
                  </label>
                ))}
              </div>
            </details>
            <details>
              <summary>Tipografía</summary>
              {["bodyFont", "headingFont"].map((key) => (
                <label key={key}>
                  {key === "bodyFont"
                    ? "Fuente del texto"
                    : "Fuente del título"}
                  <select
                    value={profile.typography[key] || ""}
                    onChange={(e) => {
                      const type = { ...profile.typography };
                      if (e.target.value) type[key] = e.target.value;
                      else delete type[key];
                      edit({ ...profile, typography: type });
                    }}
                  >
                    <option value="">Original</option>
                    {Object.entries(data.contract.fonts).map(([id, family]) => (
                      <option key={id} value={id}>
                        {family}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
              <div className="checkout-field-grid">
                {Object.entries(data.contract.typography).map(([key, bounds]) =>
                  number("typography", key, bounds),
                )}
              </div>
            </details>
            <details>
              <summary>Piezas del chasis</summary>
              <label>
                Pieza
                <select
                  value={piece}
                  onChange={(e) => setPiece(e.target.value)}
                >
                  {data.contract.surfaces.map((key) => (
                    <option key={key} value={key}>
                      {names[key]}
                    </option>
                  ))}
                </select>
              </label>
              <div className="checkout-field-grid">
                {[
                  ["radius", "Esquinas", 96],
                  ["padding", "Espacio interior", 64],
                  ["borderWidth", "Grosor del borde", 4],
                  ["marginTop", "Espacio anterior", 96],
                  ["marginBottom", "Espacio posterior", 96],
                ].map(([key, label, max]) => (
                  <label key={key}>
                    {label} (px)
                    <input
                      type="number"
                      min="0"
                      max={max}
                      value={surface[key] ?? ""}
                      placeholder="Original"
                      onChange={(e) => {
                        const next = { ...surface };
                        if (e.target.value === "") delete next[key];
                        else next[key] = Number(e.target.value);
                        edit({
                          ...profile,
                          bones: {
                            surfaces: {
                              ...profile.bones.surfaces,
                              [piece]: next,
                            },
                          },
                        });
                      }}
                    />
                  </label>
                ))}
                {[
                  ["fill", "Fondo"],
                  ["borderColor", "Color del borde"],
                ].map(([key, label]) => (
                  <label key={key}>
                    {label}
                    <input
                      type="color"
                      value={
                        typeof surface[key] === "string" &&
                        String(surface[key]).startsWith("#")
                          ? String(surface[key])
                          : "#ffffff"
                      }
                      onChange={(e) =>
                        edit({
                          ...profile,
                          bones: {
                            surfaces: {
                              ...profile.bones.surfaces,
                              [piece]: { ...surface, [key]: e.target.value },
                            },
                          },
                        })
                      }
                    />
                  </label>
                ))}
              </div>
              <button
                className="button secondary"
                type="button"
                onClick={() => {
                  const next = { ...profile.bones.surfaces };
                  delete next[piece];
                  edit({ ...profile, bones: { surfaces: next } });
                }}
              >
                Restablecer esta pieza
              </button>
            </details>
            <button
              className="button primary"
              disabled={!data.available || !dirty}
              onClick={save}
            >
              {busy ? "Guardando…" : "Aplicar al checkout"}
            </button>
          </fieldset>
          {!canWrite && (
            <p className="muted">
              Puedes revisar el diseño. Para cambiarlo necesitas permiso de
              ajustes.
            </p>
          )}
          <div className="checkout-design-actions">
            <button className="button secondary" onClick={download}>
              Exportar diseño
            </button>
            <label className="button secondary">
              Importar diseño
              <input
                type="file"
                accept="application/json,.json"
                disabled={!canWrite}
                onChange={(e) => {
                  upload(e.target.files?.[0]);
                  e.target.value = "";
                }}
              />
            </label>
            <button
              className="button secondary"
              disabled={busy}
              onClick={() => {
                setSaved(undefined);
                setDraft(undefined);
                setMeasurement(undefined);
                setError("");
                resource.retry();
              }}
            >
              Recargar diseño guardado
            </button>
          </div>
        </section>
        <section
          className="panel checkout-design-preview"
          id="checkout-preview"
        >
          <div className="checkout-preview-heading">
            <div>
              <h2>Vista previa</h2>
              <p>Permite revisar el diseño. No envía pedidos ni pagos.</p>
            </div>
            <button
              className="button secondary"
              aria-pressed={phone}
              onClick={() => {
                setPhone(!phone);
                setMeasurement(undefined);
              }}
            >
              {phone ? "Ver ancho disponible" : "Ver móvil"}
            </button>
          </div>
          <div className="checkout-frame-holder">
            <iframe
              ref={frame}
              className={phone ? "checkout-frame phone" : "checkout-frame"}
              title="Vista previa del checkout"
              src={`/?business_id=${encodeURIComponent(business)}&checkout_preview=1`}
              sandbox="allow-scripts allow-same-origin"
            />
          </div>
          <button
            className="button secondary"
            disabled={!ready}
            onClick={measure}
          >
            Medir piezas visibles
          </button>
          {measurement && (
            <div className="checkout-measurements" role="status">
              <p>
                {measurement.boxes.length} piezas visibles medidas. Contraste:{" "}
                {measurement.contrast.filter((v) => v.status === "fail").length}{" "}
                alertas,{" "}
                {
                  measurement.contrast.filter((v) => v.status === "unknown")
                    .length
                }{" "}
                sin resolver.
              </p>
              <p>
                Mediciones del área visible; no son una evaluación estética ni
                una certificación de accesibilidad.
              </p>
            </div>
          )}
          <details>
            <summary>Inventario de piezas ({CHECKOUT_ANATOMY.length})</summary>
            <ul>
              {CHECKOUT_ANATOMY.map((item) => (
                <li key={item.role}>
                  {item.role} ·{" "}
                  {item.status === "reused" ? "reutilizada" : "extraída"}
                </li>
              ))}
            </ul>
          </details>
        </section>
      </div>
    </div>
  );
}
