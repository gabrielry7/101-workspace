import { useEffect, useState } from "react";
import { ArrowRight } from "lucide-react";
import { api, Failure, Loading, useResource } from "./ui";

type Entry = {
  destination: string | null;
  needs_business: boolean;
  denied: boolean;
};
export function WorkspaceEntry({
  target,
  businesses,
  onSignOut,
}: {
  target: string;
  businesses: { business_id: string; name: string }[];
  onSignOut: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const result = useResource<Entry>(
    "/api/staff/entry?next=" + encodeURIComponent(target),
  );
  useEffect(() => {
    if (result.data?.destination) location.replace(result.data.destination);
  }, [result.data]);
  async function enter(business?: string) {
    setBusy(true);
    setError("");
    try {
      const value = await api<Entry>(
        "/api/staff/entry?next=" +
          encodeURIComponent(target) +
          (business ? "&business=" + encodeURIComponent(business) : ""),
      );
      if (value.destination) location.replace(value.destination);
      else {
        setError("Elige un negocio para continuar.");
        setBusy(false);
      }
    } catch {
      setError("No pudimos abrir el espacio. Inténtalo de nuevo.");
      setBusy(false);
    }
  }
  // Resolve through the server once; never navigate to the untrusted next value.
  if (result.data?.destination) {
    return <Loading />;
  }
  if (result.error)
    return <Failure message={result.error} retry={result.retry} />;
  if (!result.data) return <Loading />;
  return (
    <div className="login">
      <section className="entry-businesses">
        <h1>Elige tu negocio</h1>
        {result.data.denied && (
          <p role="alert">No tienes acceso al negocio de ese enlace.</p>
        )}
        <p>Continuarás en la página que querías abrir.</p>
        {businesses.map((b) => (
          <button
            key={b.business_id}
            className="button secondary"
            disabled={busy}
            onClick={() => enter(b.business_id)}
          >
            {b.name}
            <ArrowRight size={17} />
          </button>
        ))}
        {!businesses.length && (
          <p>No tienes un negocio asignado. Pide acceso al administrador.</p>
        )}
        {error && <p role="alert">{error}</p>}
        <button
          className="button secondary"
          disabled={busy}
          onClick={onSignOut}
        >
          Cambiar de usuario
        </button>
      </section>
    </div>
  );
}
