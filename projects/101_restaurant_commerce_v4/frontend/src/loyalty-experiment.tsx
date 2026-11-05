import { useRef, useState } from "react";
import { api } from "./ui";
import { EligibilityFields } from "./loyalty-program";
import {
  bps,
  CommandState,
  emptyEligibility,
  Field,
  localDate,
  normalize,
  NumberField,
  percent,
  utcDate,
  useCommand,
  type Experiment,
  type Program,
  type Resource,
} from "./loyalty-shared";

const newExperiment = (currency: string, version: string): Experiment => ({
  schema_version: 1,
  name: "",
  description: "",
  currency,
  enrollment_start: new Date().toISOString(),
  enrollment_end: new Date(Date.now() + 30 * 86400000).toISOString(),
  observation_days: 60,
  carryover_days: 0,
  eligibility: emptyEligibility(),
  variants: [
    { name: "Control", allocation_bps: 5000, strategy_version_id: null },
    { name: "Variante A", allocation_bps: 5000, strategy_version_id: version },
  ],
  exclusion_group: "loyalty",
  allow_overlap: false,
  overlap_reason: null,
  baseline_benefits_preserved: true,
  primary_metric: "incremental_contribution_profit_per_randomized_customer",
  assignment_algorithm: "sha256-v1",
  analysis_plan: "",
  analysis_protocol: null,
});

export function ExperimentEditor({
  resource,
  programs,
  currency,
  business,
  root,
  csrf,
  onSaved,
  onCancel,
}: {
  resource?: Resource<Experiment>;
  programs: Resource<Program>[];
  currency: string;
  business: string;
  root: string;
  csrf: string;
  onSaved: (r: Resource<Experiment>) => void;
  onCancel: () => void;
}) {
  const options = programs.flatMap((p) =>
    p.versions
      .filter(
        (v) =>
          (!v.document.reward || v.document.reward.type === "fixed_value") &&
          v.document.currency === (resource?.document.currency || currency),
      )
      .map((v, i) => ({
        id: v.id,
        name: `${v.document.name} · versión ${i + 1}`,
      })),
  );
  const [doc, setDoc] = useState(
      resource?.document || newExperiment(currency, ""),
    ),
    [revision, setRevision] = useState(resource?.revision);
  const command = useCommand(csrf),
    key = useRef(crypto.randomUUID());
  const change = (patch: Partial<Experiment>) => setDoc({ ...doc, ...patch });
  const total = doc.variants.reduce((n, v) => n + v.allocation_bps, 0),
    controls = doc.variants.filter(
      (v) => v.strategy_version_id === null,
    ).length;
  async function save() {
    if (total !== 10000 || controls !== 1) {
      command.fail(
        "La distribución debe sumar 100 % y tener un solo grupo control.",
      );
      return;
    }
    const submitted = structuredClone(doc),
      expected = revision,
      id = resource?.id;
    await command.run(async () => {
      let result: Resource<Experiment>;
      try {
        result = await command.send<Resource<Experiment>>(
          id ? `${root}/experiments/${id}` : `${root}/experiments`,
          id ? "PUT" : "POST",
          id
            ? { expected_revision: expected, document: submitted }
            : { request_key: key.current, document: submitted },
        );
      } catch (e) {
        if (id) {
          const current = await api<Resource<Experiment>>(
            `${root}/experiments/${id}`,
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
            {resource ? "EDITAR PROPUESTA" : "NUEVO EXPERIMENTO"}
          </span>
          <h2>{resource?.document.name || "Compara ofertas adicionales"}</h2>
        </div>
        <button className="button secondary" type="button" onClick={onCancel}>
          Volver
        </button>
      </div>
      <CommandState command={command} />
      <fieldset
        disabled={command.busy || command.uncertain}
        className="loyalty-editor-fields"
      >
        <fieldset className="loyalty-section">
          <legend>Pregunta y período</legend>
          <Field label="Nombre del experimento">
            <input
              value={doc.name}
              required
              maxLength={200}
              onChange={(e) => change({ name: e.target.value })}
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
            <Field label="Inicio de participación">
              <input
                type="datetime-local"
                required
                value={localDate(doc.enrollment_start)}
                onChange={(e) =>
                  change({ enrollment_start: utcDate(e.target.value) || "" })
                }
              />
            </Field>
            <Field label="Cierre de participación">
              <input
                type="datetime-local"
                required
                value={localDate(doc.enrollment_end)}
                onChange={(e) =>
                  change({ enrollment_end: utcDate(e.target.value) || "" })
                }
              />
            </Field>
            <NumberField
              label="Días para evaluar cada cliente"
              value={doc.observation_days}
              min={1}
              max={1095}
              onChange={(n) => change({ observation_days: n })}
            />
            <NumberField
              label="Días de resguardo entre experimentos"
              value={doc.carryover_days}
              max={1095}
              onChange={(n) => change({ carryover_days: n })}
            />
          </div>
          <small>
            Horario local: {Intl.DateTimeFormat().resolvedOptions().timeZone}.
            Elige un período que cubra el ciclo normal de compra.
          </small>
        </fieldset>
        <fieldset className="loyalty-section">
          <legend>Variantes y distribución</legend>
          <p className="loyalty-hint">
            El control conserva los beneficios habituales y no recibe la oferta
            adicional. Cada variante usa una versión publicada del programa.
          </p>
          {!options.length && (
            <p className="loyalty-notice">
              Publica al menos una versión de programa en {doc.currency} antes
              de guardar las variantes.
            </p>
          )}
          <div className="loyalty-variants">
            {doc.variants.map((variant, index) => (
              <div className="loyalty-variant" key={index}>
                <Field label={`Nombre de variante ${index + 1}`}>
                  <input
                    value={variant.name}
                    required
                    maxLength={100}
                    onChange={(e) =>
                      change({
                        variants: doc.variants.map((v, i) =>
                          i === index ? { ...v, name: e.target.value } : v,
                        ),
                      })
                    }
                  />
                </Field>
                <Field label={`Oferta de variante ${index + 1}`}>
                  <select
                    value={
                      variant.strategy_version_id === null
                        ? "__control"
                        : variant.strategy_version_id
                    }
                    required
                    onChange={(e) =>
                      change({
                        variants: doc.variants.map((v, i) =>
                          i === index
                            ? {
                                ...v,
                                strategy_version_id:
                                  e.target.value === "__control"
                                    ? null
                                    : e.target.value,
                              }
                            : v,
                        ),
                      })
                    }
                  >
                    <option value="" disabled>
                      Elegir versión publicada
                    </option>
                    <option value="__control">
                      Control · sin oferta adicional
                    </option>
                    {options.map((v) => (
                      <option value={v.id} key={v.id}>
                        {v.name}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label={`Distribución ${index + 1} (%)`}>
                  <input
                    type="number"
                    required
                    min="0.01"
                    max="100"
                    step="0.01"
                    value={percent(variant.allocation_bps)}
                    onChange={(e) => {
                      try {
                        change({
                          variants: doc.variants.map((v, i) =>
                            i === index
                              ? {
                                  ...v,
                                  allocation_bps: bps(e.target.value || "0"),
                                }
                              : v,
                          ),
                        });
                      } catch {
                        /* Native decimal validity remains visible. */
                      }
                    }}
                  />
                </Field>
                {doc.variants.length > 2 && (
                  <button
                    className="button secondary"
                    type="button"
                    aria-label={`Quitar variante ${index + 1}`}
                    onClick={() =>
                      change({
                        variants: doc.variants.filter((_, i) => i !== index),
                      })
                    }
                  >
                    Quitar
                  </button>
                )}
              </div>
            ))}
          </div>
          <div className="loyalty-title-row">
            <span
              className={
                total === 10000 && controls === 1
                  ? "loyalty-hint"
                  : "loyalty-error"
              }
              role="status"
            >
              Total: {percent(total)} % · {controls} grupo
              {controls === 1 ? "" : "s"} control
            </span>
            <button
              className="button secondary"
              type="button"
              disabled={doc.variants.length >= 20}
              onClick={() =>
                change({
                  variants: [
                    ...doc.variants,
                    {
                      name: `Variante ${doc.variants.length}`,
                      allocation_bps: 0,
                      strategy_version_id: "",
                    },
                  ],
                })
              }
            >
              Añadir variante
            </button>
          </div>
        </fieldset>
        <EligibilityFields
          value={doc.eligibility}
          onChange={(eligibility) => change({ eligibility })}
          currency={doc.currency}
          business={business}
          products={false}
        />
        <fieldset className="loyalty-section">
          <legend>Protección y evaluación</legend>
          <Field
            label="Grupo de exclusión"
            hint="Los experimentos de este grupo no comparten clientes salvo permiso explícito."
          >
            <input
              value={doc.exclusion_group}
              required
              maxLength={100}
              onChange={(e) => change({ exclusion_group: e.target.value })}
            />
          </Field>
          <label className="loyalty-check">
            <input
              type="checkbox"
              checked={doc.allow_overlap}
              onChange={(e) =>
                change({
                  allow_overlap: e.target.checked,
                  overlap_reason: e.target.checked ? doc.overlap_reason : null,
                })
              }
            />
            Permitir superposición con otros experimentos
          </label>
          {doc.allow_overlap && (
            <Field label="Motivo para permitir superposición">
              <textarea
                required
                value={doc.overlap_reason || ""}
                maxLength={2000}
                onChange={(e) => change({ overlap_reason: e.target.value })}
              />
            </Field>
          )}
          <Field
            label="Plan de evaluación"
            hint="Define la comparación con control, los costos incluidos y el período antes de ver resultados."
          >
            <textarea
              value={doc.analysis_plan}
              minLength={20}
              maxLength={10000}
              required
              onChange={(e) => change({ analysis_plan: e.target.value })}
            />
          </Field>
          <p className="loyalty-hint">
            Métrica principal: ganancia incremental de contribución por cliente
            asignado, incluidas las personas que no compren. La asignación
            original se conserva al cambiar reglas.
          </p>
          <label className="loyalty-check">
            <input
              type="checkbox"
              checked={!!doc.analysis_protocol}
              onChange={(e) =>
                change({
                  analysis_protocol: e.target.checked
                    ? {
                        method: "welch_bonferroni_v1",
                        confidence_bps: 9500,
                        minimum_customers_per_arm: 100,
                        sample_size_rationale: "",
                        readout_at: new Date(
                          new Date(doc.enrollment_end).getTime() +
                            doc.observation_days * 86400000,
                        ).toISOString(),
                      }
                    : null,
                })
              }
            />
            Definir evaluación estadística antes de asignar clientes
          </label>
          {doc.analysis_protocol && (
            <>
              <Field
                label="Fecha acordada para evaluar"
                hint="Debe permitir el seguimiento completo de la última persona inscrita."
              >
                <input
                  type="datetime-local"
                  value={localDate(doc.analysis_protocol.readout_at)}
                  required
                  onChange={(e) =>
                    change({
                      analysis_protocol: {
                        ...doc.analysis_protocol!,
                        readout_at: utcDate(e.target.value) || "",
                      },
                    })
                  }
                />
              </Field>
              <NumberField
                label="Mínimo previsto de clientes por grupo"
                min={30}
                max={10000000}
                value={doc.analysis_protocol.minimum_customers_per_arm}
                onChange={(n) =>
                  change({
                    analysis_protocol: {
                      ...doc.analysis_protocol!,
                      minimum_customers_per_arm: n,
                    },
                  })
                }
              />
              <Field label="Confianza conjunta">
                <select
                  value={doc.analysis_protocol.confidence_bps}
                  onChange={(e) =>
                    change({
                      analysis_protocol: {
                        ...doc.analysis_protocol!,
                        confidence_bps: Number(e.target.value) as
                          9000 | 9500 | 9900,
                      },
                    })
                  }
                >
                  <option value={9000}>90 %</option>
                  <option value={9500}>95 %</option>
                  <option value={9900}>99 %</option>
                </select>
              </Field>
              <Field
                label="Justificación del tamaño de muestra"
                hint="Documenta el efecto de interés y la variación esperada o el cálculo de potencia. El mínimo declarado no garantiza potencia."
              >
                <textarea
                  minLength={20}
                  maxLength={2000}
                  required
                  value={doc.analysis_protocol.sample_size_rationale}
                  onChange={(e) =>
                    change({
                      analysis_protocol: {
                        ...doc.analysis_protocol!,
                        sample_size_rationale: e.target.value,
                      },
                    })
                  }
                />
              </Field>
              <p className="loyalty-hint">
                Comparaciones Welch por cliente, con ajuste Bonferroni entre
                ofertas y control. Se conserva este plan en la versión
                publicada. Cambiarlo después no altera el experimento que ya
                empezó.
              </p>
            </>
          )}
        </fieldset>
      </fieldset>
      <div className="loyalty-actions">
        <button className="button primary" disabled={command.busy}>
          {command.busy
            ? "Guardando…"
            : command.uncertain
              ? "Reintentar guardado"
              : "Guardar experimento"}
        </button>
        {resource && (
          <button
            className="button secondary"
            type="button"
            disabled={command.busy || command.uncertain}
            onClick={async () => {
              try {
                const current = await api<Resource<Experiment>>(
                  `${root}/experiments/${resource.id}`,
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
        Publicar prepara la configuración. La participación y las ofertas reales
        requieren la habilitación operativa correspondiente.
      </small>
    </form>
  );
}
