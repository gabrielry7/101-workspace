# Familia de ubicación: un negocio y su logo sobre el mapa

Dirección del usuario: 2026-11-05. Estado: implementación local de MapLibre y
adaptador Google JS; verificación viva de Google y aprobación humana pendientes. Esta ficha amplía la
[spec 002](../../specs/002-section-bones/spec.md), sin declarar completado su
piloto de navegación/hero. ID ejecutable actual: `location.single-business@0.2.0`.
Implementación y evidencia en [spec 005](../../specs/005-location-map-bones/spec.md).

## Revisión 2026-11-08 — huesos neutros y pin con logo

La [spec 006](../../specs/006-neutral-location-bones/spec.md) aplica la dirección
del usuario: presentar las tres composiciones primero sin piel, igual que Little
Amps. Nombre, dirección, acciones y logo son espacios identificados; la tipografía
del neutro se hereda y se retiran acabados de marca. La comparación con piel queda
como demostración secundaria. Las guías y preparación de Google son del operador.

El logo ahora queda **dentro de una forma de pin**, en vez de reemplazar esa forma
por una caja. El marco mide 64 × 80 px y contiene la imagen en 44 × 44 px, sin
deformación ni recorte. La punta del SVG se mide mediante su transformación real
en pantalla. Pin neutro y pin con logo conservan el mismo anclaje geográfico.
Se versiona la modificación; configuraciones guardadas de 0.1.0 no se restauran
silenciosamente sobre 0.2.0.

El usuario confirmó que todavía no tiene proyecto/Map ID/estilo de Google. La
muestra sigue usando el dueño MapLibre existente y cartografía sintética. El
adaptador Google está preparado y comprobado offline; su apariencia real sigue
pendiente de configuración y revisión viva.

### Preparar el estilo de Google

1. Crear un proyecto propio habilitado para Maps JavaScript API. Gestionar su
   facturación en esa cuenta y restringir la clave web por sitios y API permitida.
2. En **Map styles**, crear un estilo e importar
   `tooling/bones/google-no-pois.style.json`, también descargable desde el taller.
   `pointOfInterest.label.visible: false` oculta texto y pins de lugares;
   `infrastructure.transitStation` cubre las estaciones de su jerarquía separada.
   Se conservan calles y contexto. Revisar categorías hijas que puedan sobrescribir
   la visibilidad del padre. `clickableIcons: false` sólo impide clicks, no oculta.
3. Ajustar allí colores de agua, vías y demás elementos, publicar el estilo y
   asociarlo a un **Map ID de JavaScript**. Un archivo JSON descargado sin publicar
   ni asociar no modifica el mapa real.
4. Pasar la configuración privada al `google` del componente existente: `enabled`,
   `apiKey`, `mapId` y `styleReview` del mismo ID con `pois: none`, referencia y fecha.
   Mantenerla fuera de Git; no poner claves en especificaciones o capturas.
   El estilo cloud no se pasa como `MapOptions.styles`.
5. Vincular datos reales mediante `bindLocationBone` y el logo con sus permisos.
   Verificar en navegador el estilo publicado: cero negocios ajenos al mover y
   ampliar, un solo pin con logo, punta anclada, créditos y alternativas útiles.

Referencias oficiales: [importar JSON](https://developers.google.com/maps/documentation/javascript/cloud-customization/json),
[publicar/asociar estilos](https://developers.google.com/maps/documentation/javascript/cloud-customization/map-styles),
[jerarquía](https://developers.google.com/maps/documentation/javascript/cloud-customization/taxonomy),
[restricciones de claves](https://developers.google.com/maps/api-security-best-practices).
Esta entrega no crea cuentas, activa facturación ni hace llamadas a Google.

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

El adaptador propio consume la API nativa y el hook `decorateMap` del dueño
original intacto. El hook cambia únicamente el contenido del marcador real; no
introduce otro MapLibre ni permite saltar restricciones de coordenadas.
`bindLocationBone` evalúa el logo por los gates existentes antes de serializarlo.

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
| MapLibre/PMTiles existente + adaptador de hueso | Política fija `none` y rechazo de reactivación | Logo/pin sobre el marcador real, con anclaje inspeccionable | Implementado con mapa base compatible y coordenadas de uso independiente |
| `google_embed` existente | El iframe no ofrece ese control a la página contenedora | No admite sustituir su pin desde el padre | Incompatible con el resultado completo; conservar sólo como referencia aparte |
| Google Maps JavaScript API | Estilo cloud revisado, map ID y `clickableIcons: false` | AdvancedMarkerElement con logo y fallback | Adaptador implementado; configuración/revisión viva pendientes; pruebas offline identificadas |

Google documenta [ocultar negocios](https://developers.google.com/maps/documentation/javascript/examples/hiding-features)
y [marcadores con imágenes](https://developers.google.com/maps/documentation/javascript/advanced-markers/graphic-markers).
La integración usa map ID y estilo cloud; rechaza DEMO_MAP_ID y no combina esa
configuración con estilos incrustados incompatibles. La base de importación está
en `tooling/bones/google-no-pois.style.json`; hay que publicarla y vincularla al map ID.
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
- El logo ocupa el interior del pin en la versión 0.2.0; no es una imagen flotante
  ni otro marcador adicional. Su anclaje permanece en la coordenada real al
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

## Implementación y reproducción

El componente Astro está en `src/components/bones/SingleBusinessLocation.astro`.
Sus tres variantes conservan la receta de las demos direct/map-led/editorial;
piel neutra, papel y tinta son configuraciones del mismo componente. La API nativa
original se compila con el adaptador propio sólo en un build privado bajo `.tools/`.
El checkout original de Thomas no se modifica ni se copia al repositorio público.

```powershell
$env:PATH = "$PWD\.tools\node-v24.21.0-win-x64;$env:PATH"
node tooling/bones/prepare-location-map.mjs
node --experimental-strip-types --test tests/location-map.test.ts
node --experimental-strip-types scripts/audit-location-map.ts
node tooling/bones/serve-location-map.mjs
```

Abrir http://127.0.0.1:8777/. Incluye original privado con los mismos datos de
prueba, hueso neutro, piel con logo, tres recetas, estados alternativos y anatomía.
La demo no tiene destinos reales y lo indica; sus acciones son huecos deshabilitados.
La comprobación de teclado con enlaces está en una ruta de prueba identificada.
Guardar/restaurar conserva piel y zoom versionados en el navegador, sin editar hechos.

En 0.2.1, `markerLabel` permite ocultar el recuadro del nombre sin quitar el nombre
accesible del pin. Su valor por defecto es `true`. La prueba de Honorato usa
`false` y el símbolo con permiso confirmado por el usuario dentro de la misma
silueta; ver [evidencia de Google real](honorato-google.md).

En un consumidor autorizado: validar con el `locationInput`/`navigationLinks` del
dueño mediante `bindLocationBone`, suministrar la evidencia del logo y pasar ese
`input` al componente. El `runtimeURL` debe ser un bundle local preparado con el
dueño, como el de este piloto; basemap/proveedor y configuración son explícitos.
Sin runtime hay HTML útil y un estado comprensible. La página del taller no se
incluye en una sección de cliente.

Google exige opt-in `enabled: true`, clave web restringida fuera de Git, map ID
propio y `styleReview` con map ID coincidente, `pois: none`, referencia y fecha.
La clave web es visible al navegador por diseño de la API; no se guarda en reportes.
Sin esos datos no se llama Google. Cambiar colores internos de Google requiere
otro estilo cloud revisado; no se simula cambiando CSS del marco. La entrega inicial
no realizó una prueba viva ni activó facturación. El 2026-11-09 el usuario autorizó
una prueba dedicada de hasta US$1 y se verificó Google real con Honorato; ver
[configuración, límites y resultado](honorato-google.md). El taller sintético de
8777 conserva su propósito y no inicia esa prueba por su cuenta.

### Antecedente de verificación del dueño

Verificación local de la base el 2026-11-05, Windows y Node 26.7.0:
tras restaurar las dependencias fijadas con `npm ci --ignore-scripts`, se ejecutaron
`tests/contract.test.mjs` y `tests/poi.test.mjs` del paquete original. Resultado:
16 pruebas pasaron, incluidas las cuatro de POIs; cuatro pruebas de herramientas
no pasaron por rutas `URL.pathname` interpretadas como `C:\C:\...` en Windows
y por invocar `python3`, alias no disponible en este entorno. No se alteró el
código de Thomas para ocultar esas limitaciones. La primera ejecución, anterior a
restaurar dependencias, también falló por `pmtiles` ausente.

Esa ejecución corresponde a la entrega documental anterior. La implementación de
spec 005 añade sus pruebas propias de medios, contrato, Google simulado y navegador
MapLibre; el recibo de la versión registra el resultado sin redistribuir capturas privadas.

Quedan fuera selector completo, composiciones masivas, identidad de un cliente real,
prueba viva de Google sin configuración, publicación web y aprobación humana.
