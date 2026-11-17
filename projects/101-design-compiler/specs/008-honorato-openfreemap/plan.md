# Plan de la vista

Reutilizar `SingleBusinessLocation.astro`, el cliente MapLibre fijado de Tomás, `attachMarkerVisual` y el controlador de ubicación. Cargar un estilo vectorial con las capas cartográficas necesarias mediante el punto de decoración existente y restringir las peticiones a la misma web y al servicio de teselas de OpenFreeMap. Mantener un solo mapa y el contrato de procedencia del propietario.

Preparar `/honorato/` dentro del taller privado. Vincular el símbolo mediante la evidencia de medios y comprobar su hash. Usar el centro de la geometría OSM archivada de la vía 618065505 como punto de muestra. El rojo y el negro se basan en la web de Honorato y el crema en las referencias de Studio retenidas. Los tonos de calles y edificios son adaptaciones del mapa.

Verificar con Chromium, teselas reales, varios anchos, cambios de zoom y piel, créditos, ausencia de negocios y alternativa al bloquear la fuente. Ejecutar las comprobaciones existentes del hueso. Versionar la interfaz aditiva como 0.4.0 y entregar código y verificación sin activos privados.

La revisión 0.5.0 comparte un catálogo tipado de campos entre el panel y la
validación. Actualiza las propiedades de capas del MapLibre existente, usa
variables CSS para la presentación y conserva los controles anteriores y la
lectura de ajustes válidos de 0.4.0. El guardado sigue siendo local al navegador.

La revisión 0.6.0 añade una capa `fill-extrusion` de la fuente vectorial
existente y usa `render_height`, `render_min_height` y `hide_3d`. El modo 2D
sigue disponible en la misma instancia. El taller abre con zoom 18 e inclinación
de 60 grados. La recuperación de ajustes de 0.5.0 rellena sólo los campos nuevos.
Comprobar teselas reales, alturas disponibles, alternancia 2D/3D, persistencia,
anclaje, escritorio y móvil. Conservar las capturas bajo el taller privado.

La acción de Street View usa un enlace web opcional del componente existente.
El builder vincula el enlace desde un archivo privado de Honorato. Validar
protocolo y dominio de Google Maps, conservar la orientación y mostrar un estado
pendiente al faltar el destino. Verificar la vista externa con navegador y
la acción en el taller con teclado, móvil y ambas composiciones alternativas.
Versionar la acción como 0.7.0 y recuperar los ajustes visuales de 0.6.0.
