# B0 — diagnóstico, reproducción controlada e instrumentación

Fecha local de evaluación: 2026-10-12 (America/Bogota); recibos en UTC del 2026-10-13. Base: `3f2d2f36e1617ae600237b6b289473e8209554bc`. Rama: `codex/corrections-b0-baseline`.

**Resultado: bloque B0 técnicamente preparado para revisión, con bloqueo histórico explícito.** Se reproduce el laboratorio con el mismo HTML y píxeles. La suite completa y `lock:verify -- --rebuild` todavía fallan por `LOCK_BROWSER_MISMATCH` del Edge global. No se declara H8 reparado integralmente, H9 cerrado, aprobación estética ni preparación comercial.

El usuario autorizó este primer bloque y pidió detenerse para revisión. Su instrucción actual de pausa y revisión prevalece sobre la continuidad automática descrita en el registro histórico de coordinación. No se implementaron catálogo, clasificación contextual, adquisición audiovisual, gramática nueva, feedback, aceptación final ni H10.

## Alcance y preservación

Se consultaron pipeline/V0.2, informes, contratos, historial de revisiones y prompt consolidado. El manifiesto [pre/protected-files.json](../evidence/corrections/b0/pre/protected-files.json) conserva 1.018 archivos: todos los archivos previamente versionados y las notas/corpus intencionales previos al trabajo. Texto normalizado únicamente cuando se declara LF_TEXT; medios y HTML de evidencia, BINARY. La comprobación final no detectó cambios. No se editaron contratos V1, planner, renderer, estilos, locks, reportes históricos, paquetes ni dependencias.

El commit incorpora las notas de revisión H0–H9, el prompt consolidado y el corpus aportado por el usuario. Son registro de requisitos/preferencias, no implementaciones ni autorizaciones de uso de medios de terceros. La [matriz](b0-matrix.md) conserva lo pendiente por bloque.

El runtime comercial y upstream siguen ausentes. Astro y los componentes existentes se usan como laboratorio compartido. La foto atmosférica H3 conserva original, atribución, etiqueta y aviso de no respaldo USDA/ARS. SHA256: `ffdb883d56a41ba9a03a51fb7d1bdf8f0b9e30d3946eda180b750620a17c3715`, 2.351.102 bytes. El hueco documental no se cubre ni se cambia de rol. No hubo investigación legal nueva, proveedores, descargas, cuentas o pagos en B0.

## Qué se añadió

- `scripts/b0-baseline.ts`: 18 comandos, logs, salida, tiempos de máquina y recibo estricto versionado. Un fallo ajeno al bloqueo conocido hace fallar la corrida.
- `scripts/b0-runtime.ts` y `lib/correction-runtime.ts`: materialización local de Edge 154 ya instalado y guardas de bytes completos, Node, dependencias instaladas, paquetes, OS y fuentes.
- `scripts/b0-capture.ts`: dos builds en directorios separados, tres mounts históricos, todas sus rutas y viewports, navegación/teclado, binds, medios, raster, HTML y PNG. Reutiliza observer, auditor, decodificador PNG y harness de navegador existentes.
- `scripts/b0-verify.ts`: verificación de recibos/logs, cobertura sin duplicados, PNG/RGBA/HTML, auditorías recalculadas, medio servido, comparación histórica, árboles de salida y preservación. Requiere el runtime materializado y salidas locales verificables; no inventa evidencia si faltan.
- Ocho pruebas nuevas: desconocidos de costo/tiempo humano/aprobación, redacción de credenciales ficticias, escape de rutas, corrupción de medio, cambios/inserciones de archivos, overlay ambiguo, log alterado/fallos extra y cobertura duplicada/incorrecta.

No hay dependencias nuevas ni un segundo renderer. El overlay de lanzamiento documentado deriva el harness compartido sin modificar su fuente y se conserva como `.txt`, no fuente compilada de evidencia.

## Entorno y límite del navegador

Los locks históricos fijan `Edg/154.0.4258.62`; el helper original detecta el Edge global actualizado `155.0.4283.45`. No se degrada el navegador global, no se cambia su configuración, no se resealan locks ni se relajan sus gates.

Los cuatro archivos fijados en H8 aún existen en la carpeta instalada 154 y coinciden con sus hashes. Se copió esa versión a `.tools/corrections/b0/browser-154.0.4258.62/`, incluyendo el ejecutable original; 925 archivos fijados por bytes en [runtime.json](../evidence/corrections/b0/runtime.json). Snapshot SHA256: `31703af917c090840789fe3055bc7390e96553fc562b8095bf3a768c2fa16071`.

**Excepción de laboratorio:** el Edge copiado responde a CDP pero bloquea el renderer con sandbox normal. El launch overlay usa `--no-sandbox` únicamente para builds locales fijos, más flags que deshabilitan actualización/componentes/sync/red de fondo. Intercepta y rechaza solicitudes de página externas. Esto no acredita seguridad para navegar terceros, aislamiento de toda la red del sistema ni equivalencia en otra máquina; no se usa para proveedores. El ejecutable instalado original sí respondió sin esa excepción.

El snapshot no se redistribuye dentro de Git. La copia aislada, Node, dependencias, perfiles y builds están ignorados en `.tools`/`node_modules`/`dist`. La reproducción exige los bytes registrados y el mismo OS/fuentes. Si esa copia desaparece y la versión instalada ya no está disponible, la preparación debe bloquearse; no hay descarga automática ni promesa de recuperación universal.

## Resultados verificables

| Comprobación | Resultado |
| --- | --- |
| Baseline antes de editar | 297 tests: 296 PASS, 1 FAIL por navegador. Check/validate/build/exportación/replays/verificadores pertinentes PASS. Lock histórico bloqueado. |
| Baseline final workspace | 305 tests: 304 PASS, 1 FAIL conocido; 8 pruebas B0 PASS. 16 de 18 comandos PASS, tests y lock-verify bloqueados por navegador. |
| Check, validate y build | PASS; check 0 errores/advertencias/hints; build 90 páginas. |
| Exportación de contratos/taxonomía/planner | PASS; sin cambios de artefactos protegidos. |
| Medios/composición/diseño/auditoría/cohorte | Replays/verificadores PASS; sin nueva adquisición. |
| Captura workspace `controlled-04` | Dos builds; 32 vistas; 16 pares con HTML, RGBA y observables equivalentes. Todas coinciden con originales H8. |
| Captura copia limpia `clean-02` | Repite dos builds y 32 vistas con las mismas equivalencias y guardas; todas las auditorías LAB pasan. |
| Baseline copia limpia `clean-post-02` | Mismo resultado 304/305 y bloqueo histórico; 16 comandos PASS. |
| Verificación B0 workspace y limpia | PASS para ambas ejecuciones: 32 vistas, 16 pares, match histórico y 1.018 archivos preservados. |
| H9 inventory --verify | PASS del inventario; H9 BLOCKED/NOT_TESTED, cero sitios reales aprobados, p50/p90 null. |

Recibos: [post-02/journal.json](../evidence/corrections/b0/post-02/journal.json), [controlled-04/capture.json](../evidence/corrections/b0/controlled-04/capture.json), [clean-post-02/journal.json](../evidence/corrections/b0/clean-post-02/journal.json) y [clean-02/capture.json](../evidence/corrections/b0/clean-02/capture.json). No se presenta un comando que sale 1 como prueba verde.

La [comprobación final](../evidence/corrections/b0/final/journal.json) vuelve a verificar snapshot, capturas workspace/limpia, las ocho pruebas B0 y check después de preparar toda la entrega: cinco comandos PASS. Git diff --cached --check pasa; la revisión de rutas excluye dependencias/temporales y no detecta el patrón de credencial aportado en archivos nuevos.

Cobertura por construcción: pilot-flow 2 rutas × 2 viewports, pilot-rail 2 × 2, hybrid-no-media 4 × 2 = 16. Desktop/móvil son los tamaños fijados por los locks. Se comprueban skip link, disclosure y navegación por teclado, geometría/desbordamientos, legibilidad, carga, bytes, módulo/referencia/sucursal y crédito/contexto. El permiso de medios original pesado sigue siendo excepción LAB, no rendimiento comercial demostrado.

Se inspeccionaron manualmente dos PNG adicionales: [Flow desktop](../evidence/corrections/b0/controlled-04/a-pilot-flow-desktop.png) y [Rail móvil](../evidence/corrections/b0/controlled-04/a-pilot-rail-mobile.png). Conservan atribución, avisos y hueco. Las otras vistas tienen observación/auditoría automatizada y captura; no se afirma inspección humana de las 64 ni aprobación estética. Son todavía fixtures escasos, no las demos completas que exige el feedback.

## Corridas fallidas conservadas

Los intentos se mantienen, no se sobrescriben con la última corrida verde:

1. Arranque inicial del registro PowerShell: se corrigieron rutas/quoting del bootstrap antes del baseline completo; no produjo cambios protegidos ni recibo válido de pruebas.
2. `controlled-01`: build PASS; `Page.enable` se bloquea en la copia sin excepción de sandbox. Diagnóstico posterior explícitamente separado del log.
3. `controlled-02`: selector de navegación inexistente en el harness B0. Se corrigió al contrato `.site-nav a[data-route]` existente. Evidencia parcial, sin PASS.
4. `controlled-03`: primera construcción con 16 vistas y dos vistas de la segunda; fallo del gate combinado. No persistía los arrays de excepción/red, por lo que la causa exacta permanece desconocida. Se añadió persistencia de diagnósticos de fallos y recibos parciales. No se cambió el gate.
5. `post-01`: check detectó dos errores de tipos de la colección de capturas; corregidos antes de `post-02`.
6. Primera materialización limpia: conversión CRLF cambió paquetes y HTML de evidencia. La guarda rechazó la captura y la preservación rechazó la copia; corregido el procedimiento de archivo y atributos de los nuevos artefactos, sin cambiar originales. Véase [failure.txt](../evidence/corrections/b0/clean-first-attempt/failure.txt).

No se calcularon tiempos ausentes de los intentos anteriores ni se fabricaron sus logs. Los recibos disponibles conservan tiempos reales medidos por comando; las notas posteriores lo identifican expresamente.

## Reproducción

Usar Node portátil fijado, dependencias instaladas coincidentes y fuentes/OS actuales. Ejemplo PowerShell desde la raíz:

```powershell
$node = '.tools/node-v24.21.0-win-x64/node.exe'
& $node --experimental-strip-types scripts/b0-runtime.ts --verify
& $node --experimental-strip-types scripts/b0-baseline.ts nuevo-baseline
& $node --experimental-strip-types scripts/b0-capture.ts nueva-captura
& $node --experimental-strip-types scripts/b0-verify.ts nueva-captura nuevo-baseline
```

Los IDs deben ser nuevos: se rechaza sobrescribir una corrida. `b0-runtime.ts` sin `--verify` prepara el snapshot sólo si no existe recibo; una carpeta parcial o bytes incompatibles bloquean. El baseline termina exitosamente sólo para el diagnóstico acotado cuando no aparecen fallos adicionales, conservando en los logs las dos salidas 1 conocidas; no cambia el exit del test/lock subyacente.

La prueba limpia materializó el árbol preparado `24072ededfc5f7a29ea3a6a9561b816d733b5360` con `git -c core.autocrlf=false archive`, antes de incorporar informes y nuevos recibos limpios. Contiene el mismo código ahora entregado; no es un SHA del commit final ni una instalación fresca. Se usaron junctions a dependencias, Node y browser locales, cuyos bytes se verifican; fuentes, builds y perfiles son separados. No prueba reproducibilidad de instalación por red ni portabilidad a otro OS. Logs/HTML B0 se preservan como bytes; scripts B0 se fijan LF para evitar alterar sus hashes al checkout.

## Medición, bloqueos y próxima revisión

Se registran timestamps UTC, duración wall de comandos/capturas, salida, logs/hash, versiones y fallos. Tiempo humano, tokens/costo de sesión, tarifas, moneda y costo total siguen `null`; no usar ausencia de gasto nuevo como costo total cero. No se creó benchmark desde estas muestras.

Pendientes: reparar integralmente la selección de entorno de reconstrucción H8 en un cambio versionado que preserve sus controles; catálogo/comprensión compatibles con H2; audiovisual autorizado; gramática/demos completas; feedback humano e iteración; casos reales; locks elegidos y economía medida. No se inicia ninguno por este informe.

Entrega solicitada a la tarea revisora `01a11911-1da1-73e0-8234-132547fc8f8f`: commit, informe y resultados, con petición de revisión independiente y prompt siguiente. El recibo de mensajería/feedback se informa por separado; este documento no presume entrega ni PASS independiente. Después de B0 se espera revisión y aprobación humana antes de continuar.
