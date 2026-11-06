# Contrato del componente y del taller

`DirectoryFooter({content, cookieAction = 'unbound'})` valida contenido y genera
HTML semántico. `cookieAction = 'event'` habilita el botón para emitir
`101:footer-cookie-settings` con el ID del hueso; el consumidor debe conectar
su gestor real. Sin conexión, el botón está deshabilitado y explica el estado.
Los enlaces de IA son URLs, no llamadas o clientes de modelos.

CSS: variables de piel para fuente, tinta, papel, tono secundario y líneas;
las medidas/distribución tienen dueño en la receta. El wordmark grande es
decorativo y se recorta intencionalmente; el nombre accesible no se recorta.

`collectFooterCoverage(host)` devuelve denominador total y unión recortada de
cajas funcionales: texto, controles, medios, decoración y ocupación combinada.
Sólo texto/sin-texto y ocupación/espacio-libre son pares complementarios.
Otros porcentajes se solapan y no se suman como un gráfico de partes exclusivas.

El taller carga `/__bone-tools/measure.js` y `guides.js` si se han preparado.
Conserva origen/commit/hash de esos módulos. Sin ellos, devuelve unavailable
para el informe compartido y conserva la extensión propia de texto.
La exportación `101-footer-observation-v1` añade configuración, anatomía,
fecha, tamaño y limitaciones. No importa automáticamente código o evidencia.
