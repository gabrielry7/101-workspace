# Footer Little Amps: hueso sin piel

Fecha: 2026-11-05. Estado: implementado y verificado; revisión humana pendiente.
Extensión acotada de spec 002 por petición explícita del usuario; no amplía el
piloto de hero ni aprueba una marca. ID: `footer.identity-menus-social-rail@0.1.0`.

## Intención y fuentes

Separar estructura/comportamiento, piel y contenido del footer indicado en
https://www.footer.design/sites/little-amps-coffee y https://littleampscoffee.com/.
«Quitar el diseño» conserva regiones, orden, alineaciones, espacios y funciones,
retirando paleta, tipografías, fotos, logo y dibujo originales. Cada hueco debe
explicar qué recibe y qué clase de medio es. No se interpreta literalmente
«poner una foto» en el lugar de una fuente: fuente es piel; foto es contenido.

## Requisitos y aceptación

- LA-01: tres bandas: bloque principal, carril social y cierre. En escritorio:
  identidad a izquierda; Company y Shop al centro (3 y 5 enlaces); embed a derecha.
  Bajo identidad: dos direcciones como texto, dos iconos sociales y correo.
- LA-02: cada parte tiene ID estable, tipo, posición, propósito, referencia y
  responsable (hueso, contenido, piel o proveedor). Logo gráfico ≠ foto; gráfica
  de seguimiento ≠ botón; Spotify ≠ fotografía ni reproductor implementado aquí.
- LA-03: once medios sociales cuadrados, en el orden del HTML oficial, con
  clasificación individual de foto documental, foto de producto o cartel.
  El carril móvil muestra sólo una ventana; no se pierden los demás elementos.
- LA-04: neutral sin fuentes descargadas, colores de marca, imágenes originales,
  iframe, datos comerciales ni llamadas externas. Los contornos son guías del
  taller. La piel observada se documenta aparte y no cambia composición.
- LA-05: preservar umbrales observados en CSS: menús desplegables bajo 1100 px;
  embed oculto hasta 1200 inclusive; bajo 769 cambia ancho de invitación social;
  bajo 750 cambia tamaño de imágenes. Contacto puede envolver sin romper palabras.
- LA-06: menús inicialmente abiertos; activación móvil cierra el otro grupo.
  Escritorio siempre muestra ambos. Flujo vertical normal; carril continuo lineal
  con pausa accesible añadida, pausa por foco/hover, scroll manual sin JS o con
  movimiento reducido. Sin personalización del puntero. No copiar JS comercial.
- LA-07: huecos sin destino no crean enlaces falsos. Un destino vinculado debe ser
  seguro. Datos esenciales ausentes o cantidades erróneas se rechazan. Esta versión
  no acepta URLs de imágenes/iframes para evitar saltarse los gates de medios.
- LA-08: Astro reutilizable en el runtime actual, contrato tipado, taller con
  inventario completo y comparación de referencia externa/neutro. Referencias
  descargadas sólo locales, sin redistribuir medios ni el handoff privado de Tomás.
- LA-09: comprobar anatomía, responsive, integridad de palabras, teclado, menús,
  scroll, pausa, movimiento reducido, fuente alternativa y sin JS. Build del
  componente real y pruebas positivas/negativas; aprobación humana separada.
- LA-10: entrega de archivos revisados en rama propia de `gabrielry7/101-workspace`,
  bajo `projects/101-design-compiler`, commit/push y SHA remoto verificado.

## Escenarios

1. Al abrir el taller en escritorio se reconocen las mismas regiones y posiciones
   de la captura, con medios reemplazados por huecos tipados; ningún recurso ajeno
   se carga. El inventario explica cada espacio.
2. A 360 px se conserva identidad → contacto → menús → carril → legal. Los menús
   funcionan con teclado. Los once medios siguen accesibles sin movimiento.
3. Al vincular enlaces sintéticos se conserva anatomía y navegación nativa;
   `javascript:`, cantidades incorrectas o un enlace sin destino se rechazan.
4. Al cambiar fuentes o preferencias no se cortan palabras, se evita overflow
   de página y no se pierde contenido esencial. El overflow del carril es intencional.

Fuera de alcance: nueva piel, integración real Spotify/Instagram, scraping continuo,
selector comercial, medios para otro negocio, despliegue y aprobación visual humana.
