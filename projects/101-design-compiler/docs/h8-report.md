# H8 — Design Lock y reconstrucción técnica de laboratorio

Se entregan tres `DesignLockV1` y un rebuild aislado que consume planes resueltos, el renderer compartido y snapshots verificadas. No llama al LLM, busca medios ni ejecuta sampler/search. No constituye aprobación humana o preparación para producción: los inputs comerciales siguen siendo sintéticos, runtime comercial MISSING y preferencias NOT_COLLECTED.

## Locks y snapshots

| Lock | Contexto y montaje conservado | Hash |
|---|---|---|
| [pilot-flow](../fixtures/locks/h8/pilot-flow.json) | H5 candidate-01 Rail/Sequence (ID de lock opaco), mismo cliente/proyecto/usage atmosférico H3 | `131a4550ebd18e5b14f973f003d306efd8ed6a1761f1e0ce12530e6333f80694` |
| [pilot-rail](../fixtures/locks/h8/pilot-rail.json) | H5 candidate-05 Rail/Split: otro AST del mismo piloto; no licencia transferida | `6c5834bc14816a79bbeec2ec3a13c96960a66541731ca57d3694fc07f6b093ec` |
| [hybrid-no-media](../fixtures/locks/h8/hybrid-no-media.json) | H7 híbrido tipográfico, media null, sin grants/refs | `321976f9db28102ca17daf02f42dfa42d42e4ab7ebb6b2d4829cd70efb06adb6` |

[Contrato](../contracts/lock/v1/DesignLockV1.schema.json) incluye inputs/profile/capabilities/semantic plan/requirements, manifest/brief/asset/grants/usages, proyección, output LLM resuelto/provenance/prompt/context, AST/tokens, versiones declaradas y fingerprints, montaje/rutas y aprobación **LAB_TECHNICAL_LOCK_NOT_HUMAN_APPROVED**. Unknown metering continúa null; no se crea voto o aprobación. Snapshot H3 guarda bytes originales de fotografía, ambos documentos oficiales, revisión y render HTML/PNG/receipt previo; `verifyPackageFiles` comprueba ese paquete offline. No recaptura ni cambia H3.

Las **42 fuentes runtime transitivas** se archivan como bytes de texto con LF en [source-archive](../fixtures/locks/h8/source-archive/), extensión `.txt`. Se restauran a un árbol nuevo bajo `.tools/h8-source/<id>` con hash verificado. Son cierre runtime, **no copia completa del proyecto para typecheck**: imports type-only borrados al compilar pueden referirse a archivos omitidos, como el tipo del loader histórico. El check ordinario no compila el archivo documental; el rebuild real compila sus módulos runtime restaurados. No se revierte el workspace para recuperar componentes antiguos.

El ejecutor `rebuild-lock.ts` también debe coincidir con su versión bloqueada. Un bootstrap modificado no puede interpretar un lock antiguo y fingir el mismo runtime. Cuando cambia plataforma, se materializa el snapshot exacto y se ejecuta su entry `scripts/rebuild-h8.ts` con el toolchain coincidente; un checkout aislado del commit de entrega también conserva esos bytes. Se bloquea ante toolchain distinto: no se promete reconstrucción cross-toolchain ni rollback de componentes cuyos bytes no existan.

## Rebuild dirigido y prohibiciones comprobadas

Se separó validación/contexto/estructura de `src/design/search.ts` hacia [validate.ts](../src/design/validate.ts). Search reexporta la misma API para H5–H7; renderer y auditoría importan el módulo puro. No hay segundo generador ni sitio específico por negocio.

[rebuild-lock.ts](../scripts/lib/rebuild-lock.ts) valida lock/semántica/derechos, fuentes, Node binario, package/lockfiles y todos los **12,985 archivos instalados de dependencias**, antes de render. Guarda versiones efectivas en esos paquetes y verifica bytes de dependencias indirectas. Pin de entorno: Node `v24.21.0`, win32/x64, OS `10.0.26200` / Windows 11 Home Single Language; Edge `154.0.4258.62` con exe/DLL/ICU/resources; **32 archivos de fonts Windows** relevantes y familias/postscript efectivas observadas mediante CDP. La equivalencia solo se acredita en ese entorno local controlado, DPR 1 y reduced motion.

Cada corrida crea un srcDir Astro dirigido, un wrapper estático con lab/AST ya resueltos, publicDir con solo la fotografía autorizada cuando corresponde, y un outDir **nuevo**. Reutiliza `DesignComposition` y primitivas existentes; conserva rutas/labels/montaje H5/H7. Nunca ejecuta el build normal de las 90 rutas para reconstruir. El grafo cargado por Vite se registra; hooks rechazan loaders/search/sampler y un sentinel de import deliberado lo demuestra. Fetch/http/https durante build se bloquean y contabilizan; adquisición/proveedor/sampler/LLM = 0. Los requests del documento browser son locales y se archivan; no se afirma auditoría de todo el tráfico de fondo del sistema operativo.

El build/replay histórico de H3–H7 sí usa sus loaders/search como antes. Esas verificaciones de preservación y los tests históricos son independientes del **camino aislado H8**, y no se presentan como prueba de ausencia de sampler.

## Equivalencia y rollback

[Run](evidence/h8/run.json) conserva **56 vistas**: originales 16, dos rebuilds 32, rollback 4, regresión sembrada 4. En todas las rutas y desktop 1280×900 / móvil 390×844 se compararon exactamente:

- HTML bytes, proyección DOM/bindings, geometría, legibilidad y fonts efectivas.
- PNG decodificado RGBA completo, incluyendo fotografía sin máscaras; tolerancia **0 píxeles**.
- Keyboard skip/disclosure/navigation, gates y bytes servidos del medio original.

Original vs cada rebuild, rebuild A vs B y rollback restaurado producen HTML idéntico, DOM/geometry/fonts iguales y **0 píxeles diferentes**. El raster auxiliar se recomputa con Node; únicamente entropía numérica entre runtimes admite `1e-12` de redondeo, sin tolerancia visual. HTML/CSS de salidas se archivan en [outputs](evidence/h8/outputs/) y PNG/hash por vista; no se basa equivalencia en etiquetas de status.

Historial explícito retiene lock id/hash y fingerprint del conjunto de archivos de cada output verificado. Se selecciona `pilot-flow` previo y se reconstruye en otro output: manifest completo, incluyendo foto, coincide con el fingerprint anterior y el navegador coincide con el original. Esto es rollback entre snapshots verificados del mismo toolchain, sin sobrescribir ni borrar outputs/workspace.

## Negativos y regresión

Cinco experimentos rechazan: fingerprint source cambiado, Node version cambiada, corrupción de una **copia** de foto, import sampler deliberado, y fuente CSS regredida en copia frente al lock original. Los originales no se modifican. Fuente/Node/bytes incompatibles fallan antes de render; import prohibido falla durante bundling antes de prerender.

La copia CSS con h1 de 8 px se etiqueta **SEEDED_COMPONENT_REGRESSION_TEST_ONLY** y usa lock purpose SEEDED_COMPONENT_REGRESSION, permitido solo por opción experimental. No reemplaza un lock normal. Cuatro vistas fallan gate `CONTRAST_OR_TEXT` y la comparación visual/funcional detecta diferencias; `accepted:false`. [Lock experimental](evidence/h8/seeded-component-lock.json) y [fuente CSS sembrada](evidence/h8/seeded-component-style.css.txt) permiten verificar el defecto concreto. No se simula revisión humana o una mejora.

## Reproducción y alcance

`npm run lock:rebuild -- pilot-flow` restaura fuente y recompila exclusivamente el lock en una corrida nueva. `npm run lock:verify -- --rebuild` comprueba locks, archivos/derechos, imágenes, gates, comparaciones y rollback, y reconstruye los tres outputs con hashes idénticos. No ejecuta sampler, loaders creativos, LLM o adquisición. `npm run lock:audit` recaptura solo evidencia H8 propia, requiere baseline actual `dist` y no cambia evidencia histórica. `lock:seal` es registro de snapshots resueltos, **no se ejecuta durante replay/rebuild**.

El verificador contrasta además baseline `dist` si existe; en checkout limpio sin dist usa los HTML originales archivados y lo declara **archived only**. La reproducción clean-index dirigida usa ese modo sin build normal ni sampler. Para pruebas integrales con dist existente, `scripts/verify-h8.ps1` incluye tests/check y verificadores históricos, luego rebuild H8 dirigido.

291 tests PASS, check 0 errores/warnings/hints. [Tests](evidence/h8-tests.txt), [check](evidence/h8-check.txt), [build histórico](evidence/h8-build.txt), [preservación H3–H7](evidence/h8-historical-validation.txt), [seal](evidence/h8-seal.txt), [browser](evidence/h8-browser.txt), [verify/rebuild](evidence/h8-verify.txt), [clean-index](evidence/h8-clean-repro.txt). Contratos históricos, reservas/first-evaluation H7 y artifacts H3–H7 permanecen intactos; no hay dependencias nuevas o búsqueda de medios.

La corrida final H8 observó ~67.22 s de wall total y se registran wall times de cada build. No es latencia o economía comercial. Gasto **nuevo** 0 / llamadas nuevas 0; dinero/tokens de sesión null, costo total no medido. La foto de 2.35 MB sigue siendo excepción LAB, no PERFORMANCE_PASS comercial. Estética/humanos/field p75/runtime comercial siguen pendientes. No se inicia H9 hasta PASS independiente; no hay pilotos comerciales ni sitios humanos aprobados o métricas económicas fabricadas para cerrar H9.

Corrección previa a entrega: la selección inicial de ambos locks piloto apuntaba a candidate-01 y degeneraba el experimento de rollback. Se conserva candidate-01 Rail/Sequence y se elige candidate-05 Rail/Split para el segundo snapshot. El verificador exige hashes distintos del plan resuelto y structuralSignature distinta (no basta cambiar ID); un test de regresión verifica estructura, AST e ID diferentes. [Reverificación estructural PASS](evidence/h8-structure-verify.txt). Se regeneraron únicamente locks/evidencias H8; [7 pruebas dirigidas PASS](evidence/h8-distinct-rollback-tests.txt), posteriores a los 291 tests generales, cubren la corrección. Los IDs de lock son etiquetas opacas y no describen el operador del AST.

## Corrección H8-R1: auditorías reales fijadas en el lock

La revisión inicial [H8 FAIL](reviews/h8-review.md) detectó que el literal de aprobación técnica no incluía reportes, estado ni cobertura. Esta corrección espera reauditoría independiente; no convierte aquel FAIL en aprobación histórica.

`audit_state` fija los reportes REALES de la corrida H8 anterior, capturada el **2026-10-09T03:06:46.289Z** (UTC), sobre la implementación `6cc7993`: [fuente inmutable](../fixtures/locks/h8/audit-snapshot/source-run.json), SHA-256 `b3b403e07fc02c27568c0b6d25728c8b56f8195ebbfc6619d114b3fbe047e9f1`. Es auditoría equivalente H8 de los candidatos originales montados H5/H7; **no aprobación histórica ni humana de H5/H7**. Cada lock conserva el hash del lock previo auditado y sus bytes recuperables, separados del hash del nuevo lock. No hay ciclo entre lock nuevo y su recibo futuro.

Los snapshots incluyen policy LAB, hash del candidato completo y contexto, 23 fuentes del renderer/auditor auditados, observaciones reales y reportes `AuditReportV1`, familias/gates y cobertura completa: 4 vistas por cada piloto, 8 por el híbrido (todas sus rutas × desktop/mobile). Los HTML/CSS/PNG originales están copiados bajo `audit-snapshot/files/` y referenciados con bytes y hashes. La nueva corrida H8 puede sobrescribir su evidencia de trabajo, pero no estos archivos fuente previos. El sealer comprueba reportes/cobertura y archivos antes de emitir un lock.

El validator recomputa el reporte desde observaciones congeladas y policy, contrasta resultado exacto, candidato/contexto/ruta/viewport, cobertura sin duplicados, evidencia recuperable y fuentes. Rechaza missing, FAIL real, alteración de gates, contexto o ubicación, cobertura incompleta, hashes y pins incoherentes. El rebuild verifica bytes, reportes contra su fuente y correspondencia del plan/lab/fuentes con el snapshot previo antes de renderizar. El grafo debe contener exactamente las fuentes auditadas, además de los pins runtime H8 actuales. El literal `approval` por sí solo ya no basta.

Se conservan estados reales: derechos/bindings/geometría/a11y PASS donde observados, performance **LAB_EXCEPTION sólo en las rutas donde aparece la foto** y PASS técnico local en otras, visual/diversity **NOT_MEASURED**, raster auxiliar, field p75/LCP/INP/CLS **NOT_MEASURED**, preferencias **NOT_COLLECTED**, runtime comercial **MISSING**. El contrato experimental exige `BASELINE_ONLY_SEEDED_NOT_ACCEPTED`; sus reportes fijados describen el baseline original, nunca aprueban CSS degradado. La nueva ejecución detecta cuatro vistas FAIL del componente sembrado y requiere opción explícita de experimento.

Validación final: [297 tests PASS](evidence/h8-r1-tests.txt), [14 tests dirigidos PASS](evidence/h8-r1-targeted-tests.txt), [check 0](evidence/h8-r1-check.txt), [seal](evidence/h8-r1-seal.txt), [56 vistas/10 comparaciones exactas/rollback y negativos](evidence/h8-r1-browser.txt), [offline verify y tres rebuilds sin sampler](evidence/h8-r1-verify.txt), [clean-index dirigido](evidence/h8-r1-clean-repro.txt). Las pruebas negativas incluyen un reporte FAIL internamente consistente, pruebas de contexto/policy/gates/cobertura/evidencia/renderer y bytes fuente corruptos, ausentes o un grupo de reportes inexistente. H3–H7 y la revisión FAIL permanecen intactos. Dinero/tokens totales siguen desconocidos; no producción ni H9.
Los JSON baseline-* son pruebas históricas del origen, no locks actuales aceptados por el contrato corregido. Conservan todos los 42 fingerprints de la captura previa (incluido harness/wrapper/browser/raster). Sus bytes de fuente originales se recuperan del commit 6cc799332f4f4219ae685df959f93b3d534b78a2 en fixtures/locks/h8/source-archive; los 23 pins renderer+auditor comparados con la plataforma actual corresponden a código que no cambió. Las nuevas fuentes H8 de guards y reconstrucción se recuperan del snapshot corriente. No se atribuyen reportes previos a un ejecutor modificado.
