# Familia de ubicación: un negocio y su logo sobre el mapa

Dirección del usuario: 2026-11-05. Estado: requisitos incorporados a los huesos;
integración y revisión visual pendientes. Esta ficha amplía la
[spec 002](../../specs/002-section-bones/spec.md), sin declarar completado su
piloto de navegación/hero. ID propuesto: `location.single-business@0.1.0`;
todavía no es una entrada ejecutable ni aprobada del catálogo.

## Resultado solicitado

Mostrar la **ubicación real de una sucursal**, sin nombres, iconos, marcadores ni
fichas de otros establecimientos. Conservar calles y contexto geográfico útiles.
El marcador propio debe usar preferentemente el **logo autorizado de la empresa**
en lugar del pin convencional. Los colores pueden acompañar la piel de la marca.

Referencia de resultado: [Tourist Home Cafe](https://www.touristhomecafe.com/location/tourist-home-cafe/).
Se toma la limpieza del mapa y el protagonismo de un establecimiento; no se copian
sus credenciales, datos, logo ni código de integración. Abrir «Cómo llegar» lleva
al servicio externo, cuya interfaz y otros lugares ya no controla esta sección.

## Reutilizar lo que ya hizo Tomás

Base inspeccionada: `101-world-model`, commit
`6c0ed29940985bfb1789280c1972e47386775193`, paquete `@101/location-map@0.3.0`,
contrato `101-location-map-v3`. Checkout privado local:
`.tools/bones-handoff-20261105/source`. No se redistribuye ese paquete.

| Responsabilidad | Dueño existente | Situación comprobada |
| --- | --- | --- |
| Consumo Astro y contenido sin JS | `packages/location-map/LocationMap.astro` | Slots heading/caption y dirección/acciones renderizadas en servidor |
| Identidad, coordenadas y elegibilidad | `src/contract.js`: `locationInput`, `rendererEligibility` | Vincula negocio/sucursal/fuente; distingue coordenadas usables y restringidas |
| POIs y colores | `src/contract.js`: `poiPolicy`, `presentation`, `basemapStyle` | MapLibre permite `none`, `selected`, `all`; el componente normal usa `none` por defecto |
| Pin, interacción e inspección | `src/client.js`: `mountLocationMap`, `setPresentation`, `inspect`, `destroy` | Pin propio SVG y etiqueta; no hay entrada pública de logo en esta versión |
| Direcciones | `src/navigation.js` y `navigationLinks` en `src/contract.js` | Google Maps y, cuando son elegibles, Waze/Apple; sin pedir geolocalización |
| Composición de sección | Consumidor y demos `direct`, `map-led`, `editorial` | Tres referencias de composición, no tres huesos aprobados |

Las rutas `src/` de la tabla son relativas a `packages/location-map/`.
La demo privada de densidad permite hasta 20 referencias del entorno: esa elección
de taller **no se hereda** en la familia solicitada. Aquí se fija POIs en `none`.
Cambiar piel, zoom, proveedor o cargar una configuración no puede reactivarlos.
El filtro debe aplicarse a todas las capas que puedan mostrar otros negocios,
no limitarse a ocultar los marcadores propios de la aplicación.

No crear otro renderer o servicio de mapas. Extender los dueños originales con
interfaz versionada y mantener sus regresiones y sus permisos. El hook confiable
`decorateMap` existente no constituye autorización para saltar restricciones de
coordenadas ni una API pública de logo.

## Hueso, piel y datos

| Eje | Contenido de esta familia |
| --- | --- |
| Hueso | Partes nombradas, mapa y anclaje geográfico, jerarquía de información, controles, estados, adaptación responsive y alternativas accesibles |
| Comportamiento | Un solo destino por instancia; pin no arrastrable; pan/zoom sin cambiar destino; ningún negocio ajeno; activación del marcador conduce a la acción de direcciones; scroll cooperativo y salida por teclado |
| Piel | Paleta por función, superficie/marco y radios permitidos, fuente de textos propios y referencia de logo autorizado con encuadre acotado; no modifica coordenadas ni política de POIs |
| Datos del negocio | IDs de negocio y sucursal, nombre, dirección, latitud/longitud, propósito del punto, referencia del listing, fuente/fecha, permisos y decisión de publicación |
| Instancia | Versiones de hueso/piel/componente, proveedor y capacidades verificadas, fuentes, logo vinculado, estilo, encuadre, alternativas y revisión |

Partes mínimas: `heading` cuando corresponda; `map-viewport`; `business-marker`;
`business-name`; `address`; `directions`; `provider-attribution`; `status-fallback`.
Nombre, dirección y acciones tienen un solo dueño: si los contiene la sección,
usar el `detailsMode: external` existente y mantenerlos disponibles sin JS.
La anatomía y controles de taller siguen siendo sólo del operador.

Los colores de agua, terreno, edificios, vías y etiquetas se adaptan a capacidades
reales del proveedor. La fuente de los nombres del mapa base no se promete como
si fuera texto HTML propio. La piel nunca elimina créditos ni vuelve ilegible el mapa.

## Compatibilidad de proveedores y brecha real

| Modalidad | Ocultar negocios alrededor | Logo anclado a coordenada | Elegibilidad para este hueso |
| --- | --- | --- | --- |
| MapLibre/PMTiles existente | Ya hay filtro `pois.mode: none` para el esquema de capas admitido | Extensión pendiente del marcador y de su inspección | Candidato con mapa base compatible y coordenadas de uso independiente |
| `google_embed` existente | El iframe no ofrece ese control a la página contenedora | No admite sustituir su pin desde el padre | Incompatible con el resultado completo; conservar sólo como referencia aparte |
| Google Maps JavaScript API | Permite ocultar POIs mediante estilos | Admite gráficos propios en Advanced Markers | Integración pendiente dentro del mismo paquete, con configuración y autorización de servicio aplicables |

Google documenta [ocultar negocios](https://developers.google.com/maps/documentation/javascript/examples/hiding-features)
y [marcadores con imágenes](https://developers.google.com/maps/documentation/javascript/advanced-markers/graphic-markers).
La futura integración debe elegir una configuración de estilos compatible con
el tipo de mapa y su map ID; no mezclar estilos cloud e incrustados incompatibles.
La clave/configuración de un tercero no se reutiliza. Esta ficha no activa una
cuenta, facturación ni llamadas de pago.

No superponer un logo fijo en píxeles sobre el iframe: al desplazar el mapa dejaría
de marcar el lugar real. Si el proveedor no cumple, registrar incompatibilidad y
mostrar dirección/indicaciones, sin cambiar silenciosamente a un iframe con negocios.
Mantener [atribución de Google](https://developers.google.com/maps/documentation/javascript/policies)
y créditos de los demás proveedores.

## Ubicación real y marcador de logo

- El destino lo fijan datos comprobados de la misma sucursal, no el centro del
  viewport, una búsqueda por nombre, una empresa vecina o una propuesta del modelo.
  Un punto de listing no acredita por sí solo la entrada física.
- Conservar `purpose`, fuente, fecha y `map_use`. Coordenadas de Google Places
  marcadas `requires_google_map` no pasan a MapLibre. Sin evidencia suficiente,
  no dibujar un punto presunto; conservar los datos y destinos que sí sean utilizables.
- El logo debe pertenecer al negocio y pasar los gates existentes de medios,
  ámbito y publicación. Usar una referencia al recurso validado; no admitir HTML
  o SVG arbitrario como una vía alternativa a esos controles.
- El logo **sustituye** al dibujo del pin; no es una imagen flotante ni otro
  marcador adicional. Su anclaje explícito permanece en la coordenada real al
  cambiar zoom, encuadre, tamaño o piel. El inspector debe medir el anclaje real,
  sin seguir buscando únicamente la punta del SVG antiguo.
- Conservar proporción y legibilidad del logo, con tamaño acotado y superficie
  de contraste si hace falta. Propuesta inicial para el plan: caja máxima de
  64 × 64 px CSS, imagen contenida sin recorte y área de interacción mínima de
  44 × 44 px. Estos límites requieren verificación con logos reales.
- Nombre accesible: negocio y propósito de la acción. No depender de reconocer
  el logo; dirección y enlace permanecen en texto. Sin animación obligatoria ni
  cambios de identidad del puntero; respetar movimiento reducido y colores forzados.
- Si falta el logo, falla su carga o no tiene permiso, usar el pin neutro de
  alternativa y registrar el motivo en el taller. No inventar ni tomar el logo de
  otro negocio. Si falta ubicación utilizable, el logo tampoco habilita un pin.

## Estados y comprobación requerida antes de presentar una implementación

Estados: datos insuficientes; proveedor incompatible; cargando; listo con logo;
listo con pin de alternativa; error de proveedor/recursos; alternativa sin JS.
Un iframe cargado sigue siendo `embedded`, no prueba de pin correcto ni de POIs ocultos.

| Caso | Aceptación observable |
| --- | --- |
| Ubicación utilizable y logo permitido | Exactamente un marcador del negocio, con su logo y destino de la misma sucursal; error visual de anclaje máximo propuesto de 1 px CSS tras estabilizar la vista |
| Pan/zoom, resize, cambio de piel y restauración de configuración | Coordenadas y destino conservados; cero nombres, iconos o fichas de negocios ajenos en toda la vista permitida |
| Cambio a tipo de mapa o proveedor incompatible | Rechazo explicado o alternativa de dirección/indicaciones; nunca reintroducción silenciosa de negocios |
| Logo ausente, denegado o con error de carga | Pin neutro accesible con motivo de alternativa registrado; mismo lugar y destino |
| Coordenada ausente, contradictoria, de otra sucursal o restringida para ese proveedor | Sin marcador presunto; motivo comprobable y fallback útil; no se normaliza la restricción para dibujarlo |
| Fallo de JS, red, mapas o WebGL; teclado y tacto | Dirección y acciones elegibles disponibles; foco visible, sin scroll atrapado y créditos visibles |
| 360, 768, 1440 px; ambos lados de breakpoints; fuente de respaldo | Palabras completas, sin clipping ni overflow; logo sin deformar; controles y atribución legibles |

Comparar referencia de Thomas identificada, hueso neutro y piel aplicada con las
mismas condiciones. Probar también logos horizontales/verticales, movimiento
reducido y colores forzados. Inspeccionar en navegador nativo el proveedor real:
una respuesta simulada no prueba la supresión de etiquetas ni la ubicación viva.
Datos sintéticos se etiquetan; no se presentan como una ubicación comercial real.
Pruebas de contrato y captura visual no equivalen a aprobación humana.

## Alcance entregado y siguiente implementación

Verificación local de la base el 2026-11-05, Windows y Node 26.7.0:
tras restaurar las dependencias fijadas con `npm ci --ignore-scripts`, se ejecutaron
`tests/contract.test.mjs` y `tests/poi.test.mjs` del paquete original. Resultado:
16 pruebas pasaron, incluidas las cuatro de POIs; cuatro pruebas de herramientas
no pasaron por rutas `URL.pathname` interpretadas como `C:\C:\...` en Windows
y por invocar `python3`, alias no disponible en este entorno. No se alteró el
código de Thomas para ocultar esas limitaciones. La primera ejecución, anterior a
restaurar dependencias, también falló por `pmtiles` ausente.

Esta comprobación confirma el contrato base de ocultación, no una integración
del logo ni el comportamiento visual de un proveedor real. Al ser una entrega
documental no se generó una nueva interfaz, build de aplicación ni aprobación visual.

Esta entrega registra la familia, responsabilidades, compatibilidad, alternativas y
aceptación; **no cambia el código privado de Thomas ni implementa aún el logo o
Google Maps JavaScript en el compiler**. El plan y las tareas de implementación
deben ampliar esos dueños, versionar las capacidades nuevas, vincular medios por
los gates actuales y verificar el comportamiento antes de presentar una adaptación.
No incluye selector completo, nuevas composiciones masivas ni publicación web.
