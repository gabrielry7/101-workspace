import { useEffect, useState } from "react";
import { endpoint } from "./ui";
const labels: Record<string, string> = {
  unconfigured: "Falta configurar la conexión",
  disconnected: "Sin conectar",
  authorizing: "Esperando autorización",
  discovering: "Consultando la cuenta",
  choose_location: "Confirma la cuenta",
  syncing: "Importando publicaciones",
  connected: "Importación completada",
  partial: "Importación parcial",
  access_denied: "Permiso no concedido",
  reconnect_required: "Vuelve a conectar la cuenta",
  sync_error: "No pudimos completar la importación",
  disconnecting: "Desconectada aquí; retira el acceso en Instagram",
};
export function InstagramPanel({
  business,
}: {
  business: string;
  csrf: string;
}) {
  return (
    <section className="instagram-panel">
      <div>
        <h2>Instagram</h2>
        <p>
          La cuenta, sus permisos y las publicaciones importadas se revisan en
          Conexiones.
        </p>
      </div>
      <a
        className="button secondary"
        href={`/workspace/connections?business=${encodeURIComponent(business)}&provider=instagram`}
      >
        Revisar conexión de Instagram
      </a>
    </section>
  );
}
export function InstagramCallback() {
  const [message, setMessage] = useState("Terminando la conexión…");
  useEffect(() => {
    const query = new URLSearchParams(location.search);
    history.replaceState(null, "", "/connections/instagram/callback");
    void (async () => {
      try {
        const me = await fetch("/api/staff/me");
        if (!me.ok) throw Error("Inicia sesión y vuelve a conectar Instagram.");
        const identity = await me.json();
        const result = await fetch("/connections/instagram/complete", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-101-CSRF": identity.csrf,
          },
          body: JSON.stringify({
            state: query.get("state"),
            code: query.get("code"),
            error: query.get("error"),
          }),
        });
        if (!result.ok)
          throw Error(
            "La autorización venció o no pudo completarse. Vuelve a conectar la cuenta.",
          );
        const out = await result.json();
        location.replace(
          "/workspace/connections?provider=instagram&business=" +
            encodeURIComponent(out.business_id),
        );
      } catch (e) {
        setMessage(String(e));
      }
    })();
  }, []);
  return (
    <main className="social-workspace">
      <h1>Conectar Instagram</h1>
      <p role="status">{message}</p>
      <a href="/workspace/social">Volver a contenido</a>
    </main>
  );
}
