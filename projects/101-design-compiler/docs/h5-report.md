# H5 — Dirección artística y búsqueda declarativa

**PASSED como implementación de laboratorio, pendiente de auditoría independiente.** Desde tres hipótesis artísticas redactadas por el LLM activo de esta sesión, el motor explora 24 muestras, conserva seis candidatos únicos y preselecciona cuatro topologías diferentes sobre el fixture congelado H4. Los 16 renders de navegador y 28 comprobaciones responsive/texto pasan; no se declara preferencia humana ni preparación para producción. H6 no se inicia por esta entrega.

Base: `58757961d4efb5807bf35efee4af72fe71276018`, Git limpio y 239/239 pruebas antes de editar. Se leyeron pipeline, especificación V0.2 (secciones 0–30), h0-findings, H2–H4 y coordinación. Se conserva el roadmap formal §24 y autorización de avance automático, con revisión antes del siguiente hito. No se encontraron AGENTS aplicables.

## Qué se reutilizó y añadió

Se reutilizan Foundation Astro, contenido proyectado/validado H2, las primitivas Identity/OfferingCollection/MediaFigure/AuditPanel H4, derechos y paquete físico H3, observer DOM, auditoría de bindings y harness Edge local. `@101/site-runtime`, corpus de referencias y motores históricos no están disponibles: **MISSING / NOT_TESTED**, no simulados. Se añaden AST, contratos Zod/JSON Schema, un compositor acotado, recorder de propuestas de sesión y montajes H5. Ninguna dependencia ni backend nuevo.

| Pieza | Ruta |
|---|---|
| Contratos 1.0.0 separados | `src/design/contracts.ts`, `contracts/design/v1/` |
| Contexto, prefilter, sampler, distancia/selección | `src/design/search.ts` |
| Propuestas/contexto/prompt/provenance resueltos | `fixtures/design/h5/` |
| Recorder único del output del LLM | `scripts/record-h5-proposals.ts` |
| Consumidor y exportación/replay | `scripts/load-design-lab.ts`, `scripts/design-fixtures.ts` |
| AST a componentes compartidos y CSS de enums | `src/components/composition/DesignComposition.astro`, `src/design/styles.css` |
| Montajes equivalentes de identidad/oferta | `src/pages/h5/` |
| Browser y evidencia actual | `scripts/audit-designs.ts`, `scripts/verify-designs.ts`, `docs/evidence/h5/` |
| Pruebas de invariantes y DOM | `tests/design.test.ts`, `tests/schema-export.test.ts` |

Los únicos cambios anteriores son scripts npm/export, tests de schemas y un argumento opcional de función de ruta en auditRender. Su valor por defecto H4 conserva comportamiento. Foundation, componentes factuales, fuentes/media H3, contratos H0–H3, taxonomía, planners, fixtures anteriores y lockfile no cambian.

## LLM real y procedencia

Las tres direcciones (`typographic-pause`, `balanced-dialogue`, `indexed-field`) son propuestas reales redactadas por Codex en esta sesión tras leer datos/restricciones. El recorder conserva su JSON literal; **no es una llamada LLM**, endpoint simulado ni un generador de respuesta ficticia. `loadDesignLab` y build solo consumen el output registrado; no ejecutan recorder ni creatividad. Una nueva generación necesita nuevas propuestas de sesión o un productor externo autorizado que entregue el mismo contrato, no reutilizar el recorder como supuesta API.

[Prompt](../fixtures/design/h5/prompt.txt), [contexto](../fixtures/design/h5/context.json), [output](../fixtures/design/h5/llm-output.json), [procedencia](../fixtures/design/h5/provenance.json). La familia GPT-6 proviene de instrucciones de sesión; el identificador exacto no está expuesto y se registra `null`. Tokens y coste real de sesión: **desconocidos / no medidos**, no cero. Cero llamadas nuevas a proveedor, cero gasto nuevo, cero adquisición de medios. No existe corpus autorizado de referencias: se declara ausente, sin atribuir investigación estética externa. El prompt utiliza metadatos de la inspección H3 existente; no envía el archivo a una API de visión ni solicita clasificación/embedding/edición.

Hashes canónicos comprobados por consumidor:

| Artefacto | SHA-256 |
|---|---|
| Contexto congelado | `ab9dc6c2b2cf325f07cd4afd45de0ce467184a3b1b5c54b55c0acda8c3056f38` |
| Output LLM | `926793ee4fd900d434e15ea25c2140107db70966c652681312305ba5c1a0cbc6` |
| Search resuelto | `0653ba6fa5e21655b94090bbbf794d2678b3262df544ae6643105064e13b7cb7` |
| SitePlan H2 | `4095293f66936680f0de4f49dc03410ec436154e89646da514a5307af8fa5f22` |
| Contenido H4 | `6fbe1021d1e6fd1249c04d4ebf99df477ee49bdb70e3373730d826f7b97d4c8b` |
| Manifest H3 | `233a731c012e82d0c78836aa715dd215083f9e3e51c0de282283e01378d1d948` |

Prompt/output/context/provenance se verifican antes de consumirlos. IDs/fechas/hash no son una autenticación del proveedor; provenance es un recibo de esta sesión, con sus límites explícitos.

## Presupuesto, topología y filtros

Presupuesto: **3 propuestas**, output máximo **24.000 B**, **24 intentos baratos**, **4 slots de planes para compilar**, **4 finalistas**, cero proveedor/gasto nuevo. Seed local `1010508`; no se promete recrear una respuesta LLM desde seed. Se guardan propuestas, candidatos, rechazos, pesos y planes completos en [resultado](../data/derived/design-v1/restaurante-search.json).

Cada dirección propone dos árboles coordinados; nunca se elige operador independiente por módulo o categoría. La raíz `Flow|Rail` organiza navegación y contenido; su hijo `Sequence|Split` organiza módulos y medio. La combinación **Rail/Split** es una nueva composición anidada, no solo reselección de las tres páginas H4. Los parámetros son enums de tokens/ritmo/tipografía/ancho; no JS/CSS libre, componentes arbitrarios, dependencias, texto de negocio o crops.

El sampler condiciona pesos en presencia de medio y densidad de módulos/ofertas: Split requiere medio contextual; páginas densas priorizan Sequence. Son **heurísticas no calibradas**, registradas, no probabilidades aprendidas. Las topologías proceden del concepto global; los tokens mantienen su coherencia. Se validan schema/contexto/rutas/módulos y el gate de derechos/pertinencia antes de asignar render. Estimaciones baratas de complejidad, JS cero y anchura de texto para 360/768/801/1280 se etiquetan como heurísticas del registry; no son mediciones de navegador. No optimizan una puntuación ficticia de belleza.

Resultado: seis candidatos distintos de dirección/topología; 18 intentos duplicados rechazados antes de render. Farthest-first escoge cuatro firmas topológicas, ignorando colores/fuentes. Distancias por relación raíz/hijo: 0,5 o 1 entre finalistas. Una alternativa cosmética con la misma estructura no consume un slot. Un input sin propuestas válidas devuelve `NO_ACCEPTABLE_DESIGN` y cero slots. Esta salida preseleccionada se llama `FINALISTS_READY_FOR_BROWSER`, no sitio validado; la auditoría posterior emite PASSED/FAILED.

| Finalista | Topología / concepto | Imagen desktop x/y/ancho | Capturas principales |
|---|---|---|---|
| candidate-01 | Rail/Sequence · pausa tipográfica | 416,5 / 378,36 / 640 px | [desktop](evidence/h5/candidate-01-desktop.png), [móvil](evidence/h5/candidate-01-mobile.png) |
| candidate-02 | Flow/Split · diálogo | 617,53 / 212,39 / 593,08 px | [desktop](evidence/h5/candidate-02-desktop.png), [móvil](evidence/h5/candidate-02-mobile.png) |
| candidate-04 | Flow/Sequence · pausa tipográfica | 312,5 / 462,36 / 640 px | [desktop](evidence/h5/candidate-04-desktop.png), [móvil](evidence/h5/candidate-04-mobile.png) |
| candidate-05 | Rail/Split · diálogo | 726,48 / 128,39 / 484,13 px | [desktop](evidence/h5/candidate-05-desktop.png), [móvil](evidence/h5/candidate-05-mobile.png) |

El concepto indexed-field participó con dos candidatos; no obtuvo slot porque sus topologías ya estaban representadas. No se lo declara peor visualmente. Se inspeccionaron las ocho capturas principales: identidad legible, foto íntegra, créditos/huecos visibles y diferencias desktop claras. En móvil el reflow reduce diversidad a secuencias y diferencias de navegación/ritmo: no se afirma cuatro macroestructuras móviles distintas. Oferta mantiene su página y scope, sin foto ni nombre de sede inventado.

## Veracidad y medios

Todos los módulos se conservan exactamente una vez por ruta, con orden original y bindings intactos. No se mueve la oferta de sucursal a home para fabricar riqueza visual. Los únicos textos factuales siguen siendo el nombre ficticio y “Ítem de menú de prueba”. No precios, menús detallados, capacidad nueva, botones de reserva/compra, hechos médicos ni claim de marca generado. Principios y rationale LLM no se renderizan como copy factual.

Se usa el mismo original JPEG de **2.351.102 B**, SHA `ffdb883d56a41ba9a03a51fb7d1bdf8f0b9e30d3946eda180b750620a17c3715`. Cliente/proyecto/uso/página/módulo/rol ATMOSPHERIC H3 permanecen iguales; prefijos H5 son montajes locales. Sin crop, overlay, transformación o derivado. Crédito/etiqueta/aviso de no respaldo, alt contextual y hueco documental visible pasan auditoría en cada vista. Derechos desconocidos o medio en la página de oferta se rechazan. El hueco documental sigue bloqueado.

## Pruebas y evidencia

Se ejecutaron **254/254 pruebas**: 239 anteriores y 15 nuevas (12 de diseño más 3 schemas). Negativos reales: JS/CSS/dependencias/campos/operadores arbitrarios, versiones incompatibles, pérdida/duplicación/reordenamiento de rutas/módulos, cambio de contexto, medio desconocido/otra página/crop/derechos UNKNOWN, output excesivo, gasto/seed inválidos, duplicados, cosmética sin diversidad y pérdida de DOM. El cambio de densidad altera los pesos contextuales; replay da el mismo resultado con datos/seed/budget.

| Comprobación final | Resultado | Evidencia |
|---|---|---|
| Exportación | 21 schemas; previos intactos | [log](evidence/h5-contracts-export.txt) |
| Pruebas | 254/254 | [log](evidence/h5-test.txt) |
| Check | 0 errores/warnings/hints | [log](evidence/h5-check.txt) |
| Build/validación | 18 páginas; H0/H2/H3 correctos | [log](evidence/h5-build.txt) |
| Replay | Search idéntico sin LLM/API | [log](evidence/h5-design-replay.txt) |
| Medios H3 | Paquete/HTML/avisos correctos | [log](evidence/h5-media-verify.txt) |
| Composición H4 | 12 vistas y hashes originales correctos | [log](evidence/h5-composition-verify.txt) |
| Verificación H5 | HTML/CSS/PNG actuales, bindings y hashes | [log](evidence/h5-design-verify.txt) |
| Navegador | 16 PASSED, 28 estrés PASSED | [recibo](evidence/h5/browser-audit.json) |
| Checkout limpio CRLF | Build/replay/3 verificadores PASS; HTML/CSS/PNG/prompt/output iguales | [recibo](evidence/h5-clean-repro.json) |

**4 slots** significa cuatro planes finalistas compilados en una build. Las mediciones reales son **16 vistas con captura** (4 planes × 2 rutas × 2 viewports), más **28 vistas de estrés** (4 × 7 anchuras, sin PNG), no cuatro screenshots. Edge `154.0.4258.62`, captura final `2026-10-09T01:23:28.352Z` (8 de octubre local Bogotá); móvil emulado, escala 1. Estrés 320 px con texto 200%, 360/768/801/1024/1440/1920. Reduced motion, sin animaciones. Skip link/Tab/Enter, foco de 3 px, disclosure Space, navegación real por Enter, AX landmarks, decodificación/hash servido del JPEG y targets táctiles pasan. Contraste mínimo observado **7,26:1**. No certificación WCAG completa.

Transferencia observada sin compresión: home **2.365.586–2.365.597 B**, oferta **13.770–13.781 B**, cero JS cliente/fuentes/embeds externos. No métricas de campo p75 ni pruebas de red móvil real. La imagen pesada bloquea una afirmación de rendimiento comercial satisfactorio; el permiso limitado no autoriza optimizarla aquí.

## Fallos corregidos y límites

1. El ID SitePlan upstream usa `:`; el primer schema local lo rechazaba. Se conserva como referencia opaca y comparación exacta, sin convertirlo en ruta.
2. TypeScript detectó la inferencia estrecha de suma de pesos; se tipó reduce a number.
3. Una URL de fixtures relativa a import.meta.url se resolvía contra el bundle prerender Astro. Se lee desde la raíz de ejecución como el loader existente.
4. Importar el CSS H4 desde rutas H5 alteró el particionado/nombre del asset CSS y los hashes HTML H4. H5 consume las dos gramáticas de source **como strings fijos e inline**, sin CSS generado por LLM. Esto conserva los bytes/capturas históricos H4 y evita recapturarlos para ocultar una regresión. Los hashes HTML H5 fijan su CSS inline; Foundation externo, si existe, queda fijado por recibo. Se normaliza CRLF en esos strings y se fija LF en propuestas/prompt/evidencia H5; el checkout con core.autocrlf=true comprobó 27 archivos equivalentes.

Gramática finita experimental, sin certificación multivertical ni runtime comercial. Propuestas de sesión reales registradas, no servicio autónomo permanente de generación LLM ni API de pago configurada. Falta corpus autorizado, preferencias humanas, Safari/Firefox/dispositivos físicos, frescura jurídica permanente, optimización de medios permitida y costo real instrumentado. Seeds reproducen sampler local; no respuesta LLM. No se usa una preferencia humana inventada ni se declara producción por tests.

Reproducción: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify-h5.ps1`, con Node/dependencias locales del lockfile. `npm run design:audit` recaptura en Edge y cambia fechas/píxeles; `design:verify` compara bytes actuales sin red/recaptura. `npm run dev` abre `/h5/`. El siguiente cambio previsto es **H6**, critic/auditorías/mutación/torneo, solo después del PASS independiente y orden del coordinador.
