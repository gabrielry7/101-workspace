# H9 — Inventario real y gate económico bloqueado

**Resultado H9: BLOCKED_EXTERNAL_EVIDENCE / benchmark NOT_TESTED. H9 no completo.** Se inspeccionó la evidencia conocida de este workspace: paquete H3, propuestas/recibos H5–H8, locks técnicos y cohorte H7. No se declara ausencia universal de datos externos. En esos registros hay **0 sitios reales con aprobación humana documentada** elegibles para costos por sitio aprobado. Por tanto **p50 y p90 son null / NOT_TESTED**, con denominador 0; no son cero monetario ni una distribución calculada.

Este slice implementa únicamente el inventario reproducible necesario para evaluar el gate H9 del roadmap §24. No agrega contratos económicos vacíos, proveedores/adaptadores, compras, llamadas API, descargas, catálogos, despliegues ni nuevo hito. No toca package.json, toolchain, fuentes/runtime ni locks H8 y no hace reseal para ocultar cambios.

## Evidencia disponible y límites

El [inventario JSON](evidence/h9/inventory.json) fija 26 fuentes conocidas con ruta, normalización, bytes y SHA-256. JSON/script se comparan como LF_TEXT; fotografías y documentos/artefactos mantienen BINARY, además de la verificación byte-exact del paquete H3. Su corte temporal corresponde al recibo H8 inspeccionado; los documentos anteriores conservan sus fechas propias. El [script](../scripts/inventory-h9.ts) lee archivos, verifica el paquete H3 y exige consistencia de los estados sintéticos, humanos y metering antes de emitir/reverificar el inventario. La verificación de integridad **no constituye PASS H9**.

| Evidencia observada | Lo que permite comprobar | Lo que falta para H9 |
|---|---|---|
| H3: 1 fotografía REAL USDA/ARS, 2.351.102 bytes, documentos oficiales y paquete verificable | Adquisición puntual documentada de un activo para uso atmosférico de un piloto ficticio | Muestra comparable de proveedores/sectores, cobertura de catálogo y pruebas de volumen autorizadas |
| H5: 16 recibos browser y 28 de estrés; propuestas reales de sesión | Ejecución de laboratorio y procedencia; nuevas llamadas/gasto reportados 0 | Tokens/costo de sesión son null; no costo total por sitio aprobado |
| H6: presupuesto explícito y pruebas técnicas | Límites y resultados de infraestructura LAB | Costos monetarios, tiempos humanos y sitios humanos aprobados no medidos |
| H7: 6 casos SYNTHETIC_FIXTURE; 10 planes renderizados, 63 vistas de candidatos/negativos y 2 del índice, wall 18.1505783 s | Generalización técnica del fixture y tiempos del harness observado | Esos casos no son clientes reales ni benchmark de cobertura comercial del proveedor |
| H8: 3 locks técnicos, wall 67.2211025 s, rebuild/equivalencia/rollback | Reproducibilidad técnica en ambiente fijado | Human preference NOT_COLLECTED, production false; totales monetarios/tokens desconocidos |

Los conteos/tiempos anteriores proceden de sus recibos, no se atribuyen a nuevos experimentos H9. Los gastos nuevos 0 y llamadas nuevas 0 no implican costo histórico/total 0. El activo H3 se declara `FREE; no purchase or currency asserted`; no se inventan importe numérico, moneda, factura, honorarios legales, horas humanas o almacenamiento. Tiempo wall del navegador/build no es tiempo de trabajo humano ni latencia comercial.

## Matriz de permiso: corte documental H3 e implementación interna

Esta matriz describe **el grant INTERNO evaluado en H3 el 2026-10-08**, vinculado a documentos archivados y al hash del activo. No es una reevaluación jurídica vigente del proveedor ni un acuerdo enterprise. No se investigaron términos nuevos en H9 ni se infieren derechos adicionales de una URL.

| Dimensión | Evidencia registrada | Consecuencia para esta ejecución |
|---|---|---|
| Cliente/proyecto/scope | 101-design-compiler-fixture-review / h3-restaurante-media-pilot / fixture-restaurante-001 | Conservar sólo el uso evaluado; no prestar este grant a otro negocio |
| Rol/página/transformación | ATMOSPHERIC / `/` / original sin derivados | No afirmar fotos documentales del negocio o cobertura de otras verticales |
| commercial_web | ALLOWED bajo el uso interno acotado | No convierte el piloto ficticio en sitio comercial aprobado |
| multi-client, reuse, redistribution, sublicensing | UNKNOWN | No habilita reutilización o distribución general |
| automation.search/download e IA | UNKNOWN para cada operación | No consultas automatizadas, crawls, descargas de catálogo o procesamiento IA nuevo |
| derivatives | DENIED | No recortes, edición o variantes de archivo nuevas |
| API/acuerdos y caching general | No acuerdo/API inspeccionado; permiso general NOT_VERIFIED | Sólo replay local de bytes del piloto ya congelados; no estrategia de caché multicliente/proveedor |
| retention_until y cost | null | No interpretar null como retención ilimitada o costo total cero |

El replay local H3–H8 ya existente se verifica por archivos/hashes/contexto y no consulta al proveedor. El almacenamiento local observado no acredita permisos de una API ni su economía. Los otros proveedores mencionados en el roadmap siguen sin benchmark/autorización efectiva en esta muestra; aparecer en el documento no los aprueba. No se amplía la licencia ni se altera su gate.

## Dependencias externas concretas para cerrar H9

1. **Cohorte de sitios reales aprobados:** inputs autorizados y aceptación humana real vinculada a sitio/versión/fecha/alcance. Los registros actuales son sintéticos y los votos NOT_COLLECTED. PASS técnico independiente no sustituye esa aceptación.
2. **Registro de costos reales atribuibles:** uso/facturas/tarifas y moneda de proveedor/licencias/API/LLM, gastos legales/documentales, almacenamiento, duración y tarifas humanas de implementación/revisión/corrección. Vincular cada intento y rechazo al sitio, registrar gastos compartidos con método de reparto explícito y no excluir intentos fallidos para abaratar el costo por aprobado. No mezclar monedas ni imputar nulos como cero. El metering total de esta sesión no está disponible.
3. **Benchmark y acceso permitidos:** muestras autorizadas comparables por vertical y rol, documentación efectiva de cliente/proyecto/multicliente/automatización/IA/caching/retención y acuerdos/API cuando procedan. Documentar cobertura, abstenciones, huecos y volumen realmente observado. El único activo del piloto no estima cobertura del catálogo.

Son datos/autorizaciones externas faltantes, no un problema que pueda resolverse generando fixtures o votos. No se solicitaron compras ni se realizaron adquisiciones. Hasta contar con esos registros, costos p50/p90, benchmarking multivertical real, acuerdos/caché general y escalamiento permanecen **NOT_TESTED/MISSING/NOT_VERIFIED** según cada campo. Esta entrega sirve para revisión independiente del diagnóstico; el hito H9 permanece bloqueado y no se inicia H10.

## Reproducción y validación

Con Node local del proyecto en PATH, ejecutar directamente (sin añadir scripts npm ni modificar el lock de plataforma):

```powershell
node --experimental-strip-types scripts/inventory-h9.ts
node --experimental-strip-types scripts/inventory-h9.ts --verify
```

El primer comando escribe únicamente `docs/evidence/h9/inventory.json`; el segundo recalcula el inventario desde los 26 inputs y exige igualdad exacta. El script no busca nuevos datos, recalcula probabilidades, ejecuta sampler ni adquiere medios. [Generación](evidence/h9-inventory.txt), [verificación](evidence/h9-verify.txt), [check](evidence/h9-check.txt) y [clean-index](evidence/h9-clean-repro.txt) documentan las tareas seguras. Los artefactos históricos H3–H8 y reviews/coordinación permanecen intactos. H9 no altera el renderer, por lo que no se repitieron capturas históricas o pruebas browser sin cambio funcional.

El primer clean-index detectó CRLF/LF en acquisition.json histórico ([fallo preservado](evidence/h9-clean-initial-fail.txt)). El inventario declara ahora normalización LF_TEXT explícita para JSON/script; bytes/hash de cada entrada corresponden a esa forma. No se reescribió acquisition.json ni ningún artefacto H3–H8. Los hashes legales/del activo del paquete continúan verificándose contra sus bytes originales.
