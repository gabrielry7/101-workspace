# Brasa y Herbario: renovación artística de 03/04

El usuario pidió el 25 de octubre de 2026 conservar exactamente las dos primeras propuestas Claude y rehacer las dos últimas como páginas artísticas, diferentes y con libertad creativa, aportando mucha más multimedia de Pixabay y nuestras referencias visuales si ayudaban. La implementación está completa en una copia aislada para revisión; sin commit, merge ni push.

- **03 / Brasa:** http://127.0.0.1:4323/b3/candidate-03/
- **04 / Herbario:** http://127.0.0.1:4323/b3/candidate-04/
- Copia: `.tools/claude-worktrees/restaurant-artistic-20261025`. La vista previa Astro local está en sesión de terminal Codex 76200. La anterior permanece en 4322 para comparar.

## Resultado y alcance

Brasa usa un campo negro, acento brasa, Syne ancha, rail lateral, película manual de fuego, collage fotográfico y cierre naranja. Herbario usa papel cálido, tinta ciruela, Bodoni Moda, masthead centrado y una secuencia de láminas botánicas con mucho aire, ejemplares que se mezclan con el papel y una pausa de vapor. Se rehízo la composición del inicio y el tratamiento de las once páginas de cada mundo: carta, pedidos, reservas, historia, visita, preguntas, diario, opiniones, contacto y créditos.

**Las 22 páginas de 01/02 se conservaron byte por byte.** También permanecen idénticas las otras **124 rutas**. Sólo cambian las 22 rutas de 03/04. Los JSON sellados, enums, contratos, decisiones históricas, umbrales y estilos previos no se alteraron. La dirección nueva se deriva en tiempo de render de los operadores semánticos existentes, con clases y CSS nuevos emitidos sólo para esos dos mundos. El renderer Astro y sus módulos de negocio siguen siendo compartidos.

## Claude real, contexto y recursos

Doctor autenticado, start y dos feedback por el puente real documentado. Tres respuestas exitosas en la misma sesión `b9de09a3-1a84-4ef7-968e-a59f66d95b9d`, cero denegaciones y sin herramientas de shell, red o navegador para Claude. Primer intercambio: elección de conceptos tras ver material. Codex revisó/seleccionó y portó diez archivos de la versión Claude anterior, porque el nuevo worktree empezaba en HEAD y no contenía aquella versión no confirmada. Segundo intercambio: implementación. Tercero: corrección a partir de capturas y hallazgos reales. No se sustituyó Claude por un subagente.

Se ofrecieron 16 nuevas fotografías de ingredientes, objetos y trabajo manual; dos clips candidatos, tres tipografías OFL y referencias históricas KOL, Aponiente (sólo su menú/scroll aprobado), LUNE y Dinesen. Claude eligió Brasa y Herbario por sí mismo. No se le impuso una plantilla ni una copia de las referencias. Los píxeles, marcas y fuentes de esos sitios no entran en el runtime.

Claude eligió **15 fotos nuevas**. El clip nuevo de fuego fue extraído sin audio con el remuxer ya existente; se agregó un poster de un fotograma autorizado. Para Herbario se volvió a admitir el vapor de olla anterior. El clip de aceite se excluyó por letras visibles en el envase; el cítrico cortado quedó sin usar por decisión visual de Claude. Fuentes locales: Syne, Bodoni Moda y DM Sans. Ante la ausencia del módulo Brotli opcional, fontTools generó subconjuntos WOFF, con español/latín/puntuación/flechas y sus avisos OFL: 224.248 bytes en total; cada propuesta carga sus dos familias.

Los recursos quedan en `.tools/claude-code/artistic-resources-20261025/`; los originales y cachés no se publican en Git ni se entregan como catálogo de stock. [Revisión por archivo](../evidence/claude-code/artistic-20261025/resources-review.json). La API existente se usó en diez consultas específicas sin paginación, sin cuenta nueva ni compras. No se enviaron .env, claves, respuestas crudas de API ni archivos privados ajenos al trabajo.

La admisión acompaña al paquete histórico: **55 registros de origen/derivado, 19 elecciones posibles y 792 usos exactos en las 22 rutas de 03/04**. Contratos, rightsGate y evaluateSuitability permanecen intactos. Manifest, evidencia, originales y derivados están fijados por hash; se conserva la denegación de 01/02 y de activos rechazados. Sólo los dos derivados sin audio, por hashes exactos y contenedores verificados, usan la misma excepción acotada de revisión de audio heredado que ya existe en B3. No se permite presentar las fuentes con audio. Crop, color CSS y composición multiply se revisaron para este encargo ficticio; no edición generativa, entrenamiento propio ni embeddings. No se afirma una autorización general de IA del proveedor ni de reutilización multicliente.

## Revisión y verificación

La primera composición compiló, pero las capturas y auditoría mostraron el nombre fragmentado, controles de 12/13px, una etiqueta negra sobre negro, relatos colapsados en móvil y rectángulos blancos en los ejemplares. Se devolvieron las capturas y hallazgos concretos a Claude. Corrigió esos puntos sin abandonar los dos mundos. Codex agregó sizing/eager explícito al poster, corrigió dos detalles de tipado y terminó el ancho del diario filtrado de Herbario.

- **Compilación y validación: PASS**, 168 páginas; última compilación en filtered-build.log.
- **Tipos: PASS**, 316 archivos, 0 errores/advertencias/hints; corrected-check.log. El primer chequeo detectó cinco errores (cuatro por un head potencialmente indefinido y uno por optional props estrictas), corregidos antes de aceptar. Un chequeo inicial de preparación tuvo contención EPERM del caché Vite al correr junto al build; las verificaciones finales se hicieron secuencialmente. Se conservan los registros fallidos.
- **429/430 tests PASS**. Único fallo H8 histórico: `LOCK_BROWSER_MISMATCH` donde el negativo esperaba `LOCK_AUDIT_FILE_MISMATCH`. Ya se reprodujo antes del rediseño. No se cambió ni ocultó. Tres tests nuevos verifican admisión exclusiva de 03/04, caducidad y presentación sólo de derivados silenciosos/poster.
- **220 vistas finales PASS**: 44 rutas en 360, 390, 768, 1024 y 1440 px, con controles de navegación/skip/Escape, búsqueda/vacío, selección/vaciado, reservas ficticias, filtros del diario y disclosures expandidos.
- **4 vistas de navegación abierta PASS**, escritorio y móvil para ambos mundos.
- Cero excepciones JS de la app, peticiones externas o errores HTTP. Los cuatro ensayos de película (dos mundos × dos tamaños) avanzan con audio ausente/muted y sin transferencia automática bajo movimiento reducido.
- Hechos, módulos, scopes, lecturas editoriales, reseñas ficticias, destinos originales, avisos, diagnósticos, exclusiones y créditos conservados. Se verificó cada imagen nueva contra registro, uso/ruta, archivo público y autor/fuente.
- Contraste mínimo auditado conservador: **4.94:1**. No se relajaron los umbrales. El histórico mantiene sus checks completos para 01/02; para los mundos reemplazados se comprueban sus invariantes semánticos y de medios sin exigir el antiguo vídeo pizza a ancho completo. Sólo los recortes de medios revisados y efectivamente recortados dentro de sus contenedores se distinguen del overflow accidental; texto y controles siguen fallando si se cortan.
- Detector Impeccable final: **0 hallazgos**. Dos rondas de capturas desktop/móvil de todas las páginas nuevas y sus recorridos, revisadas por Codex. La última corrección fue exclusivamente el estado filtrado del diario, confirmado en la matriz final.

El primer ensayo del filtro encontró un error de redeclaración en el propio harness CDP, no en la app; se corrigió con un scope local y las 220 vistas finales lo usan. La matriz posterior a Claude pasó 217/220 antes del ajuste final del diario; la matriz release pasa 220/220. Medición local, con movimiento reducido y caché cálida, no certificación WCAG completa ni Core Web Vitals en red fría. No se inventan nuevas notas del usuario ni aprobación final de 03/04.

## Evidencia y límites de ejecución

[Intercambios CLI](../evidence/claude-code/artistic-20261025/exchanges/index.json), [índice de verificación](../evidence/claude-code/artistic-20261025/verification/index.json), [resumen y matriz final](../evidence/claude-code/artistic-20261025/verification/summary.json). Las fuentes finales, incluidos archivos nuevos omitidos por git diff, quedan en integration-sources. Capturas en `.tools/claude-code/restaurant-artistic-20261025/final-captures/`.

Tarea acotada a 4 llamadas, 60 turnos/llamada, 720 segundos/llamada y $3 estimados por llamada/$12 por tarea. Se usaron **3 llamadas**, con **$9 reservados** y **$2.5301 estimados acumulados por CLI**. No sumar las cifras acumuladas de cada respuesta. Autenticación claude.ai; no se afirma cargo incremental de suscripción. Sin commit, merge, push ni publicación externa.
