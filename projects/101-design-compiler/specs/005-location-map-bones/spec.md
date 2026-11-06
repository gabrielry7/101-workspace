# Feature Specification: Huesos de ubicación de un negocio

**Feature Branch**: `codex/location-map-implementation-20261105`
**Created**: 2026-11-05
**Status**: Implementado y verificado localmente; Google vivo y aprobación humana pendientes.
**Input**: «Haz la implementación y después muéstrame cómo quedarían los huesos».

## User Scenarios & Testing

### US1 — Revisar el hueso y aplicar un logo (P1)

El operador compara el original de Tomás, el hueso neutro y una piel de prueba.
Se reutiliza su primitiva real de mapas; las composiciones direct, map-led y
editorial conservan sus regiones y comportamiento, retirando la marca.

Aceptación: el mapa interactivo muestra un marcador propio, cero negocios ajenos;
el logo sigue la coordenada al desplazar, ampliar, redimensionar y cambiar piel.
La anatomía nombra cada parte. Configuración y estado se pueden recuperar.

### US2 — Ubicación y medios verdaderos (P1)

La instancia vincula negocio, sucursal y coordenadas comprobadas; la piel nunca
cambia esos hechos. Logo autorizado por los gates existentes; sin permiso o con
fallo de imagen, pin neutro. Sin coordenadas elegibles, dirección/indicaciones
sin punto inventado. Datos sintéticos siempre identificados y sin navegación real.

### US3 — Elegir proveedor con límites honestos (P1)

MapLibre consume el dueño existente, coordenadas independientes y mapa local.
Google JS usa sus APIs oficiales y estilo cloud sin POIs, con configuración
explícita; sin configuración no realiza peticiones y conserva el fallback.
El iframe queda ineligible para esta familia. Prueba simulada de Google y
verificación real se reportan por separado.

### Edge cases

Logo ausente, revocado, otra sucursal, fuente Google restringida en MapLibre,
configuración con POIs, JS/WebGL/red fallidos, destrucción durante carga, texto
largo, colores forzados, movimiento reducido, teclado/tacto y ausencia del dueño privado.

## Requirements

- **LM-01**: Reutilizar `packages/location-map@0.3.0` fijado al commit de la ficha;
  no publicar su código/medios privados ni alterar el original. Extender mediante
  su hook confiable y su API nativa; agregar Google como adaptador de proveedor.
- **LM-02**: Fijar POIs en none; rechazar intentos de reactivarlos y proveedores
  incompatibles. Conservar calles, créditos y un único marcador no arrastrable.
- **LM-03**: Resolver logo con `rightsGate` y `evaluateSuitability`, asociarlo a
  negocio/sucursal, conservar proporción, nombre accesible y anclaje medible.
  Fallo/ausencia/denegación produce pin neutro con motivo. No aceptar HTML arbitrario.
- **LM-04**: Preservar identidad, fuente, fecha y elegibilidad del contrato original;
  sin coordenada válida no hay marcador. Publicación denegada no se transforma en permiso.
- **LM-05**: Añadir Google JS con carga compartida explícita, map ID y referencia
  de estilo cloud revisado sin POIs. Configuración incompleta/carga fallida produce
  fallback. No cargar un servicio facturable por defecto ni fingir verificación viva.
- **LM-06**: Componente Astro reutilizable con tres composiciones tomadas de las
  demos existentes; separación hueso/piel/contenido, estados, SSR útil sin JS,
  taller y comparación privada con original. El taller no entra en markup de cliente.
- **LM-07**: Verificar contratos positivos/negativos, componente real en navegador
  nativo a 360/768/1440 y 619/620/621, fuentes de respaldo, teclado, logo fallido,
  pan/zoom, cambio de piel, sin JS, movimiento reducido y colores forzados.
- **LM-08**: Guardar diff propio, commit/push verificable, documentación y límites
  observados. No publicar el build privado, desplegar ni conceder aprobación humana.

## Success Criteria

- En las vistas compatibles, cero negocios ajenos y un marcador de la sucursal.
- Coordenadas/destino no cambian al interactuar; error del anclaje ≤1 px CSS estable.
- Todos los estados de error conservan texto/acciones elegibles sin datos inventados.
- Cero overflow de página y palabras partidas artificialmente en los tamaños probados.
- Original, neutro y aplicación de prueba disponibles localmente, sin llamadas de pago.

## Assumptions

La demostración usa fixture sintético con logo de prueba. No se suministró una nueva
identidad/ubicación comercial autorizada ni configuración Google. La integración
queda operativa para entradas elegibles; la prueba viva de Google depende de esa
configuración y no se sustituye por mocks. El modelo general sigue en spec 002.
