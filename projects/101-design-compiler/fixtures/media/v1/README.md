# Fixtures de contrato H3

`permissions.ts` crea afirmaciones **SYNTHETIC_FIXTURE**, incluyendo revisiones, dimensiones y permisos simulados. No hay imagen, video, documento de licencia, fotógrafo, proveedor ni revisión real asociados. Los hashes son SHA-256 de tokens de texto identificados explícitamente como sintéticos, no hashes de archivos audiovisuales.

El gate bloquea estos permisos por defecto. `allow_synthetic: true` habilita únicamente su evaluación controlada en pruebas. El brief conserva `PENDING_AUTHORIZED_MEDIA_PACKAGE` incluso en el control positivo. Nunca son un paquete de medios autorizado ni una fuente para sitios reales.

`tests/media.test.ts` muta esos contratos para probar permisos desconocidos, vencidos, revocados, de otro cliente/proyecto/finalidad/página/sucursal, derivados, releases, atribución, automatización, IA, calidad, pertinencia y representación engañosa. El harness genera siete manifiestos sin activos desde el planner H2 y dos controles sintéticos. Los dos escenarios H2 sin SitePlan se abstienen.

Condición de cierre de estos controles sintéticos: **PENDIENTE**. El paquete real separado en fixtures/media/pilot sí demuestra un uso atmosférico autorizado y conserva el hueco documental; no utiliza estas autorizaciones simuladas. Se necesita un paquete real, archivos originales con hashes comprobados, documentos y autorizaciones revisados por activo/uso/cliente/proyecto, inspección factual/visual y releases cuando correspondan. No se descarga ni se licencia contenido mediante este harness.
