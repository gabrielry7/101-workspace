# B3 — Impeccable y Raven sobre los moldes existentes

Fecha: **2026-10-22, America/Bogota**. Base limpia `808d4e39b0c67c2e218da6e3b4ab25816279dae0`. Corrección de alcance solicitada por el usuario: «Perp esto se deberia hacer con los moldes de paginas que ya se estaban haciendo y perfeccionando esos.» Se continúa B3; no B4 ni hito posterior.

**Se evaluaron y refinaron los cuatro B3 completos que ya existían.** El ensayo `/quality/` anterior permanece como evidencia técnica sobre H5/H7; no certifica una mejora de B3 ni reemplaza sus moldes. Esta pasada aplica las herramientas a `ExperienceComposition.astro`, el renderer real de los moldes actuales, sus 44 rutas, contenido editorial y medios autorizados. No genera cuatro nuevas páginas mínimas ni aplica el CSS genérico del ensayo anterior a estos diseños.

## Alcance preservado

01, **La mesa abierta**, y 02, **Mucho apetito**, mantienen los operadores, paletas y tipografías de las direcciones apreciadas por el usuario. 03, **La mesa, en escena**, y 04, **Índice de sobremesa**, conservan sus propuestas actuales, aún pendientes de valoración. El feedback histórico, el rechazo de las 03/04 anteriores y la falta de aprobación de sus sustitutas siguen intactos. No hay voto nuevo, nota humana ni aprendizaje declarado.

Se conserva el mismo SitePlan, siete módulos y 42 referencias factuales por perfil, cuatro ofertas, contenido editorial/comunitario y once destinos separados por molde. Reservas, pedidos, opiniones y redes siguen siendo demostraciones explícitas. No hay backend, compras, envíos ni integración upstream. El runtime comercial 101 continúa ausente: se usa el mismo laboratorio Astro.

Contexto del sitio: `2e575a79cbdc8d708cc8695bd529717fce0a53054df35ab2a64fe2d2726ba49b`. Revisión de medios: `5f114b66dab6e87092e87e5b942135e2a17922330f845f0393d2afcaefed567a`.

## Evidencia y correcciones compartidas

| Problema observado en B3 | Corrección | Resultado comprobado |
|---|---|---|
| Buscar pasta en 01 dejaba una tarjeta de 601,94px en un grid de 1251,88px, con 80px de hueco superior. 03 también mantenía el resultado estrecho. | Estado compartido de lectura para carta filtrada: una fila de imagen/texto en escritorio y una columna en móvil. | Resultado ocupa el ancho del grid y pierde el hueco. Al limpiar filtros vuelve exactamente la composición editorial original. |
| `Saltar al contenido` enviaba al main que también contiene encabezado y menú; Tab volvía a la marca. | Destino enfocable dentro del contenido, después del encabezado. Mejora progresiva del enlace existente mediante el cliente B3. | Con JavaScript cargado, Tab/Enter/Tab termina dentro del contenido y evita el encabezado, en los cuatro moldes y ambos tamaños. La mejora estática sin JS sigue pendiente. |
| Raven midió 20 incidencias de enlaces Carta/Visita de menos de 44px de ancho en portadas. | `min-inline-size:44px` solo en las familias quick-nav/footer afectadas. | Las mismas ocho portadas pasan de 20 a cero incidencias. No se añade padding a toda la navegación. |
| El contador decía `1 platos`; el resultado vacío carecía de orientación. | Singular/plural y ayuda para probar otra búsqueda o categoría, dentro del status existente. | Un resultado, cero resultados y restauración comprobados. No se añaden productos ni hechos. |

Código: `src/design/experience-refinement.css`, `src/design/experience-refinement-client.ts` y su inclusión en `src/components/composition/ExperienceComposition.astro`. Las reglas no seleccionan clientes ni candidatos. El renderer, los módulos y los clientes existentes continúan siendo compartidos; no se añade una biblioteca visual o generador.

![Carta B3 refinada, búsqueda de pasta](../evidence/design-evaluation/b3-20261022/after/menu-refinement-visible.jpg)

El HTML de las **44 páginas conserva la misma huella semántica** antes/después: se excluyen únicamente style/script y los dos atributos nuevos del destino de foco. Por tanto se mantienen contenido, referencias, enlaces, avisos, IDs, medios y trazabilidad; no se atribuye igualdad byte a byte al HTML completo. Su CSS y bundle sí cambian.

## Herramientas realmente utilizadas

Impeccable **4.7.0 / motor 0.1.16**: guía instalada de `polish` y craft floor; detector real sobre `dist/b3` antes y después. Son refinamientos del mundo visual existente. Las guías no son una API CLI de generación. No se repite aquí el protocolo formal `critique` ni se presenta una nueva nota heurística dual-agent.

Raven **2.6.0**, mediante el adaptador MCP SDK stdio ya instalado: `get_principles`, `get_pattern`, `audit_layout`, `audit_typography`, `audit_contrast` y `audit_tap_targets`. Los principios de teclado/jerarquía y la guía de polish fundamentan las correcciones supervisadas; los targets se basan en rectángulos reales del navegador. No se aplican automáticamente juicios sobre serif cursiva, fuentes conocidas, escalas expresivas o etiquetas: el brief y la identidad apreciada prevalecen sobre avisos de patrones. Se conservan los hallazgos brutos, sin convertirlos en belleza ni borrar advertencias para conseguir un cero.

[Decisiones y causas](../evidence/design-evaluation/b3-20261022/decisions.json), [antes](../evidence/design-evaluation/b3-20261022/before/audit.json), [después](../evidence/design-evaluation/b3-20261022/after/audit.json). Son **68 operaciones reales**: 35 antes y 33 después, incluidas dos ejecuciones CLI. El ledger nuevo reserva cada operación antes de llamarla, tiene máximo 100 y registra errores; no se amplía el loop automático anterior ni se afirma que su P2 presupuestario esté corregido globalmente. Una sola iteración de refinamiento, no una comparación artística A/B/C/D nueva.

No hay nuevas llamadas API a modelos ni gasto en proveedores desde esta receta. Tokens/costo de la sesión y tiempo humano no medidos. No hay nuevos `audit_url`/taste ni adquisición de media; no se atribuyen las capturas de la corrida anterior a esta pasada.

## Pruebas y reproducción

Antes de editar: [receta baseline](../evidence/corrections/b3/tools-on-molds-baseline-20261022/journal.json). Después: [receta completa](../evidence/corrections/b3/tools-on-molds-post-20261022/journal.json). **423/424 tests**, único fallo H8 histórico `LOCK_BROWSER_MISMATCH`, tanto antes como después; no se modificó el lock para ocultarlo. Check de 301 archivos sin diagnósticos, exportación, validación y build normal de 168 páginas PASS. B1/B2/B3, taxonomía, planner, medios, composición, diseño, auditoría, cohorte e inventario H9 PASS. **2.815 archivos protegidos sin cambios**.

Comprobación final: **check PASS, build optativo de 189 páginas PASS, sellado y replay exacto B3 PASS, replay original de `/quality/` PASS y preservación PASS**, en el [journal final](../evidence/corrections/b3/tools-on-molds-final-20261022/journal.json). Las herramientas se mantienen en el entorno de evaluación; sus paquetes no se importan al cliente. El sitio funciona con el build normal sin ellas. El script `b3-evaluate.ts` reutiliza adaptadores, contratos de hallazgos y gates existentes; no se invoca en cada build normal.

CUA, browser 2, pestaña 17 nueva, viewport temporal restaurado al acabar. **16 vistas baseline y 88 vistas finales** (4 moldes × 11 páginas × escritorio1440×1000 / móvil390×844), todas con los gates B3 existentes. Se inspeccionaron visualmente las ocho entradas y se recorrieron páginas completas para cargar las imágenes. No hay overflow horizontal ni imágenes sin decodificar en esas observaciones.

[Ocho conjuntos de interacción](../evidence/design-evaluation/b3-20261022/after/interactions.json): búsqueda, cuatro categorías, vacío, reset y salto por teclado en cada molde/tamaño. Se comparan IDs, anchura y posición horizontal del catálogo restaurado. El verificador añade tres negativos: texto factual alterado, usos de medios perdidos y destino de navegación eliminado deben fallar.

Las capturas PNG son páginas completas reales, con el vídeo pausado mediante su control para registrar la composición; la reproducción previa y sus dimensiones se conservan en el recibo. No se afirma igualdad de fotogramas ni dos capturas consecutivas idénticas. Los hashes y presencia de píxeles se verifican. `observer.js` conserva la expresión usada; `matchMedia` y Performance no están expuestos en el scope DOM y se registran como no disponibles, sin inventar preferencias ni métricas.

Replay sin nuevas llamadas a proveedores, con el build final existente y el paquete privado autorizado local:

```powershell
node --experimental-strip-types scripts/b3-evaluate.ts verify
node --experimental-strip-types scripts/b3-preservation.ts --verify
```

Para adquirir otra corrida se necesita otro directorio/ID y evidencia nueva; los comandos before/after rechazan sobrescribir recibos existentes. No se ejecutan para verificar la corrida sellada. Se requiere Node24 y las dependencias locales documentadas; `.env`, dependencias, herramientas temporales y paquete privado quedan fuera de Git.

## Medios y límites

Mismos nueve archivos y **148 usos contextuales autorizados**: sin adquisiciones, catálogos, nuevas transformaciones o permisos fabricados. Se conserva la evaluación documental de 2026-10-20 y sus condiciones, revalidada por los loaders/gates existentes. No se anuncia una revisión jurídica nueva por instalar evaluadores. Imágenes/vídeo son ilustrativos de un restaurante ficticio; no prueban platos, local o personas. El original con audio no se sirve; el vídeo silencioso autorizado mantiene sus bytes/dimensiones. Créditos y aviso de no respaldo Pixabay permanecen accesibles.

Esta pasada acredita correcciones de interacción sobre los moldes completos. **La valoración estética sigue siendo humana y pendiente.** Los cuatro moldes no demuestran diversidad para cien mil sitios; los 13 grupos de datos pendientes de la matriz B3 no se completan con flags. La segunda categoría empresarial con un molde maduro y dos negocios reales verificados siguen pendientes del encargo amplio. No se crea otro hotel mínimo para aparentar ese cierre.

Sin nuevas métricas de red fría/LCP/CLS/INP, certificación WCAG, lector de pantalla físico, zoom exhaustivo o Edge. Hubo una navegación temporalmente bloqueada durante el build y un selector de etiqueta no resuelto; se recuperaron después del build y leyendo el DOM. No se interpretaron como accesos denegados a todo el computador ni como fallos del producto.

## Revisión independiente y pendiente residual

La tarea revisora autorizada `01a11911-1da1-73e0-8234-132547fc8f8f` revisó en lectura **c19bd18ff259c76844c4f0988a7fd3b2bb5cf156**. Confirmó la reutilización de los moldes, comparó capturas 01/03 desktop y 01 móvil y reprodujo replay B3, preservación 2.815, replay original quality y **31/31 tests focales B3**. Confirmó `TARGET_44` 20→0, los usos de medios conservados, diff check y Git limpio. Dictamen: **técnicamente listo para revisión humana, sin aprobación estética ni B4**.

**P2 residual, explícitamente pendiente:** con JavaScript apagado o fallido, el HTML aún conserva el salto original `href="#contenido"`, antes de la navegación. El cliente lo cambia a `#experience-main` al cargar. Los ocho recorridos por teclado prueban el comportamiento con JS; no prueban una solución sin JS. Para resolverlo robustamente hace falta renderizar el destino B3 desde servidor y comprobar el flujo sin JS, preservando la compatibilidad de Foundation y sus consumidores. No se presenta como ya solucionado ni como conformidad de accesibilidad completa.

Prompt de revisión propuesto: recorrer los cuatro moldes actuales, probar pasta/reset/salto con JS y valorar si se mantienen 01/02 y si se aprueban o rechazan las sustitutas 03/04, indicando cambios concretos por parte. El dictamen de la revisora no registra preferencias humanas.

Revisar los moldes actuales en [B3](http://127.0.0.1:4331/b3/), [01](http://127.0.0.1:4331/b3/candidate-01/), [02](http://127.0.0.1:4331/b3/candidate-02/), [03](http://127.0.0.1:4331/b3/candidate-03/) y [04](http://127.0.0.1:4331/b3/candidate-04/). Se detiene para revisión del usuario.
