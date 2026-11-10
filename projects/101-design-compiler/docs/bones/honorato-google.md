# Honorato: prueba local con Google Maps real

Fecha: 2026-11-09. Spec: [007](../../specs/007-honorato-google-live/spec.md).
Vista local: <http://127.0.0.1:8780/>. Rama del controlador:
`codex/honorato-map-controls-20261109`; logo en `codex/honorato-logo-pin-20261109`;
creación del proyecto en
`codex/honorato-google-live-20261109`.

Se creó un proyecto dedicado, se vinculó la cuenta de facturación accesible y se
habilitaron Maps JavaScript, Map Management y API Keys. El estilo propio oculta
etiquetas e iconos de puntos de interés y estaciones de transporte. Un Map ID
propio tiene el estilo asociado a ROADMAP. La clave del navegador está restringida
a `maps-backend.googleapis.com` y a `http://127.0.0.1:8780` / `http://localhost:8780`
(origen y rutas `/*`). Se releyeron las restricciones y recursos mediante las APIs
oficiales. No se alteraron proyectos ajenos.

Se usó [Map Management v2beta](https://developers.google.com/maps/documentation/mapmanagement/overview),
actualmente Preview. Esta API activa la asociación StyleConfig/MapConfig mediante
MapContextConfig; no ofrece un método independiente `publish`. La asociación fue
comprobada por API y por render real, sin simular haber pulsado un botón de consola.

El consumidor instancia **SingleBusinessLocation.astro** y el adaptador existente
`google_js`, con el contrato geográfico real de `@101/location-map@0.3.0`, commit
`6c0ed29940985bfb1789280c1972e47386775193`. No se creó otra implementación del mapa.
El paquete retenido de Honorato sigue siendo privado y `publication_allowed:false`.
Sus coordenadas de fuente Google se presentan sobre Google.

El marcador usa el símbolo de Honorato dentro del mismo pin. El logo se verificó
con Google real en `location.single-business@0.2.1`; el controlador local es 0.3.0.
El usuario confirmó expresamente permiso para usar
el logo. Su declaración está registrada en privado como autorización para esta
prueba local; no se presenta como un contrato externo ni una auditoría independiente
de titularidad. El símbolo procede del SVG de marca retenido: se conservan sus
trazos y se separa del wordmark horizontal para que quepa de forma legible en el pin.

La evidencia pasa por `bindLocationBone` y los controles existentes de medios,
incluyendo lineage/hash del archivo original y del símbolo. El archivo privado
`logo-evidence.json` añade `render_file`, cuyo SHA256 debe coincidir. No se copió
un grant sintético ni se usó un booleano para saltar los controles. La prueba
inicial de 0.2.0 usaba el pin neutro; sus capturas se conservaron en `before-logo/`.

Honorato pasa `markerLabel={false}` al componente para quitar el recuadro visible
del nombre. El pin conserva su silueta 64×80, el logo 44×44 proporcional, el nombre
accesible y la acción de indicaciones. Otros consumidores mantienen la etiqueta
por defecto. Si falla la imagen, vuelve el pin neutro sin mover el destino ni
reintroducir el recuadro oculto.

## Presupuesto y privacidad

Desde el controlador 0.3.0 abrir el taller sólo consulta el cupo, sin reservar
cargas. **Activar Google · usa 1 carga** inicia el proveedor una única vez en esa
visita. Cambiar ajustes no lo recrea. Al empezar este refinamiento el contador
marcaba 9/10; sus pruebas no consumieron la última carga. Al agotarse se pueden
seguir probando las pieles de la sección sin iniciar Google.

El panel permite piel neutra/papel/tinta, las tres composiciones, zoom, altura,
etiqueta y fondo/borde del pin. La piel se aplica a la sección, no a la cartografía
cloud ni al logo. Guarda, recupera y restablece opciones visuales sin datos privados.
Ver [verificación del controlador](location-controls-verification.json).

El usuario autorizó **hasta US$1** para esta prueba. Se impuso y releyó una cuota
efectiva de **10 cargas diarias** para `maps-backend.googleapis.com/billable_default`
(unidad `1/d/{project}`). Además, el servidor reserva un máximo de **10
inicializaciones totales**, con contador persistente entre reinicios. Al agotarlo
responde 429 antes de entregar configuración e iniciar otro mapa. Un estado de
cupo inválido falla cerrado. No borrar/resetear el contador para ampliar la prueba.

La [tarifa Dynamic Maps](https://developers.google.com/maps/billing-and-pricing/pricing)
publicada es US$7/1.000 en el primer tramo de pago. Se presupuestan las diez cargas
como US$0,07 antes de impuestos, sin asumir disponibilidad del tramo gratuito.
La estimación no es una lectura de factura. La verificación inicial reservó dos
inicializaciones del agente y el refinamiento del logo una más. Tras verificar el
logo, el contador total marcaba 4/10 y quedaban seis; incluye otra visita a la vista.
Mover, ampliar y redimensionar el mismo mapa no crea otra instancia.
No se invocaron Places ni Street View. No se confía en alertas de facturación como
corte duro. La gestión de mapas no tiene cargo según la documentación oficial.

La key web es visible para el navegador por diseño, pero no se versiona ni se
imprime. OAuth permanece en gcloud/memoria y nunca se entrega al cliente. Los
archivos privados están en `.tools/honorato-google-live/`, ignorados por Git:

- `cloud-state.json`: identificadores de recursos y límites de esta prueba.
- `browser-config.json`: configuración web, permisos de archivo 0600.
- `logo-permission.txt`, `logo-evidence.json` y `logo-review/`: declaración real,
  evidencia de medios y símbolos privados; no redistribuir en el repositorio público.
- `trial-budget.json`: reservas persistentes; conservar al reiniciar/recompilar.
- `preview/`: consumidor, bundle del dueño privado y datos conservados.
- `browser-*-report.json` y PNG: evidencia local restringida.

El servidor escucha sólo en 127.0.0.1, valida Host/Origin, rechaza peticiones cruzadas
y no expone los archivos privados. `/trial-config` admite únicamente POST local y
usa `Cache-Control:no-store`. No hay despliegue ni publicación comercial.

## Continuar en este entorno

Desde `projects/101-design-compiler`, con el checkout privado y dependencias ya
restaurados, la configuración creada y gcloud autenticado:

```bash
# Releer cuota, estilo, asociación y restricciones; sin carga facturable de mapa.
python tooling/bones/provision-google-cloud.py
# Compilar el consumidor privado, sin iniciar Google Maps.
node --experimental-strip-types tooling/bones/prepare-honorato-google.mjs
# Mantener este proceso abierto. Sólo activar Google reserva una carga.
node tooling/bones/serve-honorato-google.mjs
```

Estos comandos reutilizan el proyecto registrado en el estado privado. No son una
orden para crear otra cuenta de facturación o repetir proyectos. Si falta ese
estado en otro equipo, recuperar los identificadores desde Google Cloud y la key
mediante OAuth; no incluir credenciales en Git para trasladarlos.

Comprobaciones sin carga de Google:

```bash
node --experimental-strip-types --test tests/google-trial-budget.test.ts tests/location-map.test.ts
npm run check
```

Auditoría del controlador sin gastar cargas (servidor activo):

```bash
node --experimental-strip-types --test tests/location-map-controls.test.ts
H4_BROWSER_PATH=/home/tom/.local/bin/chromium node --experimental-strip-types scripts/audit-location-controls.ts
```

El navegador de esta auditoría intercepta configuración/SDK con un doble offline
identificado; no entrega la clave real ni pide cartografía Google. Verifica 45
casos responsive de las tres composiciones y capturas de tres pieles, persistencia,
zoom, etiqueta, altura, identidad del canvas/controlador y estado sin cargas.
El contador persistente queda intacto. Esta prueba no equivale a un nuevo render
Google vivo de 0.3.0: el último render vivo conservado corresponde al pin de 0.2.1.

Comprobación real opcional, con el servidor anterior activo: **consume una reserva**.
No forma parte de `npm test`, no reintenta ni reinicia el contador.

```bash
H4_BROWSER_PATH=/home/tom/.local/bin/chromium node --experimental-strip-types scripts/audit-honorato-google.ts --live
```

## Resultado y límites de verificación

Ver [resumen verificable sin datos privados](honorato-google-verification.json).
Se comprobaron siete anchos (390–1440 px), ambos lados de los breakpoints del
consumidor directo, fuente alternativa, foco de indicaciones, zoom 16→17 y arrastre
real con ratón. Sin overflow ni excepciones; coordenada conservada y desviación
máxima de la punta de 0,5129 px CSS en la verificación del logo, incluido el arrastre.
El logo se decodificó correctamente, no hay elementos de etiqueta visibles y el
nombre accesible sigue presente. También se provocó un error de imagen y se verificó
el pin de alternativa con la misma coordenada, sin otra inicialización del mapa.

La regresión del taller local pasó 17 anchos y 17 comprobaciones Google con el
doble offline, sin llamadas externas. Conserva las etiquetas de otros consumidores.
La primera pasada falló por una intercepción CDP caducada del harness; el log quedó
retenido y el reintento pasó sin errores. Ocho tests y typecheck sin diagnósticos.

Las capturas revisadas por el agente muestran sólo el marcador de Honorato y las
calles/geografía, sin negocios ajenos en esas vistas. Google no expone un inventario
completo de los POIs visibles: `rendered_poi_ids` permanece `null`. La inspección
automática no se presenta como validación exhaustiva ni aprobación del usuario.
Chromium headless sin GPU cayó al mapa raster de Google con el aviso esperado de
WebGL; el estilo y AdvancedMarker funcionaron en ese fallback. El render vectorial
en un dispositivo con GPU no se verificó en este entorno.

Pendiente: revisión visual humana del resultado. Cambiar el dominio o ampliar cargas
requiere revisar las restricciones y el presupuesto. Los 60 medios históricos siguen
fuera de alcance.
