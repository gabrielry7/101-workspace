import { useState } from "react";
import {
  bps,
  CommandState,
  Field,
  MoneyField,
  NumberField,
  PercentField,
  money,
  normalize,
  useCommand,
} from "./loyalty-shared";

type Projection = {
  assumed_purchase_lift_bps: number;
  expected_redemption_bps: number;
  expected_reward_cost_minor: string;
  reward_cost_percent_of_sales: string | null;
  estimated_incremental_contribution_profit_minor: string;
  projected_sales_minor: string;
  break_even: {
    status: string;
    incremental_sales_minor: string | null;
    required_lift_percent: string | null;
  };
  warnings: string[];
};
type Scenario = {
  currency: string;
  horizon_days: number;
  average_order_value_minor: number;
  purchases_per_customer: string;
  customer_count: number;
  contribution:
    | { type: "margin"; contribution_margin_bps: number }
    | {
        type: "order_contributions";
        source_reference: string;
        orders: { revenue_minor: number; contribution_minor: number }[];
      };
  reward:
    | {
        type: "proportional";
        reward_value_bps: number;
        fulfillment_cost_bps: number;
      }
    | {
        type: "per_purchase";
        reward_value_minor: number;
        fulfillment_cost_minor: number;
        rewards_per_purchase: string;
      }
    | {
        type: "fixed_issuance";
        reward_value_minor: number;
        fulfillment_cost_minor: number;
        issued_rewards: number;
      };
  expected_redemption_bps: number;
  operating_cost_minor: number;
  assumed_purchase_lift_bps: number;
  sensitivity: { redemption_bps: number[]; lift_bps: number[] };
};
type Result = {
  scenario: Scenario;
  scenario_digest: string;
  projection: Projection;
  sensitivity: Projection[];
  baseline_sales_minor: string;
  contribution_margin_percent: string;
  assumptions: string[];
};
const initial = (currency: string): Scenario => ({
  currency,
  horizon_days: 60,
  average_order_value_minor: 25000,
  purchases_per_customer: "2",
  customer_count: 1000,
  contribution: { type: "margin", contribution_margin_bps: 3000 },
  reward: {
    type: "proportional",
    reward_value_bps: 200,
    fulfillment_cost_bps: 200,
  },
  expected_redemption_bps: 5000,
  operating_cost_minor: 100000,
  assumed_purchase_lift_bps: 0,
  sensitivity: {
    redemption_bps: [2500, 5000, 10000],
    lift_bps: [0, 500, 1000],
  },
});
const warnings: Record<string, string> = {
  zero_baseline_sales:
    "No hay ventas de base para calcular un porcentaje de aumento.",
  nonpositive_contribution_margin:
    "El margen de contribución es cero o negativo.",
  nonpositive_incremental_margin_after_variable_rewards:
    "El costo variable absorbe el margen de ventas adicionales.",
  reward_cost_sales_percentage_undefined:
    "Sin ventas proyectadas, el porcentaje de costo no está definido.",
  positive_reward_value_with_zero_cost_assumption:
    "La recompensa tiene valor, pero su costo asumido es cero.",
  supplied_order_margin_extrapolated_not_causal:
    "El margen de los pedidos ingresados se extrapola al escenario.",
};

export function Economics({
  currency,
  root,
  csrf,
}: {
  currency: string;
  root: string;
  csrf: string;
}) {
  const [s, set] = useState<Scenario>(initial(currency)),
    [calculation, setCalculation] = useState<{
      result: Result;
      signature: string;
    }>(),
    [axes, setAxes] = useState({ redemption: "25, 50, 100", lift: "0, 5, 10" }),
    command = useCommand(csrf);
  const change = (patch: Partial<Scenario>) => set({ ...s, ...patch });
  const stale =
    !!calculation && calculation.signature !== normalize({ ...s, axes });
  async function calculate() {
    let scenario: Scenario;
    try {
      scenario = {
        ...s,
        sensitivity: {
          redemption_bps: axes.redemption.split(",").map((v) => bps(v.trim())),
          lift_bps: axes.lift.split(",").map((v) => bps(v.trim(), true)),
        },
      };
    } catch (e) {
      command.fail((e as Error).message);
      return;
    }
    const signature = normalize({ ...s, axes });
    await command.run(async () => {
      const result = await command.send<Result>(
        `${root}/simulator`,
        "POST",
        scenario,
      );
      if (command.alive.current) setCalculation({ result, signature });
    });
  }
  const result = calculation?.result,
    p = result?.projection;
  return (
    <div className="loyalty-economics">
      <div className="loyalty-title-row">
        <div>
          <h2>Antes de ofrecer, calcula</h2>
          <p>Compara costos y el aumento de ventas necesario para cubrirlos.</p>
        </div>
        <span className="badge">Supuestos editables</span>
      </div>
      <p className="loyalty-notice">
        Los valores iniciales son un ejemplo. El aumento de compras es un
        supuesto: este cálculo no demuestra que la recompensa lo cause.
      </p>
      <form
        className="loyalty-form"
        onSubmit={(e) => {
          e.preventDefault();
          void calculate();
        }}
      >
        <CommandState command={command} />
        <fieldset
          disabled={command.busy || command.uncertain}
          className="loyalty-editor-fields"
        >
          <fieldset className="loyalty-section">
            <legend>Ventas de base</legend>
            <div className="loyalty-grid">
              <MoneyField
                label="Compra promedio"
                currency={s.currency}
                value={s.average_order_value_minor}
                onChange={(n) => change({ average_order_value_minor: n })}
              />
              <Field label="Compras por cliente en el período">
                <input
                  required
                  type="text"
                  inputMode="decimal"
                  pattern="[0-9]+(\.[0-9]{1,6})?"
                  value={s.purchases_per_customer}
                  onChange={(e) =>
                    change({ purchases_per_customer: e.target.value })
                  }
                />
              </Field>
              <NumberField
                label="Clientes"
                value={s.customer_count}
                max={1000000000}
                onChange={(n) => change({ customer_count: n })}
              />
              <NumberField
                label="Días del escenario"
                value={s.horizon_days}
                min={1}
                max={3650}
                onChange={(n) => change({ horizon_days: n })}
              />
            </div>
            <Field label="Cómo estimar la contribución">
              <select
                value={s.contribution.type}
                onChange={(e) =>
                  change({
                    contribution:
                      e.target.value === "margin"
                        ? { type: "margin", contribution_margin_bps: 3000 }
                        : {
                            type: "order_contributions",
                            source_reference: "",
                            orders: [
                              {
                                revenue_minor: s.average_order_value_minor,
                                contribution_minor: 0,
                              },
                            ],
                          },
                  })
                }
              >
                <option value="margin">Porcentaje de margen</option>
                <option value="order_contributions">
                  Contribución por pedido
                </option>
              </select>
            </Field>
            {s.contribution.type === "margin" ? (
              <PercentField
                label="Margen de contribución (%)"
                min={-100}
                value={s.contribution.contribution_margin_bps}
                onChange={(n) =>
                  change({
                    contribution: {
                      type: "margin",
                      contribution_margin_bps: n,
                    },
                  })
                }
              />
            ) : (
              <div>
                <Field label="Fuente de costos">
                  <input
                    required
                    value={s.contribution.source_reference}
                    maxLength={200}
                    onChange={(e) => {
                      if (s.contribution.type === "order_contributions")
                        change({
                          contribution: {
                            ...s.contribution,
                            source_reference: e.target.value,
                          },
                        });
                    }}
                  />
                </Field>
                {s.contribution.orders.map((order, index) => (
                  <div className="loyalty-grid" key={index}>
                    <MoneyField
                      label={`Venta del pedido ${index + 1}`}
                      currency={s.currency}
                      value={order.revenue_minor}
                      onChange={(n) => {
                        if (s.contribution.type === "order_contributions")
                          change({
                            contribution: {
                              ...s.contribution,
                              orders: s.contribution.orders.map((o, i) =>
                                i === index ? { ...o, revenue_minor: n } : o,
                              ),
                            },
                          });
                      }}
                    />
                    <MoneyField
                      label={`Contribución del pedido ${index + 1}`}
                      currency={s.currency}
                      signed
                      value={order.contribution_minor}
                      onChange={(n) => {
                        if (s.contribution.type === "order_contributions")
                          change({
                            contribution: {
                              ...s.contribution,
                              orders: s.contribution.orders.map((o, i) =>
                                i === index
                                  ? { ...o, contribution_minor: n }
                                  : o,
                              ),
                            },
                          });
                      }}
                    />
                  </div>
                ))}
                <button
                  type="button"
                  className="button secondary"
                  disabled={s.contribution.orders.length >= 1000}
                  onClick={() => {
                    if (s.contribution.type === "order_contributions")
                      change({
                        contribution: {
                          ...s.contribution,
                          orders: [
                            ...s.contribution.orders,
                            { revenue_minor: 0, contribution_minor: 0 },
                          ],
                        },
                      });
                  }}
                >
                  Añadir pedido
                </button>
              </div>
            )}
          </fieldset>
          <fieldset className="loyalty-section">
            <legend>Valor y costo de la recompensa</legend>
            <Field label="Estructura de costo">
              <select
                value={s.reward.type}
                onChange={(e) =>
                  change({
                    reward:
                      e.target.value === "proportional"
                        ? {
                            type: "proportional",
                            reward_value_bps: 200,
                            fulfillment_cost_bps: 200,
                          }
                        : e.target.value === "per_purchase"
                          ? {
                              type: "per_purchase",
                              reward_value_minor: 1000,
                              fulfillment_cost_minor: 1000,
                              rewards_per_purchase: "1",
                            }
                          : {
                              type: "fixed_issuance",
                              reward_value_minor: 1000,
                              fulfillment_cost_minor: 1000,
                              issued_rewards: 1000,
                            },
                  })
                }
              >
                <option value="proportional">Porcentaje de ventas</option>
                <option value="per_purchase">Recompensas por compra</option>
                <option value="fixed_issuance">
                  Cantidad fija de recompensas
                </option>
              </select>
            </Field>
            {s.reward.type === "proportional" ? (
              <div className="loyalty-grid">
                <PercentField
                  label="Valor ofrecido (% de venta)"
                  value={s.reward.reward_value_bps}
                  onChange={(n) => {
                    if (s.reward.type === "proportional")
                      change({ reward: { ...s.reward, reward_value_bps: n } });
                  }}
                />
                <PercentField
                  label="Costo de cumplirlo (% de venta)"
                  value={s.reward.fulfillment_cost_bps}
                  onChange={(n) => {
                    if (s.reward.type === "proportional")
                      change({
                        reward: { ...s.reward, fulfillment_cost_bps: n },
                      });
                  }}
                />
              </div>
            ) : (
              <div className="loyalty-grid">
                <MoneyField
                  label="Valor de cada recompensa"
                  currency={s.currency}
                  value={s.reward.reward_value_minor}
                  onChange={(n) => {
                    if (s.reward.type !== "proportional")
                      change({
                        reward: { ...s.reward, reward_value_minor: n },
                      });
                  }}
                />
                <MoneyField
                  label="Costo de cumplir cada recompensa"
                  currency={s.currency}
                  value={s.reward.fulfillment_cost_minor}
                  onChange={(n) => {
                    if (s.reward.type !== "proportional")
                      change({
                        reward: { ...s.reward, fulfillment_cost_minor: n },
                      });
                  }}
                />
                {s.reward.type === "per_purchase" ? (
                  <Field label="Recompensas por compra">
                    <input
                      required
                      type="text"
                      inputMode="decimal"
                      pattern="[0-9]+(\.[0-9]{1,6})?"
                      value={s.reward.rewards_per_purchase}
                      onChange={(e) => {
                        if (s.reward.type === "per_purchase")
                          change({
                            reward: {
                              ...s.reward,
                              rewards_per_purchase: e.target.value,
                            },
                          });
                      }}
                    />
                  </Field>
                ) : (
                  <NumberField
                    label="Recompensas emitidas"
                    value={s.reward.issued_rewards}
                    max={1000000000}
                    onChange={(n) => {
                      if (s.reward.type === "fixed_issuance")
                        change({ reward: { ...s.reward, issued_rewards: n } });
                    }}
                  />
                )}
              </div>
            )}
            <div className="loyalty-grid">
              <PercentField
                label="Probabilidad de canje (%)"
                value={s.expected_redemption_bps}
                onChange={(n) => change({ expected_redemption_bps: n })}
              />
              <MoneyField
                label="Costo operativo del período"
                currency={s.currency}
                value={s.operating_cost_minor}
                onChange={(n) => change({ operating_cost_minor: n })}
              />
              <PercentField
                label="Aumento de compras supuesto (%)"
                min={-100}
                max={1000}
                value={s.assumed_purchase_lift_bps}
                onChange={(n) => change({ assumed_purchase_lift_bps: n })}
              />
            </div>
            <details>
              <summary>Escenarios de sensibilidad</summary>
              <div className="loyalty-grid">
                <Field
                  label="Probabilidades de canje (%)"
                  hint="Hasta 9 valores separados por coma."
                >
                  <input
                    required
                    value={axes.redemption}
                    onChange={(e) =>
                      setAxes({ ...axes, redemption: e.target.value })
                    }
                  />
                </Field>
                <Field
                  label="Aumentos supuestos (%)"
                  hint="Hasta 9 valores separados por coma."
                >
                  <input
                    required
                    value={axes.lift}
                    onChange={(e) => setAxes({ ...axes, lift: e.target.value })}
                  />
                </Field>
              </div>
            </details>
          </fieldset>
        </fieldset>
        <button className="button primary" disabled={command.busy}>
          {command.busy
            ? "Calculando…"
            : command.uncertain
              ? "Reintentar cálculo"
              : "Calcular escenario"}
        </button>
      </form>
      {result && p && (
        <section
          className="loyalty-results"
          aria-label="Resultado del escenario"
        >
          {stale && (
            <p className="loyalty-notice" role="status">
              Modificaste los supuestos. Calcula de nuevo para actualizar estos
              resultados.
            </p>
          )}
          <h3>
            {stale ? "Cálculo anterior" : "Resultado bajo estos supuestos"}
          </h3>
          <div className="loyalty-metrics">
            <div>
              <span>Costo esperado de recompensas</span>
              <strong>{money(p.expected_reward_cost_minor, currency)}</strong>
              <small>
                {p.reward_cost_percent_of_sales ?? "—"} % de las ventas
              </small>
            </div>
            <div>
              <span>Ventas adicionales para cubrir costos</span>
              <strong>
                {p.break_even.incremental_sales_minor === null
                  ? "Sin umbral finito"
                  : money(p.break_even.incremental_sales_minor, currency)}
              </strong>
              <small>
                {p.break_even.required_lift_percent === null
                  ? "Porcentaje sin base suficiente"
                  : `${p.break_even.required_lift_percent} % de aumento requerido`}
              </small>
            </div>
            <div>
              <span>Ganancia incremental estimada</span>
              <strong>
                {money(
                  p.estimated_incremental_contribution_profit_minor,
                  currency,
                )}
              </strong>
              <small>Incluye recompensas y operación</small>
            </div>
          </div>
          {p.warnings
            .filter((w) => w !== "behavioral_lift_is_assumed")
            .map((w) => (
              <p className="loyalty-hint" key={w}>
                {warnings[w] || w}
              </p>
            ))}
          <h3>Sensibilidad de la ganancia estimada</h3>
          <div className="loyalty-table-wrap" tabIndex={0}>
            <table>
              <caption>
                Supuestos de canje y aumento de compras; no son resultados
                experimentales.
              </caption>
              <thead>
                <tr>
                  <th>Canje esperado</th>
                  <th>Aumento supuesto</th>
                  <th>Ganancia estimada</th>
                </tr>
              </thead>
              <tbody>
                {result.sensitivity.map((cell, i) => (
                  <tr key={i}>
                    <td>{cell.expected_redemption_bps / 100} %</td>
                    <td>{cell.assumed_purchase_lift_bps / 100} %</td>
                    <td>
                      {money(
                        cell.estimated_incremental_contribution_profit_minor,
                        currency,
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
