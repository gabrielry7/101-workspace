# Revisión de los ocho candidatos según el feedback del usuario

Fecha de trabajo: 25 de octubre de 2026, Bogotá. Las verificaciones finales terminaron en UTC el 26 de octubre. Nueva versión aislada en `.tools/claude-worktrees/restaurant-feedback8-20261025`, sin merge, commit ni push. [Galería local](http://127.0.0.1:4328/b3/). La colección anterior permanece en su worktree y preview de puerto 4327. Las ocho revisiones esperan valoración del usuario; no se registra aprobación estética ni de producción.

## Cambios visibles

- **01 y 02:** se conserva la primera impresión que gustó. Se eliminan controles superpuestos al vídeo; opiniones al principio y accesos directos con nombres claros sustituyen bloques ambiguos.
- **03:** se mantienen fotografía asimétrica y fuego; vídeo de fondo silencioso, continuo y automático con preferencias normales. Navegación lateral izquierda en escritorio y menú adaptable en móvil.
- **04:** conserva vino y composición fotográfica; Fraunces vertical reemplaza la tipografía anterior.
- **05, Casa y patio:** nueva entrada fotográfica, crema y terracota, Young Serif y DM Sans.
- **06, Cocina abierta:** nueva composición partida con fotografías, verde profundo y latón, Archivo y Newsreader.
- **07, Cartel duotono:** nueva entrada de tres fotografías, coral e índigo; conserva el tratamiento de imagen que interesó, con Instrument Serif y DM Sans.
- **08, Hoja de contactos:** primera vista con fotografías de comida, hueso, tinta y rojo tomate; mantiene la transición de gris a color, con Familjen Grotesk.

Menú, Reservas, Sobre el restaurante, Ubicación, Preguntas, Noticias, Opiniones y Contacto tienen nombres explícitos. La navegación, los títulos y el pie usan esa presentación sin alterar los slugs históricos del contrato. Se retira Pedidos del recorrido público: su antigua selección demostrativa no era una reserva. La URL antigua informa que esa función está retirada y no se anuncia.

Cada tipo de página tiene una composición según su función: carta amplia por categorías, planificador de reserva de tres pasos, relato fotográfico, mapa con información de visita, preguntas desplegables, noticias editoriales, opiniones y opciones de contacto. Se mantiene coherencia de marca entre secciones. Las reservas son una demostración local: no consultan disponibilidad, envían solicitudes ni recogen datos personales.

La carta conserva 40 platos y ocho categorías, búsqueda y filtrado, retorno a categoría y detalle independiente con ingredientes, alérgenos, calorías ficticias y moneda. Cada detalle tiene una foto; sólo los cuatro platos originales conservan vídeos manuales. La acción principal ahora lleva a reservar mesa. Ningún hecho culinario se infiere de las imágenes.

## Ubicación y multimedia

El usuario respondió «Una direccin al azar, por ahora.». Se usa el punto público Parque de los Novios / El Lago, Calle 63 #45-10, Bogotá, como **ejemplo**, con aviso de que no es una sede real de La Mesa. El mapa OSM se carga por acción del visitante; se ofrecen enlaces a Google Maps e indicaciones. La ubicación del visitante se pide únicamente al pulsar calcular distancia y se procesa localmente: distancia aproximada en línea recta, sin tiempo de viaje ni persistencia de coordenadas. Se verifica denegación y reintento.

Se adquirieron 36 fotografías seleccionadas con la API Pixabay ya disponible, mediante búsquedas acotadas por plato, sin rastreo ni paginación masiva. Junto a las cuatro originales dan cobertura ilustrativa a los 40 detalles. Algunas muestran ingredientes, preparación o una presentación distinta y lo dicen expresamente: no representan recetas documentales del restaurante ficticio. Se revisaron hojas de contacto y se reemplazaron dos selecciones; no se exportan credenciales ni cachés crudas de la API.

El manifiesto complementario tiene 220 activos, 292 concesiones acotadas, 6.952 usos registrados, 408 rutas y vínculos para 40 platos y ocho categorías. Mantiene validación de permisos, bytes, transformación, créditos y handles verificados. No modifica los manifiestos, pins o concesiones históricos. Los recursos originales y derivados de producción quedan en el worktree retenido. Las fuentes nuevas son WOFF reales autoalojadas con sus licencias OFL.

El vídeo ambiental respeta movimiento reducido, ahorro de datos, visibilidad y reproducción rechazada. Un control en la navegación permite pausar/reanudar sin volver a superponer botones al hero. Los vídeos de platos siguen siendo manuales y no se precargan automáticamente.

## Colaboración y verificación

Se ejecutó el doctor real del puente Claude Code y cuatro llamadas acotadas sobre una misma sesión, con tareas JSON, respuestas reales, diffs inspeccionados y feedback. Claude implementó en los renderers Astro/CSS existentes; no se introduce generador, servicio, framework ni dependencia. Codex seleccionó explícitamente el contexto de la base sucia, adquirió y validó medios, mantuvo los permisos, realizó QA y corrigió finalmente la fila de plato destacado del candidato 06: nombre y precio ocupan dos filas junto a la foto. El desbordamiento restante estaba en esa lista, no en los accesos rápidos.

| Comprobación | Resultado |
|---|---|
| Pruebas completas | 439/440; único fallo histórico H8: `LOCK_BROWSER_MISMATCH` donde el negativo esperaba `LOCK_AUDIT_FILE_MISMATCH` |
| Astro / TypeScript | 340 archivos; cero errores, advertencias o hints |
| Build final | 532 páginas, incluidas 408 rutas de candidatos B3 |
| Preservación | 123 páginas históricas ajenas a esta iteración y sus assets referenciados idénticos |
| Carta y detalles | 472 vistas; 320 juegos de hechos conservados, filtros y alternativa sin JavaScript verificados |
| Interiores | 288 vistas en 360/390/768/1440; cierre del último desbordamiento comprobado |
| Recorridos | Menú → plato → reservas con teclado en los ocho; resumen y cancelación local de envío verificados |
| Mapa | Documento real del proveedor HTTP 200 y capturas de escritorio/móvil; permiso denegado y reintento, distancia con coordenadas emuladas |
| Movimiento | Reproducción real, silencio, bucle y pausa/reanudación en 01/02/03; poster con movimiento reducido en los ocho |
| Carga local | Máximo HTML gzip 33.656 bytes; JS referenciado 16.077 bytes; incremento máximo 6.286 bytes gzip respecto a la misma ruta anterior; dependencias intactas |

La matriz de carta/detalles y las pruebas completas preceden las últimas correcciones exclusivamente CSS de interiores/portada. El build y la matriz de interiores se repiten después de la corrección final; los módulos de datos y comportamiento permanecen iguales. No se resealan locks para ocultar H8 ni se declara la suite completamente verde. Las matrices predeterminadas no generan solicitudes externas; el mapa y la ubicación se prueban en un caso separado y explícito. La revisión local no constituye certificación integral WCAG, rendimiento de campo ni integración comercial.

El detector se ejecutó una vez: sus tres avisos por el prefijo «Inter» corresponden a la familia real Instrument Serif. No se añade una excepción global ni se repite para ocultar avisos. Georgia e Impact en 01/02 pertenecen a las identidades anteriores que el usuario pidió conservar.

Evidencia: [snapshot y hashes](../evidence/claude-code/feedback8-20261025/artifact-manifest.json), [intercambios reales con Claude](../evidence/claude-code/feedback8-20261025/cli/index.json), [carta](../evidence/claude-code/feedback8-20261025/catalogue/audit.json), [interiores](../evidence/claude-code/feedback8-20261025/interiors/audit.json), [recorridos](../evidence/claude-code/feedback8-20261025/flows/flows.json), [mapa](../evidence/claude-code/feedback8-20261025/map/map.json), [capturas](../evidence/claude-code/feedback8-20261025/captures/captures.json), [medios](../evidence/claude-code/feedback8-20261025/media-review.json).

La [revisión independiente](../evidence/claude-code/feedback8-20261025/verification/independent-review.md) emitió **ship** para presentar esta revisión acotada de los ocho candidatos al usuario. Antes pidió repetir la captura de escritorio del mapa porque se había tomado antes de su pintado; la toma final muestra calles, marcador y controles reales. No se cambió la interfaz para resolver esa captura. La [documentación del sistema](../evidence/claude-code/feedback8-20261025/design-system/DESIGN.md) queda en el paquete local de esta iteración, sin convertir propuestas en un diseño aprobado ni modificar la documentación global heredada. La [verificación del export](../evidence/claude-code/feedback8-20261025/export-verification.json) confirma 296 archivos de artefactos y 23 de CLI con hashes correctos y sin credenciales detectadas.

El [roadmap](../roadmap-next-steps-20261025.md) registra esta iteración autorizada y vuelve después a consolidación, datos reales autorizados, cobertura y recorrido de entrega. Se conservan los ocho motores como propuestas, sin abrir un noveno ni elegir un ganador por el usuario.
