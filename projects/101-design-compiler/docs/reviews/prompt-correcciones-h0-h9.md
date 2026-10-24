# Prompt consolidado — correcciones de la revisión humana H0–H9

Preparado el 2026-10-12 para ejecutar posteriormente en `C:/Users/gabri/101-design-compiler`. Este archivo reúne el encargo; prepararlo no implica haber ejecutado sus instrucciones ni haber aprobado visualmente los sitios actuales.

---

Implementa las correcciones acordadas en la revisión humana de H0–H9 de `101-design-compiler`. Construye sobre el proyecto y el runtime compartido disponibles. El objetivo es que el motor produzca páginas completas, visualmente cuidadas, con buen audiovisual e identidad propia, y que permita evaluarlas, corregir el motor y conservar exactamente la versión que yo elija y apruebe.

Los PASS históricos acreditan slices técnicos de laboratorio. Durante la revisión humana se rechazó la suficiencia estética de las demostraciones mínimas. No presentes otra página con dos textos y una foto como prueba de calidad del producto, ni cierres estas correcciones únicamente porque pasen los tests.

## 1. Lectura, estado y límites

Lee primero `docs/pipeline.md`, la especificación íntegra V0.2, `docs/h0-findings.md`, contratos, informes H0–H9, revisiones independientes, `docs/coordinacion-autonoma.md` y todas las notas `docs/reviews/h0-human-review.md` a `h9-human-review.md`. Lee también:

- `data/reference/design/101_referencias_aprobadas_completas_v01.md`.
- `docs/reviews/h4-reference-intake-2026-10-12.md`.
- `docs/reviews/h4-layout-strategy-2026-10-12.md`.
- `docs/reviews/h3-provider-options-2026-10-09.md` y `docs/h3-providers.md`.

Inspecciona Git y las instrucciones aplicables del repositorio. La base observada en la revisión fue `3f2d2f36e1617ae600237b6b289473e8209554bc`; vuelve a comprobar el estado real. Las notas de revisión y el corpus recibido pueden estar sin tracking: son trabajo intencional del usuario y deben preservarse. No borres o descartes cambios ajenos ni archivos temporales indiscriminadamente.

Repite el baseline apropiado: tests, check, validación, build, exportación/comprobación de contratos, auditorías/replays/verificadores pertinentes de medios, bindings, diseños, cohorte y locks. Registra fallos sin reescribir evidencia histórica ni fingir PASS. No ejecutes recorders creativos o reseal como parte de replay para ocultar diferencias.

`101-world-model` y el runtime comercial histórico no están disponibles aquí. Comprueba qué existe realmente y usa Astro local como laboratorio compartido cuando corresponda; no anuncies integración ausente ni construyas una plataforma paralela. Preserva contratos V1: introduce versiones o artefactos asociados para cambios incompatibles y prueba lectores existentes.

No implementes H10, pagos, reservas operativas, backend comercial o despliegues productivos. Sí documenta cómo incorporar esas funciones y representa sus estados de demostración con honestidad. No compres licencias, abras cuentas, contrates APIs/modelos o generes gastos nuevos sin autorización explícita. Puedes probar acceso existente y adquirir recursos gratuitos puntuales sólo cuando sus términos y el uso concreto lo permitan. No contactes proveedores o terceros sin autorización específica.

Trabaja por bloques revisables; conserva una matriz de requisito → implementación → evidencia → estado. Resuelve decisiones rutinarias autónomamente y agrupa solicitudes de datos/preferencias realmente faltantes. No pidas repetidamente permisos ya concedidos, pero tampoco inventes autorización para una operación que un proveedor prohíbe.

## 2. H0 — catálogo único de datos y funciones

Define una sola vez un catálogo maestro versionado de requisitos, compuesto por datos comunes a negocios, requisitos por función y agrupaciones por tipo/arquetipo. Todos los restaurantes consultan la misma lista y reglas; cambian los valores/evidencia de cada negocio, no la definición del formulario. Las funciones compartidas entre sectores reutilizan su ficha. No convertir este catálogo en plantillas visuales ni código por cliente.

Cubre todas las capacidades del registry existente, sus niveles de servicio y dependencias; no limitarlo a los datos presentes en fixtures. Cada ficha debe especificar objetivo, comportamiento esperado, datos obligatorios/condicionales, evidencias/publicación, medios/permisos, configuración, sucursal, dependencias de plataforma/proveedor y criterios de prueba. Distingue especificado, implementado y verificado.

Por negocio/sucursal muestra qué se puede hacer hoy, qué puede añadirse, qué datos tenemos, cuáles faltan, quién debe aportarlos y cuál es el siguiente paso. Conserva todo el inventario de requisitos aunque el primer bloqueo impida emitir una función. Distingue no aplicable justificado, desconocido, rechazado, datos faltantes y soporte pendiente. La falta de datos no elimina una necesidad del objetivo.

El score funcional de 1–10 NO es prioritario ni requisito central. Lo importante es la lista accionable. Para reservas, diferencia contacto, solicitud, enlace externo y confirmación mediante sistema conectado; documenta los requisitos de cada variante sin construir el backend ahora.

## 3. H1 y H2 — comprensión contextual y planificación

H1 debe interpretar el conjunto de evidencias disponibles: categorías, descripciones, ofertas/productos/servicios, hechos de actividad y recursos pertinentes autorizados. Una etiqueta desconocida o sin mapping no debe bloquear clasificación si el resto sustenta la actividad. Conserva la observación original y explica qué evidencia respalda la interpretación. El nombre por sí solo no confirma una actividad.

Considera híbridos, sucursales, evidencia insuficiente y contradicciones. Explora lo disponible antes de pedir aclaración y pide el dato específico que permite resolverla. No fuerces certeza universal ni transformes clasificación inferida en capacidades operativas confirmadas. No instancies negocios ni asociaciones entre fuentes desde filas agregadas de inventario.

Mantén H2 como está en sus responsabilidades y garantías; el usuario decidió conservarlo por ahora. Introduce sólo los ajustes necesarios para consumir el catálogo y la clasificación corregidos, con contratos/versiones y regresiones verificadas. Preserva semántica, referencias, publicación/vigencia, alcance y dependencias. Explica READY como plan válido de lo emitible, sin presentarlo como sitio completo o conectado. No reescribas el planner o taxonomía para crear soluciones particulares por sector.

## 4. H3 — audiovisual prioritario y obtención comprobada

Disponer de buen audiovisual es una prioridad esencial, no un complemento opcional. Implementa un recorrido trazable: necesidad → búsqueda permitida → selección/inspección → obtención → presentación/optimización autorizadas. Una API configurada no completa este requisito.

El usuario dispone de una clave de Pixabay, pero su autenticación/cuota/alcance no se han probado. Recíbela mediante configuración privada, por ejemplo `PIXABAY_API_KEY`; nunca copies su valor al prompt, repo, fixtures, URLs de logs o reportes. No la busques en archivos ajenos. Si falta en el entorno, solicita configuración privada y continúa con trabajo independiente; no declares la conexión funcionando hasta probarla.

Verifica documentación oficial y términos vigentes antes de conectar. Pixabay permite búsqueda de imagen/video y documenta restricciones sobre solicitudes humanas, caché y descargas masivas: no asumir que autoriza un crawler autónomo. Su biblioteca de audio no implica API de audio verificada. Pexels tenía nuevas claves pausadas el 2026-10-09; comprueba disponibilidad antes de recomendarlo como conexión accesible. Otros proveedores quedan condicionados a acceso, licencia y operación demostrados.

Busca según rol, tema, contenido y dirección artística. Inspecciona archivos reales y compara pertinencia, encuadre, resolución, calidad percibida y peso; registra sólo lo efectivamente observado. No asumir que más resolución o popularidad significa mejor resultado. Conservar procedencia, original/derivados, hash, documento/versión, alcance de cliente/proyecto/sucursal/uso, atribución, terceros y restricciones. Comprueba por separado acceso automatizado, modificaciones, almacenamiento/retención, multicliente y operaciones IA pertinentes.

Mantén DOCUMENTARY, ILLUSTRATIVE y ATMOSPHERIC. Stock no acredita platos, instalaciones o equipo de un negocio. Obtén material auténtico autorizado para esos usos o conserva el hueco exacto. Referencias estéticas tampoco son licencias de fotos/videos/código/fuentes. No reemplaces una necesidad documental por atmosférica para aprobarla.

Preserva el paquete USDA/ARS H3, sus bytes y permisos originales. Nuevos medios necesitan evidencia nueva; no amplíes su grant ni lo prestes a otros clientes. La biblioteca propia debe conservar reglas comunes versionadas y trazabilidad por archivo/uso, sin replicar catálogos de proveedores.

## 5. H4–H5 — muestras completas, criterio artístico y variedad real

Prepara demostraciones con aspecto de página final: contenido suficiente, todas las secciones aplicables, buen audiovisual autorizado y una composición cuidada. Las operaciones pueden seguir en modo demo. Separa interfaz pública de paneles técnicos de revisión; conserva avisos/atribución obligatorios y la identificación honesta del prototipo. No inventes hechos de un negocio real o permisos para llenarlo.

Una demo ficticia completa puede servir para evaluación estética, pero no sustituye los casos reales autorizados requeridos para H7/H9. Si faltan datos/materiales del piloto, presenta una solicitud concreta y conserva ese cierre pendiente; avanza con correcciones de plataforma y pruebas que no dependan de esos datos.

Implementa generación contextual probabilística sobre gramática y componentes compartidos, orientada por referencias/familias artísticas curadas. No limitar la personalización a tres páginas fijas, ni crear 1.000 templates completos como sustituto automático del criterio. El tamaño de gramática y umbrales deben justificarse con resultados; no imponer números arbitrarios o prometer 100.000 diseños únicos desde combinaciones teóricas.

Incorpora el corpus recibido: 21 positivos, 18 globales y 3 parciales, con intensidades y observaciones negativas. Inspecciona los diseños actuales en escritorio/móvil, registrando fecha, alcance y observaciones nuevas por separado de preferencias originales. Aponiente, Khufu's y Singer son aprobaciones parciales. No inventar por qué gustaron OSIP/Central cuando el documento no lo desglosa, ni aplicar estética gastronómica a todos los sectores.

La dirección artística debe gobernar coherentemente jerarquía, tipografía, color, ritmo, navegación, composición, medios y motion cuando proceda. Clasifica feeling con criterios visuales concretos; no asignar un layout fijo a cada etiqueta. Amplía diversidad estructural, relación texto/medio, proporciones y comportamiento móvil. Cosmética, seeds o más intentos no prueban diversidad.

Distingue restricciones obligatorias de decisiones artísticas: conservar contenido/permisos, legibilidad, navegación y geometría válida; simetría, vacío o asimetría son opciones contextuales. Superposiciones deliberadas requieren legibilidad y permiso de tratamiento. Mantén presupuestos y rechazo de código/dependencias arbitrarios.

Especifica y prueba cómo se producirán propuestas nuevas mediante un productor autorizado de sesión o API disponible. Conserva prompt/contexto/output/versiones/procedencia y fallos. Reproducir JSON grabado no demuestra generación nueva ni llamada API. No atribuyas referencias recién recibidas a ejecuciones históricas. Instrumenta llamadas/tiempos/consumo cuando disponibles; desconocidos explícitos, no ceros ficticios.

## 6. H6 — evaluación humana granular e iteración del motor

Amplía el panel y el registro de evaluación: elección global A/B/empate/ninguna, nota estética global de 1–10 por candidato, comparación por tipografía, paleta, distribución/tamaños y audiovisual. Añade detalle opcional de ritmo/espacio, identidad, navegación y motion cuando existan. Permite notas por aspecto, motivos de rechazo, comentarios literales y localización por sección/elemento.

Sin respuestas o notas preseleccionadas. Soporta no evaluado/no aplicable. La elección relativa no demuestra entusiasmo; una nota aislada no es aprobación global. Conserva candidato/versiones, datos, página, viewport, capturas, autor/fecha y alcance. Exporta/importa o conserva preferencias de forma trazable y utilízalas efectivamente en propuestas posteriores, sin exigir backend comercial nuevo.

No obtener la nota global promediando aspectos automáticamente. Preferir fuente A y paleta B permite explorar una nueva combinación; requiere render y evaluación propios. Aprende preferencias condicionadas por contexto y conserva juicio de armonía del conjunto. No presentar pesos heurísticos como modelo calibrado, ni referencias de terceros como votos sobre nuestros diseños.

Si ninguna propuesta gusta, identifica el motivo, ajusta parámetros/reglas o componentes del motor compartido y genera otras. Verifica mejora y regresiones con before/after y rollback. No añadir hacks de cliente ni editar hechos/permisos para aprobar. El reparador actual sólo demostró una reparación de ancho; demuestra las nuevas capacidades antes de anunciarlas.

Checks técnicos y evaluación estética son resultados separados. Incluye audiovisual nuevo, adaptación y carga por viewport; métricas raster no acreditan belleza y una nota alta no compensa permisos, hechos o accesibilidad fallidos.

## 7. H7 — validación con páginas reales y muestra independiente

Valida el recorrido corregido en varios tipos de negocio con páginas completas, contenido suficiente y medios reales/autorizados. Mantén los fixtures mínimos como controles técnicos, no prueba de estética/producto. Incluye híbridos, sucursales, datos incompletos, categoría desconocida con evidencia suficiente y casos genuinamente ambiguos.

Utiliza casos reales autorizados y distingue sus fuentes/permiso de fixtures. Si no existen inputs/materiales suficientes, documenta exactamente qué falta y no declares esta condición cumplida. No usar las webs de referencia como clientes autorizados. Pilotos pueden ser privados y sus operaciones demostrativas: no se exige desplegar ni conectar pagos/reservas para juzgar estética.

Reserva casos nuevos antes de evaluar. Conserva primera ejecución/fallos, mejora componentes comunes y usa otro grupo no empleado para ajustes cuando se mida generalización inédita. Evalúa cada caso/ruta en escritorio/móvil, con capturas, geometría/desbordamiento, lectura, navegación/accesibilidad, bytes/carga/medios, checks y preferencias reales. No ocultar un mal caso detrás de un promedio global o de una estética única para todos.

## 8. H8 — versión elegida, recuperación y entorno reproducible

El lock final debe corresponder al resultado exacto que yo escoja y apruebe, con contenido/medios/composición, evidencias y aprobación vinculada a versión y alcance. Intentos rechazados o snapshots técnicos pueden conservarse como historial, sin presentarlos como entregables aprobados. Si no me gusta, continúa el ciclo de feedback y corrección del motor; conserva la última versión aceptada.

Extiende contratos de aceptación de forma versionada. Los locks históricos están explícitamente sin aprobación humana: no añadirles una aprobación retroactiva. Cambios relevantes tras aprobación generan una nueva versión y reevaluación. Un lock no concede derechos perpetuos ni permite saltarse comprobaciones al publicar/reutilizar.

Reconstruye sin nueva generación, búsqueda de medios o decisiones probabilísticas. Prueba recuperación de la versión anterior y ausencia de regresiones. La reproducción debe conservar entornos/fuentes/herramientas pertinentes.

Hay un fallo actual comprobado: los locks fijan Edge 154.0.4258.62, pero se detectó Edge 155.0.4283.45 el 2026-10-12. Las pruebas dirigidas dieron 13 PASS y 1 FAIL por LOCK_BROWSER_MISMATCH antes del caso de corrupción de evidencia. Resuelve el aislamiento/materialización del entorno reproducible y distingue reconstrucción histórica de migración versionada al nuevo entorno. No cambiar hashes, relajar gates o reemplazar evidencia para esconderlo. No degradar el navegador global para satisfacer un test ni prometer equivalencia universal. Preserva resultados históricos y crea evidencia nueva de la solución.

## 9. H9 — medir resultados reales, sin cierre ficticio

Instrumenta costos/tiempos desde las primeras corridas nuevas, pero deja el benchmark condicionado a páginas reales aprobadas y muestra/método suficientes. Hoy sólo está verificado un inventario; H9 sigue BLOCKED_EXTERNAL_EVIDENCE / NOT_TESTED, con cero sitios reales aprobados elegibles.

Registra intentos rechazados, revisiones/correcciones, llamadas/consumo real disponible, adquisición/licencias, recursos compartidos y tiempo humano por separado de tiempo de máquina. Define atribución, moneda y tarifas observadas. Cero gasto nuevo no equivale a costo total cero; no fabricar tokens, facturas o trabajo humano histórico.

Calcula costo por aprobado y distribuciones sólo con denominadores válidos y método declarado. No calcular p50/p90 o aprobar volumen/calidad de proveedores desde una foto o una clave API. Preferencias sobre 21 webs de terceros no cuentan como sitios aprobados producidos por nuestro motor. Si falta evidencia externa, conserva bloqueo y siguiente paso concreto; no declarar H9 completo.

## 10. Orden, entrega y revisión

Primero diagnostica baseline y prepara reproducción/capturas controladas; instrumenta las nuevas corridas. Después corrige catálogo/comprensión con compatibilidad H2, obtención audiovisual y corpus, gramática/demos completas, evaluación/iteración, casos multiverticales y lock aprobado. H9 se evalúa cuando haya resultados elegibles. No avances H10.

Por bloque entrega cambios revisables, informe, evidencias y estado: implementado, técnicamente verificado, pendiente de input, pendiente de evaluación humana o rechazado. Ejecuta checks adecuados y tests significativos de contratos/bindings/medios, contexto, ausencia de datos, feedback y reconstrucción; no tests que únicamente repitan la implementación. Corrige fallos observados, inspecciona vistas nuevas en navegador y completa checks antes de proponer el commit de cada bloque. Excluye secretos, dependencias ignoradas y temporales; incluye notas/corpus intencionales que correspondan.

El usuario autoriza notificar a la tarea revisora `01a11911-1da1-73e0-8234-132547fc8f8f` al terminar cada bloque/hito: envía commit, ruta del informe y resultados, pide revisión independiente y espera feedback y prompt propuesto. Si no se puede enviar, informa que no fue entregado. No crear chats nuevos ni suponer recepción. No inicies el siguiente bloque/hito sin mi aprobación conforme al protocolo humano autorizado; dentro del bloque continúa el trabajo independiente para completar lo revisable.

Presenta páginas completas para mi revisión visual y recoge elección/rechazo real. Si no me gustan, itera corrigiendo el motor compartido antes de cerrar estéticamente. No confundir commit reproducible técnico con aprobación de diseño/producto.

Entrega un informe de correcciones con trazabilidad a H0-C…H8-C y condiciones H9, versiones nuevas, evidencia técnica/visual, feedback aplicado, límites, datos pendientes y siguiente paso. Usa lenguaje claro: quiero saber qué funciona, qué falta, cómo se verá y qué necesito aportar. No declares calidad, personalización a escala o producción sin demostración.
