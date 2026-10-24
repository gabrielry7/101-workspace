# H7 — generalización en cohorte sintética reservada

Entrega de laboratorio del §24 formal. No se declara preparación para producción, estética calibrada ni aceptación humana. Todos los negocios, nombres, hechos comerciales y decisiones de publicación de esta cohorte son **fixtures sintéticos nuevos**, no negocios reales ni evidencia externa.

## Reserva y primera exposición

Se reservaron seis casos y sus hashes en [reservation.json](../fixtures/cohort/h7/reservation.json), commit `3ff5356`, antes de ejecutar planner/proyección y antes de ampliar plataforma. Baseline anterior: `99dfa596ce922721e03330e23f04888fe7216659`. Los JSON de entrada reservados no se ajustaron al observar fallos.

[Primera evaluación](evidence/h7/first-evaluation.json): planner READY 5/6, Unknown CONTENT_BLOCKED. Proyección PASS 1/5 y FAIL 4/5 por primitivas faltantes: amenities/about/service_area (`fact_collection`) y calendario (`schedule`). Esos fallos motivaron cambios comunes de plataforma. Después del ajuste los cinco casos READY proyectan y conservan sus bindings. **La cohorte ya está expuesta para esos ajustes; no se afirma generalización inédita después de tuning.** Una futura medición de generalización inédita necesita otra cohorte independiente.

## Cobertura y plataforma compartida

| Caso | Arquetipos resueltos | Capabilities ejercitadas | Rutas | Vistas browser |
|---|---|---|---:|---:|
| Hotel | lodging | identity, rooms, amenities | 3 | 12 |
| Dentista | appointment_service, regulated_services | identity, service_catalog, professional_profiles, about | 3 | 12 |
| Servicio a domicilio | field_service_and_quote | identity, service_catalog, service_area | 3 | 12 |
| Híbrido | membership_and_classes, product_retail | identity, membership, class_schedule, product_catalog | 4 | 16 |
| Medio UNKNOWN | field_service_and_quote | identity, service_catalog | 2 | 8 |
| Unknown | unresolved | identidad retenida, clasificación pendiente | 0 | 0 |

Registry compartido amplía `fact_collection → FactCollection`, `schedule → Schedule`, `location_information → FactCollection`. Esta última compatibilidad es genérica, pero no se afirma cobertura browser de ubicación en esta cohorte. Hay contratos internos tipados y negativos para bindings, omisión de módulos y calendario fecha/timezone. No cambian planner semántico, taxonomy, las licencias o los inputs históricos.

El renderer común acepta medio autorizado nullable, navegación de módulos genérica y un encabezado principal por ruta. El nuevo gate detecta imágenes/audio/video sin figura de uso vinculado. No hay branches por negocio/arquetipo ni sitios individuales: **0 archivos de código específicos por cliente**. Los seis fixtures, cinco propuestas/contextos y diez planes son datos declarativos de clientes de prueba, contabilizados aparte del código común. No hay dependencias nuevas ni código cliente en los sitios de candidatos.

## Medios, verdad y propuestas

Los cinco casos renderizados no tienen fotografía elegible. Se mantienen huecos documentales, inventario y restricciones visibles; no se inventan fotos ni se toma prestado el grant H3. `media-unknown` conserva asset con derechos UNKNOWN e inspección desconocida y un intento de usage sin grant **rechazado** por gates. No se descarga su URI `example.invalid` y no se renderiza ese asset.

Las cinco parejas de propuestas fueron redactadas realmente por esta sesión Codex, usando sus contextos congelados. [Propuestas](../fixtures/cohort/h7/proposals/) incluyen prompt/context/output/provenance y hashes canónicos comprobados al consumirlas. No son llamadas API ejecutadas por el recorder: proveedor API 0, gasto nuevo 0; tokens/costo de esta sesión **NOT_MEASURED/null**. Familia de modelo identificada por instrucciones de sesión; identificador exacto no disponible. Una extensión **separada** `ArtDirectionV1_1`, schema_version `1.1.0`, explicita `materiality: typography-only`; JSON Schema en `contracts/design/v1.1`. El contrato histórico `ArtDirectionV1` y su schema exportado permanecen idénticos. El consumer acepta ambas versiones y bloquea materialidad de fotografía sin medio y materialidad solo tipográfica con fotografía. No se reinterpretan silenciosamente campos legados.

Sampler contextual usa únicamente Sequence al faltar imagen; dos art directions proponen Flow y Rail. Presupuesto por contexto: 2 propuestas, 12 muestras, 2 render slots, 2 finalistas, 24 KB de salida; total diez planes. Prefilter y selección preservan todas las rutas/módulos, no añaden imágenes ni código.

## Evidencias y límites

[Run browser](evidence/h7/run.json): Edge `154.0.4258.62`, 60 vistas completas de todas las rutas/planes en 1280×900 y 390×844, todas PASS técnicas. Tres negativos sembrados independientes producen FAIL: texto factual alterado, imagen no autorizada y contraste insuficiente. Son fixtures de prueba DOM explícitos; no candidatos aceptados ni fotografías del negocio. Teclado real comprueba skip/disclosure/nav; geometría, contraste, bindings y raster usan observaciones DOM y PNG reales. Raster se decodifica y recomputa de forma independiente con Node; diferencia de redondeo de entropía entre runtimes admite únicamente tolerancia `1e-12`. El negativo de imagen de test puede tener un pixel excluido por la caja de imagen; no afecta el bloqueo de derechos.

Hay diferencia estructural desktop observada Flow/Rail por navegación/frame. En móvil ambos apilan: **no se acredita diversidad estructural móvil** ni preferencia visual. Raster es un instrumento auxiliar de tinta/bordes/entropía, no un score de belleza. El panel humano H6 permanece NOT_COLLECTED.

[Cobertura](evidence/h7/coverage.json) conserva conteos, bytes locales por caso y costos no medidos. Run observado: 10 planes, 63 vistas incluyendo tres negativos; duración exacta en `run.actual.wall_seconds` para esa corrida browser. No es costo total del hito ni latencia comercial. LCP/INP/CLS y campo p75 no medidos; bytes son locales sin compresión. Ningún backend, integración comercial, benchmark de proveedor o deployment se hizo.

## Reproducción y preservación

`powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify-h7.ps1` ejecuta tests/check/build y replays/verificadores H3–H7. `npm run cohort:audit` recaptura navegador local; `npm run cohort:verify` verifica recibo actual/HTML/CSS/PNG y reevalúa gates/selección; `npm run cohort:replay` exige JSON derivado idéntico sin llamadas creativas. **No ejecutar** los recorders como parte de replay: reserva y autoría de propuestas son operaciones únicas, no simulaciones regeneradas para aparentar evidencia.

281 tests PASS, check 0 errores/warnings/hints y build 90 rutas. Reproducción inicial de índice Git limpio, conversión CRLF normal y node_modules compartidos: check/build/replays/verificadores PASS ([clean repro](evidence/h7-clean-repro.txt)); no necesita API. H3 original/grant, H4 y H5 HTML/CSS/PNG/contextos, H5 search hash y H6 browser/history/rollback/panel hashes pasan los verificadores históricos sin recapturar esos hitos. [Validación](evidence/h7-validation.txt), [tests](evidence/h7-tests.txt), [check](evidence/h7-check.txt), [build](evidence/h7-build.txt), [browser](evidence/h7-browser.txt).

## Corrección tras revisión independiente FAIL H7-R1

La entrega `3c8abc5` omitió QA del índice `/h7/`: su wrapper `main` duplicaba el main aportado por Foundation. Se cambió a `div`. El harness añade dos vistas del índice desktop/móvil, independientes de las 60 vistas de candidatos; consulta DOM y árbol AX real, verifica exactamente un main/h1, skip visible con Tab y activado con Enter al main `#contenido`, y un enlace candidato alcanzado mediante Tab y activado con Enter. Ambos índices reciben `LAB_INDEX_PASS`; capturas `index-desktop.png` / `index-mobile.png`, observaciones y nodos AX quedan en `run.index_receipts`. El verificador también comprueba el HTML actual, hashes de CSS/PNG y reevalúa esos gates. Dos tests negativos impiden aceptar main anidado/duplicado o skip/nav inaccesibles aunque candidatos pasen.

Se eliminó `commercial_audit` de los recibos H7: duplicaba LAB y no era una medición COMMERCIAL. Solo se entrega auditoría LAB; la ausencia del campo redundante se exige en verify. Contratos/inputs reservados, primera evaluación y artifacts H3–H6 permanecen intactos. La corrida ahora cuenta 63 vistas de candidatos/negativos **más 2 índices**, y registra ambos conteos separados junto a wall time. Reauditoría independiente pendiente; no se inicia H8 por esta autocorrección.

Resultado propuesto para auditoría independiente: infraestructura H7 cumple cobertura multiarquetipo sintética y ausencia de forks, con adaptación de registry y fallos iniciales preservados. Cierre comercial/producción, generalización externa inédita y calibración estética humana siguen pendientes. H8 no se inicia hasta PASS independiente del coordinador.
