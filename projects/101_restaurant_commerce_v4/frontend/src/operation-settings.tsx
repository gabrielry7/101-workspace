import { useState } from "react";
import { RefreshCw } from "lucide-react";
import { api, endpoint, useResource, Failure, Loading } from "./ui";
import { OperationNotice, useOperation } from "./operations-ui";
import "./operations-workspace.css";

export type StockItem = {
  id: string;
  name: string;
  sold_out: boolean;
  remaining: number | null;
  version: number;
};
export type OperationSettings = {
  version: number;
  timezone: string;
  items: StockItem[];
  policy: {
    ordering_enabled: boolean;
    scheduled: boolean;
    weekdays: number[];
    opens: number;
    closes: number;
    slot_minutes: number;
    lead_minutes: number;
    capacity: number;
    closed_dates: string[];
  };
};
const clock = (n: number) =>
  `${String(Math.floor(n / 60)).padStart(2, "0")}:${String(n % 60).padStart(2, "0")}`;
const minutes = (s: string) => {
  const [h, m] = s.split(":").map(Number);
  return h * 60 + m;
};

export function OperationSettingsView({
  business,
  csrf,
  permissions,
  params,
  navigate,
}: {
  business: string;
  csrf: string;
  permissions: string[];
  params: URLSearchParams;
  navigate: (changes: Record<string, string | null>) => void;
}) {
  const root = endpoint(business),
    resource = useResource<OperationSettings>(root + "/settings");
  const [revision, setRevision] = useState(0),
    [current, setCurrent] = useState<OperationSettings>();
  const [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const section =
    params.get("section") === "inventory" ? "inventory" : "operations";
  const data = current || resource.data;
  const canWrite = permissions.includes("settings.write");
  async function refresh() {
    try {
      setCurrent(await api<OperationSettings>(root + "/settings"));
      setRevision((v) => v + 1);
      setError("");
      return true;
    } catch {
      setError(
        "No pudimos actualizar los datos. Conserva tus cambios y vuelve a intentarlo.",
      );
      return false;
    }
  }
  return (
    <div className="page operations-page">
      <section className="page-heading">
        <div>
          <h1>Ajustes</h1>
          <p>Disponibilidad, recogida y existencias del negocio.</p>
        </div>
      </section>
      <div className="tabs operation-tabs" aria-label="Secciones de ajustes">
        {[
          ["operations", "Disponibilidad"],
          ["inventory", "Existencias"],
        ].map(([key, title]) => (
          <button
            key={key}
            aria-pressed={section === key}
            className={section === key ? "selected" : ""}
            onClick={() => navigate({ section: key })}
          >
            {title}
          </button>
        ))}
      </div>
      {resource.error && !data ? (
        <Failure message={resource.error} retry={resource.retry} />
      ) : !data ? (
        <Loading />
      ) : (
        <>
          <p className="source-note">
            Hora local: {data.timezone}
            {!canWrite && " · Tu acceso permite consultar estos ajustes."}
          </p>
          {error && <p role="alert">{error}</p>}
          {notice && <p role="status">{notice}</p>}
          {section === "operations" ? (
            <SettingsForm
              key={data.version + ":" + revision}
              data={data}
              csrf={csrf}
              root={root}
              canWrite={canWrite}
              refresh={refresh}
              saved={(value) => {
                setCurrent(value);
                setNotice(
                  "Disponibilidad guardada. Los pedidos existentes conservan su hora.",
                );
              }}
            />
          ) : (
            <section className="customer-surface inventory-panel">
              <div className="surface-heading">
                <h2>Existencias</h2>
              </div>
              <p className="source-note">
                Una cantidad vacía significa que no llevas un conteo aquí. Cero
                significa que no quedan unidades.
              </p>
              {!data.items.length && (
                <div className="state">
                  <h3>No hay productos registrados</h3>
                </div>
              )}
              {data.items.map((item) => (
                <StockForm
                  key={item.id + ":" + item.version + ":" + revision}
                  item={item}
                  root={root}
                  csrf={csrf}
                  canWrite={canWrite}
                  saved={(value) => {
                    setCurrent((previous) => {
                      const old = previous || resource.data!;
                      return {
                        ...old,
                        items: old.items.map((row) =>
                          row.id === item.id
                            ? value.items.find(
                                (updated) => updated.id === item.id,
                              )!
                            : row,
                        ),
                      };
                    });
                    setNotice("Existencias guardadas para " + item.name + ".");
                  }}
                />
              ))}
            </section>
          )}
        </>
      )}
    </div>
  );
}

function SettingsForm({
  data,
  root,
  csrf,
  canWrite,
  refresh,
  saved,
}: {
  data: OperationSettings;
  root: string;
  csrf: string;
  canWrite: boolean;
  refresh: () => Promise<boolean>;
  saved: (data: OperationSettings) => void;
}) {
  const op = useOperation(csrf);
  return (
    <form
      aria-label="Disponibilidad del negocio"
      className="customer-surface operation-form"
      onSubmit={async (e) => {
        e.preventDefault();
        const f = new FormData(e.currentTarget);
        const body = {
          expected_version: data.version,
          reason: String(f.get("reason") || "").trim(),
          ordering_enabled: f.has("ordering"),
          scheduled: f.has("scheduled"),
          weekdays: f.getAll("weekday").map(Number),
          opens: minutes(String(f.get("opens"))),
          closes: minutes(String(f.get("closes"))),
          slot_minutes: Number(f.get("interval")),
          lead_minutes: Number(f.get("lead")),
          capacity: Number(f.get("capacity")),
          closed_dates: String(f.get("closed") || "")
            .split(/[\s,]+/)
            .filter(Boolean),
        };
        const result = await op.perform<OperationSettings>(
          root + "/settings",
          body,
          "PUT",
        );
        if (result) saved(result);
      }}
    >
      <h2>Pedidos y recogida</h2>
      <fieldset disabled={!canWrite || op.busy || op.uncertain}>
        <label className="check-label">
          <input
            type="checkbox"
            name="ordering"
            defaultChecked={data.policy.ordering_enabled}
          />
          Aceptar pedidos
        </label>
        <label className="check-label">
          <input
            type="checkbox"
            name="scheduled"
            defaultChecked={data.policy.scheduled}
          />
          Permitir elegir una hora de recogida
        </label>
        <fieldset className="weekday-options">
          <legend>Días de atención</legend>
          {[
            "Lunes",
            "Martes",
            "Miércoles",
            "Jueves",
            "Viernes",
            "Sábado",
            "Domingo",
          ].map((day, i) => (
            <label className="check-label" key={day}>
              <input
                type="checkbox"
                name="weekday"
                value={i}
                defaultChecked={data.policy.weekdays.includes(i)}
              />
              {day}
            </label>
          ))}
        </fieldset>
        <div className="operation-grid">
          <label>
            Hora de apertura
            <input
              name="opens"
              aria-label="Hora de apertura"
              pattern="(?:[01][0-9]|2[0-3]):[0-5][0-9]"
              placeholder="08:00"
              defaultValue={clock(data.policy.opens)}
              required
            />
          </label>
          <label>
            Hora de cierre
            <input
              name="closes"
              aria-label="Hora de cierre"
              pattern="(?:(?:[01][0-9]|2[0-3]):[0-5][0-9]|24:00)"
              placeholder="20:00"
              defaultValue={clock(data.policy.closes)}
              required
            />
            <small>Usa 24:00 si cierras a medianoche.</small>
          </label>
          <label>
            Intervalo entre horarios · minutos
            <input
              name="interval"
              type="number"
              min={15}
              max={120}
              defaultValue={data.policy.slot_minutes}
              required
            />
          </label>
          <label>
            Anticipación mínima · minutos
            <input
              name="lead"
              type="number"
              min={5}
              max={720}
              defaultValue={data.policy.lead_minutes}
              required
            />
          </label>
          <label>
            Pedidos por horario
            <input
              name="capacity"
              type="number"
              min={1}
              max={500}
              defaultValue={data.policy.capacity}
              required
            />
          </label>
          <label>
            Fechas sin atención
            <textarea
              name="closed"
              rows={3}
              defaultValue={data.policy.closed_dates.join(", ")}
              placeholder="AAAA-MM-DD, AAAA-MM-DD"
            />
          </label>
        </div>
        <label>
          Motivo del cambio
          <input name="reason" maxLength={500} required />
        </label>
        {canWrite && (
          <button className="button primary" disabled={op.busy}>
            Guardar disponibilidad
          </button>
        )}
      </fieldset>
      <OperationNotice message={op.message} />
      <button
        type="button"
        className="button secondary"
        disabled={op.busy}
        onClick={async () => {
          if (await refresh()) op.checked();
        }}
      >
        <RefreshCw size={16} />
        {op.uncertain ? "Comprobar estado" : "Descartar cambios y actualizar"}
      </button>
    </form>
  );
}

function StockForm({
  item,
  root,
  csrf,
  canWrite,
  saved,
}: {
  item: StockItem;
  root: string;
  csrf: string;
  canWrite: boolean;
  saved: (data: OperationSettings) => void;
}) {
  const op = useOperation(csrf);
  return (
    <form
      className="stock-form"
      aria-label={"Existencias de " + item.name}
      onSubmit={async (e) => {
        e.preventDefault();
        const f = new FormData(e.currentTarget),
          raw = String(f.get("remaining") || "");
        const result = await op.perform<OperationSettings>(
          root + "/stock/" + encodeURIComponent(item.id),
          {
            expected_version: item.version,
            remaining: raw === "" ? null : Number(raw),
            sold_out: f.has("sold_out"),
            reason: String(f.get("reason") || "").trim(),
          },
          "PUT",
        );
        if (result) saved(result);
      }}
    >
      <h3>{item.name}</h3>
      <fieldset
        disabled={!canWrite || op.busy || op.uncertain}
        className="operation-grid"
      >
        <label>
          Unidades disponibles
          <input
            aria-label={"Unidades de " + item.name}
            name="remaining"
            type="number"
            min={0}
            max={100000}
            defaultValue={item.remaining === null ? "" : item.remaining}
          />
        </label>
        <label className="check-label">
          <input
            type="checkbox"
            name="sold_out"
            defaultChecked={item.sold_out}
          />
          Marcar como agotado
        </label>
        <label>
          Motivo del ajuste
          <input
            aria-label={"Motivo para " + item.name}
            name="reason"
            maxLength={500}
            required
          />
        </label>
        {canWrite && (
          <button className="button secondary" disabled={op.busy}>
            Guardar existencias
          </button>
        )}
      </fieldset>
      <OperationNotice message={op.message} />
      {(op.message || op.uncertain) && (
        <button
          type="button"
          className="button secondary"
          onClick={async () => {
            try {
              const value = await api<OperationSettings>(root + "/settings");
              saved(value);
              op.checked();
            } catch {
              op.setMessage(
                "No pudimos comprobar las existencias. Vuelve a intentarlo.",
              );
            }
          }}
          disabled={op.busy}
        >
          Comprobar existencias
        </button>
      )}
    </form>
  );
}
