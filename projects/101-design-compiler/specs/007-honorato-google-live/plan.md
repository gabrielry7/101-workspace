# Plan — Honorato Google real
**Spec**: [spec.md](spec.md)
## Summary
Google Cloud CLI oficial y OAuth. Proyecto dedicado; Maps JavaScript, Map Management y API Keys. API v2beta para StyleConfig/MapConfig/MapContextConfig cuando esté disponible. Clave limitada al puerto local 8780 y maps-backend.googleapis.com.
## Technical Context
Node 24/Astro/Python estándar existentes. Sin framework nuevo ni publicación.
Privados: .tools/honorato-google-live; cliente: mismo SingleBusinessLocation y adaptador Google.
Pruebas: REST readback, test de cupo, Chromium local y revisión visual.
Hasta diez cargas iniciales; precio de referencia máximo Dynamic Maps US$7/1000 antes de impuestos, sin asumir tramo gratuito. No Places/Street View. No atribuir coste cero a cargas reales sin verificar.
## Constitution Check
Spec antes de código/recursos. Reutilización de dueños, gates y procedencia. Google real separado de mocks; presupuesto explícito; sin otro motor ni datos privados en Git. Gate previo: PASS.
## Structure
tooling/bones/prepare-honorato-google.mjs: consumidor privado del componente.
tooling/bones/serve-honorato-google.mjs: servidor local y cupo de configuración.
Recursos/configuración privada fuera de Git; reports no sensibles tras verificación.
scripts/audit-honorato-google.ts: comprobación explícita --live; una sola carga para
todos los anchos, zoom, arrastre y fuente alternativa. No forma parte del test unitario.
tooling/bones/provision-google-cloud.py: crea/relee recursos del proyecto dedicado
ya creado y autenticado; lee OAuth en memoria y conserva la key fuera de Git.
tooling/bones/google-trial-budget.mjs: reserva persistente y rechazo de la carga 11.
## Dependencies
Cuenta/facturación/permisos; API Maps Management en Preview; logo puede no tener permiso para presentación comercial y debe conservar fallback.

## Final Constitution Check
PASS: mismo componente y dueños; paquete privado sin redistribución; coordenadas
Google en Google; pin neutro por LOGO_MISSING; OAuth sólo en gcloud/memoria.
Verificados cuota efectiva 10/día, contador local total 10 y origen/API de la key.
Google real y límites automáticos comprobados; aprobación visual humana pendiente.

## Refinamiento del marcador (2026-11-09)
Entrada: confirmación explícita del usuario sobre permiso del logo. Registrar
evidencia privada con el SHA de los archivos y su declaración real; no copiar
fixtures sintéticos ni afirmar una verificación independiente de titularidad.
Conservar el símbolo SVG existente extraído del archivo de marca, sin redibujarlo.
Añadir `markerLabel` booleano a SingleBusinessLocation y pasarlo a ambos adaptadores
mediante attachMarkerVisual. Por defecto true; Honorato usa false. El pin conserva
64×80, el logo 44×44 con object-fit contain y el mismo anclaje. Versión 0.2.1.
Auditoría Google: exigir marker_kind=logo, imagen decodificada y cero etiquetas;
reutilizar una sola carga para los anchos/zoom/arrastre y conservar las capturas
anteriores antes de generar las nuevas. Sin cambios de servicios, clave o cuota.

Resultado: Google real mostró el símbolo dentro del pin y cero recuadros de nombre,
con nombre accesible. Siete anchos, fuente alternativa, zoom y arrastre: sin overflow;
desviación máxima de la punta 0.513 px. Error de imagen conserva la coordenada y
la etiqueta oculta. El taller conservó sus etiquetas y pasó 17 anchos y 17 checks
Google offline. Primera pasada del taller encontró una intercepción CDP caducada;
se conservó el log y el reintento pasó sin errores. Ocho tests y check sin diagnósticos.

## Controlador local
LocationMapControls.astro es un panel de operador separado del componente de cliente.
location-map-controls.js valida y aplica sólo opciones visuales: usa data-skin,
las clases/partes existentes y mueve el mismo bloque de información entre header/body
para las tres composiciones, conservando el nodo del mapa y las acciones existentes.
Se amplía el visual del marcador con setLabelVisible y ambos adaptadores con
setMarkerLabel; no se remonta el mapa. Versión del hueso 0.3.0.
El cliente privado se compila con esbuild para compartir estos controles. Se consulta
GET /trial-status sin reserva; POST /trial-config sólo tras activar Google una vez.
Se mantiene el cupo persistente de 10 y no se consumen cargas para verificar el panel.
Pruebas de validación de configuración y navegador offline con API double, siete
anchos/breakpoints, pieles/composiciones, identidad de mapa, foco, persistencia,
estado agotado y cero llamadas reales a Google. Evidencia local etiquetada offline.

Resultado: 45 casos (15 anchos × tres composiciones), las tres pieles revisadas,
misma instancia/canvas y cero reservas reales consumidas. El estado agotado permite
seguir cambiando piel. Persistencia inválida rechazada sin cambiar la vista. Se
evitó partir el número de edificio con guion envolviendo tokens de la dirección
en spans nowrap, sin alterar su texto. Diez tests y typecheck sin diagnósticos;
regresión del taller de 17 anchos y 17 checks Google offline aprobada. No se consumió
la última reserva para una nueva prueba viva del controlador. Recibo público en
docs/bones/location-controls-verification.json; capturas/reports privados.
