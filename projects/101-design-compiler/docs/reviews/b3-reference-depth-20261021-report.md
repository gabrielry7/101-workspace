# B3 · Iteración tras rechazo de las propuestas artísticas

Evaluación: **2026-10-21 America/Bogota**; los recibos posteriores a las 19:00 llevan fecha UTC del 22. Base limpia `913393f`, rama `codex/corrections-b1-catalog-context`. Se leyeron pipeline/V0.2, H0/H2/H3, informes B3, contratos, corpus y Git antes de editar. El baseline técnico principal terminó antes de los cambios; sus replays restantes continuaron en lectura.

**Iteración implementada para revisión, sin aprobación estética ni cierre de B3.** El rechazo de las anteriores 03/04 se conserva literalmente en [human-feedback.json](../../data/design/experience-v1.2/human-feedback.json). Las direcciones 01/02 mantienen operadores de entrada, tipografía, paleta y catálogo. Las nuevas 03/04 sustituyen las rechazadas; no heredan aceptación, nota, ganador o entrenamiento. No B4.

**Seguimiento tras revisión independiente:** la pasada inicial de `26e1960` detectó dos P2: estado humano intercambiable entre candidatos y una tarjeta filtrada que conservaba su columna estrecha. Se corrigieron ambos en `f69cb195361a99614df9fc1041935473728b9c9a` y se recapturó R3. Resultado actual: **413/414 tests**, único H8 heredado, **19/19 focales**, check269 sin diagnósticos, validate/build168/replays/medios y preservación PASS. [Receta final](../evidence/corrections/b3/reference-depth-reviewed-20261021/journal.json), [seguimiento focal](../evidence/corrections/b3/reference-depth-reviewed-extra-20261021/journal.json). La revisora reprodujo esos resultados desde Git limpio y confirmó ambos P2 corregidos: **técnicamente listo para revisión humana**, con límites. Queda pendiente tu revisión estética; B3 no se declara aprobado ni se avanza a B4.

## Referencias y carencias

Se repasaron observaciones y límites de las **21 referencias anteriores**. Se volvió a navegar **12 de ellas**, además de [Pizza 4P’s Cambodia](https://pizza4ps.com/kh/) y [Artek](https://www.artek.fi/en/). Fueron visitas parciales a entradas, scroll, navegación y páginas concretas; no una auditoría de cada URL de las 23 webs. La ficha [Stool 60](https://www.artek.fi/en/products/stool-60), su información desplegable y la [carta de Pizza 4P’s](https://pizza4ps.com/kh/menu/) se inspeccionaron aparte de la home. No se enviaron reservas, compras, consultas o suscripciones.

La [matriz de 28 hallazgos](b3-reference-depth-20261021-matrix.md) distingue **11 aplicados ahora**, **2 ya presentes**, **13 que necesitan datos**, **1 fuera del caso** y **1 con observación limitada**. Detalla qué aparece, cómo se compone, qué faltaba, operador y datos necesarios. [Datos validados y enlaces a cada evidencia](../../data/reference/design/reference-depth-20261021.json), [observaciones DOM/AX y capturas](../evidence/corrections/b3/reference-depth-20261021/observations.json). La observación del asistente no añade votos. Aponiente conserva sólo su página del menú, Khufu’s sólo storytelling y Singer sólo menú.

Faltaban recorrido posterior al hero, destinos para cada pieza editorial, jerarquía de navegación, preparación de visita y cambios de escala apoyados en ejes comunes. No se reproduce toda capacidad de todos los sitios. Equipo, premios, procedencia de ingredientes, sedes adicionales, newsletters, empleo, regalos, reseñas y publicaciones reales requieren contenido, permisos y destinos propios, enumerados en la matriz. Configuradores, descargas técnicas y garantías retail no son funciones automáticas de restaurante.

## Cambio en el motor compartido

Revisión **1.2 asociada**: [contratos](../../src/design/depth-experience-contracts.ts), [loader](../../scripts/load-b3-depth-experience.ts), [validación de referencias](../../src/design/reference-depth-validation.ts). Vincula hashes de contexto, plan, contenido, medios, investigación, feedback y contenido editorial. Rechaza fuentes desconocidas, ampliación de aprobaciones parciales y cambios de dirección en 01/02. Los datos/contratos anteriores se conservan. Sin LLM, búsqueda probabilística nueva, código por cliente o dependencia visual añadida.

| Operador / componente | Cambio y propósito |
|---|---|
| ExperienceNavigation | Accesos rápidos a carta/reservas; índice con nueve destinos agrupados, página actual y cierre Escape con retorno de foco. Menú nativo desplazable, sin intro obligatoria. OSIP, menú Singer y Artek. |
| ExperienceFeatures / route-directory | Intención editorial y cuatro caminos hacia carta, visita, reserva demo y pedido demo. Los formularios siguen en páginas propias. Separación de destinos de Pizza 4P’s, Padella y Artek. |
| journal-reading / categorías | Cada pieza permite lectura ampliada; diario con filtro y contador. Textos de ficción explícita, sin eventos, proveedores o clientes reales inventados. |
| visit-preparation / groups-preview | Preparación de visita y explicación de requisitos de grupos, con acceso a preguntas/contacto de muestra. No confirma acceso, disponibilidad o evento real. |
| GalleryStage / Longform · 03 | Entrada audiovisual oscura, serif grande a la izquierda y tagline a la derecha; apertura 8:3, pareja 5:4 descentrada y cierre 5:6. Blanco/tinta verde y cambios de superficie. Sin círculos ni paleta burdeos rechazada. |
| StudioIndex / ModularIndex · 04 | Rail estrecho, marca grande sobre blanco, vídeo ancho completo, índice 2×2 y secuencia 8:3 / 4:6 con doce columnas. Acento lima localizado. Organización editorial de Artek/NORM/Modern House. |
| Reflow / movimiento | Móvil reorganiza jerarquía y proporciones. Entrada de 12px sin ocultar contenido; movimiento reducido la desactiva. El vídeo conserva política de movimiento, datos y pausa. |

Implementación: [composición](../../src/components/composition/ExperienceComposition.astro), [navegación](../../src/components/composition/ExperienceNavigation.astro), [features](../../src/components/composition/ExperienceFeatures.astro), [comunidad](../../src/components/composition/CommunitySections.astro), [CSS](../../src/design/depth-experience.css), [cliente](../../src/design/depth-experience-client.ts). Contenido sintético adicional en [features.json](../../data/design/experience-v1.2/features.json); composición declarativa en [site.json](../../data/design/experience-v1.2/site.json). Runtime comercial 101 y upstream siguen ausentes; se usa el mismo laboratorio Astro.

## Contenido y permisos

Mismo SitePlan, **7 módulos y 42 referencias factuales**, alcance de sucursal, cuatro ofertas, contenido editorial anterior y revisión de medios. Sin función operativa nueva. Contacto `.example`, WhatsApp desactivado, redes sin perfiles y opiniones ficticias mantienen avisos y restricciones. El diario no se presenta como Instagram.

Sin adquisición, catálogos descargados, cuentas, compras o reutilización de fotos/código de referencia. Continúan **148 usos registrados** y nueve archivos servidos: mismos cliente/proyecto/páginas/finalidades/transformaciones. Revisión canónica `5f114b66dab6e87092e87e5b942135e2a17922330f845f0393d2afcaefed567a`. No se emitió autorización legal nueva por cambiar composición. Se conserva la revisión documental del **2026-10-20**, fuentes/versiones y límite temporal interno; el gate vuelve a evaluar fecha y uso al cargar.

El original con audio no se sirve. El clip silencioso sigue siendo 1280×720, 9,36s, sin upscale del archivo ni filtros. Créditos, origen, licencia, ficción y no respaldo permanecen accesibles desde cada pie. Stock no prueba local, equipo o plato real: los huecos documentales H3 siguen bloqueados. Las capturas externas son evidencia interna de investigación, no media autorizado para estas páginas.

## Verificación y evidencia

Baseline: [journal](../evidence/corrections/b3/reference-depth-baseline-20261021/journal.json): 405/406 tests, único H8 `LOCK_BROWSER_MISMATCH`; check sin diagnósticos, validación, build168, medios/replays y 2.815 archivos protegidos PASS. No se reescribe el lock para ocultarlo.

Resultado inicial en `26e1960`: [receta completa](../evidence/corrections/b3/reference-depth-post-20261021/journal.json): **411/412 tests**, mismo único fallo H8 en `tests/lock-files.test.ts`: esperaba detectar cambio de auditoría, pero la comprobación del navegador falla antes. **Check de 268 archivos: 0 errores/warnings/hints.** Exportación, validación y **build168 PASS**. B3/B2/B1, taxonomy/planner, media:replay/media:verify, composición, diseño, auditoría, cohorte e inventario H9 PASS. `lock:verify --rebuild` conserva su bloqueo histórico. **2.815 archivos protegidos sin cambios.**

Ocho pruebas nuevas (seis iniciales y dos por revisión): honestidad del rechazo, preservación de contenido/medios/direcciones, límites de referencias, 104 observaciones actuales y negativos de bindings. Intercambiar destinos, perder navegación/preparación, cambiar relatos, ampliar una aprobación parcial o reutilizar evidencia antigua falla. Pruebas anteriores intactas.

Seguimiento focal inicial: [journal extra](../evidence/corrections/b3/reference-depth-extra-20261021/journal.json), **17/17 tests** de esta revisión y la anterior, replay actual y preservación PASS.

[Recibo actual](../evidence/corrections/b3/depth-iab-r3-20261021/verification.json): **88 vistas** (4 candidatos × 11 rutas × escritorio1440×1000 / móvil390×844), más **16 vistas** de home a 360/768/1024/1920. **152 capturas originales de viewport** con hash, scroll y comprobación de presencia de píxeles. No son full-page ni un montaje presentado como captura continua. El raster IAB puede ser menor que el viewport CSS; las cajas DOM complementan la inspección.

Las observaciones pasan bindings factuales/editoriales/medios, imágenes decodificadas, navegación interna, ausencia de overflow, texto ≥14px, controles comprobados ≥43px y contraste calculado ≥4,5:1. La capa negra explícita del hero03 permite una comprobación conservadora. Inspección visual de entradas y tramos de las cuatro propuestas en escritorio/móvil, hojas de contacto, interiores y estados UI seleccionados; no certificación exhaustiva de cada píxel, zoom, dispositivo físico o lector de pantalla.

[88 registros UI y 32 capturas de interacción](../evidence/corrections/b3/depth-iab-r3-20261021/interactions.json): pausa/reanudación, menú abierto/Escape/foco, cuatro categorías, lectura ampliada con aviso ficticio, restauración de la galería y búsqueda pasta a una oferta, para cada candidato y viewport principal. Sin envíos. Esos estados también pasan overflow, lectura y controles.

Se corrigió un contraste **1:1** en WhatsApp desactivado de 03 sobre oscuro. [Observación inicial](../evidence/corrections/b3/depth-initial-contrast-20261021/observed.json); ahora el botón hereda el color de la superficie. R2 se recapturó después de ese arreglo y permanece histórico en `26e1960`. R3 se recapturó después de los dos P2 independientes. La salida provisional completa permanece temporal/ignorada, excluida del commit.

Replay archivado, sin nuevas visitas:

```powershell
& ./.tools/node-v24.21.0-win-x64/node.exe --experimental-strip-types scripts/b3-depth-verify.ts --verify
& ./.tools/node-v24.21.0-win-x64/node.exe --experimental-strip-types --test tests/b3-depth-experience.test.ts tests/b3-rich-experience.test.ts
& ./.tools/node-v24.21.0-win-x64/node.exe --experimental-strip-types scripts/b3-run.ts NUEVO_ID_UNICO
```

`--record` se usó una vez por recibo versionado (R2 y R3). Replay compara fuentes normalizadas LF, HTML construido, medios, capturas y observaciones. Los recibos de octubre16/20 siguen describiendo sus fuentes; un mismatch ante el renderer nuevo no autoriza sobrescribirlos como actuales.

## Límites y revisión

- HTML B3: **62.373–74.774 bytes**, CSS incluido. Los nueve medios suman **3.462.266 bytes**; no transferencia inicial ni medición de red. Sin nuevos LCP/CLS/INP, red fría o Edge. El CSS adicional aumenta HTML; requiere medición antes de publicar.
- Cuatro fotos heterogéneas y el mismo clip no demuestran campaña audiovisual premium ni suficiencia del paquete. Pasar gates no mide belleza.
- 01/02 comparten buena parte de continuación; 03/04 son dos ensayos del vocabulario, no prueba de diversidad para cien mil sitios.
- Reproducción requiere runtime/dependencias y paquete privado autorizado ya documentados. `.env`, herramientas, dependencias, originales y derivados ignorados se excluyen. No es una instalación autónoma sin esos requisitos.
- Falta tu evaluación nueva. Puedes rechazar ambas propuestas otra vez. Los 13 grupos de datos pendientes no se resuelven con ficción o flags `VERIFIED`.

Abrir [comparador](http://127.0.0.1:4331/b3/), [03](http://127.0.0.1:4331/b3/candidate-03/) y [04](http://127.0.0.1:4331/b3/candidate-04/). La [revisión independiente](b3-reference-depth-20261021-independent-review.md) conserva hallazgos, correcciones, prompt humano y dictamen final cuando esté disponible. Se detiene para revisión humana sin avanzar de hito.

## Correcciones solicitadas por revisión independiente

1. **Estado humano por identidad:** el contrato exporta una tupla de IDs/estados literales: 01/02 `LIKED_DIRECTION_REFINEMENT`, 03/04 `REPLACEMENT_AWAITING_HUMAN_REVIEW`. Reordenar candidatos o atribuir el estado positivo a 03/04 se rechaza. No se cambió el feedback ni el sitio declarativo.
2. **Diario filtrado:** `data-journal-layout=filtered` aplica una lectura compartida de imagen/texto, dos columnas en escritorio y una en móvil; elimina offsets/anchos heredados de `nth-child`. Las cuatro categorías de cada candidato/viewport se probaron. `auditFilteredJournal` exige tarjeta alineada y ≥95% del ancho de su grid, texto ≥35% del ancho en escritorio o ≥90% en móvil. El reset compara IDs, posición horizontal y ancho con la galería original. El negativo reproduce columna estrecha, desplazamiento a la derecha y texto estrecho.

Este arreglo sí cambia CSS, cliente, HTML y observador. **No se reutiliza R2 como prueba del render nuevo ni se declara igualdad byte a byte.** La evidencia actual es R3 completa. Los hashes de site/contenido/plan/medios y sus usos permanecen iguales; se mantienen 7 módulos/42 hechos por candidato/viewport.
