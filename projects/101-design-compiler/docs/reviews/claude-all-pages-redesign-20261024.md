# Rediseño de todas las páginas B3 con Claude Code

Petición del usuario del 24 de octubre de 2026: que Claude mejore diseño y paletas de las páginas existentes, recibiendo primero más multimedia por el API existente y decidiendo qué usar. Implementación retenida para revisión, sin commit, merge ni push.

Vista local: http://127.0.0.1:4322/b3/ . Copia aislada: `.tools/claude-worktrees/restaurant-all-pages-20261024`, desde HEAD `24c4301c2a36fc5a023d3cd695030afc13a47f09`. Proceso de vista previa: sesión de terminal Codex 9719 (Ctrl+C o detener ese proceso de Astro para cerrarlo).

## Alcance y colaboración real

Cuatro propuestas × once páginas = **44 rutas B3**. Se conservaron las **124 páginas restantes con HTML idéntico byte por byte**, incluido el índice de comparación. No se alteraron fixtures, decisiones históricas, contenido de negocio, contratos ni umbrales. Los cambios previos del usuario en README, AGENTS, tooling y evidencias quedaron en su carpeta principal; no se copió ningún cambio de fuente de usuario sin revisar.

Se ejecutó doctor autenticado, start y feedback por el puente real documentado en tooling/claude-code/README.md. Dos respuestas exitosas, misma sesión `97eee40f-1496-45f5-9218-9cca307d95e4`, cero herramientas de shell/red/browser para Claude. En el primer intercambio hubo cinco intentos de lectura fuera del worktree, denegados; los archivos aprobados sí estaban dentro y la segunda revisión usó rutas correctas sin denegaciones. Claude produjo CSS/markup y Codex hizo admisión multimedia, revisión, builds, tests y navegador. No se sustituyó por un subagente.

Límites explícitos: 4 llamadas, 40 turnos por llamada, 720 segundos por llamada, estimación máxima de $2 por llamada/$8 por tarea. Se usaron 2 llamadas, con $4 reservados por el puente y **$1.1935 estimados acumulados por CLI**; no sumar los totales acumulados de ambas respuestas. Autenticación claude.ai; la estimación no afirma un cargo incremental de suscripción.

## Diseño entregado

| Propuesta | Paleta |
| --- | --- |
| 01 / inmersiva | Hueso, tinta cálida y terracota |
| 02 / portada | Blanco cálido, tinta marrón y bermellón |
| 03 / editorial | Verde tinta oscuro, blanco y celadón |
| 04 / índice | Blanco, grafito, lima y oliva para texto |

Las once páginas tienen tratamiento concreto: inicio y ritmo entre secciones; carta con filtros/detalles; pedidos con resumen; reservas con formulario y mesas; historia editorial; visita práctica; preguntas con disclosures; diario con relato principal/filtro; opiniones con etiqueta ficticia visible; contacto con atajos locales; créditos legibles. Chrome, estados, foco y móvil comparten los tokens de cada propuesta. Se corrigieron reglas laterales gruesas, sombra dura, barras ornamentales, tracking excesivo y movimiento incidental tras revisar las primeras capturas.

## Multimedia primero, elección de Claude después

Cuatro búsquedas acotadas mediante la clave Pixabay existente, sin credenciales en contexto ni caché cruda enviada. Se descargaron seis fotografías y un clip; originales/renditions, WebP 640/1280 y vídeo derivado sin audio permanecen en `.tools/claude-code/multimedia-20261024/` tanto en la carpeta principal como en el worktree. No se compró contenido ni abrió cuenta. [Revisión y hashes](../evidence/claude-code/redesign-20261024/multimedia-review.json).

Claude seleccionó 5356682 (mesa al atardecer) para reservas, 2714970 (café sobre madera) para contacto y 4642686 (hogaza) para historia. Descartó panecillos por la tela roja, la segunda foto de café por redundancia y el vídeo de vapor porque el inicio ya tiene una película. La sala 1834784 fue excluida antes de delegar por objetos/marcas visibles.

La integración de Codex agrega un acompañamiento acotado al paquete histórico, usando **los mismos MediaAssetV1, LicenseGrantV1, MediaUsageV1, rightsGate y evaluateSuitability**, sin cambiar sus reglas ni pins históricos. Nueve registros de fuente/derivado y 24 usos por ruta/tamaño, con manifest/evidencia/bytes fijados por hash, vigencia, finalidades, créditos y avisos. Sólo esas tres páginas de cada propuesta admiten cada imagen. Las nuevas fuentes figuran en los cuatro créditos. No son evidencia de productos ni de ubicación real. La autorización visual es la interpretación limitada al encargo ya usada por el proyecto, no un permiso global de IA del proveedor; sin entrenamiento, embeddings ni edición generativa.

## Verificación final

- **Build y validación: PASS**, 168 páginas. **Typecheck: PASS**, sin errores, advertencias ni hints.
- **426/427 tests PASS**. Único fallo: H8 histórico `LOCK_BROWSER_MISMATCH` donde el negativo esperaba `LOCK_AUDIT_FILE_MISMATCH`; se reprodujo antes de los cambios (423/424). No se modificó ni ocultó. Los tres tests nuevos verifican admisión por ruta, caducidad y rechazo de inventario alterado/bytes ausentes.
- **220 vistas PASS**: 44 rutas en 360/390/768/1024/1440 px. Cero overflow, fallos auditados de lectura/targets, solicitudes externas, errores HTTP o excepciones JS. Contraste mínimo auditado conservador **4.94:1**.
- Preservación de hechos, módulos, navegación, lecturas, reseñas ficticias, restricciones, diagnósticos y enlaces originales: **PASS en todas las vistas**. Skip, menú/Escape, búsqueda/vacío, selección/vaciado, reserva ficticia, filtro de diario y disclosures expandidos comprobados.
- El auditor histórico conserva íntegros los checks de sus ranuras fijadas. Las fotos nuevas se verifican separadamente contra el acompañamiento y sus gates; sólo después se proyectan las fotos históricas al auditor histórico. No se relajan contraste, geometría, contenido ni umbrales.
- **JavaScript cliente idéntico: 5.791 bytes** antes/después; sin dependencias nuevas. HTML B3 máximo: 76.212 → 95.276 bytes sin comprimir, por CSS compartido y markup. Sin petición de vídeo bajo movimiento reducido.
- Detector Impeccable ejecutado una vez: una advertencia de Arial en el símbolo de disclosure; se conserva la familia ya utilizada para controles, sin introducir fuente web. Capturas desktop/móvil de los once tipos en las cuatro propuestas y 24 vistas de las fotos colocadas revisadas por Codex.

Las mediciones son locales, con movimiento reducido y caché cálida; no constituyen certificación WCAG completa ni Core Web Vitals de red fría. La elección visual final del usuario no se inventa. Se repitieron las capturas con el paso de pintura ya existente al detectar un artefacto de mosaico de Edge; no se alteró el código de producto por ese artefacto.

## Artefactos y archivos

[Intercambios CLI originales](../evidence/claude-code/redesign-20261024/exchanges/index.json), [índice de verificación](../evidence/claude-code/redesign-20261024/verification/index.json), [comparación](../evidence/claude-code/redesign-20261024/verification/comparison.json), [auditoría de navegador](../evidence/claude-code/redesign-20261024/verification/browser-summary.json). Capturas completas de revisión en `.tools/claude-code/restaurant-all-pages-20261024/final-captures/`. Los originales multimedia no se exportan a Git ni se ofrecen como catálogo de descargas.

Implementación de Claude: `experience-refinement.css`, `ExperienceComposition.astro`, `CommunitySections.astro`, `PreviewIntent.astro`. Admisión de Codex: `optional-restaurant.ts`, `SupplementalImage.astro`, inventario acompañante y tests. Fuentes nuevas seleccionadas también se retienen en `integration-sources/` para que el patch rastreado no omita archivos nuevos. Todo queda en la copia aislada para revisión.
