# Taxonomía multivertical V1

## Cuatro niveles independientes

1. **Categoría observada:** proveedor, campo, valor/código literal, jerarquía disponible, normalización explícita, evidencia y procedencia. Nunca se reemplaza por la interpretación de 101.
2. **Arquetipo inferido:** hipótesis comercial que el mapping registry justifica; puede ser combinable, ambiguo o no resuelto. No es un hecho operativo.
3. **Capacidad candidata:** relevancia a investigar, marcada `RELEVANCE_ONLY_NOT_VERIFIED`. No tiene estado de confirmación, soporte UI, conexión o módulo.
4. **Capacidad real:** exclusivamente `BusinessInputV1.business_capabilities`, con evidencia y decisión upstream. El clasificador no crea ni modifica esta lista.

Una categoría de restaurante puede proponer estudiar `reservation`, `order` o `delivery`; no los confirma. Gym sugiere membresías/clases, no los crea; retail sugiere catálogo, no e-commerce. Las pruebas recorren los 19 casos controlados con lista operacional vacía y verifican que sigue vacía.

## Inventario y procedencia

El archivo agregado sirve para estudiar el vocabulario observado, **no para instanciar un BusinessInput por fila**. `loadInventoryBytes` conserva proveedor original y canónico, campo/valor literal, ID de categoría como string (incluidos ceros iniciales), jerarquía disponible, normalización explícita, todos los campos originales, los tres conteos separados y referencia archivo/SHA256/fila/líneas físicas.

No se fabrican padres de Overture desde `hardware_store` ni desde una fila aislada `hierarchy_level_4`; se conserva únicamente lo disponible. Una categoría normalizada `Food/Restaurant` conserva ambos niveles separados por `/`; un path Foursquare conserva nodos separados por `>`. Raw sigue reteniendo la cadena intacta. Una fila normalizada agregada no se asocia a una fila original como si fueran del mismo negocio.

Parser UTF-8 estricto con BOM opcional, TSV/CSV/semicolon y quoting con líneas/comillas escapadas. Cabeceras y conteos inválidos, columnas faltantes y encoding inválido producen error explícito. Duplicados se conservan como filas distintas. Ningún conteo se suma como número de negocios únicos, ni entre fuentes ni entre categorías.

`npm run taxonomy:audit` genera dos derivados intencionales, no archivos temporales:

- `data/derived/taxonomy-v1/coverage.json`: fuentes/hashes, hash del registry, cada fila con mapping, métricas de **filas** por proveedor. La fracción mapped no mide negocios resueltos ni calidad factual.
- `data/derived/taxonomy-v1/unresolved.json`: todas las filas UNKNOWN/UNMAPPED/AMBIGUOUS, con alternativas, regla y procedencia.

Mismo archivo, registry y versión producen bytes JSON idénticos; no se inserta fecha del reloj. El inventario real está disponible y su auditoría se documenta en `h1-report.md`. Sin archivo, la CLI falla con código 2 y no emite derivados. Los tests CLI usan directorios temporales propios, etiquetas sintéticas y los eliminan; esos conteos no se entregan como cobertura real.

## Registry y resolución

`taxonomy/v1/mappings.json`, versión 1.0.0, contiene **67 reglas semilla**, para Foursquare/OSM/Overture, que abarcan los 14 nombres de arquetipo de H0. Son reglas candidatas basadas en vocabulario de la especificación y casos controlados; su cobertura empírica parcial está documentada en `h1-report.md`. No constituyen una taxonomía oficial completa.

Regla: ID estable, proveedor, campos, igualdad literal o nodo completo de jerarquía, valores explícitos, outcome, arquetipos/alternativas y justificación. La comparación usa NFKC, espacios normalizados y case folding, conservando raw. Se restringe a proveedor/campo; no hay regex de palabras ni substring “gym” que convierta “Not a Gym” en gimnasio. En jerarquías gana el nodo más específico. Colisiones de igual especificidad con resultados distintos retornan ambigüedad en lugar de depender del orden de reglas.

La normalización explícita puede ser fallback cuando el original no tiene regla; si el original específico refina una etiqueta normalizada amplia, se conserva esa precisión. Una etiqueta incompatible produce `ORIGINAL_NORMALIZED_CONFLICT`. Una jerarquía Foursquare incompatible con su cadena original se bloquea como ambigua.

Una extensión añade reglas versionadas y tests. Puede admitir nuevos proveedores sin modificar el algoritmo; si el arquetipo requerido no existe en el enum V1, necesita una revisión contractual explícita. No alias automático `catalog → product_catalog`, ni reinterpretación silenciosa `checkout → purchase`.

## Clasificación y abstención

| Estado detallado | Significado | BusinessProfileV1.classification |
|---|---|---|
| RESOLVED | Una actividad comercial inferida y modificadores compatibles | RESOLVED |
| HYBRID | Actividades distintas con relación COEXISTING explícita y evidencia aprobada | RESOLVED |
| AMBIGUOUS | Alternativas/colisiones, contradicción comercial/no comercial o actividades sin coexistencia probada | UNRESOLVED |
| PARTIAL | Parte mapeada y parte desconocida o no soportada | UNRESOLVED |
| UNKNOWN | Ninguna observación permite actividad específica | UNRESOLVED |
| ABSTAINED | No hay categorías para resolver | UNRESOLVED |
| NON_BUSINESS | Todas las observaciones clasificadas explícitamente como no comerciales | NON_BUSINESS |

La salida detallada queda junto al profile, sin añadir campos a V1. Los casos UNRESOLVED incluyen solicitud `classification_review` upstream. No se generan rutas, requisitos de frontend, precios, contactos o ofertas desde una categoría.

Múltiples fuentes con actividades distintas podrían describir un híbrido o estar equivocadas. Solo una relación upstream `COEXISTING`, con IDs de observación y hechos `activity:coexisting=true`, aprobados, vigentes y scope de negocio, permite resolver HYBRID. `ALTERNATIVE` conserva ambigüedad. El modificador `regulated_services` puede acompañar un arquetipo sin declarar otra actividad comercial.

Confidence conserva el mínimo aportado por upstream entre observaciones pertinentes; no es una probabilidad calibrada ni reemplaza revisión factual. El clasificador necesita input válido/protocolo verificado antes de usos productivos; RESOLVED es una interpretación de actividad, no INPUT_VALID, CUSTOMER_READY o permiso de publicación.

## Cobertura y riesgos

Los 19 casos sintéticos prueban nueve pares sector/proveedor principales (restaurante/retail/gym en tres fuentes), además de salud, hotel, servicio a domicilio, vehículo, asesoría, educación, eventos, industria, espacios y logística. Las pruebas adicionales incluyen ambigüedad, coexistencia, modifiers, desconocidos, proveedores nuevos, abstención, no-negocio y no-inferencia operacional. Esto no demuestra cobertura empírica del archivo real.

Pendientes: categorías no representadas por semillas; ampliación revisada de campos/subtipos/IDs; distinción comercial de instituciones públicas/mixtas; revisión de etiquetas broad y NON_BUSINESS; taxonomía cambiante; selección de actividad por branch; confianza no calibrada; asociación con observaciones upstream reales. La estrategia ante ausencia de regla es UNMAPPED/abstención, nunca inventar funcionalidades para completar cobertura. El crosswalk actual fue auditado contra el inventario; sus límites requieren revisión antes de H2.
