# Revisión independiente de B1 — catálogo y contexto

Fecha: 2026-10-13 (America/Bogota). Entrega revisada: `43602823fda67d63937e86ddc0bf0ab457417f78`, correcciones `d17d1ba51faee94637b78588e6c46ca432a1f0cf` y `2091e5e33106df330b2f34f53c4622ff64d5fdd5`.

**Veredicto: PASS técnico acotado de B1, listo para revisión humana.** El catálogo y el diagnóstico cubren el vocabulario actual de 47 capacidades con 107 niveles y 208 definiciones compartidas. La clasificación contextual usa categorías, descripciones, afirmaciones y ofertas aprobadas con alcance/evidencia; conserva incertidumbre y no convierte arquetipos en capacidades operativas. Los contratos V1 y el comportamiento H2 por defecto permanecen compatibles. Este PASS no aprueba la utilidad final del catálogo, la estética, integraciones, derechos de medios, H8 completo ni H9.

## Comprobación propia

Desde el commit final y con Node portátil 24.21.0 ejecuté `tests/b1.test.ts` y `tests/b1-replay.test.ts` (**44/44 PASS**), `scripts/b1-fixtures.ts --verify` (catálogo y 11 escenarios byte a byte), y `scripts/b1-planner-replay.ts` con `--permission --allow-fs-read=*` (nueve archivos H2 iguales sin permiso de escritura). Repetí `npm test`: **348/349**, con el único fallo `tests/lock-files.test.ts` porque el Edge global produce `LOCK_BROWSER_MISMATCH` antes del error de auditoría esperado. `npm run check` dio cero diagnósticos; `npm run validate` pasó; `npm run build` generó **103 páginas**.

Repetí `b1-verify` para `r2-browser/r2-final` y `r2-clean-browser/r2-clean`: **28 vistas en cada reconstrucción**, 16 HTML H8 iguales, 1.330 archivos protegidos y gates de DOM/bindings/teclado/lectura correctos. `b1-compare` confirmó **28 pares** con HTML, RGBA y observables funcionales iguales. Inspeccioné las muestras móviles de catálogo y restaurante; son un inspector legible, no una demostración de calidad estética de sitios de clientes. Git quedó limpio tras mis pruebas.

## Hallazgos cerrados durante la revisión

1. La primera entrega llamaba `planner-replay` a un generador que reescribía los derivados H2. R1 lo sustituyó por comparación de bytes de solo lectura, con negativos de corrupción y guardas de mtime. Los recibos B0 originales conservan ese límite histórico; R1/R2 no afirman haberlos revalidado.
2. Un precio ajeno de la misma sucursal activaba erróneamente un faltante de moneda del menú. R1 limita `PRICES_PRESENT` a ofertas elegibles vinculadas y añade regresión.
3. Un medio presente, sin uso declarado para la función, activaba permisos opcionales de horarios. R2 mantiene el requisito en el catálogo pero deja `if_used` condicionado hasta contar con un vínculo H3 explícito; gallery conserva su gate obligatorio de archivo y derechos. Añade regresión y recaptura las vistas cuyo diagnóstico cambió.

## Límites y siguiente decisión

La política textual ES/EN es finita y se probó con fixtures sintéticos; no se midió precisión en negocios reales ni se integró `101-world-model`. El inspector puede ser denso y no representa una web final. `READY` sólo valida el plan emitible; solicitud, enlace y reserva confirmada siguen separados y ningún backend está conectado. El vínculo medio→uso/función, la adquisición autorizada y la inspección real pertenecen a un bloque posterior. H8 aún falla con el navegador global actualizado; H9 permanece `BLOCKED_EXTERNAL_EVIDENCE / NOT_TESTED`.

La revisión humana puede comprobar ahora si las fichas y los responsables explican con claridad qué falta, qué funciona y qué se podría agregar. La [propuesta de B2](b2-proposed-prompt.md) queda **sin autorización de ejecución** hasta que el usuario la apruebe expresamente.
