# Reauditoría H7 — corrección de H7-R1

**PASS — laboratorio multiarquetipo sintético, sin preparación para producción.** Commit corregido auditado: `5f3ff3844ab9ec9b83da40c8eaf142147f83e593`. HEAD coincidía y Git estaba limpio al inicio. Revisor nativo `/root/revisor`; no modificó implementación ni coordinación. El [FAIL inicial](h7-review.md) y toda su evidencia permanecen intactos en `84fd91c`.

## Corrección verificada

El índice usa ahora un `div` dentro de Foundation, que aporta el único main. Se añadió el gate compartido `src/audit/index.ts`, dos pruebas negativas de main/heading/skip/navegación y dos recibos reales de entrada al harness/verificador H7. Se eliminó el campo `commercial_audit` duplicado que reutilizaba LAB; no se presenta como medición comercial.

Repetí `scripts/verify-h7.ps1`: **281/281 tests**, check **0 errores/warnings/hints**, build **90 páginas**, replays y verificadores H3–H7 correctos, incluidos hashes/PNG/gates de las 60 vistas de candidatos, tres negativos esperados y dos índices. [Log propio](h7-correction/verification.txt).

La comprobación propia del índice usa navegador real y una fuente independiente de la función del harness de entrega. En desktop 1280×900 y móvil 390×844 confirmó:

- **Un main en DOM, ningún main anidado, un main no ignorado en AX tree y un h1.**
- Skip link visible con Tab y outline de 3px; Enter activa `#contenido`, cuyo target es MAIN.
- Un enlace candidato alcanzado por Tab y activado por Enter; la ruta destino carga `.lab`.
- Diez enlaces visibles dentro del ancho; sin overflow horizontal, documento 1265px desktop y 390px móvil.

[Recibo propio](h7-correction/index-run.json), [fuente como texto](h7-correction/index-source.txt), [log](h7-correction/browser-run.txt). Se inspeccionaron las [capturas desktop](h7-correction/index-desktop.png) y [móvil](h7-correction/index-mobile.png): estados de cinco casos READY y Unknown CONTENT_BLOCKED legibles, sin texto cortado. H7-R1 queda resuelto y cubierto contra regresión.

Git diff confirmó que reserva/inputs/propuestas, primera evaluación, H3–H6 y evidencia/informe del FAIL inicial no cambiaron en esta corrección. El nuevo build conserva hashes actuales de los candidatos; el cambio es índice, QA y eliminación del campo redundante. No fue necesario repetir una segunda recaptura completa de 63 candidatos ya capturados independientemente en la revisión inicial, porque el renderer/candidatos/contextos no cambiaron; se repitieron sus verificadores y la QA nueva del índice.

## Alcance y continuación

Se ratifican los hallazgos favorables y límites de la revisión inicial: freeze verificable, baseline independiente 1/5→5/5 con cuatro fallos iniciales preservados, componentes genéricos, materialidad 1.1 typography-only, medios ausentes/UNKNOWN bloqueados sin préstamo de grant y Unknown sin sitio. La cohorte sintética quedó expuesta tras ajustar registry; no se afirma generalización externa inédita, preferencia humana ni producción. Móvil apila, diversidad estructural móvil no acreditada; runtime comercial, estética calibrada, red/campo y costos de sesión siguen pendientes/no medidos.

No quedan hallazgos bloqueantes del slice H7. El coordinador puede iniciar **H8 — Design Lock y reconstrucción**, conforme al roadmap y autorización registrada, sin LLM ni nuevos medios en rebuild. H9 necesitará pilotos reales y costos por sitio aprobado; no podrá cerrarse con esta cohorte sintética o tokens/costos null. H10 permanece fuera del alcance actual.
