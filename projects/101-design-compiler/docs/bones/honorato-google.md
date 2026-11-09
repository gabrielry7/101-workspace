# Honorato: prueba local con Google Maps real

Fecha: 2026-11-09. Spec: [007](../../specs/007-honorato-google-live/spec.md).
Vista local: <http://127.0.0.1:8780/>. Rama: `codex/honorato-google-live-20261109`.

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

El marcador es el pin neutro del mismo hueso `location.single-business@0.2.0`.
No se encontró un logo real que pase los controles de permisos y alcance. El SVG
reconstruido sin validación no se promovió a activo autorizado. Un futuro logo
debe entrar por `bindLocationBone` y los controles existentes de medios; el archivo
opcional privado `logo-evidence.json` añade `render_file`, cuyo SHA256 debe coincidir.

## Presupuesto y privacidad

El usuario autorizó **hasta US$1** para esta prueba. Se impuso y releyó una cuota
efectiva de **10 cargas diarias** para `maps-backend.googleapis.com/billable_default`
(unidad `1/d/{project}`). Además, el servidor reserva un máximo de **10
inicializaciones totales**, con contador persistente entre reinicios. Al agotarlo
responde 429 antes de entregar configuración e iniciar otro mapa. Un estado de
cupo inválido falla cerrado. No borrar/resetear el contador para ampliar la prueba.

La [tarifa Dynamic Maps](https://developers.google.com/maps/billing-and-pricing/pricing)
publicada es US$7/1.000 en el primer tramo de pago. Se presupuestan las diez cargas
como US$0,07 antes de impuestos, sin asumir disponibilidad del tramo gratuito.
La estimación no es una lectura de factura. Dos inicializaciones se reservaron para
las verificaciones del agente; al terminar esas verificaciones quedaban ocho.
Mover, ampliar y redimensionar el mismo mapa no crea otra instancia.
No se invocaron Places ni Street View. No se confía en alertas de facturación como
corte duro. La gestión de mapas no tiene cargo según la documentación oficial.

La key web es visible para el navegador por diseño, pero no se versiona ni se
imprime. OAuth permanece en gcloud/memoria y nunca se entrega al cliente. Los
archivos privados están en `.tools/honorato-google-live/`, ignorados por Git:

- `cloud-state.json`: identificadores de recursos y límites de esta prueba.
- `browser-config.json`: configuración web, permisos de archivo 0600.
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
# Mantener este proceso abierto. Cada visita nueva reserva una carga.
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
máxima de la punta de 0,0078125 px CSS.

Las capturas revisadas por el agente muestran sólo el marcador de Honorato y las
calles/geografía, sin negocios ajenos en esas vistas. Google no expone un inventario
completo de los POIs visibles: `rendered_poi_ids` permanece `null`. La inspección
automática no se presenta como validación exhaustiva ni aprobación del usuario.
Chromium headless sin GPU cayó al mapa raster de Google con el aviso esperado de
WebGL; el estilo y AdvancedMarker funcionaron en ese fallback. El render vectorial
en un dispositivo con GPU no se verificó en este entorno.

Pendientes para ampliar el alcance: revisión visual humana y logo de Honorato con
evidencia válida. Cambiar el dominio o ampliar cargas requiere revisar las
restricciones y el presupuesto. Los 60 medios históricos siguen fuera de alcance.
