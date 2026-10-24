# H1 — revisión humana en curso

Fecha: 2026-10-09. Base técnica inspeccionada: `3f2d2f36e1617ae600237b6b289473e8209554bc`.

El usuario solicita continuar la revisión humana con H1. Esto no constituye aprobación global de H0 o H1 ni instrucción para corregir código ahora. Las correcciones se acumularán para un prompt final según el acuerdo registrado en [H0](h0-human-review.md).

## Qué se presenta al usuario

H1 tiene dos responsabilidades: interpretar categorías de distintos proveedores con reglas comunes y validar un paquete candidato de datos upstream conservando procedencia, versión, alcance e integridad.

Ejemplos probados: OSM `amenity=restaurant`, Foursquare `Dining and Drinking > Restaurant > Italian Restaurant` y Overture `taxonomy.primary=restaurant` sugieren `food_hospitality`. OSM `shop=hardware` sugiere retail; `leisure=fitness_centre` sugiere membresías/clases. Una categoría sugiere capacidades a investigar, no confirma operaciones ni produce un sitio.

En conexión con el feedback H0, el arquetipo puede servir para consultar un catálogo compartido de requisitos. El catálogo completo de datos solicitado por el usuario no está implementado por estas listas de capacidades candidatas.

## Evidencia inspeccionada

- Inventario real de vocabulario: 4.582 filas, no 4.582 negocios únicos. Se conservan raw, proveedor/campo, jerarquías disponibles, conteos y procedencia.
- Registry: 67 reglas semilla; 60 participan en resoluciones finales.
- Cobertura por filas MAPPED: Foursquare 189/890 (21,24%), OSM 59/1.195 (4,94%), Overture 77/2.497 (3,08%). No son porcentajes de negocios soportados.
- 4.251 filas permanecen UNMAPPED/UNKNOWN/AMBIGUOUS. Algunas son infraestructura, categorías amplias o capas repetidas; no se pueden convertir todas automáticamente en negocios ni declarar irrelevantes sin revisión.
- El mismo valor puede tener resultado distinto según proveedor/campo; por ejemplo Overture basic_category no tiene reglas en esta versión. Es una limitación conocida del mapping.
- Categorías desconocidas, ambiguas y no comerciales se distinguen. Dos actividades sólo producen híbrido si hay evidencia explícita de coexistencia; no basta con etiquetas contradictorias.
- Protocolo propuesto, no integración real con 101-world-model. Checksum comprueba integridad, no autenticidad de la fuente ni autorización.

## Comprobación durante esta revisión

53/53 pruebas actuales PASS ejecutando `tests/taxonomy.test.ts`, `tests/taxonomy-audit.test.ts`, `tests/taxonomy-inventory.test.ts` y `tests/upstream.test.ts`, con Node portable 24.21.0. Es una ejecución dirigida de H1, no la suite total ni un nuevo build/replay de todos los hitos. Los tests de auditoría usan temporales propios; no se regeneró la evidencia histórica.

## Correcciones solicitadas por el usuario para el prompt final

El usuario señala que el sistema debe entender el tipo de negocio usando los otros datos y recursos que recibe, y no depender de que una categoría tenga regla en el diccionario. Se registra como requisito de interpretación contextual; no se modifica código durante la revisión.

- H1-C01: clasificar a partir del conjunto de evidencia disponible: categorías, descripción aprobada, ofertas/productos/servicios, hechos de actividad y otros recursos accesibles/autorizados con procedencia. Evaluar datos reales del negocio, no asociaciones entre filas agregadas del inventario. Nombre y etiquetas amplias pueden ser pistas, no evidencia suficiente por sí solos.
- H1-C02: una categoría UNKNOWN/UNMAPPED no debe impedir resolver el tipo cuando el resto de datos lo sustenta. Conservar literalmente esa observación y su diagnóstico, pero permitir una interpretación trazable basada en otras evidencias. El fallback y sus criterios necesitan especificarse y probarse en la corrección posterior.
- H1-C03: explicar qué datos justifican la interpretación, distinguir actividades por negocio/sucursal, considerar coexistencia y contradicciones y reevaluar cuando cambien los datos. Inferir tipo de negocio no confirma capacidades operativas, disponibilidad, permisos o integraciones.
- H1-C04: explorar las evidencias disponibles pertinentes antes de pedir aclaraciones. Si son insuficientes o contradictorias, conservar alternativas y pedir el dato concreto que permita decidir. No prometer certeza universal con datos imposibles ni fabricar evidencia o acceso a recursos ausentes.

Ejemplo conceptual para criterios futuros: categoría desconocida + descripción de restaurante + oferta aprobada de platos puede sustentar actividad gastronómica; categoría desconocida + descripción de gimnasio + membresías/clases puede sustentar membresías/clases. No son resultados producidos ahora por H1 ni nuevas evidencias reales. Casos ambiguos e híbridos requieren preservar el contexto y alcance.

## Puntos todavía sin decisión

1. Confirmar que el traductor común de categorías debe permitir consultar el catálogo de datos compartido solicitado en H0, sin confirmar capacidades desde la categoría.
2. Revisar cobertura y plan de ampliación por proveedor/campo; preservar trazabilidad y evitar rules generales que inflen resultados. No priorizar automáticamente por sumas de negocios inexistentes.
3. Definir el siguiente paso accionable cuando la clasificación es ambigua/desconocida: qué información aclaratoria pedir y cómo conservar alternativas. No implementar esta política durante la revisión.
4. Confirmar compatibilidad del protocolo con snapshots upstream reales cuando estén disponibles; no tratar la propuesta actual como integración terminada.

Estado: feedback H1 registrado sobre comprensión contextual y resolución con datos adicionales; aprobación humana global todavía no registrada. No hay cambios funcionales ni commit de cierre humano.
