# H9 — revisión humana del hito pendiente

Fecha: 2026-10-12. Base técnica `3f2d2f36e1617ae600237b6b289473e8209554bc`. Inventario original `85ed75bbe92eedd9489b66605e579025ce21cb62`; diagnóstico revisado independientemente en `8376e4b2ccf2c5a8249a42fb3085f8759f2e70b0`.

El usuario solicita revisar H9 y recuerda que no se ejecutó, preguntando por el motivo. Se distingue inventario de evidencia ya ejecutado del benchmark económico pendiente. No se inicia benchmark, adquisición, compra, integración ni H10.

## Qué mide H9

Costo y tiempo reales de producir sitios aceptados, incluyendo exploración/rechazos/correcciones y revisión humana; disponibilidad/calidad/cobertura de medios y permisos efectivos por uso/proveedor en muestra multisector comparable. Requiere método de atribución, unidades/monedas y contexto/versión; no basta precio de lista, tiempo de build o cero gasto nuevo.

## Qué se ejecutó y por qué se detuvo

Se inventariaron 26 fuentes H3–H8, preservando hashes/normalización, datos sintéticos, aceptación humana y estado de medición. Revisión independiente aceptó ese diagnóstico, no el hito económico. Benchmark NOT_TESTED, H9 BLOCKED_EXTERNAL_EVIDENCE.

La evidencia inspeccionada tiene cero sitios reales generados por 101 con aprobación humana documentada. Datos de fixtures y votos simulados no cuentan; las preferencias sobre 21 sitios de terceros tampoco equivalen a aprobar nuestros sitios. Tokens/costos totales y horas humanas de las corridas anteriores no medidos; falta muestra autorizada de proveedores/sectores para economía/cobertura reales. p50/p90 null con denominador cero, no costo cero.

La clave Pixabay aportada ahora es una credencial disponible por declaración; no demuestra conexión probada, permiso universal de automatización, medios obtenidos ni benchmark económico. El bloqueo Edge de H8 observado durante esta revisión es un problema adicional de reproducción que debe corregirse; no se usa para reinterpretar el motivo histórico del bloqueo H9.

## Secuencia propuesta después de las correcciones

Derivada de feedback H0–H8, no nuevo método H9 ratificado:

1. Corregir y comprobar el flujo de requisitos, interpretación, medios, composición, generación/evaluación, iteración y lock aprobado.
2. Obtener inputs/materiales autorizados de casos reales y producir páginas completas; recoger aceptación humana vinculada a versión/página/viewport/alcance.
3. Instrumentar antes de las nuevas corridas llamadas/consumo/costos disponibles, obtención de medios/licencias, tiempo de máquina y humano por separado, revisiones, reintentos y fallos; no reconstruir costos pasados inventando cifras.
4. Medir costo por aprobado y distribución por tipo/funciones/proveedor con denominadores y reparto de gastos comunes explícitos. Mantener desconocidos y no aplicar percentiles sin muestra/método suficientes.
5. Comprobar acceso/uso/caché/retención/automatización y procesamiento según proveedor/archivo. No declarar calidad/volumen de catálogo desde una única foto o la existencia de una API.

Los pilotos pueden evaluarse sin despliegue productivo, reservas/pagos reales o backend comercial. El método, cohorte suficiente y presupuestos deben acordarse; esta propuesta no autoriza gastos ni producción.

## Verificación realizada ahora

`node --experimental-strip-types scripts/inventory-h9.ts --verify`, usando Node portable 24.21.0: exit 0, inventario VERIFIED, H9 BLOCKED/NOT_TESTED, cero sitios reales aprobados elegibles, percentiles null. No se recapturó ni reconstruyó H8, alteraron fuentes históricas o hicieron llamadas/adquisiciones a proveedores.

Estado: diagnóstico confirmado; H9 no completo ni aprobado humanamente como benchmark. Revisión presentada, feedback específico pendiente. Sólo notas para prompt consolidado, sin cambios funcionales ni commit.
