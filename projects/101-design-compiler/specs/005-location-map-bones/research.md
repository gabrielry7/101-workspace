# Investigación y decisiones

- Decisión: API nativa y hook `decorateMap` del dueño fijado. Motivo: cambia el
  contenido del marcador real sin otra implementación de MapLibre. Alternativa
  rechazada: dibujar un mapa paralelo o poner una imagen sobre el iframe.
- Decisión: tres recetas parentales de las demos direct/map-led/editorial,
  extraídas como variantes Astro. No son aprobaciones humanas nuevas.
- Decisión: logo evaluado en servidor por gates existentes; sólo binding de salida
  serializable, nunca documentos privados o HTML/SVG sin validar en el navegador.
- Decisión: Google requiere map ID y estilo cloud revisado. AdvancedMarkerElement
  requiere map ID; `MapOptions.styles` no se aplica con map ID/vector. No combinar
  ambos ni usar DEMO_MAP_ID como prueba de POIs ocultos.
- Decisión: no activar Google sin opt-in/configuración; prueba offline usa API
  simulada identificada. La revisión viva del estilo queda pendiente de credenciales.

Fuentes oficiales consultadas:
[map options](https://developers.google.com/maps/documentation/javascript/reference/map),
[advanced markers](https://developers.google.com/maps/documentation/javascript/reference/advanced-markers),
[cloud JSON](https://developers.google.com/maps/documentation/javascript/cloud-customization/json-reference),
[loader](https://developers.google.com/maps/documentation/javascript/load-maps-js-api),
[projection](https://developers.google.com/maps/documentation/javascript/reference/overlay-view).
No incógnitas técnicas sin resolución; las entradas comerciales/Google ausentes
son dependencias de instancia, no autorización para inventarlas.
