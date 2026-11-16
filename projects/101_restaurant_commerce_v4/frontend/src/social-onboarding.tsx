import { useEffect, useRef, useState } from "react";
import type { BusinessContext } from "./social-context";

type Answer = { choice: string; detail: string };
type Answers = {
  goal: Answer;
  channels: Answer[];
  feature: Answer;
  materials: string[];
  material_detail: string;
  conditions: Answer[];
  lead_time: Answer | null;
  locale: string | null;
};
const goals = {
  discovery: "Que más personas me conozcan",
  orders: "Recibir más pedidos",
  bookings: "Conseguir más reservas",
  repeat: "Que mis clientes vuelvan",
  promote: "Promover algo específico",
  other: "Otra prioridad",
  unknown: "No estoy seguro",
};
const channels = {
  store: "En el local",
  whatsapp: "Por WhatsApp",
  instagram: "Por Instagram",
  website: "En mi página",
  platform: "Por una plataforma",
  other: "Otra forma",
  later: "Lo vemos después",
};
const features = {
  product: "Un producto o servicio",
  process: "Cómo trabajamos",
  team: "Nuestro equipo",
  news: "Una novedad",
  question: "Responder una pregunta frecuente",
  other: "Otra idea",
  help: "Ayúdenme a decidir",
};
const materials = {
  photos: "Fotos",
  videos: "Videos",
  logo: "Logo",
  posts: "Publicaciones anteriores",
  other: "Otro material",
  none: "Todavía no tengo material",
  later: "Lo vemos después",
};
const conditions = {
  advance: "Trabajamos por encargo",
  limited: "Tenemos cupos limitados",
  area: "Atendemos ciertas zonas",
  variable_price: "Los precios varían",
  other: "Otra condición",
  none: "Nada por ahora",
  later: "Lo vemos después",
};
const leadTimes = {
  same_day: "El mismo día",
  one_day: "Un día antes",
  two_days: "Dos días antes",
  depends: "Depende del producto",
  other: "Otro plazo",
  unknown: "No estoy seguro",
};
const blank = (): Answers => ({
  goal: { choice: "", detail: "" },
  channels: [],
  feature: { choice: "", detail: "" },
  materials: [],
  material_detail: "",
  conditions: [],
  lead_time: null,
  locale: null,
});
function initial(c: BusinessContext): Answers {
  if (c.onboarding) return structuredClone(c.onboarding);
  const a = blank(),
    b = c.brief;
  if (b) {
    if (b.objective) a.goal = { choice: "other", detail: b.objective };
    if (b.buying_destination)
      a.channels = [{ choice: "other", detail: b.buying_destination }];
    if (b.offering) a.feature = { choice: "other", detail: b.offering };
    if (b.constraints)
      a.conditions = [{ choice: "other", detail: b.constraints }];
    a.locale = b.locale || null;
  }
  return a;
}
function Options({
  label,
  options,
  selected,
  onSelect,
  multi = false,
}: {
  label: string;
  options: Record<string, string>;
  selected: string[];
  onSelect: (key: string) => void;
  multi?: boolean;
}) {
  return (
    <fieldset className="onboarding-options">
      <legend>{label}</legend>
      <div className="onboarding-choices">
        {Object.entries(options).map(([key, text]) => (
          <label key={key} className={selected.includes(key) ? "selected" : ""}>
            <input
              type={multi ? "checkbox" : "radio"}
              name={label}
              checked={selected.includes(key)}
              onChange={() => onSelect(key)}
            />
            <span>{text}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
const describe = (a: Answer, labels: Record<string, string>) =>
  a.choice
    ? a.choice === "other"
      ? a.detail
      : labels[a.choice] + (a.detail ? " · " + a.detail : "")
    : "Sin responder";
export function SocialOnboarding({
  context,
  request,
  onSaved,
  onClose,
}: {
  context: BusinessContext;
  request: (p: string, m?: string, b?: unknown) => Promise<any>;
  onSaved: (c: BusinessContext) => void;
  onClose: () => void;
}) {
  const [answers, setAnswers] = useState<Answers>(() => initial(context)),
    [step, setStep] = useState(0),
    [confirmed, setConfirmed] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const heading = useRef<HTMLHeadingElement>(null),
    form = useRef<HTMLFormElement>(null);
  const firstStepRender = useRef(true);
  useEffect(() => {
    if (firstStepRender.current) {
      firstStepRender.current = false;
      return;
    }
    heading.current?.focus();
  }, [step]);
  function change<K extends keyof Answers>(key: K, value: Answers[K]) {
    setAnswers((a) => ({ ...a, [key]: value }));
    setConfirmed(false);
    setError("");
  }
  function toggle(key: "channels" | "conditions", choice: string) {
    const old = answers[key];
    const exclusive = ["none", "later"];
    const next = old.some((a) => a.choice === choice)
      ? old.filter((a) => a.choice !== choice)
      : [
          ...old.filter(
            (a) => !exclusive.includes(a.choice) && !exclusive.includes(choice),
          ),
          { choice, detail: "" },
        ];
    setAnswers((a) => ({
      ...a,
      [key]: next,
      ...(key === "conditions" && !next.some((v) => v.choice === "advance")
        ? { lead_time: null }
        : {}),
    }));
    setConfirmed(false);
    setError("");
  }
  function details(
    key: "channels" | "conditions",
    choice: string,
    value: string,
  ) {
    change(
      key,
      answers[key].map((a) =>
        a.choice === choice ? { ...a, detail: value } : a,
      ),
    );
  }
  function field(
    label: string,
    value: string,
    update: (v: string) => void,
    required = false,
  ) {
    return (
      <label className="onboarding-detail">
        {label}
        <textarea
          rows={2}
          maxLength={2400}
          required={required}
          value={value}
          onChange={(e) => update(e.target.value)}
        />
      </label>
    );
  }
  const titles = [
    "¿Qué te gustaría conseguir primero?",
    "¿Cómo te compran o contratan hoy?",
    "¿Qué te gustaría mostrar primero?",
    "¿Qué material tienes?",
    "Revisa lo que nos contaste",
  ];
  function next() {
    if (!form.current?.reportValidity()) return;
    const ready = [
      !!answers.goal.choice,
      !!answers.channels.length,
      !!answers.feature.choice,
      !!answers.materials.length,
    ][step];
    if (!ready) {
      setError("Elige una respuesta. También puedes dejarlo para después.");
      return;
    }
    setError("");
    setStep(step + 1);
  }
  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (step < 4) {
      next();
      return;
    }
    setBusy(true);
    setError("");
    try {
      const saved = await request("/context/onboarding", "PUT", {
        expected_revision: context.revision,
        location_id: context.location_id || null,
        answers,
        confirmed,
      });
      onSaved(saved);
      onClose();
    } catch (e) {
      setError(
        String(e).includes("context_revision_conflict")
          ? "La información cambió en otra sesión. Cierra esta guía y recarga antes de guardar."
          : String(e),
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="social-onboarding" aria-label="Guía de tu negocio">
      <div className="onboarding-progress">
        <span>Paso {step + 1} de 5</span>
      </div>
      <progress aria-label="Progreso de la guía" max={5} value={step + 1} />
      <h2 ref={heading} tabIndex={-1}>
        {titles[step]}
      </h2>
      <p>
        {step === 0
          ? "Elige una prioridad para empezar. Puedes cambiarla más adelante."
          : step === 1
            ? "Puedes elegir varias. Añade los detalles que ya tengas."
            : step === 2
              ? "Una primera idea es suficiente. Si todavía no la tienes, la dejamos pendiente."
              : step === 3
                ? "Por ahora solo dinos qué tienes. Podrás subirlo después."
                : "Estas respuestas orientan el trabajo. Los datos que aparezcan en una publicación se confirman por separado."}
      </p>
      <form ref={form} onSubmit={(e) => void save(e)}>
        <fieldset disabled={busy} className="onboarding-body">
          {step === 0 && (
            <>
              <Options
                label="Tu prioridad"
                options={goals}
                selected={[answers.goal.choice]}
                onSelect={(choice) => change("goal", { choice, detail: "" })}
              />
              {["other", "promote"].includes(answers.goal.choice) &&
                field(
                  "Cuéntanos tu prioridad",
                  answers.goal.detail,
                  (detail) => change("goal", { ...answers.goal, detail }),
                  answers.goal.choice === "other",
                )}
            </>
          )}
          {step === 1 && (
            <>
              <Options
                label="Formas de comprar"
                options={channels}
                selected={answers.channels.map((a) => a.choice)}
                onSelect={(v) => toggle("channels", v)}
                multi
              />
              {answers.channels
                .filter((a) => a.choice !== "later")
                .map((a) => (
                  <div key={a.choice}>
                    {field(
                      a.choice === "other"
                        ? "Describe la otra forma de comprar"
                        : `${channels[a.choice as keyof typeof channels]} · dirección, número o enlace (opcional)`,
                      a.detail,
                      (v) => details("channels", a.choice, v),
                      a.choice === "other",
                    )}
                  </div>
                ))}
            </>
          )}
          {step === 2 && (
            <>
              <Options
                label="La primera idea"
                options={features}
                selected={[answers.feature.choice]}
                onSelect={(choice) => change("feature", { choice, detail: "" })}
              />
              {answers.feature.choice &&
                answers.feature.choice !== "help" &&
                field(
                  "¿Qué quieres mostrar o explicar?",
                  answers.feature.detail,
                  (detail) => change("feature", { ...answers.feature, detail }),
                  ["other", "product", "news", "question"].includes(
                    answers.feature.choice,
                  ),
                )}
            </>
          )}
          {step === 3 && (
            <>
              <Options
                label="Material disponible"
                options={materials}
                selected={answers.materials}
                multi
                onSelect={(key) => {
                  const exclusive = ["none", "later"];
                  const next = answers.materials.includes(key)
                    ? answers.materials.filter((v) => v !== key)
                    : [
                        ...answers.materials.filter(
                          (v) =>
                            !exclusive.includes(v) && !exclusive.includes(key),
                        ),
                        key,
                      ];
                  setAnswers((a) => ({
                    ...a,
                    materials: next,
                    material_detail: next.includes("other")
                      ? a.material_detail
                      : "",
                  }));
                  setConfirmed(false);
                }}
              />
              {answers.materials.includes("other") &&
                field(
                  "Describe el otro material",
                  answers.material_detail,
                  (v) => change("material_detail", v),
                  true,
                )}
              {answers.materials.includes("none") && (
                <p>
                  Podemos empezar por definir qué fotografiar. La guía de
                  grabación de video aún está pendiente.
                </p>
              )}
            </>
          )}
          {step === 4 && (
            <>
              <dl className="onboarding-review">
                {[
                  ["Prioridad", describe(answers.goal, goals)],
                  [
                    "Cómo compran",
                    answers.channels
                      .map((a) => describe(a, channels))
                      .join("; "),
                  ],
                  ["Qué mostrar", describe(answers.feature, features)],
                  [
                    "Material",
                    answers.materials
                      .map((k) =>
                        k === "other"
                          ? answers.material_detail
                          : materials[k as keyof typeof materials],
                      )
                      .join("; "),
                  ],
                ].map(([label, text], i) => (
                  <div key={label}>
                    <dt>{label}</dt>
                    <dd>{text}</dd>
                    <button
                      type="button"
                      className="button secondary"
                      onClick={() => {
                        setStep(i);
                        setConfirmed(false);
                      }}
                    >
                      Cambiar {label.toLowerCase()}
                    </button>
                  </div>
                ))}
              </dl>
              <details className="onboarding-extra">
                <summary>
                  ¿Hay algo que debamos tener en cuenta? · opcional
                </summary>
                <Options
                  label="Condiciones del negocio"
                  options={conditions}
                  selected={answers.conditions.map((a) => a.choice)}
                  multi
                  onSelect={(v) => toggle("conditions", v)}
                />
                {answers.conditions
                  .filter(
                    (a) => !["none", "later", "advance"].includes(a.choice),
                  )
                  .map((a) => (
                    <div key={a.choice}>
                      {field(
                        a.choice === "other"
                          ? "Describe la otra condición"
                          : `${conditions[a.choice as keyof typeof conditions]} · detalles (opcional)`,
                        a.detail,
                        (v) => details("conditions", a.choice, v),
                        a.choice === "other",
                      )}
                    </div>
                  ))}
                {answers.conditions.some((a) => a.choice === "advance") && (
                  <>
                    <Options
                      label="¿Con cuánto tiempo deben pedir?"
                      options={leadTimes}
                      selected={[answers.lead_time?.choice || ""]}
                      onSelect={(choice) =>
                        change("lead_time", { choice, detail: "" })
                      }
                    />
                    {answers.lead_time &&
                      ["depends", "other"].includes(answers.lead_time.choice) &&
                      field(
                        "Detalles del plazo",
                        answers.lead_time.detail,
                        (detail) =>
                          change("lead_time", {
                            ...answers.lead_time!,
                            detail,
                          }),
                        answers.lead_time.choice === "other",
                      )}
                  </>
                )}
              </details>
              <label className="onboarding-detail">
                Idioma y región · opcional
                <input
                  maxLength={5}
                  pattern="[a-z]{2}(-[A-Z]{2})?"
                  placeholder="Por ejemplo, es-CO"
                  value={answers.locale || ""}
                  onChange={(e) => change("locale", e.target.value || null)}
                />
              </label>
              <label className="social-check">
                <input
                  type="checkbox"
                  checked={confirmed}
                  onChange={(e) => setConfirmed(e.target.checked)}
                />
                Revisé mis respuestas. Lo que dejé pendiente sigue sin
                confirmar.
              </label>
            </>
          )}
          {error && <p role="alert">{error}</p>}
          <div className="onboarding-actions">
            {step > 0 && (
              <button
                type="button"
                className="button secondary"
                onClick={() => {
                  setStep(step - 1);
                  setError("");
                }}
              >
                Atrás
              </button>
            )}
            {step < 4 ? (
              <button type="submit" className="button primary">
                Continuar
              </button>
            ) : (
              <button
                type="submit"
                className="button primary"
                disabled={!confirmed}
              >
                {busy ? "Guardando…" : "Guardar mis respuestas"}
              </button>
            )}
            <button
              type="button"
              className="button secondary"
              onClick={onClose}
            >
              Cerrar sin guardar
            </button>
          </div>
          <p className="onboarding-save-note">
            Tus respuestas se guardan al confirmar el último paso.
          </p>
        </fieldset>
      </form>
    </section>
  );
}
