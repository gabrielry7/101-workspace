# Entrega H1: taxonomía y protocolo upstream

## Estado de cierre

**H1 implementado y auditado empíricamente; listo para revisión. No se avanzó a H2.** La disponibilidad del inventario resolvió el bloqueo anterior. Se procesó íntegramente `data/reference/message (4).txt`: 311.045 bytes UTF-8, siete columnas y **4.582 filas de inventario**, sin errores de parsing. Las comprobaciones previas de archivo ausente fueron reales y quedan superadas por esta ejecución satisfactoria; no se usaron para estimar cobertura.

H0 permanece cerrado en `ec306f28fcbca5123e111d3f6ca58e536769a4f3`. Los cambios H1 quedan en el worktree para revisión. No se añadieron dependencias, integraciones ni librerías visuales. Los contratos, cuatro esquemas exportados y fixtures H0 y package-lock.json permanecen intactos contra ese commit.

## Evidencia reproducible

Toolchain: Node 24.21.0, npm 11.19.0, Astro 7.3.7, TypeScript 6.0.3 y Zod 4.6.5. Se utilizó Node portable ignorado en `.tools/`; no forma parte de la entrega.

- Inventario SHA-256: `ef6e8856e431e6414b5826887cabafb12667f8c0bba4a9d3998d91b747de5f80`.
- Registry V1 / **67 reglas sin cambios**: `ef4193767d1cb9ab9ff7a53bb48584ed8f1e44b963718d85d26c757e34375635`.
- coverage.json SHA-256: `5b81ffa89f0ca62e438019b0642a7fb7eab001fa360e4f3adb035f038c5906da`.
- `npm run taxonomy:audit`: exit 0; [log](evidence/h1-inventory-audit.txt).
- Segundo `npm run taxonomy:audit`: exit 0, coverage.json idéntico byte por byte; [log](evidence/h1-inventory-replay.txt).
- `npm test`: **95/95**, 0 fallos, omitidos o cancelados; [log](evidence/h1-tests.txt).
- `npm run check`: 0 errores, warnings o hints; [log](evidence/h1-check.txt).
- `npm run validate`: tres fixtures PASSED; [log](evidence/h1-validate.txt).
- `npm run build`: validación y una ruta Astro estática correctas; [log](evidence/h1-build.txt).

Los derivados intencionales [coverage.json](../data/derived/taxonomy-v1/coverage.json) y [unresolved.json](../data/derived/taxonomy-v1/unresolved.json) contienen todas las filas originales y sus diagnósticos, proveedor, campo, categoría/código, jerarquía, normalización explícita, raw, pesos y procedencia archivo/SHA/fila/líneas. No son archivos temporales. El resultado verifica resolución determinista, no precisión estadística ni aprobación editorial de cada arquetipo.

Verificación independiente sobre el archivo completo con `csv.DictReader`: 4.582 filas originales iguales, en orden y celda por celda, a `records[].raw`; 4.582 IDs distintos; SHA original igual al publicado; todos los totales ponderados iguales a la suma de sus cinco estados. Resultado PASSED. **60 de las 67 reglas** participaron en alguna resolución final; siete quedaron sin uso en este inventario. Esta comprobación de conservación tampoco deduplica negocios.

## Cobertura por proveedor: filas

M = MAPPED; A = AMBIGUOUS; N = NON_BUSINESS; D = UNKNOWN; U = UNMAPPED. Cobertura = M / todas las filas del grupo, incluidos casos no comerciales. Las filas de distintas capas no son negocios independientes.

| Proveedor | Filas | M | A | N | D | U | Cobertura por filas |
|---|---:|---:|---:|---:|---:|---:|---:|
| foursquare | 890 | 189 | 2 | 1 | 1 | 697 | 21.24% |
| osm | 1195 | 59 | 2 | 4 | 1 | 1129 | 4.94% |
| overture | 2497 | 77 | 2 | 1 | 1 | 2416 | 3.08% |

## Cobertura por proveedor y campo

Cada ponderación usa solo las filas del mismo **proveedor y campo**. O/C indican sumas de pesos de observaciones/candidatos del inventario; %O/%C = peso MAPPED / peso total respectivo. No son negocios únicos. No se suman proveedores, ni basic/primary/hierarchy/normalized, ni campos OSM. El denominador cero produce N/A. `other_observations` también tiene desglose completo por estado en coverage.json. Los porcentajes son descriptivos de menciones; las poblaciones pueden solaparse y los pesos no son confianza.

| Proveedor | Campo | Filas | M/A/N/D/U | % filas | O | %O | C | %C |
|---|---|---:|---|---:|---:|---:|---:|---:|
| foursquare | `101.normalized_category` | 34 | 5/2/1/1/25 | 14.71% | 126460 | 34.88% | 100523 | 43.41% |
| foursquare | `foursquare.category` | 856 | 184/0/0/0/672 | 21.50% | 139241 | 34.45% | 112749 | 42.09% |
| osm | `101.normalized_category` | 37 | 5/2/1/1/28 | 13.51% | 171517 | 6.31% | 56300 | 19.21% |
| osm | `osm.aerialway` | 4 | 0/0/0/0/4 | 0.00% | 18 | 0.00% | 0 | N/A |
| osm | `osm.aeroway` | 9 | 0/0/0/0/9 | 0.00% | 27 | 0.00% | 0 | N/A |
| osm | `osm.amenity` | 148 | 18/0/3/0/127 | 12.16% | 27206 | 38.19% | 20655 | 49.47% |
| osm | `osm.artwork_type` | 11 | 0/0/0/0/11 | 0.00% | 177 | 0.00% | 161 | 0.00% |
| osm | `osm.attraction` | 5 | 0/0/0/0/5 | 0.00% | 15 | 0.00% | 8 | 0.00% |
| osm | `osm.barrier` | 23 | 0/0/0/0/23 | 0.00% | 4397 | 0.00% | 409 | 0.00% |
| osm | `osm.boundary` | 8 | 0/0/0/0/8 | 0.00% | 2217 | 0.00% | 3 | 0.00% |
| osm | `osm.building` | 85 | 0/0/0/0/85 | 0.00% | 20619 | 0.00% | 7949 | 0.00% |
| osm | `osm.building:part` | 4 | 0/0/0/0/4 | 0.00% | 28 | 0.00% | 18 | 0.00% |
| osm | `osm.club` | 11 | 0/0/0/0/11 | 0.00% | 41 | 0.00% | 39 | 0.00% |
| osm | `osm.craft` | 57 | 5/0/0/0/52 | 8.77% | 796 | 16.96% | 796 | 16.96% |
| osm | `osm.emergency` | 9 | 0/0/0/0/9 | 0.00% | 69 | 0.00% | 43 | 0.00% |
| osm | `osm.entrance` | 5 | 0/0/0/0/5 | 0.00% | 52 | 0.00% | 13 | 0.00% |
| osm | `osm.feature_tag` | 1 | 0/0/0/0/1 | 0.00% | 1156 | 0.00% | 0 | N/A |
| osm | `osm.golf` | 1 | 0/0/0/0/1 | 0.00% | 44 | 0.00% | 31 | 0.00% |
| osm | `osm.government` | 26 | 0/0/0/0/26 | 0.00% | 112 | 0.00% | 95 | 0.00% |
| osm | `osm.healthcare` | 22 | 2/0/0/0/20 | 9.09% | 1764 | 24.26% | 1764 | 24.26% |
| osm | `osm.highway` | 33 | 0/0/0/0/33 | 0.00% | 76365 | 0.00% | 25 | 0.00% |
| osm | `osm.historic` | 17 | 0/0/0/0/17 | 0.00% | 199 | 0.00% | 7 | 0.00% |
| osm | `osm.industrial` | 15 | 0/0/0/0/15 | 0.00% | 72 | 0.00% | 72 | 0.00% |
| osm | `osm.landuse` | 29 | 0/0/0/0/29 | 0.00% | 6417 | 0.00% | 257 | 0.00% |
| osm | `osm.leisure` | 46 | 2/0/0/0/44 | 4.35% | 13076 | 3.32% | 8405 | 5.15% |
| osm | `osm.man_made` | 46 | 1/0/0/0/45 | 2.17% | 2088 | 14.51% | 2 | 100.00% |
| osm | `osm.military` | 4 | 0/0/0/0/4 | 0.00% | 9 | 0.00% | 0 | N/A |
| osm | `osm.mountain_pass` | 1 | 0/0/0/0/1 | 0.00% | 8 | 0.00% | 0 | N/A |
| osm | `osm.natural` | 21 | 0/0/0/0/21 | 0.00% | 314 | 0.00% | 7 | 0.00% |
| osm | `osm.office` | 59 | 6/0/0/0/53 | 10.17% | 1701 | 8.35% | 1698 | 8.36% |
| osm | `osm.place` | 15 | 0/0/0/0/15 | 0.00% | 1715 | 0.00% | 4 | 0.00% |
| osm | `osm.power` | 10 | 0/0/0/0/10 | 0.00% | 199 | 0.00% | 1 | 0.00% |
| osm | `osm.public_transport` | 7 | 0/0/0/0/7 | 0.00% | 5451 | 0.00% | 210 | 0.00% |
| osm | `osm.railway` | 11 | 0/0/0/0/11 | 0.00% | 211 | 0.00% | 0 | N/A |
| osm | `osm.route` | 7 | 0/0/0/0/7 | 0.00% | 977 | 0.00% | 0 | N/A |
| osm | `osm.shop` | 219 | 16/0/0/0/203 | 7.31% | 23610 | 50.69% | 23606 | 50.69% |
| osm | `osm.sport` | 149 | 0/0/0/0/149 | 0.00% | 4626 | 0.00% | 4372 | 0.00% |
| osm | `osm.tourism` | 21 | 4/0/0/0/17 | 19.05% | 1156 | 50.00% | 1146 | 50.44% |
| osm | `osm.traffic_calming` | 1 | 0/0/0/0/1 | 0.00% | 1 | 0.00% | 0 | N/A |
| osm | `osm.water` | 9 | 0/0/0/0/9 | 0.00% | 59 | 0.00% | 1 | 0.00% |
| osm | `osm.waterway` | 9 | 0/0/0/0/9 | 0.00% | 912 | 0.00% | 1 | 0.00% |
| overture | `101.normalized_category` | 33 | 5/2/1/1/24 | 15.15% | 158634 | 30.82% | 126342 | 38.68% |
| overture | `overture.basic_category` | 242 | 0/0/0/0/242 | 0.00% | 158634 | 0.00% | 126342 | 0.00% |
| overture | `overture.taxonomy.alternate` | 21 | 0/0/0/0/21 | 0.00% | 583 | 0.00% | 583 | 0.00% |
| overture | `overture.taxonomy.hierarchy_level_1` | 13 | 0/0/0/0/13 | 0.00% | 151116 | 0.00% | 126342 | 0.00% |
| overture | `overture.taxonomy.hierarchy_level_2` | 108 | 5/0/0/0/103 | 4.63% | 142693 | 10.91% | 122447 | 12.72% |
| overture | `overture.taxonomy.hierarchy_level_3` | 516 | 19/0/0/0/497 | 3.68% | 109364 | 26.53% | 98753 | 29.38% |
| overture | `overture.taxonomy.hierarchy_level_4` | 435 | 12/0/0/0/423 | 2.76% | 43940 | 13.07% | 40870 | 12.69% |
| overture | `overture.taxonomy.hierarchy_level_5` | 83 | 0/0/0/0/83 | 0.00% | 4689 | 0.00% | 4592 | 0.00% |
| overture | `overture.taxonomy.hierarchy_level_6` | 4 | 0/0/0/0/4 | 0.00% | 1135 | 0.00% | 1135 | 0.00% |
| overture | `overture.taxonomy.primary` | 1042 | 36/0/0/0/1006 | 3.45% | 151116 | 24.75% | 126342 | 29.16% |

## Alcance efectivo de las 67 reglas

`rule_coverage` registra reglas que participan en la resolución final de al menos una fila. No cuenta coincidencias de menor especificidad descartadas; una regla utilizada no prueba exactitud de su arquetipo. Las reglas de abstención también cuentan como utilizadas.

| Proveedor | Reglas | Con filas resueltas | Sin filas resueltas |
|---|---:|---:|---:|
| foursquare | 22 | 19 | 3 |
| osm | 23 | 21 | 2 |
| overture | 22 | 20 | 2 |

Reglas sin participación final: `osm-normalized-health`, `overture-normalized-health`, `foursquare-normalized-health`, `foursquare-vehicle`, `osm-transport`, `overture-transport`, `foursquare-transport`.

## Ambigüedad, desconocidos y no comerciales

| Proveedor | Campo | Categoría literal | Estado | Peso O | Peso C |
|---|---|---|---|---:|---:|
| foursquare | `101.normalized_category` | Unknown | UNKNOWN | 21259 | 0 |
| foursquare | `101.normalized_category` | Professional Services/Other Professional | AMBIGUOUS | 18794 | 18725 |
| foursquare | `101.normalized_category` | Non Business | NON_BUSINESS | 3879 | 0 |
| foursquare | `101.normalized_category` | Beauty and Wellness/Fitness and Wellness | AMBIGUOUS | 1230 | 1224 |
| osm | `101.normalized_category` | Non Business | NON_BUSINESS | 90995 | 0 |
| osm | `101.normalized_category` | Unknown | UNKNOWN | 23565 | 0 |
| osm | `101.normalized_category` | Beauty and Wellness/Fitness and Wellness | AMBIGUOUS | 448 | 448 |
| osm | `101.normalized_category` | Professional Services/Other Professional | AMBIGUOUS | 333 | 333 |
| osm | `osm.amenity` | bench | NON_BUSINESS | 896 | 0 |
| osm | `osm.amenity` | waste_basket | NON_BUSINESS | 812 | 0 |
| osm | `osm.amenity` | drinking_water | NON_BUSINESS | 21 | 0 |
| overture | `101.normalized_category` | Unknown | UNKNOWN | 13170 | 364 |
| overture | `101.normalized_category` | Professional Services/Other Professional | AMBIGUOUS | 12565 | 12565 |
| overture | `101.normalized_category` | Non Business | NON_BUSINESS | 7974 | 0 |
| overture | `101.normalized_category` | Beauty and Wellness/Fitness and Wellness | AMBIGUOUS | 4767 | 4766 |

Las dos etiquetas ambiguas de cada proveedor permanecen como alternativas: `Professional Services/Other Professional` (asesoría o servicio de campo) y `Beauty and Wellness/Fitness and Wellness` (membresías/clases o atención por cita). `Unknown` conserva UNKNOWN en los tres proveedores. `Non Business` conserva NON_BUSINESS sin reinterpretar los conteos del proveedor; en OSM también bench, waste_basket y drinking_water. No se infiere que todas las categorías restantes de infraestructura sean comerciales o no comerciales: sin regla, UNMAPPED.

## Casos sin resolver y decisiones

La revisión recorrió todas las filas para resolución, procedencia, pesos y estados. `unresolved.json` enumera exactamente **4.251 filas**: 700 Foursquare, 1.132 OSM y 2.419 Overture (UNMAPPED/UNKNOWN/AMBIGUOUS). Esta suma describe tamaño del artefacto, no entidades. La lista completa conserva sus diagnósticos; las siguientes son muestras por proveedor ordenadas por peso de observaciones, sin mezclar denominadores.

| Proveedor | Campo | Categoría sin regla | Peso O | Peso C |
|---|---|---|---:|---:|
| foursquare | `foursquare.category` | Community and Government > Residential Building > Apartment or Condo | 7096 | 51 |
| foursquare | `foursquare.category` | Business and Professional Services > Office | 6965 | 6937 |
| foursquare | `101.normalized_category` | Education/Education | 5058 | 5019 |
| foursquare | `foursquare.category` | (missing) | 4615 | 0 |
| foursquare | `foursquare.category` | Landmarks and Outdoors > Structure | 3869 | 326 |
| foursquare | `101.normalized_category` | Health/Other Health | 3797 | 3777 |
| foursquare | `101.normalized_category` | Entertainment/Entertainment Venue | 3633 | 3612 |
| foursquare | `101.normalized_category` | Beauty and Wellness/Beauty Service | 2900 | 2890 |
| osm | `osm.highway` | residential | 38128 | 0 |
| osm | `101.normalized_category` | Retail | 13657 | 13657 |
| osm | `osm.building` | yes | 10380 | 7254 |
| osm | `osm.highway` | footway | 9594 | 5 |
| osm | `101.normalized_category` | Entertainment | 8294 | 8022 |
| osm | `osm.highway` | tertiary | 8045 | 0 |
| osm | `osm.leisure` | pitch | 5870 | 5623 |
| osm | `101.normalized_category` | Transport/Transport Service | 5370 | 4989 |
| overture | `overture.taxonomy.hierarchy_level_1` | shopping | 36664 | 36664 |
| overture | `overture.taxonomy.hierarchy_level_1` | services_and_business | 36160 | 36160 |
| overture | `overture.taxonomy.hierarchy_level_1` | food_and_drink | 24359 | 24359 |
| overture | `overture.taxonomy.hierarchy_level_2` | specialty_store | 17522 | 17522 |
| overture | `101.normalized_category` | Professional Services | 15213 | 15213 |
| overture | `overture.basic_category` | restaurant | 13808 | 13797 |
| overture | `overture.taxonomy.hierarchy_level_1` | lifestyle_services | 10344 | 10344 |
| overture | `overture.basic_category` | fashion_and_apparel_store | 9041 | 9041 |

Causas examinadas:

- Foursquare: cobertura parcial del vocabulario y categorías residenciales, públicas o institucionales; `(missing)` no se convierte en actividad.
- OSM: 39 campos observados, muchos de infraestructura/geografía (highway, building, landuse, natural, etc.). `building=yes`, usos del suelo y deportes no identifican por sí solos un arquetipo comercial. Shop/craft/office requieren ampliar vocabulario mediante crosswalk revisado.
- Overture: 10 campos observados; basic_category y taxonomy.alternate no tienen reglas, y hierarchy_level_1 es amplio. Etiquetas shopping, services_and_business o health_care no prueban comercio, servicios específicos ni coexistencia. Se requiere revisar equivalencias de basic/primary y jerarquías, en vez de habilitar todo el campo.
- Normalización: nombres amplios Retail, Education/Education o Professional Services carecen de decisión suficiente en las semillas. No se asocian sus agregados a filas originales como si fueran observaciones de un negocio.

**Decisión:** conservar las 67 reglas y documentar sus límites. El inventario demuestra vocabulario y frecuencia, pero no aporta ground truth de actividad por negocio, titularidad pública/privada ni operaciones. No se agregaron reglas generales para mejorar artificialmente las cifras. La cobertura baja es un resultado de esta auditoría, no un error ocultado ni una promesa de soporte productivo.

## Separación de capacidades y alcance implementado

Categoría observada → arquetipo inferido → capacidad candidata → capacidad real verificada son niveles distintos. `classifyBusiness` propone relevancia marcada `RELEVANCE_ONLY_NOT_VERIFIED`, sin modificar `BusinessInputV1.business_capabilities`, crear CapabilityProfile o SitePlan, conectar módulos ni activar operaciones. Se mantuvieron pruebas de capacidades UNKNOWN/ausentes y rechazo de afirmaciones upstream sin evidencia aprobada.

La nueva prueba `tests/taxonomy-inventory.test.ts` recorre las **4.582 categorías reales** usando un único input **SYNTHETIC_FIXTURE** como sonda de seguridad: lista operacional vacía, entrada sin mutación, candidatas con autoridad explícita y ausencia de salida operacional/plan. No convierte filas en negocios ni inventa datos reales. Su SHA fijado detecta cambios del inventario que requieren revisión; los 19 casos controlados y los tests de abstención/híbridos/protocolo siguen separados.

Implementado: parser UTF-8 estricto y procedencia; registry y resolución extensibles; ambigüedad/híbridos con evidencia/abstención; protocolo candidato UpstreamEnvelopeV1 con payload H0 intacto, sidecars y checksum; schemas exportados; CLI, métricas, tests y documentación. Simulado: fixtures y sonda de seguridad. Pendiente: acuerdo con 101-world-model, adapter real, autenticación/transporte/idempotencia persistente, calibración y crosswalk más amplio. No existe integración funcional.

## Errores y riesgos pendientes

- Auditoría final, pruebas, check, validación y build: sin errores. Al escribir la nueva prueba, una primera ejecución falló porque la sonda añadía `actions`, campo inexistente en el contrato estricto. Se retiró ese campo de la prueba; no se cambió el contrato. La ejecución final pasó 95/95.
- No hay etiquetas independientes que permitan medir precision/recall. MAPPED mide cobertura de reglas, no veracidad comercial; una coincidencia con un ancestro Foursquare requiere revisión semántica de los descendientes.
- NON_BUSINESS deriva de etiquetas y reglas explícitas; no valida la decisión original del proveedor. Candidatos/observaciones son conteos de origen, no hechos confirmados ni deduplicación.
- El porcentaje global por proveedor mezcla filas de distintas capas y está sesgado por el tamaño de cada taxonomía. Se presentan campos y ponderaciones separados para que no se interprete como cobertura de locales.
- Cambios de inventario/IDs/jerarquías o clasificación por sucursal requieren nueva evaluación y posiblemente revisión del protocolo. Confidence no está calibrada; checksum no autentica al productor.
- El build demuestra compatibilidad técnica del inspector, no calidad visual, costo marginal, accesibilidad completa ni rendimiento de sitios comerciales.

H1 queda listo para revisión con estas limitaciones explícitas. No se implementaron H2, generación de diseño, nuevas librerías visuales, multimedia, checkout, reservas operativas ni integraciones externas.

## Cierre autorizado antes de H2

Se repitieron 95/95 pruebas, check sin diagnósticos, validación y build antes del commit H1. `.gitattributes` conserva los bytes originales del inventario y fija LF para registry/derivados con hashes, independientemente de `core.autocrlf` en Windows. Los logs se normalizaron a UTF-8 para lectura y diff. Las herramientas y dependencias ignoradas no se incluyen; el hash del commit de cierre se registra en el informe H2.
