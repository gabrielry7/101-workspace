# Revisión independiente H6

**PASS — infraestructura y experimento de laboratorio; aceptación humana pendiente.** Commit auditado `94e948b1939e0a5df9ed8b4a22ba714471b6b6db`. HEAD coincidía y Git estaba limpio al inicio. Revisor nativo `/root/revisor`, con exclusividad de outputs; no corrigió implementación ni modificó coordinación.

## Comprobaciones repetidas

Se inspeccionaron informe, diff, contratos, nueve familias de evaluación, mutator, medición raster y decoder PNG, preferencias/panel, loaders, renderer, pruebas y verificadores. Se usó el roadmap formal §24 y los límites registrados de H5/H6.

`scripts/verify-h6.ps1`: **272/272 tests**, check **0 errores/warnings/hints**, build **59 páginas**, replay H5 y verificadores H3/H4/H5/H6 correctos. [Log propio](h6/verification.txt). La reconstrucción actual conserva los hashes históricos comprobados por esos verificadores; no se recapturaron ni alteraron sus recibos.

Se ejecutaron copias del harness desde `.tools/h6-review`, cambiando únicamente imports y destino de evidencia. Es una nueva ejecución independiente del harness compartido, no otro auditor implementado desde cero. Las copias se conservan como texto, excluidas de TypeScript: [browser](h6/audit-h6-source.txt), [panel](h6/audit-h6-panel-source.txt), [replay](h6/verify-h6-source.txt).

La recaptura independiente produjo **27 vistas**, con los FAIL esperados para los defectos y PASS de laboratorio para baseline/reparación/restauración; [run propio](h6/run.json), [log](h6/browser-run.txt). Se recapturó el panel en dos vistas, con **8 elecciones TEST_SIMULATION**, estado humano **NOT_COLLECTED**, reset correcto y cero escrituras externas: [recibo](h6/panel-audit.json), [log](h6/panel-run.txt). El replay propio decodificó y recomputó los píxeles de los **27 PNG**, además de gates/hashes/mutaciones/panel: [log](h6/independent-replay.txt).

Cinco sondas adicionales del revisor confirmaron separación de viewport solicitado/observado, exclusión por hash de candidato corrupto aun con cobertura completa, política incompatible de mutación, bloqueo de pérdida de crédito aun con raster intacto, y rechazo de contexto/screenshot/simulación de preferencia. El objeto usado en la prueba de schema es **REVIEW_TEST_ONLY**, no voto humano. [Resultados](h6/probes.json), [fuente](h6/probes-source.txt).

## Gates, reparación y rollback

| Criterio | Evidencia / juicio |
|---|---|
| Nueve familias | Input/capabilities/semantic/rights/geometry/a11y/performance usan invariantes y observaciones. Visual/diversity de una vista quedan NOT_MEASURED; selección completa compara estructura. No se finge nueve evaluadores estadísticos independientes. PASS. |
| Fallos sembrados | Overflow real, texto factual falso, crédito eliminado y contraste inválido emiten FAIL con código, familia, selector, ruta, viewport y captura. Verdad/derechos/a11y críticas no se compensan con raster. PASS. |
| Viewport solicitado/observado | Antes y peor en móvil: solicitado **390**, observado/documento **1308**, gate **FAIL**; el report y cobertura conservan solicitado 390. Después/restaurado: solicitado/observado/documento **390**, PASS. No se normaliza la expansión para ocultar overflow. PASS. |
| Reparación acotada | Critic propone FLUID_MEASURE para `.identity`; solo cambia el enum de medida, preservando plan/hechos/medios. Dos errores antes y cero después, nuevos renders y KEEP_REPAIR. PASS. |
| Rollback | Mutación peor introduce overflow, juicio ROLLBACK; snapshot completo y hash recuperados, dos renders restaurados PASS. Comparación exige iguales rutas semánticas, viewports solicitados, políticas y hashes; nuevos códigos/familias en otra ruta/viewport impiden KEEP. PASS. |
| Ningún diseño aceptable | Selección exige toda cobertura. Conjunto fallido y política comercial terminan NO_ACCEPTABLE_DESIGN; cuatro finalistas baseline quedan NEEDS_HUMAN_REVIEW. PASS. |
| Raster real | Canvas procesa PNG y máscara excluye el medio original; decoder Node recomputa 27 medidas. Tinta/bordes/entropía son auxiliares sin belleza calibrada ni análisis semántico de stock. PASS. |
| Panel y votos | 24 pares equivalentes en ruta/viewport, orden contextual registrado; A/B/TIE/NONE y descarga local por acción explícita. Simulaciones son rechazadas por consumidor de preferencias humanas. No votos reales ni ganador. PASS de infraestructura. |

Se inspeccionaron visualmente las capturas nuevas de before/repair/worse/restored móvil y ambos paneles. Antes/peor exhiben reducción del contenido y área vacía asociadas a expansión móvil; reparación/restauración recuperan lectura normal. Avisos, créditos, hueco documental y diagnóstico visible permanecen. El panel desktop usa scroll horizontal para comparar dos iframes de 1280px; móvil se refiere al viewport de candidato 390px dentro del panel de QA, no a una prueba completa del panel en teléfono físico.

## Límites y continuación

No hay hallazgo bloqueante reproducible en el alcance H6 actual. El mutator solo tiene una corrección de medida; no demuestra reparaciones universales. La detección de nuevos fallos en el juicio usa ruta semántica/viewport/familia/código, sin comparación fina de selector dentro de una misma vista; es suficiente para esta mutación acotada, pero ampliar mutaciones requerirá mayor detalle y pruebas. El conjunto fallido diagnóstico tiene cobertura incompleta por entrada; la exclusión comercial sí se prueba con cobertura completa y fallos reales de bytes.

La política LAB permite explícitamente el original de 2.351.102 B; COMMERCIAL bloquea la home por bytes. LCP/INP/CLS/p75 no medidos. La licencia y contexto siguen congelados, sin servicio de vigilancia jurídica. Runtime y critic/mutator históricos ausentes; implementación local identificada correctamente. Corpus, preferencias humanas, red real, dispositivos físicos, accesibilidad exhaustiva y generalización multivertical pendientes. No se repitió el checkout limpio CRLF adicional de la entrega; se repitieron rebuild y verificaciones actuales más recaptura independiente.

H6 demuestra infraestructura y ciclo de laboratorio, **no torneo humano completado, excelencia estética ni producción**. H7 deberá probar la cohorte retenida, al menos cuatro arquetipos distintos y casos Unknown/media pobre o ausente, sin forks de cliente. El coordinador puede iniciar H7 previsto bajo la autorización existente y sus límites; este revisor no implementa ni inicia ese hito.
