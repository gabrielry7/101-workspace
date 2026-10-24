# Complemento B2 — medios de Pixabay para pruebas ficticias

Fecha: 2026-10-14 America/Bogota; recibos UTC del 15 de octubre. Base `58fb846f99be2ba0ff8da3aaba98da8778c9d708`. El usuario aclara que las primeras pruebas serán ficticias y autoriza obtener los medios necesarios mediante la API existente. **El material documental de una empresa real no es condición para preparar estas demos.** Se corrige esa ambigüedad del panel y se completa el recorrido de Pixabay, sin iniciar B3.

Resultado: **cuatro imágenes de platos y un vídeo ilustrativo**, obtenidos, inspeccionados y presentados localmente en `/b2/demo/`. Se mantienen los permisos por uso y el bloqueo documental del fixture H2 original. No se declara aprobación estética de una página final ni un negocio real. El informe B2 anterior conserva el estado histórico previo a esta aclaración; este documento describe el complemento vigente.

## Archivos seleccionados y permisos

Las fichas oficiales identifican los siguientes recursos. Términos evaluados: [Pixabay 2024-11-18](https://pixabay.com/service/terms/), [API](https://pixabay.com/api/docs/) y [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/legalcode.en). Consulta realizada en esta sesión; las fichas servidas por búsqueda web son copias oficiales indexadas con antigüedad indicada por la herramienta, no capturas HTTP nuevas certificadas. La API sí respondió y entregó los bytes en vivo.

| Uso ficticio | Archivo/ficha, autor y publicación reportada | Licencia aplicable evaluada |
| --- | --- | --- |
| Pizza, módulo de carta; portada del vídeo como uso separado en identidad | [4991789](https://pixabay.com/photos/pepperoni-pizza-thin-crest-4991789/), shailesh68, 2020-04-02 | Pixabay Content License, con composición contextual y restricciones. |
| Pasta, carta | [3547078](https://pixabay.com/photos/pasta-italian-cuisine-dish-3547078/), RitaE, 2018-07-19 | CC0 por regla explícita §4 para Published date anterior a 2019-01-09. |
| Ensalada, carta | [791891](https://pixabay.com/photos/salad-fresh-veggies-vegetables-791891/), JillWellington, 2015-06-01 | CC0 por §4. Sin rostros en este archivo; no se ignora la nota de la autora sobre otros usos con caras. |
| Postre, carta; sin afirmar que sea una receta concreta | [1971552](https://pixabay.com/photos/cake-piece-plate-dessert-pastry-1971552/), Daria-Yakovleva, 2017-01-11 | CC0 por §4. No se llama tiramisú por el término buscado. |
| Escena culinaria, identidad | [149678](https://pixabay.com/videos/pizza-peperonni-cheese-italian-149678/), u_mcy3jdr8zw, 2023-02-07 | Pixabay Content License; únicamente se presenta el derivado sin audio verificado. |

La interfaz de los tres archivos antiguos muestra la etiqueta genérica Content License, mientras los términos §4 establecen CC0 por fecha. Se registra la diferencia y se conserva una política interna más estrecha: composición ficticia contextual, sin redistribución de archivos sueltos en Git. No se atribuye una sola licencia indiferenciada al paquete.

Los originales obtenidos son **renditions del proveedor**, no originales de cámara: imágenes de 1280 px y MP4 1280×720. `camera_original=NOT_OBTAINED`. El modo REAL señala archivos/permisos reales; el escenario es SYNTHETIC_DEMO. `ai_generated=NOT_REPORTED` conserva la ausencia de etiqueta positiva observada, sin certificar origen fotográfico o ausencia de IA. Se excluyó una alternativa expresamente marcada AI Generated.

| Bytes de origen retenidos privadamente | Tamaño | SHA256 |
| --- | ---: | --- |
| `4991789.jpg` | 476.639 | `7b18540ba092957d5be611ff45096ba8339f46102bf523ce08fdff4290e00bfb` |
| `3547078.jpg` | 229.835 | `de53d4b3b757d22f964b0c7a9c7058be60afb64e9c6978a49a789180fdfe47c1` |
| `791891.jpg` | 283.569 | `88287ff705eae28a0690ce06c0b411da1461b9b875bdab8a2c79bb832542376c` |
| `1971552.jpg` | 253.809 | `1845534709cdd7efad8f66f872dc07de79c43b231fec8b44c917c6ccefe5dc36` |
| `149678.mp4` | 2.801.470 | `37d5f583f0368d376dcb461b18b5c06021eeee92bed281dc16be4df2734223d0` |

Se conservan ocho WebP de 640/1280, calidad 84/effort 6 sin crop ni ampliación, y un WebM VP8 640×360, 234 frames/25 fps = 9,36 s. [Paquete versionado](../../data/media/demo-v1/pixabay-fictional.json) contiene **los 14 hashes, rutas/tamaños, cinco fuentes, cinco grants y diez usos**. Seis necesidades de presentación: cuatro cards, vídeo y portada separada; ésta tiene scope/finalidad/relevancia/grant propios, no hereda implícitamente la autorización de carta.

El WebM presentable pesa **4.446.094 B**, SHA `d49c312d1db0515b802ce668206cbf4ded1670ea3b537f0dfbf1a058563d353b`. Es más pesado que el MP4 recibido: no se presenta como mejora de compresión ni listo para un hero en autoplay. Se eligió el derivado 640 frente al primer VP8 1280 de 11,9 MB; los candidatos se conservaron privadamente. H264 local no ofreció una vía de mejora demostrada sin otras herramientas; no se instalaron librerías. El vídeo final se carga sólo por interacción y su peso se informa en la demo.

## Alcance y evidencia de derechos

[Evaluación por archivo](../evidence/corrections/b2-demo/legal-review.md): cliente `101-design-compiler-fixture-review`, proyecto `b2-fictional-pixabay-demo`, página `/b2/demo/`, CO. Los usos de carta apuntan al módulo/scope de sucursal del SitePlan; vídeo/portada al módulo/scope de identidad. Cada imagen es ILLUSTRATIVE; vídeo/portada ATMOSPHERIC, representación GENERIC_CONTEXT y sin factual subject IDs. No satisface las necesidades DOCUMENTARY del restaurante histórico. No se cambia H2, no se inventan ingredientes, alérgenos, nutrición o empresa real.

Permite descarga individual, alojamiento local y transformaciones técnicas especificadas, en un escenario compuesto con texto/créditos/avisos; no redistribución/venta standalone, catálogo competidor, uso como marca, respaldo engañoso, otro cliente/proyecto o entrenamiento. La expresión abreviada «no descarga standalone» del documento de evaluación significa no ofrecer archivos sueltos a terceros; no prohíbe obtener individualmente los recursos autorizados. Los términos admiten incorporación y modificación, pero no expresan una autorización universal de visión por modelos: la inspección visual asistida de estos archivos para este encargo se documenta como **interpretación acotada del permiso de uso**, con riesgo residual, no permiso genérico de IA. No hay entrenamiento, embedding, clasificación o edición generativa.

No se observaron personas identificables, marcas o arte/texto identificable en los cuatro archivos finales; no se identificaron releases necesarios para este uso contextual. No se afirma que Pixabay haya entregado releases ni garantía universal de terceros. Las fotos originales, sus derivados y muestras del clip se abrieron realmente mediante `view_image`. La revisión visual del vídeo cubre muestras a un segundo en todo el intervalo; la decodificación técnica sí cubre los 234 frames. No se afirma revisión visual exhaustiva cuadro a cuadro.

El MP4 contiene `vide` y `soun`; no se escuchó ni aprobaron derechos del audio. OpenCV/Python **ya instalados** transcodificaron únicamente frames BGR a VP8, sin pasar audio al writer. [current-container.json](../evidence/corrections/b2-demo/current-container.json) verifica los hashes del MP4 correcto y el WebM con una única TrackEntry `V_VP8`/tipo 1; [recibo de decodificación](../evidence/corrections/b2-demo/video-derivation-640.json) conserva herramienta/binario y ambos conteos. Mutear el MP4 no se aceptaría.

La excepción asociada B2 sólo resuelve `VIDEO_AUDIO_RIGHTS_REVIEW_REQUIRED` para el **derivado exacto verificado** dentro del handle opaco. Conserva el resto de gates H3. El MP4 de origen no tiene un uso presentable y sigue bloqueado. No se modificaron contratos/gate H3 originales. Inspección/relevancia referencian los archivos evaluados y sus hashes; la revisión de licencia referencia su documento/SHA correspondiente. Un fixture que escriba VERIFIED o recalcule checksum no consigue admisión.

Sello revisado del paquete: `970cc4a6bfbe7af3d8d1de15656fe532a97883963a3e81d9c9390dc07d57f425`. `verifyDemoPackage` contrasta fuentes/evidencias/bytes reales, dimensiones/decodificación de imágenes, estructura de tracks, recibo de vídeo, fixture/bindings y contenido exacto de la carpeta presentable. `evaluateDemoUsage` valida uso completo, finalidad, módulo, sucursal, página, cliente/proyecto, crédito, avisos y fecha. Rechaza originales privados, uso documental engañoso y nuevas transformaciones no inspeccionadas. La vigencia interna de 30 días obliga a revisar antes de construir/publicar; el HTML estático ya generado no monitoriza revocación.

## Búsqueda, selección, privacidad y reproducción

Hubo **seis consultas acotadas** (tres resultados cada una): pizza, pasta, salad, tiramisu, vídeo pizza y refinamiento green salad bowl después de inspección. No se paginó, automatizó catálogo o abrió cuenta; no hubo compra. Se obtuvieron diez candidatos explícitos, de los que se usan cinco medios finales. [Recibos](../evidence/corrections/b2-demo/search/receipt.json) conservan las primeras cinco; `salad-bowl.json` registra la sexta y su motivo. Éxito 2xx comprobado por el código antes de aceptar respuestas; esta serie no conserva el número HTTP exacto en cada recibo, a diferencia de la primera prueba histórica B2.

Se rechazaron: 5904093 por decoración/texto/terceros sin resolver; 7030032 por mostrar preparación en vez de postre servido; 7543170 por pertinencia insuficiente de su preparación de remolacha; 8503073 por etiqueta positiva AI Generated, fuera del paquete elegido; 136431 por audio no admitido. Rechazos y candidatos de manifiesto no son permisos actuales. [quarantine.json](../evidence/corrections/b2-demo/quarantine.json) documenta que los artefactos candidatos salieron de `public` antes de cualquier build; el consumidor rechaza archivos adicionales no admitidos allí.

Originales/candidatos, URLs firmadas y respuestas crudas quedan en `.tools/b2-demo`, ignorado. Los únicos nueve archivos presentables quedan en `public/media/b2-fictional/`, ignorado por `public/media/.gitignore`, para la composición local. **Ningún archivo de stock ni vídeo se redistribuye en Git**. El repositorio conserva código, contratos, hashes, evaluación y capturas compuestas con contexto, no una descarga de stock suelto. `.env` no se copia ni imprime. [private-package.json](../evidence/corrections/b2-demo/private-package.json) identifica el respaldo local `.tools/b2-demo/authorized-package.zip`: los 14 archivos seleccionados, el manifiesto y su evidencia, sin clave, caché de búsquedas, candidatos rechazados o dependencias.

Cada caché de consulta tiene ventana 24 h; no se afirma que el timestamp produzca borrado automático. Tras expirar se ejecuta `scripts/b2-demo-cache-purge.ts --expired-only`, que elimina únicamente las respuestas privadas vencidas sin contactar al proveedor. Builds/replays no leen cachés ni realizan nuevas consultas. No se infiere permiso de guardar/redistribuir indefinidamente un catálogo de respuestas. La biblioteca seleccionada y los créditos por archivo son un dossier de usos, separado de esa caché.

Una copia Git pública **no contiene el paquete privado**. Sin la carpeta presentable, la ruta muestra un aviso sin medios; si hay bytes pero falla su verificación, el build bloquea su presentación. El replay explícito falla si falta el dossier/archivos privados. No se declara una reproducción autónoma desde Git solamente. La receta de copia aislada materializa fuentes Git y copia explícitamente esos 14 archivos por SHA, sin API, clave o nuevas descargas. No se copian respuestas crudas ni todos los contenidos de `.tools`.

## Comprobaciones y límites

Siete tests nuevos prueban datos ficticios/archivos reales, licencia CC0 por fuente, gate H3 original bloqueando audio y excepción exacta sin audio, paquete self-sealed/handle forjado, documento real engañoso, otro cliente/proyecto/sucursal/finalidad/página, crédito/avisos perdidos, IA o transformación no permitidas, expiración actual y corrupción de bytes/contenedor. Tests históricos B2 permanecen intactos.

Primera corrida completa [demo-post-01](../evidence/corrections/b2/demo-post-01/journal.json) y [demo-post-02](../evidence/corrections/b2/demo-post-02/journal.json): **372/373**, único fallo histórico `LOCK_BROWSER_MISMATCH`; check/validate/build/replays PASS. El bloque sigue sin declarar toda la suite verde ni reabrir/aprobar H8/H9. Se exporta un contrato asociado nuevo `FictionalMediaPackageV1`, manteniendo los anteriores.

QA-01 detectó el texto eyebrow de 13,6 px frente al mínimo elegido de 14; se aumentó a 14,4. QA-02/03 detectaron iconos nativos del reproductor como URLs data:image/svg+xml; se registró que no son red externa y se corrigió la clasificación, manteniendo el rechazo a HTTP externo y a exposición de JPEG/MP4 originales. Se conservan fallos/primeras capturas.

QA final [qa-05](../evidence/corrections/b2-demo/qa-05/qa.json), posterior al uso de portada explícito: full-page desktop/móvil, 16 HTML H8 idénticos, 2.630 archivos protegidos, ningún overflow, un main/h1/lang=es, skip y anclas por teclado, cuatro imágenes reales decodificadas, crédito/contexto y vídeo reproducido con bytes exactos. Video inicial **0 B**, autoplay=false, preload=none; duración 9,36 s/640×360. Cuatro WebP 640 suman 209.860 B; HTML ronda 8,8 KB, sin JS cliente ni formularios. Lazy no garantiza diferimiento en todos los navegadores: el Edge local precargó las cuatro por su umbral. El coste del vídeo llega sólo al reproducir. No se simula 4G ni se declaran Core Web Vitals de campo, WCAG completa o buena estética final.

Las capturas compuestas y los originales/derivados se inspeccionaron visualmente. El componente usa Foundation/Astro compartidos, contenido separado del estilo y bindings procedentes del paquete; no es una nueva gramática B3 ni una plantilla comercial por cliente. No hay pedidos, reservas, pagos o upstream. Se conserva la baseline de fuentes B2, sin revalidar píxeles históricos B0/H8.

## Reproducción y resultados finales

Fuentes materializadas desde el árbol Git preparado **`f9b4ec58c040e6195058fc9b1aa5b5707b90eaa7`**, con Node/dependencias/browser existentes verificados y copia explícita de los 14 medios autorizados privados. [Materialización](../evidence/corrections/b2-demo/reproduction/materialization.json) documenta cada SHA y ausencia de `.env`, caché API o llamadas al proveedor. No es una instalación nueva ni una copia autosuficiente sólo de Git.

La primera copia aislada pasó tests/check/validate/build/replays, pero la guarda adicional del complemento detectó siete `.txt` históricos normalizados por Git: el manifiesto previo los conservaba como bytes. Se mantienen el fallo [clean-qa-01](../evidence/corrections/b2-demo/clean-qa-01/failure.json) y las capturas. Se comprobaron hash del original y equivalencia LF, y se copiaron exclusivamente esos siete documentos al clon, sin cambiar código, medios o evidencia original: [overlays con rutas y hashes](../evidence/corrections/b2-demo/reproduction/historical-byte-overlays.json). El helper exige exactamente ese conjunto, investiga diferencias adicionales y no permite overrides de producto. Los JSON nuevos que forman evidencia byte-pinned se preservan con `-text`; se verificó también su identidad en el índice Git antes de materializar.

| Comprobación final | Resultado |
| --- | --- |
| Exportación / check / validate / build | PASS, cero errores/warnings/hints, 123 páginas. [demo-post-03](../evidence/corrections/b2/demo-post-03/journal.json). |
| Tests completos | **372/373**, siete nuevos PASS; único fallo histórico LOCK_BROWSER_MISMATCH. Mismo resultado en [demo-clean-01](../evidence/corrections/b2/demo-clean-01/journal.json). |
| Replays B1/H2/H3 y verificadores posteriores pertinentes | PASS, sin nueva adquisición ni recorders creativos. H8 lock verify sigue bloqueado por navegador global heredado; H9 sólo inventario, sin sitios reales elegibles. |
| Replay nuevo actual/histórico y tests después de overlays | PASS, ocho WebP regenerados idénticos en memoria, 14 archivos/10 usos, 2.630 protegidos. [final-clean-checks](../evidence/corrections/b2-demo/final-clean-checks/journal.json). |
| QA aislada final | 2/2 full-page, reproducción de vídeo real, contexto/créditos/bytes comprobados, 16 HTML H8 y 2.630 protegidos PASS. [clean-qa-02](../evidence/corrections/b2-demo/clean-qa-02/qa.json). |
| Comparación raíz/aislada | **HTML, DOM estable y medios servidos idénticos en 2/2 vistas**. [comparison](../evidence/corrections/b2-demo/reproduction/comparison.json). No se declara igualdad RGBA total. |

La comparación de PNG registra 3.263 píxeles distintos desktop dentro de una banda 608×37, y 1.966 móvil dentro de 326×36, coincidentes con los controles nativos inferiores del vídeo. Fuera de esas bandas no hay diferencias; no hay cambios en fotografías, texto o geometría. [Medición de diferencias](../evidence/corrections/b2-demo/reproduction/pixel-differences.json). Se conservan capturas completas, sin enmascararlas. El vídeo/controles no se congelaron a un estado de pintura determinista: se documenta esta variación de captura en vez de afirmar pixel identity o alterar los medios. No se revalida el lock de píxeles histórico B0/H8.

Recetas sin proveedor:

```powershell
$node = '.tools/node-v24.21.0-win-x64/node.exe'
& $node --experimental-strip-types scripts/b2-demo-verify.ts
& $node --experimental-strip-types scripts/b2-demo-verify.ts --historical-replay
& $node --experimental-strip-types --test tests/b2-demo.test.ts
& $node --experimental-strip-types scripts/b2-demo-qa.ts <nuevo-id>
```

El replay actual bloquea revisión interna vencida; el histórico no autoriza servir un paquete caducado. Los writers de búsqueda/obtención/transcode/package son comandos explícitos, no forman parte del build/replay. Falta disponibilidad del paquete privado en otra máquina hasta materializarlo; no se resuelve con descargas automáticas ni un fixture VERIFIED nuevo.

La tarea revisora autorizada emitió **PASS técnico independiente** tras revisar código, archivos, fuentes, informe, staging, pruebas y reproducción; [feedback conservado](../reviews/b2-fictional-independent-review.md). El [recibo final de privacidad/índice](../evidence/corrections/b2-demo/reproduction/delivery.json) comprueba cero coincidencias de la clave, cero rutas privadas y los siete hashes de evidencia exactamente preservados en Git. Se conserva su [prompt B3 actualizado](../reviews/b3-proposed-prompt-after-pixabay.md) sólo como propuesta. Se detiene para revisión humana, sin iniciar B3. Los medios ya permiten pruebas ficticias; los materiales auténticos de una empresa sólo serán necesarios cuando se quiera representarla como tal. La aceptación estética se decidirá al revisar las propuestas completas, no por tener cinco recursos autorizados.
