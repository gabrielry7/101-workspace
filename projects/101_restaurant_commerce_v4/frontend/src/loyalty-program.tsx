import { useEffect, useRef, useState } from "react";
import { api, useResource } from "./ui";
import {
  CommandState,
  Field,
  MoneyField,
  NumberField,
  PercentField,
  emptyEligibility,
  localDate,
  normalize,
  utcDate,
  useCommand,
  type Eligibility,
  type Program,
  type Resource,
} from "./loyalty-shared";

export const newProgram = (currency: string): Program => ({
  schema_version: 1,
  name: "",
  description: "",
  currency,
  start_at: null,
  end_at: null,
  eligibility: emptyEligibility(),
  earning: { type: "points", spend_minor_per_point: 1000, points_per_unit: 1 },
  reward: null,
  minimum_redeem_points: 1,
  maximum_reward_minor: 10000,
  expiration_days: null,
  per_customer_budget_minor: 50000,
  campaign_budget_minor: 1000000,
  estimated_cost_per_point_minor: 10,
  expected_redemption_bps: 10000,
  stack_with_promotions: false,
  eligible_spend_basis: "net_items_excluding_tax_and_delivery",
  rounding: "floor_per_order",
});

type Product = { id: string; name: string };
export function EligibilityFields({
  value,
  onChange,
  currency,
  business,
  products = true,
}: {
  value: Eligibility;
  onChange: (e: Eligibility) => void;
  currency: string;
  business: string;
  products?: boolean;
}) {
  const store = useResource<{
    menus: { categories: { items: Product[] }[] }[];
  }>(
    products
      ? `/api/restaurants/${encodeURIComponent(business)}/storefront`
      : null,
  );
  const all =
    store.data?.menus.flatMap((m) => m.categories.flatMap((c) => c.items)) ||
    [];
  const [q, setQ] = useState(""),
    [restricted, setRestricted] = useState(value.customer_ids.length > 0);
  const searchRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    searchRef.current?.setCustomValidity(
      restricted && !value.customer_ids.length
        ? "Selecciona al menos un cliente o desactiva la selección específica."
        : "",
    );
  }, [restricted, value.customer_ids.length]);
  const customers = useResource<{
    items: {
      id: string;
      name: string | null;
      email: string | null;
      phone: string | null;
    }[];
  }>(
    restricted
      ? `/api/operator/restaurants/${encodeURIComponent(business)}/customers?q=${encodeURIComponent(q)}&limit=20`
      : null,
  );
  const toggle = (
    field: "included_product_ids" | "excluded_product_ids" | "customer_ids",
    id: string,
  ) =>
    onChange({
      ...value,
      [field]: value[field].includes(id)
        ? value[field].filter((x) => x !== id)
        : [...value[field], id],
    });
  return (
    <fieldset className="loyalty-section">
      <legend>Quién puede participar</legend>
      {products && (
        <MoneyField
          label="Compra mínima"
          value={value.minimum_purchase_minor}
          onChange={(n) => onChange({ ...value, minimum_purchase_minor: n })}
          currency={currency}
        />
      )}
      {!products &&
        (value.minimum_purchase_minor > 0 ||
          value.included_product_ids.length > 0 ||
          value.excluded_product_ids.length > 0) && (
          <p className="loyalty-notice">
            Esta selección depende de una compra. La participación se decide
            antes de comprar; coloca estas condiciones en los programas.{" "}
            <button
              type="button"
              className="button secondary"
              onClick={() =>
                onChange({
                  ...value,
                  minimum_purchase_minor: 0,
                  included_product_ids: [],
                  excluded_product_ids: [],
                })
              }
            >
              Quitar requisitos de compra de la participación
            </button>
          </p>
        )}
      <p className="loyalty-hint">
        Las recompensas requieren una identidad verificada. Un teléfono en un
        pedido no confirma quién compra.
      </p>
      {products && (
        <details>
          <summary>Productos incluidos y excluidos</summary>
          {store.error ? (
            <p role="alert">
              No pudimos cargar los productos. Conservamos tu selección.
            </p>
          ) : (
            <div className="loyalty-products">
              {all.map((p) => (
                <div key={p.id}>
                  <span>{p.name}</span>
                  <label>
                    <input
                      type="checkbox"
                      checked={value.included_product_ids.includes(p.id)}
                      disabled={value.excluded_product_ids.includes(p.id)}
                      onChange={() => toggle("included_product_ids", p.id)}
                    />
                    Incluir
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={value.excluded_product_ids.includes(p.id)}
                      disabled={value.included_product_ids.includes(p.id)}
                      onChange={() => toggle("excluded_product_ids", p.id)}
                    />
                    Excluir
                  </label>
                </div>
              ))}
            </div>
          )}
          <small>
            Sin productos incluidos, se consideran todos salvo los excluidos.
          </small>
        </details>
      )}
      <label className="loyalty-check">
        <input
          type="checkbox"
          checked={restricted}
          onChange={(e) => {
            setRestricted(e.target.checked);
            if (!e.target.checked) onChange({ ...value, customer_ids: [] });
          }}
        />
        Elegir clientes específicos
      </label>
      {restricted && (
        <div>
          <Field label="Buscar participantes">
            <input
              ref={searchRef}
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Nombre, correo o teléfono"
            />
          </Field>
          <span className="loyalty-hint">
            {value.customer_ids.length} seleccionados · máximo 20 resultados por
            búsqueda
          </span>
          {customers.data?.items.map((c) => (
            <label className="loyalty-check" key={c.id}>
              <input
                type="checkbox"
                checked={value.customer_ids.includes(c.id)}
                onChange={() => toggle("customer_ids", c.id)}
              />
              {c.name || c.email || c.phone || "Sin nombre"}
            </label>
          ))}
          {customers.error && (
            <p role="alert">No se pudo cargar la búsqueda.</p>
          )}
        </div>
      )}
    </fieldset>
  );
}

export function ProgramEditor({
  resource,
  currency,
  business,
  root,
  csrf,
  onSaved,
  onCancel,
}: {
  resource?: Resource<Program>;
  currency: string;
  business: string;
  root: string;
  csrf: string;
  onSaved: (r: Resource<Program>) => void;
  onCancel: () => void;
}) {
  const [doc, setDoc] = useState(resource?.document || newProgram(currency)),
    [revision, setRevision] = useState(resource?.revision);
  const key = useRef(crypto.randomUUID()),
    command = useCommand(csrf);
  const change = (patch: Partial<Program>) => setDoc({ ...doc, ...patch });
  const unsupported = !!doc.reward && doc.reward.type !== "fixed_value";
  async function save() {
    if (!doc.earning && !doc.reward) {
      command.fail("Activa la acumulación de puntos o una recompensa.");
      return;
    }
    const submitted = structuredClone(doc),
      expected = revision,
      id = resource?.id;
    await command.run(async () => {
      let result: Resource<Program>;
      try {
        result = await command.send<Resource<Program>>(
          id ? `${root}/programs/${id}` : `${root}/programs`,
          id ? "PUT" : "POST",
          id
            ? { expected_revision: expected, document: submitted }
            : { request_key: key.current, document: submitted },
        );
      } catch (e) {
        if (id) {
          const current = await api<Resource<Program>>(
            `${root}/programs/${id}`,
          );
          if (normalize(current.document) !== normalize(submitted)) throw e;
          result = current;
        } else throw e;
      }
      if (command.alive.current) onSaved(result);
    });
  }
  return (
    <form
      className="loyalty-form"
      onSubmit={(e) => {
        e.preventDefault();
        void save();
      }}
    >
      <div className="loyalty-title-row">
        <div>
          <span className="eyebrow">
            {resource ? "EDITAR PROPUESTA" : "NUEVO PROGRAMA"}
          </span>
          <h2>{resource?.document.name || "Define la recompensa"}</h2>
        </div>
        <button type="button" className="button secondary" onClick={onCancel}>
          Volver
        </button>
      </div>
      <CommandState command={command} />
      {unsupported && (
        <p role="status" className="loyalty-notice">
          Este tipo de recompensa conserva su configuración histórica. El editor
          de esta versión admite puntos y descuentos de valor fijo.
        </p>
      )}
      <fieldset
        disabled={command.busy || command.uncertain || unsupported}
        className="loyalty-editor-fields"
      >
        <fieldset className="loyalty-section">
          <legend>Información del programa</legend>
          <Field label="Nombre">
            <input
              value={doc.name}
              maxLength={200}
              onChange={(e) => change({ name: e.target.value })}
              required
            />
          </Field>
          <Field label="Descripción">
            <textarea
              value={doc.description}
              maxLength={4000}
              onChange={(e) => change({ description: e.target.value })}
            />
          </Field>
          <div className="loyalty-grid">
            <Field label="Comienza">
              <input
                type="datetime-local"
                value={localDate(doc.start_at)}
                onChange={(e) => change({ start_at: utcDate(e.target.value) })}
              />
            </Field>
            <Field label="Termina">
              <input
                type="datetime-local"
                value={localDate(doc.end_at)}
                onChange={(e) => change({ end_at: utcDate(e.target.value) })}
              />
            </Field>
          </div>
          <small>
            Horario local: {Intl.DateTimeFormat().resolvedOptions().timeZone}.
            Los importes se guardan en {doc.currency}.
          </small>
        </fieldset>
        <fieldset className="loyalty-section">
          <legend>Cómo se ganan y usan los puntos</legend>
          <label className="loyalty-check">
            <input
              type="checkbox"
              checked={!!doc.earning}
              onChange={(e) =>
                change({
                  earning: e.target.checked
                    ? {
                        type: "points",
                        spend_minor_per_point: 1000,
                        points_per_unit: 1,
                      }
                    : null,
                })
              }
            />
            Acumular puntos por compra
          </label>
          {doc.earning && (
            <div className="loyalty-grid">
              <MoneyField
                label="Por cada compra de"
                value={doc.earning.spend_minor_per_point}
                onChange={(n) =>
                  change({
                    earning: { ...doc.earning!, spend_minor_per_point: n },
                  })
                }
                currency={doc.currency}
              />
              <NumberField
                label="Puntos que se ganan"
                value={doc.earning.points_per_unit}
                min={1}
                onChange={(n) =>
                  change({ earning: { ...doc.earning!, points_per_unit: n } })
                }
              />
            </div>
          )}
          <label className="loyalty-check">
            <input
              type="checkbox"
              checked={!!doc.reward}
              onChange={(e) =>
                change({
                  reward: e.target.checked
                    ? {
                        type: "fixed_value",
                        points_cost: 10,
                        discount_minor: 1000,
                      }
                    : null,
                })
              }
            />
            Canjear puntos por un descuento fijo
          </label>
          {doc.reward && (
            <div className="loyalty-grid">
              <NumberField
                label="Puntos por canje"
                value={doc.reward.points_cost || 1}
                min={1}
                onChange={(n) =>
                  change({ reward: { ...doc.reward!, points_cost: n } })
                }
              />
              <MoneyField
                label="Valor del descuento"
                value={doc.reward.discount_minor || 0}
                onChange={(n) =>
                  change({ reward: { ...doc.reward!, discount_minor: n } })
                }
                currency={doc.currency}
              />
            </div>
          )}
          <div className="loyalty-grid">
            <NumberField
              label="Saldo mínimo para canjear"
              value={doc.minimum_redeem_points}
              min={1}
              onChange={(n) => change({ minimum_redeem_points: n })}
            />
            <MoneyField
              label="Descuento máximo por compra"
              value={doc.maximum_reward_minor}
              currency={doc.currency}
              onChange={(n) => change({ maximum_reward_minor: n })}
            />
          </div>
          <label className="loyalty-check">
            <input
              type="checkbox"
              checked={doc.expiration_days !== null}
              onChange={(e) =>
                change({ expiration_days: e.target.checked ? 90 : null })
              }
            />
            Los puntos vencen
          </label>
          {doc.expiration_days !== null && (
            <NumberField
              label="Días hasta el vencimiento"
              value={doc.expiration_days}
              min={1}
              onChange={(n) => change({ expiration_days: n })}
            />
          )}
          <label className="loyalty-check">
            <input
              type="checkbox"
              checked={doc.stack_with_promotions}
              onChange={(e) =>
                change({ stack_with_promotions: e.target.checked })
              }
            />
            Permitir combinar con promociones
          </label>
        </fieldset>
        <EligibilityFields
          value={doc.eligibility}
          onChange={(eligibility) => change({ eligibility })}
          currency={doc.currency}
          business={business}
        />
        <fieldset className="loyalty-section">
          <legend>Límites y costo estimado</legend>
          <div className="loyalty-grid">
            <MoneyField
              label="Presupuesto por cliente"
              value={doc.per_customer_budget_minor}
              currency={doc.currency}
              onChange={(n) => change({ per_customer_budget_minor: n })}
            />
            <MoneyField
              label="Presupuesto total"
              value={doc.campaign_budget_minor}
              currency={doc.currency}
              onChange={(n) => change({ campaign_budget_minor: n })}
            />
            <MoneyField
              label="Costo de cumplir cada punto"
              value={doc.estimated_cost_per_point_minor}
              currency={doc.currency}
              onChange={(n) => change({ estimated_cost_per_point_minor: n })}
            />
            <PercentField
              label="Canje esperado (%)"
              value={doc.expected_redemption_bps}
              onChange={(n) => change({ expected_redemption_bps: n })}
            />
          </div>
        </fieldset>
      </fieldset>
      <div className="loyalty-actions">
        <button
          className="button primary"
          disabled={command.busy || unsupported}
        >
          {command.busy
            ? "Guardando…"
            : command.uncertain
              ? "Reintentar guardado"
              : "Guardar borrador"}
        </button>
        {resource && (
          <button
            type="button"
            className="button secondary"
            disabled={command.busy || command.uncertain}
            onClick={async () => {
              try {
                const current = await api<Resource<Program>>(
                  `${root}/programs/${resource.id}`,
                );
                if (command.alive.current) {
                  setDoc(current.document);
                  setRevision(current.revision);
                }
              } catch {
                command.fail("No se pudo recargar la versión guardada.");
              }
            }}
          >
            Recargar versión guardada
          </button>
        )}
      </div>
      <small>
        Guardar crea una propuesta. Podrás revisar la versión antes de
        publicarla. Una pausa existente se conserva.
      </small>
    </form>
  );
}
