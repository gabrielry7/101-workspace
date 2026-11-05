import { useEffect, useState } from "react";
import "./color-preview.css";

const pairings = [
  ["original", "Actual · comparar"],
  ["gray-white", "Gris + blanco"],
  ["ink", "Blanco + tinta"],
  ["cobalt", "Blanco + cobalto"],
  ["violet", "Blanco + violeta"],
  ["forest", "Crema + bosque"],
  ["lime", "Negro + lima"],
] as const;
const known = (value: string | null) => pairings.some(([id]) => id === value);
const key = "101.workspace.color-preview";
function initialPairing() {
  const url = new URLSearchParams(location.search).get("pairing");
  if (known(url)) return url!;
  try {
    const stored = localStorage.getItem(key);
    if (known(stored)) return stored!;
  } catch {
    /* Storage restrictions must not block the workspace. */
  }
  return "original";
}
/** Mounted only in the explicit demo. No business setting or provider action. */
export function ColorPreview() {
  const [pairing, setPairing] = useState(initialPairing);
  useEffect(() => {
    if (pairing === "original")
      delete document.documentElement.dataset.workspacePairing;
    else document.documentElement.dataset.workspacePairing = pairing;
    try {
      localStorage.setItem(key, pairing);
    } catch {
      /* Optional persistence. */
    }
    return () => {
      delete document.documentElement.dataset.workspacePairing;
    };
  }, [pairing]);
  return (
    <div className="color-preview-bar">
      <label>
        Vista de color
        <select
          aria-label="Vista de color"
          value={pairing}
          onChange={(event) => {
            const next = event.target.value;
            setPairing(next);
            const url = new URL(location.href);
            url.searchParams.set("pairing", next);
            history.replaceState(history.state, "", url);
          }}
        >
          {pairings.map(([id, name]) => (
            <option key={id} value={id}>
              {name}
            </option>
          ))}
        </select>
      </label>
      <span>Prueba visual · solo en este navegador</span>
    </div>
  );
}
