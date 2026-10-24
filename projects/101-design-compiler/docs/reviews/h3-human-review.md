# H3 — revisión humana en curso

Fecha: 2026-10-09. Base técnica: `3f2d2f36e1617ae600237b6b289473e8209554bc`. Cierre técnico histórico H3: `e2b83d441776bcc7d643ffa2f0c3dee4e648b62d`.

El usuario solicita revisar H3 después de mantener H2 sin cambios por ahora. Se presentan medios, permisos y huecos. No se realizan adquisiciones, cambios de contratos, modificaciones de permisos ni integración upstream. Correcciones futuras se acumulan para el prompt final.

## Responsabilidad

Generar necesidades de medios desde SitePlan/SiteRequirements por módulo, sujeto, sucursal y finalidad; contrastar activos con autorizaciones, calidad/pertinencia revisadas y representación; conservar usos permitidos y huecos. No es un buscador automático de proveedores ni un conector a catálogos. No demuestra elección estética óptima ni derechos por existir una URL.

Tres roles: DOCUMENTARY prueba el negocio/oferta/sede concretos; ILLUSTRATIVE explica de manera genérica; ATMOSPHERIC aporta ambiente sin acreditar identidad o producto. Una foto genérica no sustituye la documentación de un plato o sede.

## Caso presentado

Piloto restaurante: dos necesidades, una foto real atmosférica permitida y una necesidad documental bloqueada. USDA/ARS Bell peppers D255-19, autor Steve Ausmus. Revisión/adquisición de fuentes oficiales archivadas realizada el 2026-10-08; esta revisión humana verifica evidencia local, no realiza una nueva evaluación de términos online.

Original JPEG 2.351.102 bytes, 2700×1819; SHA256 `ffdb883d56a41ba9a03a51fb7d1bdf8f0b9e30d3946eda180b750620a17c3715`. Uso interno permitido sólo para cliente/proyecto/scope/página/finalidad definidos. El grant interno deliberadamente limita más usos que la declaración pública de la fuente; no confundir esa limitación con una prohibición general del titular.

Conserva crédito, etiqueta atmosférica y aviso de no respaldo USDA/ARS. No se autorizaron derivados, otros clientes/proyectos o usos IA/automatizados. Su presencia no demuestra que sean ingredientes, productos o platos del restaurante ficticio. La necesidad documental exige fotografía auténtica con vínculo factual y autorización verificable.

## Datos que documenta H3

Por archivo: procedencia, identidad de bytes, revisión/inspección real, sujeto/sucursal, original y linaje. Por permiso: documento/versiones, revisión, cliente/proyecto/uso/página/territorio/fecha, atribución, terceros, transformaciones y restricciones. Por uso: necesidad y módulo atendidos, rol y decisión con motivos. El hash acredita integridad, no autoría o derecho por sí solo.

La matriz histórica de proveedores separa comercial, multicliente, automatización, modificaciones, IA, atribución, releases, costos y restricciones. Investigar términos no autoriza un proveedor completo ni su descarga automatizada.

## Evidencia comprobada ahora

`scripts/verify-media-pilot.ts`: PASSED, AUTHORIZED_PILOT_PACKAGE_WITH_GAPS; original/documentos/render/atribución/contexto comprobados; HTML actual coincide con render; hueco documental sigue bloqueado.

66/66 tests dirigidos de `tests/media.test.ts` y `tests/media-pilot.test.ts` PASS con Node portable 24.21.0. Incluyen derechos desconocidos/vencidos/incompatibles, derivados, sucursales, inspección ausente y representación engañosa. No se ejecutó build completo ni se regeneraron evidencias históricas.

## Aspectos a revisar, sin decisión aún

- Cómo presentar al usuario las fotos reales necesarias y materiales genéricos opcionales, con una solicitud concreta de archivo, vínculo factual y autorización.
- Vincular necesidades de medios con el catálogo común solicitado en H0; el manifiesto actual por plan no equivale al catálogo aspiracional completo por tipo de página.
- Mantener diferencia entre permiso, autenticidad documental, pertinencia/calidad y suficiencia del paquete. Un archivo ALLOWED no cubre todas las necesidades.

## Correcciones solicitadas por el usuario

El usuario valora distinguir la finalidad de cada imagen/video/audio y pide conectar el sistema a fuentes de recursos de alta calidad para buscar y obtener medios pertinentes. También pide explicar el control de permisos y las condiciones en lenguaje sencillo. Se investiga documentación oficial; no se implementa la conexión durante la revisión.

- H3-C01: diseñar conectores a proveedores seleccionados con búsqueda/obtención expresamente autorizadas, según medio, rol y necesidad. Separar descarga manual, API, alojamiento remoto y almacenamiento local; no tratar permiso comercial como permiso de automatización. Cuentas, pagos y conectores quedan para el prompt posterior y su alcance autorizado.
- H3-C02: definir búsqueda y selección por finalidad, tema, contexto, calidad inspeccionada, encuadre/tamaño, peso y licencia compatible. La mejor calidad se evalúa por uso; no basta con popularidad, resolución o el nombre del proveedor. Inspección/procesamiento IA exige revisar permiso de esa operación.
- H3-C03: conservar una biblioteca interna de medios autorizados y procedencia por activo/uso, con reglas comunes versionadas por proveedor y licencia. Reutilizar las reglas sin presumir que todos los archivos o clientes tienen igual autorización; no copiar catálogos enteros ni mezclar licencias sin trazabilidad.
- H3-C04: explicar condiciones con ejemplos: crédito, modificación, cliente/proyecto, forma de alojamiento y ausencia de respaldo. El sistema debe cumplir y conservar automáticamente las condiciones que pueda, y explicar el bloqueo concreto en las restantes. No simplificar eliminando permisos.
- H3-C05: las fuentes externas pueden cubrir material genérico permitido; imágenes documentales del negocio/oferta/sucursal siguen requiriendo material auténtico y vínculo factual. No presentar stock como foto real del negocio.
- H3-C06: verificar disponibilidad real de onboarding/credenciales y alcance de acceso antes de recomendar una conexión como viable. Una API documentada puede tener nuevas claves pausadas. Pexels queda pendiente de acceso tras captura del usuario y verificación del aviso oficial el 2026-10-09; no se intenta eludir la pausa ni sustituir API por scraping.
- H3-C07: prioridad explícita del usuario: disponer de buen audiovisual es central para hacer viable el producto. El prompt final debe priorizar un recorrido comprobado de necesidad → búsqueda autorizada → selección/inspección → obtención → presentación y optimización permitidas, con archivos reales y huecos documentales conservados. Una API configurada o un manifiesto correcto no prueban suficiencia ni calidad audiovisual. La clave aportada de Pixabay no cambia esta distinción.

Investigación preliminar oficial del 2026-10-09: [comparación de proveedores](h3-provider-options-2026-10-09.md). No acredita permiso de un activo nuevo ni sustituye la evaluación histórica/paquete H3; no se descarga ningún medio.

El usuario aporta posteriormente una clave API de Pixabay. Se registra únicamente disponibilidad declarada de credencial; su valor no se copia en documentos, fixtures, código, logs ni prompt final. No se ha probado autenticación, cuota ni alcance. La implementación futura debe recibirla mediante configuración privada y comprobar una búsqueda/obtención permitida con evidencia de uso concreto, sin registrar el secreto. Durante esta revisión no se crea conector ni se consume la clave.

Estado: feedback H3 registrado sobre proveedores, selección pertinente y claridad de condiciones; revisión continúa. Sólo documentación, sin cambios funcionales ni commit.
