# Coordinación autónoma de hitos

El usuario autorizó el 2026-10-08 continuar por el roadmap existente sin solicitar aprobación ordinaria entre hitos. Esta autorización sustituye la pausa anterior antes de H5; no autoriza gastos nuevos, despliegues de producción, operaciones destructivas ni cambios sustanciales de alcance. Esas decisiones y los bloqueos imposibles de resolver vuelven al usuario.

## Protocolo

1. El implementador entrega un commit, un informe del hito y evidencia reproducible. No declara implementado lo simulado o pendiente.
2. El revisor comprueba de forma independiente el estado de Git, el informe frente al código y artefactos, las pruebas pertinentes y los criterios de cierre de `pipeline.md`.
3. Con **FAIL**, comunica hallazgos verificables y pide correcciones antes de avanzar. Con **PASS**, registra el alcance exacto aprobado y comunica al coordinador que puede iniciar el siguiente hito del roadmap.
4. El coordinador conserva el orden H0–H10 y la frontera entre laboratorio y producción. Cada nuevo hito se revisa antes de iniciar el siguiente.

### Coordinación nativa en esta sesión

El usuario solicitó reemplazar la mensajería MCP entre conversaciones independientes por subagentes nativos el 2026-10-08. Las conversaciones anteriores se conservan como historial y se comprobaron inactivas antes de empezar; no se les asigna trabajo nuevo. No se utiliza `codex_tui.send_message_to_thread`.

El coordinador `/root` utiliza `/root/implementador` y `/root/revisor`. Solo el implementador escribe código y evidencias durante implementación; el revisor prepara criterios en lectura y espera la entrega. Durante auditoría el implementador queda sin editar y el revisor ejecuta comprobaciones independientes. El coordinador mantiene este registro. Cada traspaso identifica el commit evaluado; FAIL devuelve correcciones al mismo implementador, PASS permite el siguiente hito formal dentro del alcance autorizado.

Las herramientas nativas `list_agents`, `spawn_agent`, `send_message` y `followup_task` funcionaron y ambos subagentes confirmaron recepción. Se comprobó el ciclo completo: implementación, commit/evidencias, auditoría independiente, correcciones ante FAIL en H7/H8, reauditoría y avance automático tras PASS. H5–H8 tienen PASS dentro de sus alcances de laboratorio. La continuidad aplica mientras esta sesión está ejecutándose, sin prometer un servicio persistente fuera de ella.

H10 sigue siendo fase posterior fuera del alcance actual (§24); H9 depende de pruebas reales y no permite gastos o adquisiciones nuevos sin autorización.

## Progreso nativo

- Base comprobada: `59f19b3`, árbol limpio; H4 y sus artefactos conservados.
- H5: entrega `58af61e34f15e38342acab5ea477da1fd5c2c667`; **PASS independiente de laboratorio**, revisión `6f81fb0` y aclaración `65218a1`. Se repitieron 254 pruebas, check, build, replay y verificadores H3/H4/H5; recaptura propia de 16 vistas y 28 estrés, con HTML equivalente. Cuatro topologías desktop; diversidad móvil menor. Costos/tokens de sesión no medidos. El fixture exige el piloto autorizado: todavía no demuestra negocio sin medios. [Revisión](reviews/h5-review.md).
- Ciclo nativo comprobado hasta entrega y revisión: acuses, commit y veredicto llegaron por herramientas nativas; no se usó mensajería MCP bloqueada. Gate H5 PASS habilita H6 sin aprobación humana adicional.
- Corrección documental posterior a H5: `ba2954a` cambia la copia del harness de revisión a `.txt`, preservando sus bytes; la evidencia `.ts` había sido incluida por check. No cambió implementación; check vuelve a pasar.
- H6: entrega `94e948b1939e0a5df9ed8b4a22ba714471b6b6db`; **PASS independiente de infraestructura/laboratorio**, revisión `3c1225d24d317d094620f9b3b1be31d5d952c1ba`. Repetidos 272 tests, check, build de 59 páginas, replay y verificadores H3–H6. Recaptura propia de 27 vistas, recomputación raster de 27 PNG y panel de dos vistas/ocho elecciones TEST_SIMULATION. Reparación y rollback comprobados con snapshot/hash/cobertura; comercial NO_ACCEPTABLE_DESIGN. Votos humanos NOT_COLLECTED. [Revisión](reviews/h6-review.md).
- H7: autorizado al mismo implementador tras PASS H6. Cohorte retenida de nuevos arquetipos, híbrido y Unknown/media pobre, sin código de cliente ni forks; debe demostrar ausencia/escasez de medios y al menos cuatro arquetipos. Se conservan los límites de datos ficticios frente a pruebas reales y de laboratorio frente a producción.
- H7 primera entrega `3c8abc53797ede3b8cdebdf901c968beec0c6407`, freeze `3ff5356`; **FAIL independiente** `84fd91c7fe154124b98e0c5393a872404ddea8f8`. 279 tests y 60 vistas de candidatos pasan, pero `/h7/` tiene dos landmarks main anidados, confirmado DOM/AX y no cubierto por esas vistas. Se devuelve al mismo implementador corrección y QA índice desktop/móvil, skip/teclado, antes de reauditar. H8 no está autorizado hasta PASS. [Revisión inicial](reviews/h7-review.md).
- H7 corrección `5f3ff3844ab9ec9b83da40c8eaf142147f83e593`; **PASS independiente de laboratorio**, revisión `9dfae0a47f73602d5cf242b6b84371eff422f301`. Repetidos 281 tests/check/build/replays H3–H7 y QA propia del índice desktop/móvil DOM/AX/un main/skip/navegación/foco/overflow. FAIL original conservado. Cohorte congelada intacta, cuatro fallos iniciales preservados y posterior adaptación común; no se afirma holdout externo ni aceptación humana. [Reauditoría](reviews/h7-correction-review.md).
- H8: autorizado tras PASS H7. Design Lock, reconstrucción sin LLM/adquisición/redecisión probabilística, rollback y regresión de componentes en entorno controlado; aprobación humana y preparación comercial no se presumen por congelar un AST de laboratorio.
- H8 primera entrega `6cc799332f4f4219ae685df959f93b3d534b78a2`; **FAIL independiente** `7fce09c4f453b9db4a43ca96e1a21b81b45bb450`. Rebuild dirigido, 292 pruebas y 56 recapturas propias pasan; equivalencia exacta y rollback entre AST distintos comprobados. Falta en los tres locks el estado/cobertura/referencias hash de auditorías técnicas exigidas por §21.3; approval literal no sustituye evidencia. Se devuelve al mismo implementador contrato/sealer/validator y snapshots de reportes reales, con rechazo de missing/FAIL/inconsistent antes de reauditar. H9 detenido. [Revisión inicial H8](reviews/h8-review.md).
- H8 corrección `ca1a86b048a5c92da9b5a44cb1de423b7c0e3cfd`; **PASS independiente de laboratorio**, revisión `30cbf0ff17de7d23f80849314ee68907e4d47ffa`. Audit_state recuperable vincula reportes reales, contexto/candidato/política/cobertura 4/4/8 y pins de renderer/auditor; nueve negativos propios rechazados. Repetidos 297 tests, check, históricos, tres rebuilds dirigidos y 56 capturas; diez equivalencias de cero píxeles, rollback entre AST/outputs distintos y regresión rechazada. FAIL inicial intacto. Humanos NOT_COLLECTED y excepción LAB conservados. [Reauditoría H8](reviews/h8-correction-review.md).
- H9: evaluar el gate y ejecutar únicamente trabajo verificable sin gasto/adquisición no autorizada. El benchmark exige pilotos y métricas reales; no sustituir costos desconocidos o datos sintéticos por p50/p90 de sitios aprobados. Si faltan evidencias externas necesarias, documentar el bloqueo concreto con revisión independiente. H10 permanece fuera del alcance actual.
- H9 inventario/diagnóstico `85ed75bbe92eedd9489b66605e579025ce21cb62`; revisión independiente `8376e4b2ccf2c5a8249a42fb3085f8759f2e70b0`: **inventario aceptado; H9 BLOCKED_EXTERNAL_EVIDENCE / benchmark NOT_TESTED, no hito completo**. Verificados 26 hashes, check, normalización LF/BINARY y preservación H3–H8. En la evidencia inspeccionada: cero sitios reales aceptados, costos/tokens totales y tiempos humanos desconocidos, sin muestra comparable autorizada multisector; denominador cero y p50/p90 null. [Informe](h9-report.md), [revisión](reviews/h9-review.md).

## Punto de detención y reanudación

La coordinación se detiene tras confirmar independientemente el bloqueo externo de H9. No falta aprobación ordinaria entre hitos: la autorización autónoma sigue registrada. El paso pendiente exige evidencia que no puede fabricarse mediante más código, fixtures, investigación de precios o votos simulados.

Para reanudar H9 se necesitan inputs de pilotos reales autorizados con aceptación vinculada a sitio/versión/fecha/alcance; costos y tiempos humanos atribuibles, monedas/tarifas/intentos fallidos y reparto de gastos compartidos; muestras multisector y roles con permisos efectivos de acceso/automatización/IA/cache/retención/volumen. Pilotos aceptados no requieren despliegue de producción. No se autorizan nuevos gastos o producción por este registro. H10 queda fuera del alcance actual.

Todas las validaciones H5–H8 son de laboratorio: runtime comercial ausente, preferencias humanas sin recoger, costos de sesión no medidos y foto pesada H3 sin permiso de derivados. No se declara preparación para producción. Las conversaciones antiguas, los FAIL iniciales y la evidencia histórica se conservaron; no se usó mensajería MCP entre tareas durante la coordinación nativa.

## Revisión H4

**PASS como laboratorio Astro**, commit `65877747aa526d7e6711142a3df6c6e8e5deca0b`. En la revisión independiente, HEAD coincidió con el commit y Git estaba limpio. Se inspeccionaron las seis capturas principales de Editorial, Split y Rail. Se repitieron 239/239 pruebas, check, build, `media:verify` y `composition:verify` con éxito; el informe y sus recibos registran doce vistas auditadas. Véanse [informe H4](h4-report.md), [pruebas](evidence/h4-tests.txt) y [verificación de composición](evidence/h4-composition-verify.txt).

El PASS confirma tres estructuras distintas con los mismos datos y medio permitido, bindings y avisos preservados. En móvil la diferencia visual es menor. `@101/site-runtime` no está disponible aquí; Astro sigue siendo laboratorio. Permanecen el hueco documental de la oferta, la fotografía original de 2,35 MB sin permiso para derivados y la preferencia visual humana pendiente. Este PASS no acredita publicación comercial, rendimiento móvil real ni generalización multivertical.

**Siguiente hito autorizado por el protocolo:** H5 — dirección artística por LLM y búsqueda probabilística, sujeto a sus propias pruebas y a una nueva revisión PASS/FAIL. El revisor no implementa H5.
