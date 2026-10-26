# Ocho motores de estilo y salida de la iteración visual

Entrega del 25 de octubre de 2026: **ocho motores en total**, sobre el laboratorio Astro compartido de restaurante. Se preservan 01–04 como preliminarmente aceptados; 05–08 son propuestas nuevas pendientes de valoración humana. No hay Design Lock final, integración comercial ni aprobación de producción.

| Motor | Papel | Dirección |
|---|---|---|
| 01 WhiteInk | General, conservado | Hueso, terracota y composición clásica |
| 02 Vermilion | General, conservado | Rojo y composición de periódico |
| 03 Brasa | Artístico, conservado | Negro, ascuas, Syne y carril lateral |
| 04 Herbario | Artístico, conservado | Papel, ciruela y Bodoni |
| 05 Mercado | General, nuevo | Tiza, pino, mostaza; DM Sans; acceso directo por categorías |
| 06 Marea | General, nuevo | Verde mar, azul y arena; Bodoni; arco fotográfico y carta tranquila |
| 07 Riso | Artístico, nuevo | Azul y amarillo; cartel tipográfico y sobreimpresión de imágenes de ambiente |
| 08 Índice | Artístico, nuevo | Hueso gris, carbón y lima; Syne ancho y navegación por palabras |

[Comparación local](http://127.0.0.1:4327/b3/). La implementación queda en `.tools/claude-worktrees/restaurant-engines8-20261025`. No se hizo merge, commit o push. El README modificado y el resto del trabajo del usuario se conservaron.

## Implementación y procedencia

Claude Code real, doctor autenticado y CLI restringida 2.1.308. Tarea `restaurant-engines8-20261025`, sesión `65c3b819-f25d-472a-a5ee-b1d1b4425ed2`: plan, implementación y corrección concreta en tres intercambios genuinos de la misma sesión. Estimación acumulada reportada del modelo: **USD 1,5655793**, distinta de factura/cuota. Límites: cuatro llamadas, 75 turnos y 720 segundos por llamada, USD 3 por llamada/USD 12 por tarea; reservas consumidas USD 9. Codex conserva arquitectura, revisión, datos, medios y verificación. El revisor independiente no sustituye la implementación de Claude.

El nuevo worktree arrancó en HEAD `24c4301c2a36fc5a023d3cd695030afc13a47f09`. Se seleccionaron y verificaron explícitamente 45 fuentes del worktree aceptado de carta40, sus paquetes locales y evidencias de medios y el runtime existente. No se copiaron credenciales, cachés de API ni cambios ajenos del checkout principal. [Snapshot de base](../evidence/claude-code/engines8-20261025/baseline.json).

El registro independiente `style-engines.ts` añade cuatro operadores sin reescribir el contrato histórico de cuatro perfiles. `StyleEngineSite.astro` combina cuatro composiciones de portada con interiores, componentes y datos compartidos. Las rutas estáticas suman 51 páginas por estilo: once páginas de negocio y cuarenta detalles. Se mantienen carta normal, búsqueda, ocho categorías, selección demostrativa, detalles y enlaces de retorno. No hay generador, framework, servicio o dependencia nuevos.

El nuevo paquete de medios admite explícitamente las rutas 05–08: 76 activos con linaje, 128 concesiones acotadas, 1.780 usos registrados y 60 rutas con medios. Se conservan hashes, vigencias, permisos por transformación, créditos, silenciamiento comprobado y handles no falsificables. Los manifiestos históricos permanecen intactos. Se reutilizan recursos autorizados disponibles; no hubo nuevas consultas o descargas de Pixabay. Los 36 platos añadidos conservan detalles sólo de texto; no se les adjudica una foto o vídeo de otro plato. Los originales cuatro mantienen sus medios ilustrativos y vídeo manual.

## Verificación final

| Comprobación | Resultado |
|---|---|
| Pruebas | 437/438; único fallo histórico H8 `LOCK_BROWSER_MISMATCH` donde el negativo esperaba `LOCK_AUDIT_FILE_MISMATCH` |
| Astro/TypeScript | 330 archivos, cero errores, advertencias o hints |
| Build | 532 páginas; 408 rutas B3 entre los ocho motores |
| Preservación | 327 páginas previas idénticas y todos sus assets conservados; sólo cambia el índice B3 para mostrar ocho opciones |
| Carta/detalles nuevos | 256 vistas en 360/390/768/1024/1440; cero fallos; hechos de los 160 detalles nuevos contrastados |
| Otros interiores | 144 vistas en 360/390/768/1440; cero fallos |
| Flujo | Teclado categoría → plato → selección → vaciado; 40 elecciones, query de plato, estado vacío, búsqueda y fallback sin JS verificados |
| Preview | 168 rutas nuevas de carta/pedidos/detalle idénticas al build; perfil y plato desconocidos devuelven 404 |
| Medios/red | Cero errores de recursos, excepciones JS o requests externos en las matrices; vídeo no se descarga automáticamente en carta |
| Rendimiento local | HTML comprimido máximo 26.168 bytes; JS referenciado máximo 10.546 bytes; incremento comprimido máximo 2.324 bytes frente a la página equivalente 01; dependencias idénticas a la base aceptada |
| Detector | Una pasada sobre los targets nuevos: `[]` |

La primera revisión encontró tres errores de tipos y desbordamientos de textos en Índice y en selección Mercado a 1024. Claude aplicó una corrección acotada de columnas y tipografía según el contenedor; se repitió la matriz con cero fallos. Los WOFF contienen los ejes de peso declarados y conservan sus licencias OFL. Las capturas son viewports nativos con compositor asentado; se reemplazaron las tomas inválidas de Edge, sin alterar el producto para ocultar defectos de captura.

Evidencia: [snapshot y manifest de artefactos](../evidence/claude-code/engines8-20261025/artifact-manifest.json), [QA de carta](../evidence/claude-code/engines8-20261025/catalogue/audit.json), [QA de interiores](../evidence/claude-code/engines8-20261025/interiors/audit.json), [preservación](../evidence/claude-code/engines8-20261025/verification/protection-final.json) y [rendimiento](../evidence/claude-code/engines8-20261025/verification/performance.json). Estas son pruebas locales, no certificación WCAG integral, rendimiento de campo o preferencia humana por los cuatro nuevos.

## Revisión y continuación

La [revisión independiente](../evidence/claude-code/engines8-20261025/verification/independent-review.md) emitió **ship**, limitado a presentar esta colección preliminar para valoración del usuario. Su revisión de evidencia y muestra de fuentes no sustituye las pruebas ejecutadas por Codex ni acredita integración o producción. No encontró arreglos materiales pendientes dentro de ese alcance. La [documentación local](../evidence/claude-code/engines8-20261025/design-documentation.md) registra los tokens y reglas de los cuatro nuevos; no modifica el sistema global ni convierte sus propuestas en decisiones aprobadas. Los recursos de producción quedan en el worktree retenido; el paquete de evidencia incluye fuentes, manifiestos y capturas de QA, no redistribuye el catálogo multimedia original.

El [roadmap](../roadmap-next-steps-20261025.md) fija la siguiente prioridad: consolidar la base revisada, conectar un snapshot autorizado al contrato existente y probar extremos de contenido/medios. Después siguen generación/revisión trazables, generalización y piloto. Otra ronda estética queda acotada a problemas observados tras ese recorrido. Los bloqueos históricos H8 y H9 permanecen visibles; no se resealan ni se presentan como completados.
