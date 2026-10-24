# B3 — revisión independiente del feedback humano del 20 de octubre

Tarea autorizada `01a11911-1da1-73e0-8234-132547fc8f8f`. La petición sobre `b0eefce10b96e5c409e72e2009ae14e7f1e90576` fue entregada. No se transfiere el dictamen del 16 de octubre ni se convierte el gusto por 01/02 en aprobación de esta entrega nueva.

## Hallazgos recibidos y corregidos

1. **Redes de muestra con self-links.** La revisora señaló que Instagram/Facebook, aunque declarados ficticios, eran enlaces activos de vuelta a contacto con flecha de salida. Se reemplazaron por elementos no interactivos «De muestra». El observador registra placeholders y controles sociales; la auditoría bloquea enlaces/botones sociales y mailto/tel/WhatsApp activos sin datos autorizados. Pruebas negativas cubren self-link/control y protocolos de envío. El recorrido R3 confirma cero controles/enlaces sociales y WhatsApp deshabilitado.
2. **Binding editorial insuficiente.** La revisora señaló que se auditaban texto/ID de post y medios globales, pero un intercambio de imágenes entre tarjetas podía pasar. Ahora cada tarjeta registra slot, `currentSrc` y usos; se contrastan con `post.slot`, necesidad exacta, asset URI y uso autorizado. Los negativos intercambian bytes/uso o sustituyen slot sin cambiar el conjunto global y deben fallar.
3. **Capturas vacías.** La revisora abrió `human-responsive-20261020/candidate-01-home-small.jpg` y `candidate-04-home-tablet.jpg`: sólo mostraban fondos, por lo que no acreditaban visualmente esos tamaños. También detectó una portada parcial gris en el primer intento R3. Se conservan los archivos históricos y se retira su valor como prueba visual vigente. Con navegador visible se recapturó la matriz R3, sin atribuir una causa raíz demostrada al problema de pintura en background. Un timeout reinició la sesión de automatización; el JSON parcial queda como `observations-aborted.json`.

## Evidencia de seguimiento

`human-iab-r3-20261020` y `human-responsive-r3-20261020` son los conjuntos vigentes: **88 + 16 observaciones y 136 capturas originales**, incluyendo contacto/redes en home y página propia. El observador actual conserva asociaciones editoriales y estado no interactivo de redes. Se volvieron a inspeccionar las 16 portadas responsive mediante hojas de contacto y muestras originales ampliadas. El tamaño nativo puede diferir del viewport CSS y algunos encuadres anchos quedan recortados por la superficie de captura; no prueba completa a píxel, certificación de todos los elementos o Web Vitals.

`capture-presence.ts` recorta el centro de la captura para excluir barras, materializa el crop/resize y calcula entropía, desviación, proporción gris y bordes horizontales. Bloquea uniformidad y capturas mayormente grises, con negativos sobre **los dos JPEG reales rechazados**. Es una heurística de presencia, no un evaluador estético, OCR o garantía de encuadre. El primer umbral producía cinco falsos negativos (vídeo de fondo desenfocado y textos pequeños a ancho grande); se inspeccionaron, se conservó `pixel-presence-initial.json` y se ajustó la regla para admitir textura o bordes, manteniendo el rechazo de los archivos vacíos. `pixel-presence.json` contiene los resultados actuales, 136/136, y el replay los recalcula desde los bytes.

La receta `human-reviewed-20261020-01` registra **405/406 tests**, único H8 heredado `LOCK_BROWSER_MISMATCH`, **11/11 nuevos**, check 256 sin diagnósticos, exportación/validación/build168/replays/medios PASS y 2.815 protegidos intactos. `human-reviewed-extra-20261020` registra las pruebas focales y replay nuevo. Una ejecución del verificador mientras build reemplazaba dist falló temporalmente con una ruta ausente; se repitió secuencialmente después de build, sin relajar la comprobación de enlaces.

## Dictamen final recibido

Recibido el 2026-10-20 sobre `986e3b27d8ef7e22ce5e5b42201d7bede701d533`: **B3 técnicamente listo para revisión humana**, sin aprobación estética final, Design Lock, B4 o publicación como negocio real.

La revisora informó contrastar el diff de redes, binding por tarjeta y negativos, y abrir capturas R3 verificadas de 01/04 móvil y contacto 04 desktop. Confirmó que muestran contenido y redes no interactivas. No se le atribuye inspeccionar las 136 imágenes o todas las combinaciones.

Verificaciones que declaró repetir con Git limpio: suite **405/406**, único fallo `tests/lock-files.test.ts` por H8 `LOCK_BROWSER_MISMATCH`; pruebas nuevas **11/11**; check **256 archivos, cero diagnósticos**; build/validate **168 páginas**; replay **88+16**, **44 rutas**, **3.462.266 bytes de medios**. Git limpio después de build. No se afirma un clon nuevo sin medios privados ni una repetición independiente de toda la receta de 24 pasos: esa receta y los 2.815 protegidos son evidencia del ejecutor.

Límites expresos: la heurística sólo filtra capturas sin contenido suficiente; persisten recorte de superficie y fullPage no conseguido, sin vitals ni Edge. Las direcciones 01/02 fueron apreciadas antes, pero sus refinamientos y 03/04 siguen sin valoración final.

## Prompt propuesto recibido literalmente

> Revisa las cuatro propuestas B3 del commit 986e3b2 en /b3/, en escritorio y móvil. Compara 01 La mesa abierta y 02 Mucho apetito con las versiones que te gustaron; dime si las mejoras de diario, opiniones y contacto conservan esa calidad. Valora si 03 El arte de quedarse y 04 Fuera del reloj ya tienen suficiente intención artística. Señala cuál(es) conservarías, cambios concretos y problemas de lectura, navegación o medios; si ninguna convence, dilo. Las opiniones/redes/contacto son datos ficticios de demostración y no están conectados. Tu preferencia anterior no cuenta como aprobación de estas versiones. No iniciar B4 ni bloquear diseño hasta tu decisión explícita.

Se presenta la entrega y se espera juicio humano. No se registra ninguna nota o aprobación a partir del dictamen técnico.
