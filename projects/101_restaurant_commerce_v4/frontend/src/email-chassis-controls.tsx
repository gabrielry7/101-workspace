import { useState } from "react";

type Surface = {
  fill?: string;
  radius?: number;
  padding?: number;
  borderWidth?: number;
  borderColor?: string;
  marginTop?: number;
  marginBottom?: number;
  shadow?: "none" | "soft";
};
type TypeStyle = {
  fontFamily?: string;
  fontSize?: number;
  fontWeight?: number;
  lineHeight?: number;
  letterSpacing?: number;
  textTransform?: string;
  color?: string;
};
export type EmailChassis = {
  schema_version: "1";
  coat?: "source" | "neutral";
  geometry?: { maxWidth?: number; logoWidth?: number };
  bones?: {
    shape?: "recipe" | "square" | "soft" | "round";
    surfaces?: Partial<
      Record<
        | "panel"
        | "card"
        | "stage"
        | "brand"
        | "intro"
        | "content"
        | "photo"
        | "controls"
        | "footer",
        Surface
      >
    >;
    colors?: Record<string, string>;
  };
  typography?: Partial<
    Record<"heading" | "body" | "label" | "action" | "meta", TypeStyle>
  >;
};
export function EmailChassisControls({
  value,
  change,
}: {
  value?: EmailChassis | null;
  change: (v: EmailChassis | undefined) => void;
}) {
  const [error, setError] = useState("");
  const c = value || ({ schema_version: "1", coat: "source" } as EmailChassis);
  function set(v: Partial<EmailChassis>) {
    change({ ...c, ...v });
    setError("");
  }
  function surface(
    role: "content" | "controls",
    key: keyof Surface,
    v: string | number | undefined,
  ) {
    set({
      bones: {
        ...c.bones,
        surfaces: {
          ...c.bones?.surfaces,
          [role]: { ...c.bones?.surfaces?.[role], [key]: v },
        },
      },
    });
  }
  function text(
    role: "heading" | "body",
    key: keyof TypeStyle,
    v: string | number | undefined,
  ) {
    set({
      typography: {
        ...c.typography,
        [role]: { ...c.typography?.[role], [key]: v },
      },
    });
  }
  function download() {
    const href = URL.createObjectURL(
      new Blob([JSON.stringify(c, null, 2)], { type: "application/json" }),
    );
    const a = document.createElement("a");
    a.href = href;
    a.download = "101-email-chassis.json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(href), 1000);
  }
  return (
    <details className="email-chassis">
      <summary>Huesos y chasis</summary>
      <p>
        Conserva la estructura del diseño y ajusta su apariencia. El contenido,
        los enlaces y la baja siguen siendo los de esta campaña.
      </p>
      <div className="form-fields">
        <label>
          Estilo base
          <select
            aria-label="Estilo base"
            value={c.coat || "source"}
            onChange={(e) =>
              set({ coat: e.target.value as EmailChassis["coat"] })
            }
          >
            <option value="source">Diseño original</option>
            <option value="neutral">Chasis neutro</option>
          </select>
        </label>
        <label>
          Forma de las superficies
          <select
            aria-label="Forma de las superficies"
            value={c.bones?.shape || "recipe"}
            onChange={(e) =>
              set({
                bones: {
                  ...c.bones,
                  shape: e.target.value as NonNullable<
                    EmailChassis["bones"]
                  >["shape"],
                },
              })
            }
          >
            <option value="recipe">Según el diseño</option>
            <option value="square">Recta</option>
            <option value="soft">Suave</option>
            <option value="round">Redondeada</option>
          </select>
        </label>
        <label>
          Ancho máximo · px
          <input
            type="number"
            min={320}
            max={800}
            value={c.geometry?.maxWidth ?? ""}
            placeholder="Según el diseño"
            onChange={(e) =>
              set({
                geometry: {
                  ...c.geometry,
                  maxWidth: e.target.value ? Number(e.target.value) : undefined,
                },
              })
            }
          />
        </label>
        <label>
          Tamaño del título · px
          <input
            type="number"
            min={12}
            max={72}
            value={c.typography?.heading?.fontSize ?? ""}
            placeholder="Según el diseño"
            onChange={(e) =>
              text(
                "heading",
                "fontSize",
                e.target.value ? Number(e.target.value) : undefined,
              )
            }
          />
        </label>
        <label>
          Tipografía del mensaje
          <select
            aria-label="Tipografía del mensaje"
            value={c.typography?.body?.fontFamily || ""}
            onChange={(e) =>
              text("body", "fontFamily", e.target.value || undefined)
            }
          >
            <option value="">Según el diseño</option>
            {[
              "Inter",
              "Arial",
              "Georgia",
              "Instrument Serif",
              "IBM Plex Sans Condensed",
              "IBM Plex Mono",
              "Geist",
            ].map((name) => (
              <option key={name}>{name}</option>
            ))}
          </select>
        </label>
        <label>
          Espacio interior del mensaje · px
          <input
            type="number"
            min={0}
            max={64}
            value={c.bones?.surfaces?.content?.padding ?? ""}
            placeholder="Según el diseño"
            onChange={(e) =>
              surface(
                "content",
                "padding",
                e.target.value ? Number(e.target.value) : undefined,
              )
            }
          />
        </label>
        <label>
          Fondo del mensaje
          <input
            placeholder="#ffffff · opcional"
            pattern="#[a-fA-F0-9]{6}"
            value={c.bones?.surfaces?.content?.fill || ""}
            onChange={(e) =>
              surface("content", "fill", e.target.value || undefined)
            }
          />
        </label>
        <label>
          Color del texto
          <input
            placeholder="#202020 · opcional"
            pattern="#[a-fA-F0-9]{6}"
            value={c.typography?.body?.color || ""}
            onChange={(e) => text("body", "color", e.target.value || undefined)}
          />
        </label>
        <label>
          Radio del botón · px
          <input
            type="number"
            min={0}
            max={96}
            value={c.bones?.surfaces?.controls?.radius ?? ""}
            placeholder="Según el diseño"
            onChange={(e) =>
              surface(
                "controls",
                "radius",
                e.target.value ? Number(e.target.value) : undefined,
              )
            }
          />
        </label>
        <div className="heading-actions">
          <button type="button" className="button secondary" onClick={download}>
            Exportar chasis
          </button>
          <button
            type="button"
            className="button secondary"
            onClick={() => {
              change(undefined);
              setError("");
            }}
          >
            Restablecer diseño
          </button>
        </div>
        <label>
          Importar chasis · JSON
          <input
            type="file"
            accept="application/json,.json"
            onChange={async (e) => {
              const f = e.target.files?.[0];
              if (!f) return;
              try {
                if (f.size > 16384) throw Error();
                const v = JSON.parse(await f.text());
                if (
                  !v ||
                  Array.isArray(v) ||
                  v.schema_version !== "1" ||
                  Object.keys(v).some(
                    (key) =>
                      ![
                        "schema_version",
                        "coat",
                        "geometry",
                        "bones",
                        "typography",
                      ].includes(key),
                  )
                )
                  throw Error();
                change(v);
                setError("");
              } catch {
                setError(
                  "No pudimos leer el chasis. Usa un archivo JSON de 101 de hasta 16 KB.",
                );
              }
              e.target.value = "";
            }}
          />
        </label>
        {error && <p role="alert">{error}</p>}
      </div>
      <p>
        Al guardar cambias la versión y tendrás que revisarla y aprobarla de
        nuevo.
      </p>
    </details>
  );
}
