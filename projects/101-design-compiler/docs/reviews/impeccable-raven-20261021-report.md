# Impeccable + Raven — piloto integrado, activación pendiente

Evaluación del **2026-10-21, America/Bogota**; recibos en UTC del 2026-10-22. Base Git: `04cadc9`. La integración participa en generación y evaluación reales del laboratorio. **No queda aprobada para producción ni activada por defecto.** Faltan preferencia humana y contraste con negocios reales. La [crítica formal dual-agent del 2026-10-22](impeccable-critique-20261022.md), autorizada posteriormente, ya está realizada: confirma mejoras de lectura y límites de la muestra, con cuatro problemas de usabilidad pendientes. No se inicia otro hito.

## Arquitectura comprobada

**Corrección de alcance del 2026-10-22:** el usuario indicó que la mejora debía aplicarse a los moldes que ya se estaban perfeccionando. La [pasada sobre los cuatro B3 completos](b3-tools-on-molds-20261022-report.md) evalúa el renderer ExperienceComposition, 44 rutas, sus medios y contenido actuales, con correcciones compartidas y nueva evidencia. El ensayo H5/H7 que describe este informe conserva su alcance técnico original; no sustituye esa validación sobre B3.

Se revisaron pipeline V0.2, contratos, findings H0 e informes H3/H5/H7, código y Git. El árbol inicial estaba limpio. `SiteSpec`, Truth productivo, `WebsiteCompiler`, `@101/site-runtime` y upstream siguen ausentes. No se simula su integración. Astro local es el laboratorio compartido.

| Etapa | Implementación real utilizada |
|---|---|
| Verdad / entrada | `BusinessInputV1`, validaciones y fixtures marcados `SYNTHETIC_FIXTURE` |
| Requisitos / plan | `planBusiness`, `SiteRequirementsV1`, `SitePlanV1` |
| Contenido | `src/composition/content.ts`, proyección y bindings factuales |
| Dirección / DNA disponible | `ArtDirectionV1` / `V1_1`, `TokensV1`, búsqueda guardada y `DesignPlanV1`; no existe un contrato local llamado `DesignDNA` |
| Composición / componentes | Registry existente: Flow/Rail, Sequence/Split, Identity, OfferingCollection, FactCollection, Schedule, MediaFigure y AuditPanel |
| Compilación | Astro y **el mismo `DesignComposition.astro`**, conservado intacto |
| Evaluación / corrección | Observador de composición existente, `auditRender`, esquema común nuevo, propuesta acotada y juicio con rollback |

La ampliación usa una configuración **optativa que importa la configuración original**, `tooling/design-evaluation/astro.config.mjs`. Su hook oficial `astro:build:generated` aplica los bindings de presentación de `/quality/`. No genera módulos, hechos, componentes ni páginas desde HTML escrito por un proveedor. Valida contexto, montaje, esquema de refinamiento y navegación; conserva los spans factuales y rechaza una segunda aplicación. Solo inserta CSS fijo, clases acotadas y metadatos/enlaces del montaje de laboratorio. Los 20 HTML resultantes son **idénticos por hash a los capturados antes de trasladar la extensión al hook**.

La implementación inicial modificaba el renderer y luego la configuración raíz; eso rompió dos tests adicionales y huellas congeladas H8. Se corrigió preservando ambos archivos y usando la extensión optativa. **Los 2.815 archivos de la preservación B3 permanecen iguales**, sin excepciones; tampoco cambian dependencias/configuración raíz ni contratos V1 anteriores. Las pantallas B3/DepthExperience y sus preferencias anteriores se conservan: este experimento usa la ruta común H5/H7, no certifica una mejora de las páginas B3 completas.

## Herramientas instaladas y llamadas reales

| Herramienta | Versión / interfaz / evidencia |
|---|---|
| Impeccable | npm **4.7.0**, motor **0.1.16** Windows. Instalación oficial de proyecto para Codex con `--no-hooks`; `impeccable context` ejecutado y guías instaladas leídas. Detector real `detect --json` sobre HTML compilado. Lockfile e integridad del skill en `tooling/design-evaluation/`. |
| Raven | npm **2.6.0**, MCP stdio local; cliente SDK **1.32.1**. Descubrimiento real de **111 herramientas** en `preflight/raven.json`. Entorno del servidor sin credenciales de proveedores, sin creative runner, update check ni usage log. Estado separado por proyecto. |
| Navegadores | IAB existente para DOM y capturas completas; no se obtiene una versión del motor IAB. `audit_url` usa su Chromium oficial de Playwright **1.64.1**, Chrome for Testing **156.0.8078.4**. No se confunden sus recibos con las capturas IAB. |

La configuración Codex se genera en `.codex/config.toml`, ignorada por contener rutas de este computador. No se modifica configuración global. El host puede necesitar una sesión nueva/reinicio para descubrirla; las llamadas de esta entrega **sí pasaron por el servidor MCP real mediante su cliente stdio**, no por funciones imitadas. Los binarios de navegador usan la caché oficial de Playwright; configuración/estado de Raven quedan en el proyecto.

Se llamaron `get_principles`, `get_pattern`, `audit_layout`, `audit_typography`, `audit_contrast`, `audit_tap_targets`, `score_page`, `evaluate_design` y `audit_url`. Este último obtuvo **4/4 capturas solicitadas** en dos URLs D, escritorio/móvil, tema claro. La primera llamada falló por Chromium ausente: se conserva `raven-url-initial-unavailable.json`; nunca se interpreta cobertura cero como aprobación. `list_taste_profiles` devolvió `[]`: **no se llama `audit_taste` ni se inventa un perfil**.

Impeccable `craft` es un alias obsoleto de trabajo visual, no una API CLI de generación. `audit`, `polish` y `distill` son playbooks del agente: se aplicaron como guía de auditoría/refinamiento, sin afirmar ejecución automática de comandos CLI inexistentes. `context` permitió refinamiento del sistema visual existente sin inventar PRODUCT.md. La crítica formal `critique` exige autorización de dos subagentes en su sección Codex; quedó pendiente en la corrida original y **se completó el 2026-10-22 tras autorización expresa**, con A visual y B detector/browser aislados. No se presenta la inspección inicial como ese protocolo completo.

El [SKILL.md instalado](../../.agents/skills/impeccable/SKILL.md) remite a [critique.md](../../.agents/skills/impeccable/reference/critique.md), que indica: “ask exactly once” y “Then stop until the user answers.” Se respetó la pausa de esa crítica; la respuesta posterior fue “Sí, usar dos agentes independientes”. Su [informe separado](impeccable-critique-20261022.md) conserva método, cobertura, 58 avisos contextuales y el defecto de salto por teclado descubierto. No aplica correcciones ni registra un voto humano.

Fuentes oficiales consultadas: [Impeccable](https://github.com/pbakaus/impeccable), [Raven MCP](https://github.com/rhinocap/raven-mcp), [MCP en Codex](https://learn.chatgpt.com/docs/extend/mcp?surface=cli), [hooks de Astro](https://docs.astro.build/en/reference/integrations-reference/#astrobuildgenerated). Los dos repositorios declaran Apache-2.0; Raven incluye NOTICE con atribuciones. Los términos de medios no se deducen de estas licencias de software.

## Integración y límites del adaptador

Antes de renderizar, Raven devuelve principios/patrón y la sesión aplica la guía instalada de Impeccable. `guidedRefinement` exige evidencia y traduce únicamente decisiones soportadas por el contrato: medida de lectura, tamaño táctil, ritmo tipográfico, tracking y posición visual de etiqueta. No escoge una paleta por sector. Los planes/direcciones existentes conservan su identidad, topología, semilla guardada y tokens originales.

`EvaluatorFlagsV1` tiene ambos valores en false por defecto. A no recibe refinamiento; B usa Impeccable; C Raven; D ambos. El build original se probó **con los paquetes evaluadores físicamente fuera de su ruta de resolución**, restaurándolos en finally: PASS, **168 páginas**. El build optativo tiene 189. No hay dependencias del evaluador ni scripts en los 20 sitios de candidatos. El comparador tiene únicamente su interacción local de preferencias.

Los seis contratos nuevos son flags, hallazgo, refinamiento, presupuesto, preferencia y experimento. Hallazgos separan `MEASURED`, `HEURISTIC` y `AESTHETIC`, con severidad, ruta, viewport, selector, evidencia, recomendación, confianza y procedencia. La deduplicación conserva fuentes independientes. Una crítica estética o de baja confianza no se convierte en parche automático. No hay campos para modificar hechos, módulos, medios, licencias, URLs, CSS libre o scripts.

La reparación propone cambios del contrato, vuelve a compilar/renderizar y compara la misma cobertura. Revierte ante nuevos fallos duros o falta de mejora. Máximo **2 iteraciones**; política de 200 operaciones por corrida artística y gasto nuevo permitido cero. Esta corrida cumple el total verificado. **La revisión independiente detectó que los controles previos no son un ledger acumulado completo entre fases/refresh y que judge puede conservar una mejora aunque el presupuesto ya esté excedido.** Esto queda pendiente antes de extender/promover el loop: registrar consumo acumulado antes de cada operación y probar sobrepresupuesto con rollback. No se afirma un límite preventivo global ya resuelto. El reloj de 600 segundos instrumentado cubre el procesamiento de evaluación; **no es un límite de latencia de todo el pipeline/browser/trabajo humano**. La coordinación del navegador sigue siendo asistida por el agente; no se entrega un servicio autónomo comercial.

## Experimento ejecutado

Dos categorías: restaurante del piloto H3/H5 y hotel H7. **Sus datos están validados como fixtures sintéticos, no verificados como negocios reales.** El requisito de evaluación con dos negocios reales permanece pendiente por falta de snapshots aprobados; no se sustituyó por una afirmación ficticia de verificación.

| Condición | Influencia previa | Corrección posterior |
|---|---|---|
| A | Generador/renderer existente, sin evaluadores | Baseline congelado |
| B | Tracking natural, título balanceado y etiqueta posterior | Una iteración: textos de lectura/créditos/avisos a la variante compartida |
| C | Medida de lectura, ritmo y tamaño táctil desde Raven | Sin parche seguro adicional; detenida |
| D | Ambas guías | Sin parche seguro adicional; detenida |

Mismos SitePlan, hechos, contenido y medio disponible dentro de cada caso; misma salida guardada del sampler. **No son cuatro layouts nuevos** ni cuatro contenidos diferentes. Son condiciones de evaluación del mismo plan. Son 20 rutas, **40 vistas finales completas** en 1280×900 y 390×844, más 40 observaciones iniciales. Se conservan capturas iniciales como material diagnóstico; las finales tienen dos capturas consecutivas idénticas y hashes. Una captura con pintura atrasada se archivó en `capture-anomalies/` y se reemplazó; las métricas DOM solas no detectaban ese defecto. Se inspeccionaron las 16 homes finales de A–D en ambos tamaños.

El comparador `/quality/` muestra esas capturas lado a lado y enlaza a las páginas navegables. El formulario admite preferencia A/B/C/D/empate/ninguna, nota 1–10, dimensiones y explicación. Guarda solo al enviar, localmente, y exporta JSON. **No se creó ningún voto humano**, ni se dice haber aprendido gusto. El campo source de un JSON es una declaración de procedencia, no autenticación de una persona.

## Resultados verificables

| Medición común en homes | A | B final | C | D |
|---|---:|---:|---:|---:|
| Restaurante: párrafos visibles menores de 16px | 6 | 0 | 0 | 0 |
| Hotel: párrafos visibles menores de 16px | 3 | 0 | 0 | 0 |
| Desbordamiento observado, ambos tamaños | 0 | 0 | 0 | 0 |
| Objetivos interactivos menores de 44px | 0 | 0 | 0 | 0 |

La cuenta de párrafos incluye avisos, etiquetas y créditos; no se presenta 16px como mínimo obligatorio universal de WCAG. Los bindings pasan **40/40**, sin omitir hechos, scopes, diagnósticos ni restricciones. B pasó de **18 ubicaciones reparables a 0 por caso**, sumando sus rutas/tamaños. Se conservó la reparación. La siguiente propuesta terminó en `STOP_NO_SAFE_PATCH`; **no hubo un segundo render de reparación**.

Mejoró la lectura de crédito/avisos y desapareció tracking excesivo en B/D. El beneficio artístico permanece sin demostrar: B y D convergen en parte del resultado. Raven añadió padding que hace ocupar dos filas a la navegación móvil sin resolver un fallo táctil previo. Eso es una desventaja observada, no un éxito. C/D quedan como condiciones experimentales, sin promoción ni ganador automático.

Las recomendaciones de escala modular, pesos 650/750, ritmo uniforme, paleta crema y el supuesto orphan del header se revisaron como heurísticas. No se estrechó todo el header ni se redujo el interlineado legible para subir un score. `score_page` examina HTML/CSS; contar colores de variantes CSS inactivas puede distorsionar su resultado. `evaluate_design` por descripción devuelve conocimiento/checklist, no demuestra una inspección visual por LLM. Los scores brutos se conservan como diagnósticos, no como belleza objetiva.

HTML de candidatos: **13.012–15.781 bytes**, scripts observados cero. La foto original pesa **2.351.102 bytes**: no se optimizó contra su contrato. No se midieron LCP/INP/CLS, tráfico frío ni p75; Performance no está expuesto en el scope DOM del IAB y no se rellenaron con ceros. Los 40 PNG finales suman 2.489.002 bytes; son evidencia, no peso de carga de una página comercial. Su ventana de adquisición fue 412,311s e incluye pausas de trabajo, no una latencia de producto.

Se probó Tab→skip, Enter→fragmento, disclosure por teclado y navegación real hacia la oferta de sucursal. No se confirmó transferencia de foco al main ni se declara conformidad WCAG completa, Safari, dispositivos físicos o gestos táctiles. El formulario se prueba sin fabricar preferencias.

El comparador se inspeccionó también en 390px: documento de 375px, un main/h1 y controles dentro del viewport. Exportación vacía y envío inválido terminan sin evaluaciones para exportar. Las capturas de paneles móviles cerrados permanecen lazy; no se cuentan como descargas fallidas.

## Medios y derechos

Solo se usa el original H3 `public/media/h3-pilot/usda-ars-d255-19.jpg`, SHA-256 **ffdb883d56a41ba9a03a51fb7d1bdf8f0b9e30d3946eda180b750620a17c3715**. Mismos cliente/proyecto, página semántica, módulo, rol atmosférico, crédito Steve Ausmus/USDA ARS, etiqueta genérica y aviso de no respaldo. Las rutas nuevas son montajes locales de ese contexto; no cambian grant ni finalidad. Los huecos documentales siguen bloqueados; el hotel no tiene fotografía elegible. Sin adquisición, cuentas, pagos, conectores ni catálogos adicionales. Se conserva la evaluación legal H3 del 2026-10-08, sin afirmar una nueva revisión jurídica por instalar herramientas.

## Costos, intentos y validación

Corrida controlada: 5 llamadas MCP previas; evaluación inicial 100 MCP + 10 detector; evaluación posterior 54 MCP + 10 detector; refresco de pintura 2 MCP nuevos y 98 resultados reutilizados con inputs iguales. Dos llamadas `audit_url` auxiliares: **183 operaciones** en total. Hubo intentos de ingeniería fuera de esa corrida: primer auditado con comparaciones de claves JSON erróneas, bootstrap de Chromium, instalación temporal en raíz y posteriores correcciones de compatibilidad congelada. Se registran como fallos/depuración, no se ocultan dentro de una cifra de mejora ni se afirma un total de sesión medido.

La duración de procesamiento registrada es 1,966s inicial y 1,922s posterior acumulada; no incluye browser, instalación ni elaboración. API de modelos invocada por las recetas: **0**; proveedores pagos: **0**. Tokens/costo de esta sesión Codex y costo total: **null/no medidos**, no cero inventado. Las guías tienen hashes canónicos de texto JSON en la traza; `seal.json` identifica explícitamente los hashes de bytes y normalización LF de fuentes.

La instalación temporal en raíz contaminó dos intentos de baseline con huellas de dependencias/configuración; se restauraron package/config y dependencias originales. Se conservaron los logs fallidos. La extensión final no modifica ningún archivo histórico protegido. La captura atrasada y el fallo `REPLAY_TOOL_INPUT_DRIFT` motivaron refrescar solo dos entradas MCP; el replay se niega a reutilizar inputs distintos.

`final-checks/journal.json`: **423/424 tests PASS**, único fallo histórico H8 `LOCK_BROWSER_MISMATCH`, igual que el baseline anterior a la integración. Los 10 tests nuevos pasan. Check: **298 archivos, 0 errores/warnings/hints**. Exportación de contratos, validate, build optativo, taxonomy, media replay/verify, composition replay/verify, design replay/verify, audit verify, cohort replay/verify y auditoría npm de herramientas PASS. `lock:verify` falla por el mismo navegador congelado; no se reseñaron locks ni se convirtió a PASS. El intento anterior `checks/` tenía dos regresiones nuevas: **ya corregidas**, no corresponde al resultado final.

El sellado/replay añade validación de hashes, cobertura exacta, raster no vacío, estabilidad de pintura final, HTML actual, cero scripts, gates de verdad/medios y **2.815 archivos preservados**. La prueba con paquetes ausentes está en `baseline-without-tools.json/.txt`. Los proyectos B2/B3 existentes requieren su paquete privado autorizado local para un build completo en otro computador; no se incorporan dependencias ni medios ignorados al commit.

## Reproducción y revisión

Desde la raíz, usando Node 24 del proyecto en PATH:

```powershell
npm ci
npm --prefix tooling/design-evaluation ci --ignore-scripts --registry=https://registry.npmjs.org
node tooling/design-evaluation/install.mjs
node tooling/design-evaluation/probe.mjs
npm run build -- --config tooling/design-evaluation/astro.config.mjs
node --experimental-strip-types scripts/quality-verify.ts
npm run preview -- --host 127.0.0.1 --port 4331
```

`install.mjs` usa el instalador oficial y rechaza drift del skill contra `skill-integrity.json`; depende de disponibilidad del distribuidor oficial. No actualiza el pin silenciosamente. Para una corrida nueva: `quality-prepare.ts`, build optativo, `quality-observer.ts`, capturas IAB de la matriz, `quality-audit.ts 0`, `quality-repair.ts 0`, nuevo build/capturas, `quality-audit.ts 1`, `quality-judge.ts 1` y propuesta de parada. `--replay` prohíbe llamadas nuevas; `--refresh` conserva resultados iguales y reevalúa entradas distintas. Estos comandos escriben una nueva corrida: no se ejecutan al verificar los recibos congelados. Se usa **build + preview**; el hook no aplica refinamientos en `astro dev`.

Código: `src/design/evaluators/`, `scripts/quality-*.ts`, `scripts/load-quality-lab.ts`, `src/components/quality/`, `src/pages/quality/`, `tooling/design-evaluation/`. Contratos: `contracts/design/evaluation-v1/`. Plan del experimento: `data/derived/design-evaluation-v1/experiment.json`. Evidencia: `docs/evidence/design-evaluation/`. Inventario completo en `impeccable-raven-files.txt`.

No se activa por defecto hasta tu comparación. Quedan pendientes dos negocios reales con evidencia/aprobación, validación visual de mayor riqueza, presupuesto acumulado preventivo y las correcciones de la [crítica formal ya completada](impeccable-critique-20261022.md). La [revisión independiente y su prompt](impeccable-raven-independent-review-20261022.md) consideran el checkpoint apto para revisión humana como piloto opt-in, con dos P2; no sustituyen tu preferencia ni autorizan otro hito. La crítica posterior tampoco valida diversidad artística ni calidad de páginas finales con estos fixtures mínimos.
