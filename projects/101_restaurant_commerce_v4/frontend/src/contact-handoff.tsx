import { useState } from "react";
import { api, useResource } from "./ui";

export function ContactHandoff({
  kind,
  id,
}: {
  kind: "orders" | "reservations";
  id: string;
}) {
  const policy = useResource<{offline_demo?:boolean}>("/api/browser-policy");
  const [draft, setDraft] = useState<{ message: string; url: string }>();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <section className="contact-handoff">
      {!draft ? (
        <button
          className="button secondary"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            setError("");
            try {
              const value = await api<{ message: string; url: string }>(
                `/api/operator/${kind}/${encodeURIComponent(id)}/whatsapp`,
              );
              const url = new URL(value.url);
              if (url.origin !== "https://wa.me")
                throw new Error("Invalid destination");
              setDraft(value);
            } catch {
              setError(
                "No pudimos preparar el mensaje. Revisa el teléfono y tu acceso.",
              );
            } finally {
              setBusy(false);
            }
          }}
        >
          {busy ? "Preparando…" : "Preparar mensaje de WhatsApp"}
        </button>
      ) : (
        <>
          <p>
            {policy.data?.offline_demo ? "Vista de prueba: este mensaje no se enviará." : "Revisa el mensaje antes de abrir WhatsApp. Se enviará cuando tú lo confirmes allí."}
          </p>
          <p className="handoff-message">{draft.message}</p>
          {!policy.data?.offline_demo && policy.data && <a
            className="button secondary"
            href={draft.url}
            target="_blank"
            rel="noopener noreferrer"
          >
            Abrir WhatsApp
          </a>}
        </>
      )}
      {error && <p role="alert">{error}</p>}
    </section>
  );
}
