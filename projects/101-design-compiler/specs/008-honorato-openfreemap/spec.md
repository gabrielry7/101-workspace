# Honorato en OpenFreeMap

Vista privada para revisar el mismo hueso de ubicación con cartografía real de OpenFreeMap, el símbolo autorizado de Honorato y una adaptación de su rojo, negro y crema. Mostrar calles y edificios y excluir las capas de negocios vecinos. Conservar zoom, arrastre, controles de composición y la etiqueta del pin apagada inicialmente.

El centro de la muestra procede de la geometría OSM de Complex Llanogrande. Al faltar una coordenada independiente del local 57–58, el pin es una muestra de diseño identificada junto al mapa. El texto de dirección sí corresponde a la sucursal. Las acciones de navegación de esta muestra carecen de destino. Su publicación queda desautorizada por el paquete privado.

Aceptación. La vista abre en el taller local con teselas reales, atribución visible y un solo pin con logo. La punta queda a ≤1 px del punto de muestra después de mover o ampliar. El mapa y los controles se pueden usar en móvil y escritorio. La integración conserva la dirección al fallar las teselas y no usa Google Maps API.

## Edición completa de la vista

El panel debe cubrir cada capa del estilo disponible: fondo, vegetación, agua,
edificios, vías y nombres de vías. Debe permitir editar sus colores, visibilidad
y propiedades gráficas aplicables, además de la cámara, interacción, pin,
etiqueta y apariencia de la sección. Guardar, recuperar y restablecer deben
incluir estos ajustes. El mapa permanece visible junto a los controles en
escritorio y es accesible desde el panel en móvil.

Los ajustes son de presentación. La fuente, los créditos, la política de
negocios vecinos, la geometría del pin y los datos del negocio quedan vinculados
por el contrato existente. Se verificará cada campo en la vista de Honorato
con cartografía real, sin recrear la instancia del mapa.

## Ejemplo de edificios en 3D

Mostrar Honorato con los edificios de OpenFreeMap en volumen y una cámara
inclinada. El panel permite activar y desactivar el 3D, ajustar la escala de
altura y la iluminación. Color, opacidad y visibilidad continúan usando los
ajustes de edificios existentes. Las alturas se presentan como aproximaciones
de la cartografía. El pin mantiene su identificación como punto de muestra.

La comparación con los colores originales usa la paleta del estilo Bright de
OpenFreeMap en el mapa del taller. Los colores proceden de su estilo publicado.

## Abrir la fachada en Street View

Añadir una acción opcional que abra la vista real de la fachada en Google
Street View, con el encuadre del enlace seleccionado. Reutilizar el componente
de ubicación para las tres composiciones. El destino procede de una vista
comprobada de la sucursal. El taller muestra un estado pendiente mientras
se obtiene ese enlace. La acción funciona con HTML y abre una pestaña nueva.
