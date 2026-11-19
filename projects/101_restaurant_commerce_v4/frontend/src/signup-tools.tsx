import { useRef, useState } from "react";
import { ArrowDownToLine, Copy, Check, RefreshCw } from "lucide-react";
import { endpoint, useResource, Failure, Loading } from "./ui";
import "./growth-channels.css";

type Signup = {
  business_name: string;
  signup_url: string | null;
  qr_url: string | null;
  available: boolean;
  mode: string;
  funnel: { source: string; stage: string; count: number }[];
};
const terms: Record<string, string> = {
  qr: "QR",
  website: "Sitio web",
  direct: "Enlace directo",
  page_opened: "Página abierta",
  code_requested: "Código solicitado",
  identifier_verified: "Identificador verificado",
  membership_created: "Nuevo registro",
};
export function SignupTools({ business }: { business: string }) {
  return (
    <div className="page growth-channel-page signup-tools">
      <section className="page-heading">
        <div>
          <h1>Registro de clientes</h1>
          <p>
            Comparte el enlace o el QR de este negocio y consulta sus registros.
          </p>
        </div>
      </section>
      <section className="work-surface signup-working">
        <SignupContent key={business} business={business} funnel />
      </section>
    </div>
  );
}
export function SignupContent({
  business,
  funnel = false,
}: {
  business: string;
  funnel?: boolean;
}) {
  const result = useResource<Signup>(endpoint(business) + "/signup"),
    input = useRef<HTMLInputElement>(null);
  const [notice, setNotice] = useState(""),
    [copied, setCopied] = useState(false),
    d = result.data;
  if (result.error)
    return <Failure message={result.error} retry={result.retry} />;
  if (!d) return <Loading />;
  return (
    <>
      {d.signup_url ? (
        <>
          <div className="qr-card">
            <span className="qr-business">{d.business_name}</span>
            <img
              src={endpoint(business) + "/signup/qr.png"}
              width="208"
              height="208"
              alt={`Código QR de registro para ${d.business_name}`}
            />
            <strong>Escanea. Únete. Vuelve.</strong>
            <span>Con tu teléfono o tu correo.</span>
          </div>
          {d.mode === "test" && (
            <p className="test-note">
              Demostración local · registro y códigos de prueba. El enlace local
              solo abre en esta máquina.
            </p>
          )}
          {!d.available && (
            <p className="test-note" role="status">
              El enlace está preparado. El envío de códigos aún no está
              configurado.
            </p>
          )}
          <div className="qr-downloads">
            <a
              className="button primary"
              download
              href={endpoint(business) + "/signup/qr.png"}
            >
              <ArrowDownToLine size={16} />
              Descargar PNG
            </a>
            <a
              className="button secondary"
              download
              href={endpoint(business) + "/signup/qr.svg"}
            >
              SVG
              <ArrowDownToLine size={15} />
            </a>
          </div>
          <label className="link-label">
            O comparte el enlace
            <input
              ref={input}
              readOnly
              value={d.signup_url}
              aria-label="Enlace de registro"
              onFocus={(e) => e.target.select()}
            />
          </label>
          <button
            className="button copy-button"
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(d.signup_url!);
                setCopied(true);
                setNotice("Enlace copiado.");
              } catch {
                input.current?.focus();
                input.current?.select();
                setCopied(false);
                setNotice("Seleccionamos el enlace para que puedas copiarlo.");
              }
            }}
          >
            {copied ? <Check size={16} /> : <Copy size={16} />}
            <span>{copied ? "Enlace copiado" : "Copiar enlace"}</span>
          </button>
          <p role="status">{notice}</p>
          <a
            className="button secondary"
            href={d.signup_url}
            target="_blank"
            rel="noopener noreferrer"
          >
            Abrir registro
          </a>
          <p className="source-note">
            El enlace compartido registra origen «Sitio web»; el QR usa origen
            «QR». Abrir la página no equivale a completar un registro.
          </p>
        </>
      ) : (
        <div className="state">
          <h2>Tu enlace aún no está listo</h2>
          <p>
            Falta configurar la dirección pública del negocio. No se generó un
            enlace para otro negocio.
          </p>
        </div>
      )}
      {funnel && (
        <section className="signup-funnel">
          <h2>Actividad de registro</h2>
          <p className="source-note">
            Conteos históricos de eventos del entorno{" "}
            {d.mode === "test"
              ? "de prueba"
              : d.mode === "unconfigured"
                ? "sin configurar"
                : "configurado"}
            . No son visitantes únicos ni conversiones atribuidas.
          </p>
          {d.funnel.length ? (
            <table>
              <caption className="sr-only">Eventos por origen y etapa</caption>
              <thead>
                <tr>
                  <th>Origen</th>
                  <th>Etapa</th>
                  <th>Eventos</th>
                </tr>
              </thead>
              <tbody>
                {d.funnel.map((r, i) => (
                  <tr key={r.source + r.stage + i}>
                    <td>{terms[r.source] || r.source}</td>
                    <td>{terms[r.stage] || r.stage}</td>
                    <td>{r.count.toLocaleString("es-CO")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p>No hay eventos registrados para este entorno.</p>
          )}
          <button className="button secondary" onClick={result.retry}>
            <RefreshCw size={16} />
            Actualizar actividad
          </button>
        </section>
      )}
    </>
  );
}
