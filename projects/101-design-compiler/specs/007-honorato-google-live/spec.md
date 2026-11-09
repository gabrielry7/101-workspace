# Feature Specification: Prueba de Honorato con Google Maps personalizado
**Branch**: `codex/honorato-google-live-20261109` | **Created**: 2026-11-09
**Status**: Implementado y verificado con Google real; pendiente de revisión visual del usuario.
**Input**: Crear proyecto, publicar estilo, configurar Map ID y clave de navegador; probar Honorato con Google. El usuario autorizó hasta US$1 para esta prueba.

## User Scenarios & Testing
### US1 — Preparar la cuenta y el mapa (P1)
Crear recursos dedicados a la prueba y una clave restringida, conservando otras aplicaciones.
**Independent Test**: Consultar proyecto/servicios/estilo/asociación/restricciones con su dueño autenticado.
**Acceptance**: El mapa tiene un estilo propio sin lugares ajenos, identidad de mapa propia y acceso limitado al origen local autorizado.

### US2 — Revisar Honorato en el componente existente (P1)
Ver ubicación con fuente conservada sobre Google real, conservando permisos del logo y alternativas.
**Independent Test**: Renderizar la vista local, comprobar proveedor real y coordenadas/indicaciones.
**Acceptance**: Un marcador de sucursal, sin negocios ajenos; logo sólo si pasa los gates, alternativa neutra en otro caso. No trasladar coordenadas restringidas a otro proveedor.

### US3 — Respetar presupuesto y privacidad (P1)
Conservar claves/tokens fuera de Git y limitar cargas de la prueba.
**Independent Test**: El servidor rechaza nuevas inicializaciones al consumir el cupo; ninguna respuesta pública incluye OAuth.
**Acceptance**: Máximo US$1 autorizado; plan inicial de hasta 10 cargas de un mapa y ningún servicio Places/Street View.

### Edge Cases
Cuenta no habilitada, facturación pendiente, API sin permisos, estilo no aplicado, key/referrer inválidos, logo inelegible, límite consumido y reinicio del servidor.

## Requirements
- **HG-01**: Proyecto y recursos de prueba separados; no modificar otras aplicaciones.
- **HG-02**: Clave de navegador restringida al origen local y Maps JavaScript API.
- **HG-03**: Crear/asociar estilo sin lugares y comprobarlo en Google real; no sustituirlo por iframe.
- **HG-04**: Reutilizar SingleBusinessLocation, dueño geográfico y adaptador existentes con datos de Honorato conservados.
- **HG-05**: Respetar gates del logo/publicación; sin evidencia suficiente usar pin neutro y registrar motivo.
- **HG-06**: Registrar límite US$1, cargas y procedencia de estimación; no depender sólo de alertas de presupuesto.
- **HG-07**: Secretos/datos privados fuera de commits; registro público sólo de código/esquemas y resultados no sensibles.
- **HG-08**: Verificar y guardar cambios propios en GitHub.

## Success Criteria
Un mapa real verificable con una sucursal y cero negocios ajenos; punta ≤1 px CSS tras estabilizar vista; sin overflow móvil/escritorio.
Ninguna clave OAuth expuesta; clave web limitada. Cupo de prueba preservado al reiniciar y cero inicializaciones adicionales al agotarlo.

## Assumptions
OAuth iniciado por el usuario; una cuenta de facturación activa accesible.
La autorización de prueba no equivale a publicación comercial de Honorato o su logo.
Recursos de Maps Management no tienen coste según documentación; las cargas reales se presupuestan por Dynamic Maps.

## Delivered evidence
Ver [verificación pública](../../docs/bones/honorato-google-verification.json) y
[operación local](../../docs/bones/honorato-google.md). Google real se verificó en
Chromium con siete anchos, zoom y arrastre; se conservaron coordenadas y gates.
La inspección visual del agente confirma ausencia de negocios ajenos en las vistas
observadas; Google no expone un inventario exhaustivo de POIs renderizados.
El entorno headless utilizó el fallback raster de Google al no disponer de WebGL.
En esa verificación inicial el logo real estaba pendiente; el pin neutro fue la
alternativa prevista en HG-05. El refinamiento siguiente incorpora la autorización
posterior del usuario y el logo. La aprobación visual humana del resultado sigue pendiente.

## Refinamiento solicitado: logo dentro del pin, sin etiqueta (2026-11-09)
El usuario confirma expresamente permiso para usar el logo de Honorato y solicita
mantener la forma del pin con el logo dentro, quitando el recuadro visible del nombre.
Registrar esta declaración como autorización del usuario para la prueba local,
sin presentarla como un contrato externo ni como permiso de redistribución pública.
Usar el símbolo existente de la marca conservando los trazos, proporción y procedencia;
el wordmark horizontal completo no cabe de forma legible dentro del marcador.
Reutilizar los contratos de medios y el mismo componente/adaptador. La etiqueta
visible será una opción booleana del componente, por defecto activada para preservar
otros consumidores. Honorato la desactiva; el nombre accesible y el foco de
indicaciones se conservan. Mantener fallback neutro al fallar la imagen, anclaje
≤1 px, ubicación, estilo sin POIs y presupuesto existentes. Versión del hueso 0.2.1.
**Prueba de aceptación**: Google real carga el logo dentro del pin sin recuadro del
nombre; escritorio/móvil, zoom y arrastre mantienen el destino. Guardar evidencia
local y código propio en GitHub, sin publicar el SVG o la declaración privada.
