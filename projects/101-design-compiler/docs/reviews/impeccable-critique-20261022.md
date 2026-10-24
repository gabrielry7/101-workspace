Method: dual-agent (A: /root/critique_design_a · B: /root/critique_evidence_b)

# Crítica formal de Impeccable — 2026-10-22

**Dictamen: el piloto mejora lectura, pero no demuestra todavía la calidad artística de páginas finales.** B ofrece el equilibrio más favorable según la revisión visual del agente; D no demuestra una ventaja adicional y C/D consumen más altura móvil. Esto es un juicio del revisor, no una preferencia humana ni una selección automática. Los evaluadores siguen desactivados por defecto.

## Especificidad y alcance

Target estable: `src/pages/quality/[variant].astro`, slug resuelto por el helper: `src-pages-quality-variant-astro`. Superficie: la familia `/quality/`, restaurante y hotel, A–D, con sus páginas interiores. Código evaluado: `2f68b9ef16aed0d2166729d47f2dac91edaaa034`; HEAD documental al comenzar: `a9827fb`. No se modificaron páginas, contratos, planes, estilos, medios, flags ni preferencias durante esta revisión.

A formó su juicio sin detector ni informes anteriores; terminó antes de que B entregara sus hallazgos al coordinador. B no recibió el informe de A. El comparador sí revela qué proveedor corresponde a cada letra: revisión independiente del detector, **sin cegamiento por proveedor**. Ambos agentes usaron pestañas nuevas en sus respectivos contextos CUA, sin compartirlas, y las cerraron.

La serif, el fondo cálido y las reglas finas construyen una familia coherente. Su carácter pertenece al laboratorio: restaurante y hotel siguen siendo intercambiables como páginas informativas. A–D mantienen la misma composición para aislar refinamientos. No son cuatro diseños artísticos distintos ni este experimento certifica las páginas B3 completas.

Los fixtures son sintéticos. Restaurante tiene un solo medio atmosférico autorizado, un ítem de menú y un hueco documental bloqueado; hotel no tiene fotografía elegible y ofrece dos objetos de habitación y una frase de comodidad. La muestra permite juzgar lectura y navegación, pero no valida riqueza final, audiovisual, diversidad de composición ni calidad con dos negocios reales. Esa evidencia sigue pendiente.

![Comparador real, restaurante A/B](../evidence/design-evaluation/critique-20261022/comparison-live.jpg)

## Heurísticas de usabilidad

Evaluación de la familia informativa: capturas A–D y recorridos en vivo, no una media de scores técnicos. El formulario de preferencias no fue enviado y queda fuera de esta nota.

| # | Heurística | Nota | Hallazgo principal |
|---|---|---:|---|
| 1 | Visibilidad del estado | 3/4 | Página activa y destinos claros; no hay operación asíncrona relevante. |
| 2 | Correspondencia con el mundo real | 2/4 | `amenities`, `rooms`, `fixture`, `Alcance` e IDs requieren interpretar el modelo. |
| 3 | Control y libertad | 3/4 | Enlaces de retorno y navegación funcionan; no se observan estados que atrapen al visitante. |
| 4 | Consistencia y estándares | 3/4 | Familia coherente; mezcla de idiomas y jerarquía home/interior desigual. |
| 5 | Prevención de errores | 3/4 | Ficción, foto atmosférica y funciones no operativas se distinguen. |
| 6 | Reconocimiento frente a recuerdo | 3/4 | Dos o tres destinos visibles; `rooms` termina bajo el H1 genérico `Oferta`. |
| 7 | Flexibilidad y eficiencia | n/a | Demo Persuade/Read sin tarea repetitiva que necesite aceleradores. |
| 8 | Estética y minimalismo | 2/4 | Hay orden, pero títulos y vacíos dominan sobre la información útil. |
| 9 | Recuperación de errores | n/a | El recorrido informativo no contiene entradas ni flujo operativo que produzca errores. |
| 10 | Ayuda y documentación | 3/4 | Límites y trazabilidad próximos; vocabulario orientado al constructor. |
| **Total** | | **22/32 — 68,75 %, Aceptable** | **Nota heurística de esta demo; no mide belleza ni completitud comercial.** |

La comprobación adicional de B descubre un defecto del salto por teclado que la revisión visual no detectó. Se incorpora como prioridad propia; no se disfraza como resultado del detector estático.

## Carga cognitiva y recorrido emocional

| Criterio | Resultado | Evidencia |
|---|---|---|
| Foco único | Pasa | Lectura y elección de página sin interrupciones. |
| Fragmentación | Pasa | Grupos de uno a tres elementos en los fixtures. |
| Agrupación | Pasa | Reglas y proximidad separan navegación, contenido y restricciones. |
| Jerarquía visual | Falla | El título experimental domina, especialmente en hotel. |
| Una cosa a la vez | Pasa | No hay decisiones simultáneas obligatorias. |
| Opciones mínimas | Pasa en fixtures | Restaurante: dos destinos; hotel: tres. |
| Memoria de trabajo | Pasa | Navegación visible con estado actual. |
| Revelación progresiva | Pasa | Trazabilidad extensa en desplegable. |

**Un fallo de ocho: carga baja, favorecida por la escasez de contenido.** En el comparador, `Qué influyó` muestra seis casillas simultáneas; preferencia y nota revelan seis y diez opciones dentro de controles nativos. Las cuatro variantes por grupo son comparables, aunque comparar detalles pequeños exige ampliar capturas.

La entrada es tranquila y ordenada. En restaurante la fotografía produce el único pico sensorial; la oferta posterior pierde interés por su escaso desarrollo. El final tranquiliza sobre restricciones, pero no deja una idea memorable del negocio. Hotel carece de ese pico: es una revisión honesta de contratos, insuficiente para imaginar una estancia. La ausencia de permisos no se corrige sustituyéndola por una imagen engañosa.

## Qué funciona

- Procedencia, crédito Steve Ausmus/USDA ARS, etiqueta atmosférica y ausencia de respaldo permanecen visibles. La foto no se presenta como plato ni como evidencia del establecimiento.
- Navegación convencional, estado activo y desplegable de trazabilidad funcionan; B comprobó navegación y apertura por Enter.
- B/D hacen más cómodos créditos y restricciones sin introducir ornamentación gratuita. La familia conserva coherencia tipográfica y cromática.

## Prioridades

1. **P1 — Etiquetas internas en la interfaz.** Hotel muestra `amenities` y `rooms`; Habitaciones desemboca en `Oferta`. `Alcance: h7-synthetic-hotel` y el ID de sucursal son metadatos visibles. Dificultan entender destinos. Usar etiquetas de presentación `Comodidades`/`Habitaciones`, alinear título y enlace, y situar IDs en trazabilidad conservando sus bindings, hechos y restricciones. Fuentes: `tooling/design-evaluation/compiler-extension.mjs:17`, `src/components/composition/FactCollection.astro:8`, `OfferingCollection.astro:9-10`. Comando asociado: `$impeccable clarify`.

2. **P2 — El salto por teclado no evita la navegación repetida.** B verificó en hotel A: Tab → Enter en `Saltar al contenido` → Tab termina en `Identidad`, primer enlace del menú. `#contenido` engloba también encabezado y navegación. Elegir un destino/foco en el contenido de la página y verificar el recorrido con teclado. Fuentes: `src/layouts/Foundation.astro:14-15`, `src/components/composition/DesignComposition.astro:28-30`. Comando asociado: `$impeccable audit` y corrección acotada con `$impeccable harden`.

3. **P2 — C/D gastan altura móvil sin resolver un defecto táctil previo.** Las capturas muestran una segunda fila de navegación frente a A/B. El padding extra viene de `src/design/evaluators/refinement.css:3-4`; el baseline ya tenía cero targets menores de 44px. Activar el ajuste solo con necesidad medida y comprobar filas/altura, conservando targets adecuados y permitiendo salto cuando el texto lo exija. No se propone una prohibición general de envolver menús. Comando asociado: `$impeccable adapt`.

4. **P2 — Proporción tipográfica de laboratorio.** El título largo del hotel ocupa tres líneas monumentales y A reduce demasiado el peso de créditos frente a él. Ajustar la proporción del título experimental y espacios, conservando serif/paleta/copy y lectura auxiliar de B/D. No agrandar todo ni alterar hechos. Fuentes: `src/composition/styles.css:14-20`, `src/design/evaluators/refinement.css:5-13`, `src/components/composition/Identity.astro:7-8`. Comandos asociados: `$impeccable typeset`, `$impeccable layout` y `$impeccable polish` como comprobación final de una futura corrección autorizada.

**Cero P0, un P1 y tres P2 en este recorrido.** Son propuestas pendientes: esta crítica no aplica parches ni autoriza un hito posterior.

## Detector y contraste con navegador

Ejecución real de B: `.agents/skills/impeccable/scripts/impeccable.cmd detect --json dist/quality`, versión 4.7.0, motor instalado 0.1.16. **21 HTML, exit 2, 58 warnings, stderr vacío.** No existe lista `ignore.md`. El coordinador reutiliza esa salida; no repite el detector.

| Regla | Cuenta | Lectura contextual |
|---|---:|---|
| `cream-palette` | 20 | Fondo compartido detectado; señal de estilo, no fallo demostrado de accesibilidad o calidad. |
| `wide-tracking` | 20 | Dos rótulos por página A/C. Propiedad real; no equivale a dos párrafos ilegibles. |
| `cramped-padding` | 12 | Hipótesis contradicha por render representativo: `.semantic` computa borde 0/none. No añadir padding para silenciarla. |
| `hero-eyebrow-chip` | 5 | Patrón de A observado; juicio heurístico. La identificación ficticia debe conservarse. |
| `flat-type-hierarchy` | 1 | Falso positivo confirmado: comparador h1 56px, h2 24px, h3 18,72px, párrafo 16px. |

Todas las ubicaciones del detector devuelven **line 0**, sin línea fuente fiable. [Salida completa](../evidence/design-evaluation/critique-20261022/assessment-b-detector.stdout.json) y [matriz por archivo](../evidence/design-evaluation/critique-20261022/assessment-b-cli-metadata.json) conservan las 21 rutas, reglas y snippets. No se resta un número arbitrario de supuestos falsos positivos para fabricar una nota limpia: el render se contrastó sobre ejemplos representativos, no sobre cada instancia de padding.

A/B coinciden en la dificultad de rótulos internos. El detector reconoce cambios de tracking y jerarquía, pero no demuestra carácter artístico ni descubre el problema del salto. Tampoco convierte el fondo crema en un error que justifique uniformar todas las paletas.

## Personas y detalles menores

- **Jordan, primera visita:** `rooms` → `Oferta` y los IDs obligan a descifrar el modelo antes de comprender el contenido.
- **Casey, móvil distraído:** C/D requieren más desplazamiento para llegar a lo mismo; B/D facilitan leer los avisos.
- **Sam, teclado:** el skip tiene foco visible pero vuelve a recorrer la navegación; la apertura de trazabilidad por Enter sí funciona.

Las pestañas repiten `candidate-01 · laboratorio QUALITY`, lo que dificulta distinguir caso/página. La jerarquía invertida de home en B/D no se aplica uniformemente a interiores. B no encontró overflow horizontal en sus cinco vistas desktop (1280×720, documento 1265px); A no lo observó en sus capturas. Ninguno probó interacción móvil nueva, zoom o lector de pantalla físico; no se declara conformidad WCAG integral.

## Cobertura, evidencia y límites

A inspeccionó **28 capturas**: 16 homes A–D y 12 secundarias A/D, desktop/mobile; recorrió comparación, restaurante D/oferta, hotel D/habitaciones/comodidades. B inspeccionó las 16 homes y visitó comparación, restaurante B/oferta y hotel A/comodidades, con teclado y estilos computados. Ambos leyeron viewport live 1280×720 sin modificarlo; móvil procede de las capturas comprometidas 390×844 y desktop de 1280×900. Los dos contextos CUA asignaron localmente el ID 1 a su pestaña nueva; son identificadores de contextos distintos, no prueba de una pestaña compartida. El coordinador dejó el comparador como entregable en su tab 16.

[Evidencia B](../evidence/design-evaluation/critique-20261022/assessment-b-browser-evidence.json), [hashes HTML](../evidence/design-evaluation/critique-20261022/assessment-b-scanned-file-hashes.json), [hashes de capturas](../evidence/design-evaluation/critique-20261022/assessment-b-capture-hashes.json) y [recibo de esta revisión](../evidence/design-evaluation/critique-20261022/review-receipt.json) documentan cobertura y límites. Los outputs B se copiaron sin modificarlos; sus referencias `.impeccable/critique/` identifican el scratch original. Su comprobación Git falló por ownership; el coordinador confirmó posteriormente que ese scratch está ignorado con `git -c safe.directory=... check-ignore`.

La API browser evaluate es read-only: **no hubo overlay ni intento de inyección**, ni live-server exclusivo. El fallback fue CLI + DOM + teclado + capturas reales. Los logs Impeccable vacíos no se presentan como aprobación. El preview preexistente permanece disponible. No hubo nuevas llamadas Raven ni adquisición de recursos. La nueva CLI formal está fuera de las 183 operaciones de la corrida anterior, cuyo recibo no se modifica. Tokens/costo de agentes no medidos.

Esta revisión repitió **`quality-verify.ts`: EXACT_REPLAY_PASS**, 40 vistas finales + 40 observaciones iniciales, **2.815 archivos protegidos**, 162 archivos sellados, sin preferencia humana. No repitió suites/builds porque no cambió implementación: se conservan los recibos anteriores (423/424 tests, único fallo histórico `LOCK_BROWSER_MISMATCH`; focales 10/10; check/validate/build PASS) y la reproducción independiente existente. No se presenta esa suite como ejecutada nuevamente hoy por la crítica.

Sigue pendiente el ledger acumulado preventivo documentado en la revisión técnica; esta crítica no lo corrige. También siguen pendientes prueba con negocios reales, rendimiento LCP/INP/CLS y red fría, medios suficientes autorizados, variedad artística y decisión humana. La foto original sigue pesando 2.351.102 bytes: su carga y posibles derivados requieren evaluación y permisos específicos; no se alteró para mejorar una métrica.

## Preguntas para la decisión humana

La próxima decisión debe distinguir la corrección de estos cuatro problemas de usabilidad de la validación artística con una muestra completa. ¿Debe ser la primera prioridad reparar navegación/claridad, o preparar la prueba visual con el restaurante B3 más completo? Si se repara el piloto actual, ¿se toma la legibilidad y navegación compacta de B como punto de partida o se conserva A para otra comparación? Estas preguntas no registran una preferencia: quedan a la espera de respuesta humana.
