# H6 — Auditoría, crítica, mutación y comparación local

**PASSED como implementación/experimento de laboratorio; pendiente de auditoría independiente.** El sistema detecta defectos reales sembrados, repara un layout acotado, conserva y restaura el artefacto anterior cuando una mutación empeora, excluye fallos duros y ofrece A/B/empate/ninguna. La selección termina en **NEEDS_HUMAN_REVIEW**; votos humanos **NOT_COLLECTED**. El perfil comercial devuelve **NO_ACCEPTABLE_DESIGN** por el original pesado. No se declara producción ni se inicia H7 por esta entrega.

Base autorizada `72e0e0aba0f91013cad4db2724e52a63d6cf1dbc`, H5 PASS independiente sobre `58af61e`. Mientras se implementaba H6 se corrigió únicamente una evidencia de revisión en `ba2954a`: el harness archivado como `.ts` tenía imports relativos a su ubicación temporal y producía 18 diagnósticos de check. El revisor lo renombró a `.txt` conservando SHA y actualizó enlaces. El implementador no modificó reviews/coordinación. Se leyeron §18–20/24 de V0.2 y review H5; la frontera de laboratorio y el roadmap se conservan.

## Piezas y reutilización

| Pieza | Responsabilidad |
|---|---|
| `src/audit/contracts.ts`, `contracts/audit/v1/` | Seis contratos strict 1.0.0: candidato, política, issue, report, mutación y preferencia |
| `src/audit/evaluate.ts` | Nueve familias, gates duros, critic con selector/ruta/viewport/evidencia y selección con cobertura exacta |
| `src/audit/mutate.ts` | Única mutación acotada de medida; comparación por ubicación/política, historial y rollback exacto |
| `src/audit/raster.ts` | Medición determinista de píxeles de screenshot con foto excluida |
| `src/audit/png.ts` | Decoder propio mínimo 8-bit RGB/RGBA, sin interlace, para recomputar offline métricas reales |
| `src/audit/preference.ts`, `panel.ts` | Consumo de preferencias con contexto exacto y formulario local; simulaciones no aceptadas como votos |
| `scripts/load-audit-lab.ts`, `audit-h6.ts`, `verify-h6.ts` | Fixture/casos congelados, experimento browser y replay de evidencia |
| `scripts/load-comparisons.ts`, `audit-h6-panel.ts` | Parejas equivalentes, orden registrado, QA del panel |
| `src/pages/h6/`, `DesignComposition.astro` | Montajes locales y comparación sin backend; renderer compartido H5 parametrizado |

Se reutilizan Foundation, H2 content/bindings, gate/paquete H3, componentes y observer H4, AST/tokens/search H5 y Edge/CDP local. El renderer añade props opcionales de montaje y fixture diagnóstico; los defaults H5 conservan HTML/CSS históricos byte por byte. Los cuatro finalistas siguen las cuatro topologías H5, con mismas dos rutas, hechos, scopes, uso/grant y foto original. No hay nuevos datos, descargas, proveedores, gastos, backend, fuentes, librerías ni cambios de lockfile.

Los critic/mutator históricos y runtime comercial continúan **MISSING / NOT_TESTED**. Las piezas añadidas se identifican como `LOCAL_LAB_V1_NOT_HISTORICAL_INTEGRATION`; no se inventa integración ni excelencia estética. H6/H7 ≥4 arquetipos se comprobará en H7: este experimento utiliza únicamente el fixture restaurante congelado.

## Gates y estados

Las nueve familias son entrada/contexto, capacidades, cobertura semántica, derechos/representación, geometría, accesibilidad, rendimiento, calidad visual y diversidad. Comparten los validadores previos; no se presentan como nueve evaluadores estadísticos independientes.

Entrada/capacidad/bindings/medios se contrastan con plan y DOM observado. Geometry detecta overflow y visibilidad. A11y contrasta contraste/tamaño/reduced motion y resultados reales de skip/teclado/disclosure/navegación. Un fallo de verdad/derechos/a11y bloquea; raster favorable o apariencia no compensa. Los issues contienen código, severidad, selector, ruta, viewport solicitado, screenshot y observación concreta. Se conserva también el layout viewport observado por navegador.

`LAB_TECHNICAL_PASS_NEEDS_HUMAN_REVIEW` permite presentar el candidato como laboratorio, nunca `DESIGN_ACCEPTED`/producción. Calidad/preferencia humana están **NOT_MEASURED / NOT_COLLECTED**. Diversidad estructural se comprueba para la selección completa; el report de una vista individual no finge medir diversidad global.

Políticas explícitas, hipótesis de laboratorio sin calibración de campo:

| Política | Límite body sin compresión | Requests incl. HTML | JS cliente en candidato | Original H3 |
|---|---:|---:|---|---|
| LAB | 2.500.000 B | 3 | cero scripts | `LAB_EXCEPTION` visible; solo fixture congelado |
| COMMERCIAL control | 300.000 B | 3 | cero scripts | sin excepción; **FAIL** |

Requests y bytes se observan de HTML/recursos locales, sin prometer bandwidth real. LCP, INP, CLS y p75 de campo se registran **NOT_MEASURED** por contrato; video **NOT_APPLICABLE**. Oferta sin imagen pasa bytes locales; home no obtiene PERFORMANCE_PASS comercial. La foto original de 2.351.102 B sin permiso de derivados mantiene su bloqueo comercial. No se altera el grant para repararla.

La selección exige todos los pares ruta/viewport esperados, sin duplicados y con hash de candidato correcto; una sola vista PASS no aprueba un sitio. Conserva cuatro firmas topológicas distintas, ignorando cosmética. Si ninguno cumple, retorna **NO_ACCEPTABLE_DESIGN**, demostrado tanto con el conjunto fallido como con el perfil comercial.

## Raster medido, sin score de belleza

Cada PNG se decodifica realmente en canvas del navegador. Se recorren píxeles con stride 4; la caja del JPEG original se excluye de estadísticas. Se miden ratio de tinta, bordes por luminancia, entropía de 16 bins y centroide auxiliar en píxeles de texto/layout. No se llama API de visión, no se analiza semánticamente el stock, no se hace embedding/edición/crop ni se crea derivado del asset.

Ejemplo real Rail/Sequence desktop: PNG 1265×1304, **86.062 muestras de layout**, **17.280 muestras de la foto excluidas**, ink ratio 0,01917, edge density 0,02473, entropy 0,5390. Son instrumentos sin estética calibrada ni criterio universal de ocupación.

El verificador lee bytes PNG, aplica decoder Node (zlib estándar), deshace filtros PNG y recomputa las métricas con la misma función pura. Coinciden las **27** mediciones browser/offline; no se copiaron metadatos como sustituto de procesar píxeles. Solo se soportan PNG RGB/RGBA de 8 bits no interlazados como los de Chromium; otros formatos se rechazan. Los hashes del recibo fijan integridad, sin pretender firma del proveedor.

## Experimento before / repair / worse / rollback

Presupuesto: 8 planes montados (4 reales + 4 fases diagnósticas), **16 vistas baseline**, **8 vistas de mutación**, **3 vistas de otros defectos DOM**, 2 propuestas de mutación y cero gasto/API. Las cuatro clases de defecto son ancho excesivo, texto factual alterado, crédito eliminado y contraste inválido. Las páginas `SEEDED_DEFECT_TEST` son diagnósticas y tienen rótulo visible; el parámetro `fixed-wide` se rechaza en un candidato `FROZEN_LAB`. No se burla un validador comercial ni se devuelve este layout como válido.

1. `repair-before`: ancho fijo 80rem en identidad. Desktop documento **1542px** frente viewport solicitado **1280px**; móvil documento/layout viewport **1308px** frente solicitado **390px**. Ambos **FAIL / OVERFLOW**.
2. Critic identifica `.identity`, ruta/view/screenshot y recomienda `FLUID_MEASURE`. Mutator solo cambia el enum de medida a `fluid`; ningún campo del plan, hecho o permiso cambia. `repair-after` vuelve a renderizar: desktop ancho documento 1265px, móvil 390px; ambos **PASS de laboratorio**.
3. Control `worse-after` vuelve a medida fija: dos **FAIL**. No aporta mejora; el juicio hace **ROLLBACK** al snapshot anterior completo.
4. `rollback-restored` renderiza el artefacto recuperado y comprueba hash previo, referencias y dos **PASS**. Rollback no es solo una etiqueta.

| Artefacto | SHA-256 canónico |
|---|---|
| Antes defectuoso / mutación peor | `9c6cf67e1d5d84ff3285af518321e096b8dc11d64e2a104ad4fa38cb00d68cd9` |
| Reparado / conservado / restaurado | `e08b2fddf29a6b2968ad8646a51b025553d4661d57756764b569ca7482463b12` |

Historial guarda candidatos completos before/after/kept, hashes, reports y rutas de evidencia. Juicio exige cobertura idéntica de **ruta semántica y viewport solicitado**, sin duplicados, política idéntica y hashes concordantes. La mejora exige menos fallos bloqueantes **sin introducir código/familia en otra ubicación**. Un count global menor no oculta un fallo desplazado. Pruebas negativas cubren cobertura desigual, swaps, políticas/hash corruptos y mismo código en nueva ubicación. Derechos/copy nunca son patches autorizados: sin reparación lícita conserva el bloqueo.

Capturas: [antes móvil](evidence/h6/repair-before-mobile.png), [reparado móvil](evidence/h6/repair-after-mobile.png), [peor móvil](evidence/h6/worse-after-mobile.png), [restaurado móvil](evidence/h6/rollback-restored-mobile.png). La expansión automática del layout móvil y la gran zona fuera del documento visible antes del arreglo son precisamente el defecto medido; no se retoca la captura para ocultarlo.

Los otros tres negativos se inyectan únicamente en DOM del harness, se rotulan `SEEDED_DOM_DEFECT_TEST` y nunca se incorporan al input/build factual: precio falso textual, crédito vacío y h1 con color del fondo. Emiten respectivamente binding loss/invention, media presentation invalid y contrast/text; todos **FAIL**. No se convierten en contenidos o licencias nuevas.

## Panel y preferencia humana

`/h6/` presenta **24 comparaciones**: seis parejas × dos viewports × dos rutas. Cada iframe usa exactamente 390×844 o 1280×900 y la misma ruta semántica; el harness verifica medidas/layout real y espera decodificación de imágenes en ambas frames. A/B se distribuye por hash pseudoaleatorio contextual con seed/orden registrados; es reproducible, no una prueba ciega completa porque los headers internos aún muestran IDs de laboratorio.

El panel ofrece **A / B / empate / ninguna**, razón opcional literal y JSON descargable. Solo tras una acción en el formulario prepara una decisión; no hay backend, red de escritura, almacenamiento local persistente ni voto preseleccionado. Snapshot/contexto, candidatos, imágenes, ruta, viewport, orden y decisión quedan en el registro. La aceptación se limita a `THIS_PAIR_ROUTE_VIEWPORT_ONLY`, sin inventar aprobación global o razones. El consumidor rechaza contexto diferente y `TEST_SIMULATION` como voto humano; un futuro import debe recibir el JSON real, no inferirlo de esta QA.

QA con `?qa=1` produjo **8 decisiones TEST_SIMULATION**, no humanas: cuatro opciones por dos vistas. Space activó radios y submit nativos; el artefacto registra solo cobertura simulada y disponibilidad del download. Reload ordinario devuelve **NOT_COLLECTED**, sin votos conservados o transmitidos. Candidatos siguen sin JS; el pequeño script inline fijo pertenece únicamente al panel. Sin JS el botón está deshabilitado y se explica la descarga local.

[Panel móvil](evidence/h6/panel-mobile.png), [panel desktop](evidence/h6/panel-desktop.png), [recibo](evidence/h6/panel-audit.json). Preferencia humana y torneo completado: **NOT_COLLECTED**, no se fabrica vencedor.

## Pruebas, ejecución y límites

**272/272 tests**: 254 anteriores +12 pruebas de auditoría/mutación/raster/preferencia +6 schemas. Check 0 errores/warnings/hints; export 27 schemas; build 59 páginas. El [recibo completo](evidence/h6/run.json) registra Edge 154.0.4258.62 y fecha final 2026-10-09T01:46:01.320Z (8 de octubre local), 27 vistas, problemas localizables, comparación de políticas, histories y conjuntos bloqueados.

| Verificación | Evidencia |
|---|---|
| Contracts/export | [log](evidence/h6-contracts-export.txt) |
| Tests | [log](evidence/h6-test.txt) |
| Check | [log](evidence/h6-check.txt) |
| Build/validación | [log](evidence/h6-build.txt) |
| Replay H5 | [log](evidence/h6-design-replay.txt) |
| H3/H4/H5 actuales | [media](evidence/h6-media-verify.txt), [composition](evidence/h6-composition-verify.txt), [design](evidence/h6-design-verify.txt) |
| H6 / PNG / panel / mutation replay | [log](evidence/h6-audit-verify.txt) |
| Checkout limpio CRLF | [build/replay/H3–H6 verificadores PASS](evidence/h6-clean-repro.txt) |

Corregidos durante desarrollo: revisión archivada `.ts` fuera de ubicación original (corrección documental del revisor), cobertura mobile confundida con innerWidth expandido por overflow (ahora viewport solicitado/observado separados), evento Enter CDP que no activaba submit nativo (se comprobó Space sin modificar UI), captura de panel antes de decodificar imágenes en iframes (espera explícita de cada frame). Ningún fallo se ocultó como PASS; recibos anteriores incompletos fueron sustituidos solo en evidencia H6 en desarrollo. H3/H4/H5 históricos se preservan.

Reproducción sin recaptura: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify-h6.ps1`. Recaptura: build → `npm run audit:browser` → build (actualiza fingerprints del panel) → `npm run audit:panel` → `npm run audit:verify`. Ninguna etapa requiere API o red de proveedor. `npm run dev` y `/h6/` permiten revisar; las decisiones humanas se descargan solo si ocurren.

Límites: corpus/reference/taste e infraestructura histórica ausentes; raster sin juicio estético humano, cuatro topologías de gramática finita y un fixture; red local/móvil emulado, no dispositivos físicos ni accesibilidad exhaustiva; LCP/INP/CLS/p75 y costos/tokens de sesión no medidos; licencia congelada sin servicio continuo de vigilancia jurídica. Datos, grants y original sin derivados permanecen iguales. Se demuestra infraestructura/ciclo acotado de H6, no aceptación humana, calidad multivertical ni readiness comercial. **Siguiente hito formal: H7**, únicamente después de auditoría PASS y orden del coordinador.
