# Revisión independiente H5

**PASS — laboratorio Astro, sin aprobación de producción ni preferencia humana.** Commit auditado: `58af61e34f15e38342acab5ea477da1fd5c2c667`; base comparada: `58757961d4efb5807bf35efee4af72fe71276018`. Revisor nativo `/root/revisor`, distinto del implementador. HEAD coincidía y Git estaba limpio antes de crear los artefactos de esta revisión. Se mantuvo exclusividad de ejecución y no se corrigió implementación.

## Evidencia independiente

Se leyó la especificación V0.2, el roadmap formal §24, h0-findings, H4, coordinación, informe H5, diff, contratos, búsqueda, recorder/provenance, consumidor, render, estilos, tests y verificadores. La excepción de propiedad Git se resolvió con `git -c safe.directory=C:/Users/gabri/101-design-compiler`, sin modificar configuración global.

Se ejecutó `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify-h5.ps1`: **254/254 pruebas**, check con **0 errores/warnings/hints**, build de **18 páginas**, replay y verificadores H3/H4/H5 correctos. [Log propio](h5/verification.txt).

Se repitió el harness de navegador desde una copia temporal bajo `.tools/h5-review/`, cambiando únicamente imports y destino a `docs/reviews/h5`. Es una ejecución independiente del harness compartido, no una segunda implementación del auditor. La evidencia histórica H3/H4/H5 quedó intacta. La [copia ejecutada](h5/audit-source.txt) permite revisar exactamente el procedimiento. Se conserva como texto de evidencia para excluirla del compilador TypeScript; el cambio de extensión preservó su SHA-256 `c310e2a60445386941f43d8f207cd814e452f55478a5dd64629fa8dc82993852` y todos sus bytes.

Resultado: **16 vistas PASSED**, **28 vistas de estrés PASSED**, cero errores; Edge 154.0.4258.62, fecha UTC `2026-10-09T01:28:22.722Z`. Todos los hashes HTML coinciden con la entrega. Las nuevas capturas tienen sus propios hashes; no se promete identidad universal de PNG. Contraste mínimo calculado **7,26:1**. [Recibo propio](h5/browser-audit.json), [log](h5/browser-run.txt), [resumen](h5/summary.json).

Se inspeccionaron visualmente las ocho capturas principales de la entrega, más capturas nuevas de Rail/Sequence, Rail/Split, Flow/Split móvil y oferta Flow/Sequence. Se observan título/foto legibles, créditos y aviso de no respaldo, hueco documental visible y ausencia de falsas operaciones. No clipping u overflow detectado en las comprobaciones. Las pruebas de teclado, navegación entre las dos rutas, disclosure, landmarks y medio original servido pasan.

## Criterios H5

| Criterio | Verificación / resultado |
|---|---|
| Dirección artística real y declarativa | Tres hipótesis redactadas por el LLM de sesión y registradas como datos; recorder identificado expresamente como recorder, sin endpoint/API ficticios. Prompt/context/output/provenance concordantes; modelo exacto, tokens y costo no expuestos quedan null/no medidos. PASS dentro de esa procedencia de sesión. |
| Contratos y prohibiciones | Zod strict y JSON Schema separados, enums finitos. Pruebas de JS/CSS/dependencias/tokens/operadores arbitrarios, versión inválida y texto factual extra rechazan. No dependencias nuevas ni cambio de lockfile. PASS. |
| Búsqueda contextual y presupuesto | Tres propuestas, límite 24.000 B, 24 intentos, seis candidatos únicos y cuatro planes finalistas. Sampling por topología coordinada y densidad/medio; pesos etiquetados heurísticos. Prefilter precede slots; duplicados y propuestas inválidas no consumen render. Cero llamadas externas/adquisición/gasto nuevo. PASS. |
| Variedad no cosmética | Cuatro relaciones observables en desktop: Rail/Sequence, Flow/Split, Flow/Sequence y Rail/Split. Cambian navegación lateral/horizontal y texto/medio adyacentes o secuenciales, además de tamaño/ritmo. Distancia estructural no cuenta paletas/fuentes. PASS acotado. |
| Módulos, rutas y hechos | Igualdad exacta de rutas y refs evita pérdida, duplicados, cambio de scope o reordenamiento; la auditoría DOM compara hechos/textos/sedes/ledger. Oferta sigue en su propia ruta y sin imagen. PASS. |
| Medios y derechos | Mismo asset/grant/usage ATMOSPHERIC H3 y JPEG original servido; crédito/etiqueta/no respaldo intactos. Derechos UNKNOWN, otro uso/página y transformaciones rechazan. Gate usa fecha congelada del laboratorio, no certificación jurídica permanente. PASS. |
| Preservación de H0–H4 | Diff limitado a añadidos H5 e integración de export/route callback; callback default conserva H4. Rebuild y verificadores históricos pasan sin recapturar sus evidencias. PASS. |

## Límites y observaciones no bloqueantes

El paso LLM nativo de esta sesión produce propuestas reales, pero el programa consume propuestas registradas: **no es un servicio continuo de invocación LLM**. Provenance y hashes son un recibo confiado de sesión, no autenticación independiente de proveedor. No se exige API pagada para este experimento y no se interpreta costo desconocido como costo cero.

El espacio de búsqueda es una gramática finita de cuatro combinaciones raíz/hijo. H5 demuestra exploración de esas topologías en un fixture, no búsqueda abierta ni excelencia visual/generalización. La oferta escasa limita diferencias entre rutas; en móvil todas las topologías refluyen a secuencia, con diferencias de navegación/ritmo, y no se declara cuatro macroestructuras móviles. El concepto indexed-field no fue seleccionado porque sus topologías ya estaban representadas, sin fingir un juicio de inferioridad estética.

La suite negativa H5 prueba medios no autorizados, uso desconocido/otra página/crop y cambio de densidad; **no demuestra entrada de negocio sin media**. El contexto y `mediaCodes` requieren el paquete piloto autorizado. La ruta de oferta sin foto sí fue renderizada, pero no equivale a un negocio entero sin medio elegible. Es una limitación explícita del fixture H5; H7 deberá admitir y comprobar media pobre/ausente sin inventar ni exigir un asset.

`@101/site-runtime` sigue ausente; corpus autorizado y votos humanos no disponibles. El original de 2.351.102 B sin permiso para derivados bloquea una afirmación de rendimiento comercial satisfactorio. No se probaron usuarios/red móvil reales, campo p75, Safari/Firefox, dispositivos físicos ni accesibilidad exhaustiva. El recibo de checkout limpio de la entrega fue examinado; esta revisión repitió rebuild/replay/recaptura en el workspace, no una segunda reconstrucción de checkout CRLF.

No hay hallazgos bloqueantes reproducibles para los criterios de cierre H5 en este laboratorio. El coordinador puede iniciar **H6**, ya previsto, bajo la autorización registrada y los mismos límites. H6 debe añadir gates/fallos sembrados, crítica concreta, mutación y rollback, y panel A/B/empate/ninguna; jamás fabricar aceptación humana. Este revisor no autoriza producción ni implementa el siguiente hito.
