# B3 — segunda iteración: entrada audiovisual y navegación por páginas

Histórico del 2026-10-16. El usuario valoró 01/02 y pidió otra ampliación el 2026-10-20: consultar [valoración y entrega posterior](b3-human-feedback-20261020-report.md). Las rutas muestran ahora esa entrega, no las capturas históricas de este informe.

Evaluación: 2026-10-16, America/Bogota. Base Git `3451ad7e171696895eb08cdd4b641ad951598c6b`. **Preparado para revisión técnica y humana; no aprobado estéticamente, sin ganador y sin inicio de B4.** La revisión anterior fue rechazada por el usuario por genérica, paletas poco favorables, entrada débil, créditos bajo imágenes y acumulación de funciones. El dictamen independiente anterior no se transfiere a este cambio.

## Resultado revisable y petición atendida

Abrir [comparador](http://127.0.0.1:4331/b3/). Cada propuesta dispone de ocho páginas: inicio, carta, reservas, pedidos, visita, historia, preguntas y créditos. Son **32 rutas**, mismo restaurante ficticio, SitePlan y contenido aprobados. El inicio contiene identidad y enlaces; no apila carta, pedido ni reserva. La carta conserva imágenes por plato, buscador, categorías e ingredientes/alérgenos/calorías ficticios. Reserva y selección conservan su carácter demostrativo explícito, sin envío, cobro ni disponibilidad real.

| Petición humana | Cambio compartido | Evidencia |
| --- | --- | --- |
| Entradas y paletas más próximas a referencias | Cuatro operadores de portada; blanco/negro/rojo, escalas y relaciones diferentes | `site.json`, ocho portadas desktop/móvil, 16 tamaños adicionales |
| Funciones en páginas propias | Navegación a rutas reales; carta enlaza al pedido con un ID permitido | 32 HTML, auditoría de enlaces, recorrido móvil registrado |
| Vídeo ambiental ancho completo y automático | Fondo silencioso, loop/playsinline, cover, pausa accesible, poster y política de movimiento | 24 observaciones reales de portada con reproducción y geometría; prueba pausa/reanudar |
| Créditos fuera de las fotos | Página de créditos por propuesta, enlazada en todas las páginas | Cero figcaption en 64 vistas, autores/licencias/orígenes contrastados |
| Iterar antes de calificar | Rechazo y recomendaciones registrados, sin score ni favorito supuesto | `data/design/experience-v1/human-feedback.json` |

Las cuatro propuestas usan los mismos medios y hechos:

1. **La mesa abierta:** vídeo a toda pantalla detrás de identidad serif centrada; interior blanco y carta en dobles páginas desplazadas.
2. **Mucho apetito:** masthead rojo condensado sobre blanco, vídeo debajo sin marco; carta en filas alternas.
3. **En movimiento:** negro/blanco, navegación centrada, título y manifiesto separados y banda audiovisual; catálogo de escalas asimétricas.
4. **A nuestra manera:** blanco puro, título sans y manifiesto serif en campos laterales; carta con índice y relaciones horizontales.

`ExperienceComposition.astro`, `experience.css` y el runtime compartido consumen selectores declarativos de composición. No hay CSS por candidato/cliente, dependencia visual nueva ni cuatro componentes independientes por restaurante. Se reutilizan `ContextualModule`, `ContextualImage`, `PreviewIntent`, Foundation y cliente contextual. El runtime comercial 101 y `101-world-model` continúan ausentes; es el laboratorio Astro local.

## Referencias y juicio visual

Se conserva el corpus de 21 referencias y sus alcances: no se transforman observaciones del asistente en preferencias humanas. Se volvió a abrir **OSIP** en navegador: su entrada real usa fotografía a sangre y navegación mínima; la captura anterior seleccionada no mostraba bien ese primer pliegue. Recibo y captura originales en `experience-reference-revisit-01/`. No se copiaron fotografías, marcas o código de referencias. Las referencias restringidas a menú o storytelling siguen teniendo esos límites. La correspondencia por propuesta está en `site.json` y el corpus previo `visual-review-2026-10-15.json`.

Inspección del asistente: portadas desktop y móvil originales; cartas desktop, reserva y pedido móvil ampliados; conjunto de 64 capturas mediante hojas de contacto derivadas para QA (temporales excluidas). Se observa separación clara de funciones, ancho audiovisual completo, tipografía y blanco/negro/rojo consistentes, sin colisiones visibles. La imagen de stock del clip y la heterogeneidad de las cuatro fotos siguen limitando la dirección audiovisual. **Esto no demuestra que al usuario le gusten, ni que alcance la calidad de una campaña de referencia.** La siguiente decisión es humana y puede ser «ninguna».

## Permisos y bytes reales

No hubo nuevas adquisiciones, llamadas a Pixabay, cuentas, compras o descarga de catálogos. Se conserva B2/H3 y el manifiesto B3 anterior. La evaluación contextual nueva está separada en `data/media/demo-v1/b3-experience-review.json`, con 84 usos exactos, 32 rutas, cliente/proyecto/sucursal/finalidad y revisión interna hasta no más tarde de 2026-11-14. No licencia general multicliente ni permiso documental.

Fuentes oficiales comprobadas el **2026-10-16**: [términos Pixabay](https://pixabay.com/service/terms/), versión visible **November 18, 2024**, y [resumen de licencia](https://pixabay.com/service/license-summary/). Las secciones 4–6 sustentan CC0 según fecha, adaptación y atribución opcional, sujetas a restricciones. El detalle por archivo y revisión de terceros permanece en B2 y en [review.md](../evidence/corrections/b3/experience-media-01/review.md). No se inventan releases; una URL ni un campo VERIFIED constituyen la evidencia.

Se admite CROP de presentación CSS y crédito enlazado sólo para el nuevo manifiesto revisado. La política anterior continúa intacta. El componente bloquea crédito enlazado si el handle no proviene de la nueva evaluación confiable, y bloquea cover si el uso no incluye CROP. Aviso de escenario ficticio y no respaldo de Pixabay/autores permanece en cada pie. El hueco documental histórico sigue bloqueado.

Se reutilizó el original privado de B2 `.tools/b2-demo/originals/149678.mp4`, SHA `37d5f583f0368d376dcb461b18b5c06021eeee92bed281dc16be4df2734223d0`. Remultiplexado local sin recodificar ni ampliar, copiando únicamente muestras de vídeo y eliminando pista y bytes huérfanos de audio:

- Derivado: `public/media/b3-experience/149678-silent-1280.mp4`.
- SHA: `15d8a7edce609b9a48eea6815cd7d1a275610e3bbce9a8488b86ad1548d252c1`.
- 2.577.142 bytes, H264 1280×720, 25 fps, 234 frames, 9,36 s, única pista `vide`.
- Decodificación OpenCV de **todos los frames** contra el original: píxeles idénticos. `remux.json` y `decode.json` fijan comprobaciones y herramientas.

El original con audio no se sirve ni adquiere permiso sonoro. La excepción heredada de audio sólo permite el nuevo derivado y SHA exactos. El vídeo es ilustrativo del concepto ficticio, no prueba de un plato real. Pantallas grandes pueden ampliar visualmente la fuente 720p hasta 1,5× en las vistas probadas; no se afirma 1080p/4K ni calidad de campaña.

Los bytes audiovisuales privados se excluyen de Git. Sólo se versiona el `.gitignore` específico del nuevo directorio, sin alterar `.gitignore` raíz ni el protegido de H3. Para reproducir en otra máquina hacen falta los originales autorizados B2 y sus evidencias privadas; no se promete una descarga automática desde un clon. Con el original local, `b3-remux-video.ts --derive-reviewed-source` reproduce el archivo exacto sólo si el destino no existe.

## Verificación y resultados

Baseline anterior a la edición de runtime: `experience-baseline-01/journal.json`, contratos/tests/check/validate/build128 y replays. El único fallo de tests previo era H8 `LOCK_BROWSER_MISMATCH`. La receta no invoca proveedores.

Receta posterior completa: `experience-reviewed-01/journal.json` (tras `experience-post-02`). Resultado: **394/395 tests**, único fallo histórico `tests/lock-files.test.ts` por `LOCK_BROWSER_MISMATCH`; ocho pruebas nuevas B3 pasan. Exportación de contratos, check (245 archivos; cero errores/avisos/hints), validación, build **156 páginas**, B3 scenario/proposals, B2 media/library, B1, taxonomy/planner, media replay/verify H3, composition/design/audit/cohort y H9 pasan. H8 lock verify continúa bloqueado por entorno y no se reseña como PASS. **2.815 archivos protegidos sin cambios.**

La primera receta `experience-post-01` conserva dos fallos propios ya corregidos: importación no usada y separación incorrecta de 80 observaciones en el test que esperaba 64. Se guardó `observations-all-attempts.json` intacto y se separaron, sin cambiar resultados, 64 vistas principales y 16 responsive. No se ocultan intentos fallidos ni se atribuyen a H8. `verification-initial.json` es un recibo histórico previo a añadir responsive/interacciones; el recibo vigente es `verification.json`.

Verificación nueva: `scripts/b3-experience-verify.ts --verify`, diario `experience-extra-01`. Contrasta contexto, 64 parejas página/viewport exactas, **42 hechos únicos y siete módulos por propuesta y viewport**, alcance, oferta→archivo/uso, medios decodificados, fuentes/créditos/avisos, diagnósticos y restricciones, rutas, HTML, bytes public/dist y hashes de fuentes/capturas. Valida otras 16 portadas a 360/768/1024/1920 px. Cero desbordamientos observados, fuentes computadas ≥14 px, controles auditados ≥43 px y contraste calculado ≥4,5 para los elementos cubiertos. Es una auditoría principal acotada, no certificación WCAG completa ni análisis de todos los frames del fondo.

La captura IAB fullPage excluye barra de desplazamiento y puede refluir texto: algunos JPEG y la observación DOM posterior difieren de altura hasta 69 px (<5%). Se conservan ambos; no se afirma geometría idéntica a píxel ni DPR1. Las capturas originales, fechas, hashes y observador exacto están en `experience-iab-01`. No se recapturó Edge controlado, ni se midieron Web Vitals o transferencia fría. Las auditorías históricas siguen siendo evidencia de sus commits; no se reseñan recibos viejos para aprobar un renderer nuevo.

Recorrido interactivo **representativo**, candidato 04 móvil: autoplay silencioso, pausa/reanudar, abrir menú, Escape devuelve foco a summary, navegación a carta propia, búsqueda pasta, filtro ensalada, detalles pizza, enlace al pedido con pizza, añadir segundo plato, vaciar y pasar a reserva; mesa 2 seleccionable y mesas 3/6 deshabilitadas, resumen inequívocamente ficticio. `interactions.json` registra observaciones reales. No se afirman todas las combinaciones de todos los candidatos, teclado/lectores de pantalla exhaustivos o preferencia reduced-motion emulada en navegador. La política de cinco condiciones (movimiento reducido, ahorro de datos, pestaña oculta, fuera de vista y pausa manual) sí tiene pruebas unitarias; sin JS queda imagen estática.

Peso estático verificable: 32 HTML entre **31.811 y 44.186 bytes**, nueve archivos de medios utilizados entre todas las rutas **3.462.266 bytes** (incluye dos tamaños de cada foto y el vídeo de 2.577.142). No equivale a descarga inicial por página. Fuentes del sistema, sin descargas tipográficas. El selector responsive y lazy loading se conservaron; las páginas sin vídeo no incluyen el reproductor. El coste real de autoplay y su efecto sobre LCP requieren una medición de red/rendimiento posterior, no inventada aquí.

Comandos desde raíz, con Node portable 24.21.0:

```powershell
.tools/node-v24.21.0-win-x64/node.exe --experimental-strip-types scripts/b3-run.ts NUEVO_ID
.tools/node-v24.21.0-win-x64/node.exe --experimental-strip-types scripts/b3-experience-verify.ts --verify
.tools/node-v24.21.0-win-x64/node.exe --experimental-strip-types scripts/b3-remux-video.ts --verify
& 'C:/Users/gabri/AppData/Local/Programs/Python/Python313/python.exe' scripts/b3-inspect-video.py --verify
```

La receta exporta los nuevos contratos asociados `ExperienceV1` y `ExperienceMediaReviewV1`, preservando los V1 anteriores. El remux es deliberadamente estrecho para el MP4 fijado, no un conversor multimedia universal.

## Pendiente

[Revisión independiente y corrección de cobertura](b3-experience-independent-review.md) recibidas: **APTO PARA REVISIÓN HUMANA** sobre `fa0735a` + `24e2bfc`, sin aprobación estética. Sigue pendiente el juicio humano. Ningún ganador, preferencia positiva, publicación, entrenamiento o Design Lock final. Si el usuario rechaza las nuevas entradas, la corrección continúa en la gramática y selección audiovisual dentro de B3. No iniciar B4.
