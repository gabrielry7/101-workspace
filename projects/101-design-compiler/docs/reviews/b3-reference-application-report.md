# B3 — aplicación del feedback de referencias

2026-10-16, America/Bogota. Autorización humana: «ejecuta el prompt», sobre [el prompt corregido](b3-external-proposed-prompt.md). Alcance: correcciones B3; sin B4, Design Lock, adquisición adicional ni integración comercial. **Implementado para revisión humana; no cierre estético de B3.**

## Resultado y comparación

Se aplicaron relaciones, ritmo y reflow en los componentes compartidos del laboratorio Astro. Ya no se entrega sólo investigación. Se reconstruyeron las cuatro páginas con exactamente el mismo SitePlan, 42 hechos, siete módulos, sucursal ficticia, copy y paquete autorizado. No se añadieron fuentes ni dependencias, imágenes de referencias, fotos documentales, backend o reseñas inventadas.

| Página | Antes: qa-08 | Ahora: revisión asociada V1 | Móvil |
| --- | --- | --- | --- |
| [01 · Sobremesa](http://127.0.0.1:4331/b3/candidate-01/) | Texto izquierdo / imagen derecha equilibrados; grilla regular. | Fotografía izquierda mayor y ficha editorial derecha entre reglas; historia con campos 2:3 y pausas; segunda columna de carta desplazada. | Lectura primero, fotografía después; se elimina el desplazamiento del catálogo. |
| [02 · Carta abierta](http://127.0.0.1:4331/b3/candidate-02/) | Hero de texto seguido por foto al 75%; filas con imagen siempre izquierda. | Dos campos reales lado a lado y desplazamiento vertical; filas alternan imagen y texto, conservando sus asociaciones. | Índice desplegable; foto desplazada al 88%; carta compacta adyacente, sin alternar el orden de lectura. |
| [03 · Después de las ocho](http://127.0.0.1:4331/b3/candidate-03/) | Título centrado y gran foto al 80%; mosaico de columnas iguales. | Título horizontal amplio, línea y acciones en campos diferentes; foto contenida de 720 px máximo y mosaico 3:2 escalonado; encabezado de carta desplazado. | Rótulo antes del título, acciones agrupadas y secuencia fotográfica sin escalonamiento. |
| [04 · Cuaderno de mesa](http://127.0.0.1:4331/b3/candidate-04/) | Texto arriba del marco; filas parecidas a 02. | Marco fotográfico antes de ficha editorial en desktop; carta con tres campos imagen / índice / lectura. | Título, marco, descripción y acciones; se simplifican las tres columnas a lectura vertical. |

Las decisiones se registran en [compositions.json](../../data/design/reference-application-v1/compositions.json), contrato [ReferenceCompositionV1](../../src/design/contextual-contracts.ts), validador [reference-application.ts](../../src/design/reference-application.ts) y operadores [contextual.css](../../src/design/contextual.css). No hay selectores CSS por candidato, cliente o sector. Se conserva el contexto productor V2 y sus cuatro propuestas históricas: esta entrega es una revisión declarativa asociada, no cuatro nuevas llamadas creativas ni 24 nuevas muestras probabilísticas.

SHA canónico de aplicación: `0637e6d732c4e1a744ccd77f9b426510d5e156411c3da79c3673f3a8abf868dc`. El loader exige los hashes del contexto histórico, investigación visual, contenido y revisión de medios. Una modificación de autoridad, paleta incompatible con la dirección, referencia desconocida o falta de diversidad declarativa se rechaza. Esto no calcula belleza ni inventa el gusto del usuario.

## Matriz de aplicación

Las observaciones originales conservan su autoridad de asistente y límites. «Aplicado» significa mecanismo concreto en esta revisión, no aprobación humana de la referencia entera ni equivalencia de calidad con ella.

| Hallazgo y referencias | Regla compartida / cambio | Condiciones y evidencia |
| --- | --- | --- |
| Relaciones entre imagen y texto: Etxebarri, Central, LUCA, Modern House | EditorialCard / OffsetPair / TypeGallery / FramedCover, separados en contrato y CSS. | Una imagen hero permitida, relación natural, texto fuera de foto. Cuatro pares de capturas y geometría. Díptico de **dos medios distintos** no demostrado: no hay segunda necesidad hero autorizada. |
| Capítulos y densidad: OSIP, Aponiente, Khufu | Editorial / Direct / Exhibit / Notebook: narrativa 2:3, filas alternas, mosaico 3:2 y carta de tres campos. | Sin quitar módulos o accesos. No intro obligatoria. Recorrido horizontal y montaje narrativo completo diferidos: fotografías y relato disponibles no los sostienen; no se implementó un efecto vacío para aparentarlo. |
| Tipografía + paleta + medio: Dinesen, Modern House, KOL | La revisión selecciona juntas voz, paleta y relación; valida compatibilidad con la dirección existente. Marco, aire y reglas sustituyen texto sobre foto. | Se mantienen Georgia/Arial/Segoe UI del entorno; ninguna fuente del sitio externo. Contraste mínimo observado 6,93:1. Coherencia es una hipótesis revisable, no un score calibrado. |
| Móvil propio: Central, ÄNG, Noma | ReadingFirst / CompactIndex / ImageSequence / CoverFirst, con reglas explícitas. | 390 px y controles a 360/768/1024/1920. Sin crop, conservación de hechos y acciones; no hace falta autoplay móvil. |
| Papel del vídeo: Aira, Noma, Heckfield, Polène | Se conserva foto estática hero, vídeo a petición, poster y descripción independiente; se impide ampliarlo a portada. | Reproducción UI real en 8/8, dimensiones nativas 640×360 y duración 9,36 s; tamaño de caja estable. No se afirma calidad de película full-screen ni nueva medición de red. |
| Capas seguras: Heckfield, Singer | Foto, texto y controles mantienen campos separados; marco y superficies como decoración no invasiva. Menú móvil nativo con Escape y foco. | No se añadió superposición fotográfica o menú translúcido: no hay una necesidad que justifique poner texto sobre el stock. No se declara implementado un solver de capas ni contrastes por fotograma. |
| Oscuro y asimetría: LUNE, Padella | TypeGallery + Exhibit: identidad oscura, dos escalas y desplazamiento del catálogo, sin tintar fotos. | Contraste y ausencia de overflow en seis anchos por candidato. No se generaliza negro más foto a todos los negocios. |
| Sede / catálogo / historia / campaña: Kadeau, FRAMA, Padella | Preservación de módulos, scopes y acciones DEMO_ONLY; carta y relato usan operadores distintos. | Una sede ficticia; no se inventa selector multisede o tienda real. Una campaña comercial requeriría contenido y permiso específico. |
| Aprobaciones parciales y negativos | Contexto original y corpus permanecen intactos; investigación se consume como revisión asociada con hash. | Aponiente sólo menú, Khufu sólo storytelling, Singer sólo menú; Polène énfasis audiovisual. No se usan capturas como media, votos nuevos o autorización de entrenamiento. |

Cobertura de las 21 referencias, sin ampliar su alcance:

| Ref. | Disposición concreta |
| --- | --- |
| 01 OSIP | Ritmo Editorial; horizontal diferido por material/relato insuficiente. No se inventa por qué fue favorita. |
| 02 Central | OffsetPair y reflow móvil; dos vídeos hero distintos pendientes de medios y usos adecuados. |
| 03 Etxebarri | FramedCover y separación imagen/información; sin foto de edificio ficticio. |
| 04 KOL | Coherencia cálida foto/ficha en 01; sin copiar tipografía o botones. |
| 05 Aira | Política conservadora del clip y reproducción comprobada; su montaje no se dio por inspeccionado. |
| 06 LUCA | Desplazamiento en 02 y marco 04; sin logo externo ni superposición ilegible. |
| 07 Padella | Recorrido directo y oscuro; no reduce los requisitos B1 de fotos/detalles de cada plato. |
| 08 Noma | Hero estático y vídeo a petición; sin atribuir reproducción móvil al sitio de referencia. |
| 09 ÄNG | Reflow de navegación; no inventa interiores ni integra reserva externa. |
| 10 Kadeau | Scope de sede se conserva; selector multisede no aplicable a la única sede ficticia. |
| 11 MIL | Proporción/atmósfera consideradas; relación territorial documental bloqueada por inexistencia de fotos auténticas. |
| 12 Aponiente | Ritmo de carta Exhibit/Notebook; sólo alcance de página exacta. |
| 13 Khufu | Capítulos sin intro bloqueante; storytelling completo no demostrado por la investigación ni por este paquete. |
| 14 Heckfield | Marco, campos seguros y clip limitado; no se revoca ni confirma su crítica histórica de vídeo desktop. |
| 15 FRAMA | Separación catálogo/relato, sin construir campaña, configurador ni comercio. |
| 16 Dinesen | Ficha y color cálido coordinados con madera; no se afirma reproducción del vídeo externo pausado. |
| 17 LUNE | Oscuro y asimetría controlada en 03; sin copiar producto, assets o CTA comercial. |
| 18 NORM | Aire/organización 04 y tamaño mínimo legible. |
| 19 Modern House | EditorialCard en 01 y ficha diferenciada del catálogo; no copia tipografía licenciada. |
| 20 Polène | Poster, límite de resolución y observación de frames; no se utiliza la captura tapada para calificar su sitio completo. |
| 21 Singer | Sólo navegación: cierre Escape y retorno de foco en menú móvil; no adopta el resto del sitio. |

## Corrección oferta → medio

La convención explícita del laboratorio B3 es `offering.id → b3-need:<offering.id>`. `validateContextualPresentation` rechaza pizza→pasta, hero u otro slot, y se llama también en el componente antes de renderizar. La revisión H3/B2 independiente ya fija cada necesidad a activos concretos y sus bytes; no se deriva permiso de esa convención.

El DOM ahora conserva oferta, slot, URI seleccionada y usos, y la auditoría compara **cada asociación**, además del conjunto global anterior. El verificador de revisión actual exige el hash de aplicación; una observación antigua sin esos campos sólo puede acreditar la auditoría histórica, nunca la revisión actual. Pruebas negativas intercambian URIs y usos válidos entre ofertas sin cambiar el conjunto global. No se pretende resolver reconocimiento semántico universal: para otros datos haría falta una asociación de sujetos revisada con igual trazabilidad.

## Evidencia, comprobaciones y límites

Baseline: [reference-application-baseline-01](../evidence/corrections/b3/reference-application-baseline-01/journal.json). Resultado: 382/383, único `LOCK_BROWSER_MISMATCH` histórico H8; check, validate, build, replays, media:verify y preservación de 2.815 archivos PASS. El baseline técnico principal terminó antes de editar; sus replays adicionales continuaron en lectura durante las primeras correcciones.

Primera receta posterior: [reference-application-post-01](../evidence/corrections/b3/reference-application-post-01/journal.json): **385/386**, incluido el nuevo negativo y 13/13 tests B3; único fallo histórico H8. Check/validación/build/replays PASS. La [receta final](../evidence/corrections/b3/reference-application-final-01/journal.json) repite los controles después de los últimos ajustes de auditoría y comparador; los resultados exactos están en su journal.

Resultado antes de la corrección del comparador: **385/386**, sólo H8 `LOCK_BROWSER_MISMATCH`; check 0 errores/warnings/hints, exportación, validate, build de 128 páginas, medios, bindings, replays y 2.815 archivos protegidos PASS. El [seguimiento final](../evidence/corrections/b3/reference-application-replay-02/journal.json) verifica el auditor de evidencia con sus últimos controles de fuente: check PASS, 13/13 B3 PASS, replay de aplicación/referencias/evidencia actual PASS. [Comparación geométrica antes/después](../evidence/corrections/b3/reference-application-iab-02/before-after.json): ocho pares con el mismo contexto factual; navegadores diferentes, no regresión píxel a píxel ni puntuación de belleza. Los hashes de fuentes del renderer y el observador derivado también se verifican, para que un cambio posterior de CSS no reutilice este recibo sin detectarse.

El harness Edge controlado no arrancó en [qa-01](../evidence/corrections/b3/reference-application-qa-01/) ni [qa-02](../evidence/corrections/b3/reference-application-qa-02/): `Browser startup timeout`, después de build PASS. No se cambió su sandbox, sus flags o sus protecciones para eludirlo. No es una prueba fallida de geometría: no llegó a observar páginas. Se conserva la transcripción identificada del error; no se inventa un log de stderr.

Se completó el recorrido con el **navegador integrado IAB**, controles UI y observación DOM de sólo lectura. El primer registro [iab-01](../evidence/corrections/b3/reference-application-iab-01/) conserva la limitación del getter `video.preload` ausente y screenshots de reproducción tomados durante desplazamiento; no se usa como PASS final ni como prueba de frames visibles. Se corrigió el observador para leer el atributo DOM real `preload="none"`; no se rellenó retrospectivamente el dato faltante. La evidencia nueva está en [iab-02](../evidence/corrections/b3/reference-application-iab-02/verification.json).

- Ocho capturas completas: cuatro candidatos × escritorio 1440×1000 / móvil 390×844 CSS px; 16 casos adicionales 360/768/1024/1920. Los píxeles de captura excluyen scrollbar: 1424 px desktop y 375 px móvil, alturas completas dentro de 1 px del DOM. No dispositivo físico ni igualdad raster con Edge154 histórico.
- 24/24 auditorías DOM actuales: siete módulos, 42 hechos, scope de sede, diagnósticos, restricciones, exclusiones, 12 usos por página, crédito y contexto íntegros; cinco imágenes decodificadas por vista, sin crop/filtro y proporción natural. Sin overflow detectado.
- Ocho recorridos UI: Tab al skip, Enter al contenido, búsqueda pasta, filtro ensalada, detalles expandidos, selección y resumen ficticios. Menú Rail móvil: Escape cierra y devuelve foco. Detalles abiertos sin desbordamientos ni pérdida de lectura. No se simulan pedidos/reservas enviados.
- Ocho reproducciones mediante teclado; frame visible y avance de currentTime; 640×360, 9,36 s, sin error. Caja 640 px máximo y relación 16:9 constante antes/después. La posición vertical cambia por scroll: no se presenta como medición de CLS.
- Tamaño mínimo observado 14 px; contraste calculado mínimo 6,93:1 sobre superficies opacas. Sin texto sobre foto/vídeo. No auditoría WCAG completa, lector de pantalla ni zoom.
- HTML individual 57.308–57.322 bytes, CSS/JS compartidos embebidos según build; aumento aproximado de 8,4 KB frente a qa-08. Tamaños de archivos seleccionados por `currentSrc` y hashes del paquete en verification.json; son bytes locales, **no transferencia de red medida**. WebM idéntico de 4.446.094 bytes. No se miden nuevos LCP/CLS/INP ni red lenta; los resultados antiguos no se atribuyen al CSS nuevo. En IAB se observaron 429.114 bytes únicos de imágenes seleccionadas en desktop y 515.180 en móvil; hubo cambios de viewport y posible reutilización de caché/renditions, por lo que esto no mide una navegación fría ni certifica DPR1.

Se inspeccionaron las ocho capturas completas mediante imagen, además del recorrido de navegador. La carta compacta 02 sigue siendo la más densa y la tercera página la más larga; son límites para la decisión humana. El material heterogéneo de stock y el clip de 640 px no equivalen a una campaña audiovisual premium. No se adquirió material para esconder ese límite.

Reproducción de datos y evidencia archivada, sin nuevas visitas ni creatividad:

```powershell
& ./.tools/node-v24.21.0-win-x64/node.exe --experimental-strip-types scripts/b3-reference-application.ts --verify
& ./.tools/node-v24.21.0-win-x64/node.exe --experimental-strip-types scripts/b3-reference-verify.ts
& ./.tools/node-v24.21.0-win-x64/node.exe --experimental-strip-types scripts/b3-reference-current-verify.ts --verify
& ./.tools/node-v24.21.0-win-x64/node.exe --experimental-strip-types scripts/b3-proposals.ts --verify
& ./.tools/node-v24.21.0-win-x64/node.exe --experimental-strip-types scripts/b3-preservation.ts --verify
```

El paquete privado de medios y herramientas instaladas siguen siendo necesarios para build y verificación, como B2/B3 anterior. No se incluyeron `.env`, medios privados, node_modules, caches o herramientas ignoradas. Reproducibilidad de build/contratos y evidencia archivada no equivale a una instalación nueva sin esos requisitos ni a recaptura automática aprobada: Edge controlado sigue bloqueado. Las fuentes y fechas de investigación externa permanecen en el informe del 2026-10-15, sin nuevas afirmaciones legales.

## Estado para revisión

Durante la revisión independiente se detectó un error real en el recibo auxiliar antes/después: `JSON.stringify` comparaba orden de claves y marcaba `shared_context:false` pese a coincidir los cuatro hashes. Se conserva el recibo erróneo como `before-after-order-sensitive-original.json`; [el comparador reproducible](../../scripts/b3-reference-comparison.ts) usa validación estricta de cuatro hashes e igualdad canónica. El test nuevo rechaza cambios reales de cualquiera de ellos y campos ausentes, y acepta distinto orden. Resultado posterior: [receta revisada](../evidence/corrections/b3/reference-application-reviewed-01/journal.json), **386/387 tests**, sólo fallo histórico H8; export/check/validate/build128/replays/medios/preservación PASS. [Replay canónico](../evidence/corrections/b3/reference-application-canonical-01/journal.json): comparación 8/8, evidencia actual y **14/14 tests B3 PASS**. El recibo corregido informa ocho contextos iguales; no se cambió un hash factual para conseguirlo.

También se retiró del comparador el feeling histórico que decía «título centrado» para 03: ya no describía su composición actual. Se sustituyó por un rótulo neutro; la descripción aplicada y la estructura siguen visibles. El [recibo de delta](../evidence/corrections/b3/reference-application-caption-01/receipt-delta.json) confirma que, al actualizar la prueba de fuentes por esa edición, sólo cambió el hash de `src/pages/b3/index.astro`: HTML candidato, geometría, fotos y capturas permanecen iguales. Check/build/replay del [seguimiento de copy](../evidence/corrections/b3/reference-application-caption-01/journal.json) PASS. No se atribuye a dist un mismatch observado por la revisora durante esa edición concurrente. La reconstrucción y el replay posterior pasan; se conserva su explicación temporal sin ocultar el incidente.

Verificación adicional del contexto:

```powershell
& ./.tools/node-v24.21.0-win-x64/node.exe --experimental-strip-types scripts/b3-reference-comparison.ts --verify
```

Implementación compartida y refuerzo oferta→medio entregados. La [revisión independiente](b3-reference-application-independent-review.md) de a80b7ec y 1da1fff respondió **APTO PARA REVISIÓN VISUAL HUMANA**, tras comprobar 14/14 B3, build/check, replay, comparación canónica y ocho capturas. Se conserva su [prompt propuesto](b3-reference-application-human-review-prompt.md); no se ejecuta B4. **B3 sigue pendiente de elección o rechazo estético explícito del usuario.** El comparador no preselecciona ganador; permite responder una, varias o ninguna, nota 1–10 y comentarios sobre tipografía, paleta, distribución, audiovisual, contenido y móvil. No se guardan votos inexistentes ni se entrena con el corpus. Si ninguna gusta, se registran motivos y se itera el motor dentro de B3. No B4.
