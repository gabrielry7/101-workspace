import { useEffect, useRef, useState } from "react";
import { Dialog } from "@base-ui/react/dialog";
import { ArrowLeft, ArrowRight, RefreshCw, X } from "lucide-react";
import {
  api,
  ApiError,
  endpoint,
  count,
  useResource,
  Failure,
  Loading,
} from "./ui";
import { periodQuery } from "./workspace-views";
import { ContactHandoff } from "./contact-handoff";

const states: Record<string, string> = {
  requested: "Por confirmar",
  confirmed: "Confirmada",
  seated: "En el local",
  completed: "Completada",
  cancelled: "Cancelada",
  no_show: "No asistió",
};
const actions: Record<string, string> = {
  confirmed: "Confirmar reserva",
  seated: "Registrar llegada",
  completed: "Completar reserva",
  cancelled: "Cancelar reserva",
  no_show: "Registrar inasistencia",
};
type Reservation = {
  id: string;
  public_code: string;
  status: string;
  version: number;
  starts_at: string;
  party_size: number;
  notes: string | null;
  customer_name: string | null;
  customer_phone: string;
  source_channel: string;
  actions: string[];
  timezone?: string;
};
type Props = {
  business: string;
  permissions: string[];
  csrf: string;
  params: URLSearchParams;
  navigate: (changes: Record<string, string | null>, push?: boolean) => void;
};
const stamp = (value: string, zone: string) =>
  new Intl.DateTimeFormat("es-CO", {
    timeZone: zone,
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));

export function ReservationWorkspace({
  business,
  permissions,
  csrf,
  params,
  navigate,
}: Props) {
  const status = params.get("reservation_status") || "active";
  const offset = Math.max(0, Number(params.get("reservation_offset")) || 0);
  const selected = params.get("reservation");
  const root = `${endpoint(business)}/sales-reservations`;
  const list = useResource<{
    items: Reservation[];
    count: number;
    timezone: string;
  }>(
    `${root}?status=${encodeURIComponent(status)}&offset=${offset}&limit=25&${periodQuery(params)}`,
  );
  return (
    <div
      className={`sales-workspace reservation-workspace ${selected ? "sale-selected" : ""}`}
    >
      <div className="page">
        <section className="page-heading">
          <div>
            <h1>Reservas</h1>
            <p>Confirma las visitas y lleva el registro de quién llegó.</p>
          </div>
          <button className="button secondary" onClick={list.retry}>
            <RefreshCw size={16} />
            Actualizar
          </button>
        </section>
        <section className="customer-surface" aria-label="Reservas del negocio">
          <div className="surface-heading">
            <h2>
              Reservas <span>{list.data ? count(list.data.count) : "…"}</span>
            </h2>
          </div>
          <div className="toolbar">
            <label className="reservation-filter">
              Estado de la reserva
              <select
                aria-label="Estado de la reserva"
                value={status}
                onChange={(e) =>
                  navigate({
                    reservation_status: e.target.value,
                    reservation_offset: null,
                    reservation: null,
                  })
                }
              >
                <option value="active">Próximas y en curso</option>
                <option value="all">Todas</option>
                {Object.entries(states).map(([key, text]) => (
                  <option key={key} value={key}>
                    {text}
                  </option>
                ))}
              </select>
            </label>
            <span className="muted">
              Hora local del negocio · {list.data?.timezone || "…"}
            </span>
          </div>
          {list.error ? (
            <Failure message={list.error} retry={list.retry} />
          ) : !list.data ? (
            <Loading />
          ) : !list.data.items.length ? (
            <div className="state">
              <h3>No hay reservas en esta vista</h3>
              <p>Prueba otro estado o revisa las fechas seleccionadas.</p>
            </div>
          ) : (
            <div className="list-scroll reservation-list">
              {list.data.items.map((r) => (
                <a
                  className={`reservation-row ${selected === r.id ? "selected" : ""}`}
                  key={r.id}
                  href={`/workspace/sales?${new URLSearchParams({ ...Object.fromEntries(params), reservation: r.id })}`}
                  onClick={(e) => {
                    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey)
                      return;
                    e.preventDefault();
                    navigate({ reservation: r.id }, true);
                  }}
                >
                  <span>
                    <strong>#{r.public_code}</strong>
                    <small>{r.customer_name || "Sin nombre registrado"}</small>
                  </span>
                  <span>
                    <strong>{stamp(r.starts_at, list.data!.timezone)}</strong>
                    <small>{r.party_size} personas</small>
                  </span>
                  <span className="badge">{states[r.status]}</span>
                </a>
              ))}
            </div>
          )}
          {list.data && (
            <div className="pagination">
              <span>{count(list.data.count)} reservas</span>
              <button
                className="icon-button"
                aria-label="Reservas anteriores"
                disabled={!offset}
                onClick={() =>
                  navigate({
                    reservation_offset: String(Math.max(0, offset - 25)),
                    reservation: null,
                  })
                }
              >
                <ArrowLeft size={17} />
              </button>
              <button
                className="icon-button"
                aria-label="Más reservas"
                disabled={offset + 25 >= list.data.count}
                onClick={() =>
                  navigate({
                    reservation_offset: String(offset + 25),
                    reservation: null,
                  })
                }
              >
                <ArrowRight size={17} />
              </button>
            </div>
          )}
        </section>
      </div>
      {selected && (
        <ReservationDetail
          key={business + selected}
          id={selected}
          root={root}
          csrf={csrf}
          canOperate={permissions.includes("operations.write")}
          canContact={permissions.includes("contact.read")}
          close={() => {
            if (history.state?.customerWorkspace) history.back();
            else navigate({ reservation: null });
          }}
          changed={list.retry}
        />
      )}
    </div>
  );
}

function ReservationDetail({
  id,
  root,
  csrf,
  canOperate,
  canContact,
  close,
  changed,
}: {
  id: string;
  root: string;
  csrf: string;
  canOperate: boolean;
  canContact: boolean;
  close: () => void;
  changed: () => void;
}) {
  const resource = useResource<Reservation>(
    `${root}/${encodeURIComponent(id)}`,
  );
  const [current, setCurrent] = useState<Reservation>();
  const [pending, setPending] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [notice, setNotice] = useState("");
  const [checked, setChecked] = useState(false);
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    setCurrent(resource.data);
    if (resource.data) heading.current?.focus();
  }, [resource.data]);
  const d = current;
  async function change(target: string) {
    if (!d || busy || uncertain) return;
    setBusy(true);
    setNotice("");
    try {
      const value = await api<Reservation>(
        `/api/operator/reservations/${encodeURIComponent(id)}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json", "X-101-CSRF": csrf },
          body: JSON.stringify({ status: target, expected_version: d.version }),
        },
      );
      setPending(null);
      setCurrent({ ...value, timezone: d.timezone, actions: [] });
      resource.retry();
      changed();
    } catch (error) {
      setPending(null);
      if (error instanceof ApiError && error.status < 500) {
        setNotice(
          error.status === 409
            ? "La reserva cambió. Revisa su estado antes de continuar."
            : error.message,
        );
        setCurrent(undefined);
        resource.retry();
        changed();
      } else {
        setUncertain(true);
        setNotice(
          "No recibimos confirmación. Comprueba el estado antes de hacer otra acción.",
        );
      }
    } finally {
      setBusy(false);
    }
  }
  async function check() {
    setBusy(true);
    try {
      const value = await api<Reservation>(`${root}/${encodeURIComponent(id)}`);
      setCurrent(value);
      setUncertain(false);
      setNotice("Estado actualizado.");
      changed();
    } catch {
      setNotice(
        "No pudimos comprobar el estado. Inténtalo cuando tengas conexión.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <aside className="sale-detail" aria-label="Detalle de reserva">
      <div className="detail-top">
        <button
          className="icon-button"
          aria-label="Cerrar reserva"
          onClick={close}
        >
          <X size={19} />
        </button>
      </div>
      {resource.error ? (
        <Failure message={resource.error} retry={resource.retry} />
      ) : !d ? (
        <Loading />
      ) : (
        <div className="detail-body">
          <span className="eyebrow">
            {stamp(d.starts_at, d.timezone || "UTC")}
          </span>
          <h2 tabIndex={-1} ref={heading}>
            Reserva #{d.public_code}
          </h2>
          <span className="badge">{states[d.status]}</span>
          <section className="sale-customer">
            <strong>{d.customer_name || "Sin nombre registrado"}</strong>
            <span>{d.customer_phone || "Sin teléfono registrado"}</span>
            <p>{d.party_size} personas</p>
            {canContact && d.customer_phone && (
              <ContactHandoff kind="reservations" id={d.id} />
            )}
          </section>
          {d.notes && (
            <section>
              <h3>Notas</h3>
              <p>{d.notes}</p>
            </section>
          )}
          {notice && <p role="status">{notice}</p>}
          {uncertain ? (
            <button
              className="button secondary"
              disabled={busy}
              onClick={check}
            >
              Comprobar estado
            </button>
          ) : canOperate ? (
            <div className="order-actions">
              {d.actions.map((target) => (
                <button
                  className="button secondary"
                  key={target}
                  disabled={busy}
                  onClick={() => {
                    if (["cancelled", "no_show"].includes(target)) {
                      setChecked(false);
                      setPending(target);
                    } else change(target);
                  }}
                >
                  {actions[target]}
                </button>
              ))}
            </div>
          ) : (
            <p>Tu acceso permite consultar las reservas.</p>
          )}
          <Dialog.Root
            open={!!pending}
            onOpenChange={(open) => {
              if (!open && !busy) setPending(null);
            }}
          >
            <Dialog.Portal>
              <Dialog.Backdrop className="backdrop" />
              <Dialog.Popup className="action-dialog">
                <Dialog.Title>{pending && actions[pending]}</Dialog.Title>
                <Dialog.Description>
                  Revisa el estado de esta reserva antes de confirmar.
                </Dialog.Description>
                <label className="confirm-cash">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={(e) => setChecked(e.target.checked)}
                  />
                  Confirmo este cambio de la reserva #{d.public_code}.
                </label>
                <div className="dialog-actions">
                  <button
                    className="button secondary"
                    disabled={busy}
                    onClick={() => setPending(null)}
                  >
                    Volver
                  </button>
                  <button
                    className="button primary"
                    disabled={busy || !checked}
                    onClick={() => pending && change(pending)}
                  >
                    Confirmar
                  </button>
                </div>
              </Dialog.Popup>
            </Dialog.Portal>
          </Dialog.Root>
        </div>
      )}
    </aside>
  );
}
