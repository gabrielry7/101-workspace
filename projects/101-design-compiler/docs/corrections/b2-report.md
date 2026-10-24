# B2 — medios autorizados y corpus

Fecha: 2026-10-14, America/Bogota. Base: `3d4dd86c11caa29f6ffda72d9652fe17e023d0ff`. Alcance autorizado: [prompt B2](../reviews/b2-proposed-prompt.md), después de B1. **B2 técnicamente verificado, reproducido y revisado independientemente, con bloqueo histórico de navegador y huecos explícitos; evaluación humana pendiente.** No se declara aprobación estética, suficiencia audiovisual de un restaurante ni cierre H9. No se inició B3.

## Qué se puede revisar

- `/b2/`: resultado y faltantes.
- `/b2/pilot/`: archivo real, derivados, crédito/contexto, necesidades y vínculos.
- `/b2/providers/`: condiciones oficiales separadas por operación.
- `/b2/corpus/`: las 21 referencias con notas originales y alcance global/parcial.

Son inspectores del laboratorio Astro compartido. No son una página final de restaurante, integración con runtime comercial o `101-world-model`, catálogo autónomo ni nuevas composiciones H4/H5. Se preservan las demandas de demo completa y buen audiovisual para el bloque de gramática/demos; esta prueba verifica el recorrido de medios sin simular una aprobación de producto.

## Trazabilidad

| Requisito | Implementación y evidencia | Estado |
| --- | --- | --- |
| B2-1 / H3-C03: necesidades desde B1 por función, módulo, scope, sujeto y rol | `function-needs.ts`, `MediaRequirementRequestV1`, `MediaFunctionBindingV1`, [biblioteca](../../data/media/library-v1/usda-pilot.json), overlay asociado `media-diagnostic.ts` | Implementado: 32 necesidades; una atmosférica autorizada, 23 pendientes de material auténtico, ocho de recurso permitido. Aspiraciones no se anuncian como módulos emitidos. |
| B2-2 / H3-C04/C05: biblioteca y permiso concreto | `library.ts`, original/derivados, [revisión legal](../evidence/corrections/b2/legal-review.md), [inspección real](../evidence/corrections/b2/visual-review.md), documentos/hash | Un original real, dos derivados y tres usos de una misma necesidad. Hueco documental intacto. |
| B2-3 / H3-C01/C06: acceso y términos | [evaluación oficial de siete fuentes](b2-providers.md), `providers.ts`, [recibo Pixabay](../evidence/corrections/b2/pixabay/receipt.json) | USDA puntual obtenido; Pixabay autenticación/búsqueda probadas. Otros conectores, activos de Pixabay y automatización multicliente pendientes. |
| B2-4 / H3-C02/C07: recorrido autorizado | Selección oficial → [adquisición](../evidence/corrections/b2/acquisition/receipt.json) → hash/inspección → grant B2 → gate → figura responsive; `b2-derive.ts`, `b2-verify.ts`, `b2-qa.ts` | Recorrido acotado demostrado con bytes reales. No suficiencia del paquete completo. |
| B2-5 / corpus H4 | `reference-corpus.ts`, [corpus versionado](../../data/reference/design/corpus-v1.json), documento fuente original sin cambios | 21 positivas, 18 globales y tres parciales; negativos y notas literales. Inspección web nueva pendiente, sin nuevos votos ni permisos de reutilización. |
| B2-6: rechazo y reproducción | 11 pruebas B2, seis nuevos JSON Schema, journals, QA desktop/móvil y reproducción aislada | Verificación final y recibos abajo. |

## Archivo real, autorización y restricciones

Se readquirió exactamente **USDA/ARS D255-19**, pimientos fotografiados por Steve Ausmus, de su [ficha oficial](https://www.ars.usda.gov/oc/images/photos/featuredphoto/mar23/bell-peppers/) y [política](https://www.ars.usda.gov/oc/images/copyright/). La ficha declara dominio público y enlaza el original; los bytes de ambas páginas, versiones no numeradas, fechas, tamaños y SHA están en el recibo. El GET del original ocurrió `2026-10-15T01:02:58.987Z–01:03:00.264Z`; se deduplicó porque coincide con el JPEG H3. No se reescribió H3 ni su permiso.

| Archivo local | Bytes / dimensiones medidas | SHA256 |
| --- | --- | --- |
| `public/media/h3-pilot/usda-ars-d255-19.jpg` | 2.351.102 / 2700×1819 JPEG | `ffdb883d56a41ba9a03a51fb7d1bdf8f0b9e30d3946eda180b750620a17c3715` |
| `public/media/b2/d255-19-480.webp` | 32.510 / 480×323 | `591dd2b3a366d8cb2a9c571f5cd7d3734430e7ca5c88db0a598ab0c0dd1218f8` |
| `public/media/b2/d255-19-960.webp` | 108.258 / 960×647 | `bead733d81673ac54b11d4e1179defce5a2992c94081bc25b7dc788ac49d0f72` |

Nuevo grant B2, más acotado que la declaración pública: cliente `101-design-compiler-fixture-review`, proyecto `b2-media-library-pilot`, negocio/scope `fixture-restaurante-001`, finalidad `generic:atmosphere`, página semántica `/`, territorio CO. Presentación física `/b2/pilot/`. Permite este original y resize proporcional/transcode WebP, alojamiento local e inspección visual local; no crop, color, edición generativa, clasificación, embedding o entrenamiento autorizados. Multicliente/otro proyecto no cubiertos por este grant. La revisión interna tiene 30 días desde `manifest.evaluated_at`; no se afirma que expire el dominio público.

Crédito: **Photo by Steve Ausmus, USDA Agricultural Research Service.** Etiqueta: **Imagen atmosférica de pimientos; no documenta este negocio ficticio ni sus platos.** Aviso: **USDA ARS no respalda este fixture, producto, empresa ni posición.** Se verifican antes de renderizar y en el DOM. La imagen no acredita plato, ingrediente, proveedor, cultivo o sucursal. El hueco `offering-1` conserva su rol documental bloqueado.

Se abrió el original y ambos derivados mediante `view_image`; `sharp` decodificó todos los píxeles y midió metadatos. No se observaron personas, marcas, carteles o inmuebles identificables; no se identificó necesidad de releases para este uso limitado. Esto no garantiza ausencia universal de derechos de terceros. Imagen reconocible a tamaño de figura, fondo ocupado y sin texto superpuesto; no se aprueba hero, alta densidad o recorte. La inspección técnica y la visual son recibos distintos: `technical-inspection.json` conserva `visual_review=PENDING_SEPARATE_REVIEW` porque no reemplaza [visual-review.md](../evidence/corrections/b2/visual-review.md), enlazado y fijado por SHA en la biblioteca.

Derivación con herramientas ya instaladas: sharp 0.35.5 / libvips 8.18.7 / WebP 1.6.0, anchuras 480/960, calidad 82, effort 6, proporcional sin crop ni ampliación. Replay regenera en memoria y compara bytes; no modifica originales/derivados ni descarga de nuevo. Un único evento de transferencia enlaza el original; los usos derivados heredan ese evento y añaden derivación/inspección, sin afirmar tres descargas.

## Contratos y barrera de confianza

Se exportan seis contratos asociados bajo `contracts/media/library-v1`: necesidad, binding, evento de procesamiento, biblioteca, diagnóstico asociado y corpus. BusinessInput/SitePlan/MediaAsset/LicenseGrant/MediaUsage/MediaManifest/MediaBrief V1 y los locks permanecen compatibles y sin edición. El nuevo modelo compone los contratos H3; no duplica semántica de permisos.

El lector fija el sello revisado `56149318785d0990032e2b902aab01ad15879d1924f4e423c2e2c382eb6a1e45`, recalcula documentos, archivos, metadatos y manifiesto, comprueba ficha/política, recibo del URL/SHA exactos y catálogo/bindings. Sólo emite un handle opaco en memoria. Un fixture puede escribir VERIFIED o recalcular su checksum, pero no obtiene ese handle. Es un ancla revisada para **este paquete**, no un clasificador jurídico universal ni un sistema completo de admisión de proveedores. Admitir otro paquete requiere evidencia y revisión explícita, no editar un flag.

El gate H3 evalúa cada uso por cliente, proyecto, finalidad, página, sucursal, territorio, fecha, terceros, crédito, operaciones y linaje. B2 además rechaza cambios de cualquier campo del uso registrado y transformaciones todavía no inspeccionadas. El consumidor usa reloj actual antes de prerenderizar; no puede volver a construir el piloto con el permiso interno vencido. **Los HTML estáticos ya emitidos no reevalúan permisos en cada petición HTTP:** antes de publicar/reutilizar hay que ejecutar la evaluación actual, y retirar/reevaluar el paquete al vencer su ventana interna. No hay monitor de revocación ni backend de permisos en este laboratorio. `b2-verify.ts --historical-replay` sólo reproduce bytes/decisiones a la fecha registrada y declara **HISTORICAL_REPLAY_NOT_CURRENT_AUTHORIZATION**; no sirve páginas ni renueva derechos.

El overlay B1 no muta el diagnóstico original. Exige todos los usos relevantes permitidos y todos los sujetos conocidos/cubiertos para activar `if_used`; una foto válida no compensa otra bloqueada ni cubre dos platos. El material atmosférico de identidad no satisface el rol documental que pide el catálogo: **cero requisitos documentales SATISFIED**, aunque exista un uso atmosférico permitido. No se cambian backend, readiness u operaciones.

El `MediaBriefV1` embebido no lleva un `H3PackageProof` histórico nuevo y conserva su cierre pendiente por paquete H3; esa salida no se presenta como certificado B2. La prueba asociada B2 es el sello de biblioteca + fuentes/archivos + QA real. El cierre histórico H3 `e2b83d4` y sus evidencias siguen intactos.

## Corpus y proveedores

El documento de referencias original permanece byte idéntico. Se conservan intensidad, sector y sección literal: Aponiente sólo su página de menú, Khufu sólo storytelling, Singer sólo dropdown. No se inventan motivos para OSIP/Central. Se conserva la observación negativa del vídeo desktop de Heckfield y la sección de referencias negativas. `new_observations=[]`, `inspected_at=null`, sin capturas ni entrenamiento; preferencias originales no equivalen a nuevas inspecciones o votos sobre nuestro motor. La navegación del panel no carga esas webs o sus recursos.

Las condiciones oficiales, fechas/versiones visibles, restricciones y UNKNOWN están en [b2-providers.md](b2-providers.md). USDA fue la única adquisición; Pixabay recibió una consulta humana, HTTP 200/3 hits/0 descargas, con caché privada temporal excluida de Git. No hay claves en evidencias, cuenta nueva, gasto, scraping o descarga de catálogos. La prueba de acceso no autoriza los medios de los resultados ni una automatización masiva. Video/audio siguen sin obtener ni inspeccionar. Tiempo humano, tokens, tarifas y costo total desconocidos; duración de máquina medida en journals, sin costo total cero ficticio.

## Pruebas, visualización y reproducción

Baseline: [b1/b2-pre/journal.json](../evidence/corrections/b1/b2-pre/journal.json), antes de B2: 354/355 pruebas; único fallo histórico `LOCK_BROWSER_MISMATCH`; check/validate/build/export/replays PASS, build 118 páginas. El baseline se guardó en carpeta B1 por reutilizar su runner; no representa cambios nuevos de B1.

La primera corrida B2 [post-01](../evidence/corrections/b2/post-01/journal.json) pasó check/validate/build y replays, 365/366 pruebas y build 122 páginas. [post-02](../evidence/corrections/b2/post-02/journal.json) detectó un nuevo error TypeScript en el script QA por `context_notices` opcional; se corrigió usando acceso opcional. No se disfraza esa corrida como PASS.

Las once pruebas nuevas cubren bytes/linaje, fixture VERIFIED forjado, mutación de uso/etiqueta/contexto, cliente/proyecto/finalidad/página/sucursal/territorio, permisos desconocidos/vencidos, crédito/avisos perdidos, IA/automatización no permitidas, transformación no autorizada o no inspeccionada, bindings falsos, cobertura parcial de dos sujetos, overlay que no convierte atmósfera en evidencia, build futuro vencido, archivo corrupto y corpus parcial/literal. Las demás pruebas H3 conservan sus coberturas anteriores.

[qa-04/qa.json](../evidence/corrections/b2/qa-04/qa.json): cuatro rutas × 1280×900 y 390×844, DPR 1. Ocho vistas PASS, ningún overflow, un main/h1, lang=es, skip link, navegación y detalles por teclado; mínimo tipográfico observado 13 px en códigos y 16 px en texto del panel. Se expanden todos los detalles para comprobar geometría y cobertura, luego se captura viewport inicial. Las ocho capturas finales se inspeccionaron con `view_image`, además de las ocho de qa-03. No es auditoría WCAG completa, medición de campo o aprobación humana de diseño.

El navegador confirmó WebP decodificado y `currentSrc` correcto: 960 en escritorio, 480 en móvil. CDP obtuvo los cuerpos servidos y sus SHA coinciden con la biblioteca; no se cargó el JPEG de 2,35 MB ni hubo solicitudes externas. HTML: resumen 3.736 B, piloto 29.150 B, corpus 26.794 B, proveedores 25.475 B; CSS inline, sin JS del cliente ni formularios. Piloto aprox. 137.408 B desktop / 61.660 B móvil para HTML+imagen, sin cabeceras/favicon. Duraciones de carga localhost constan en QA, sin simular 4G ni extrapolar Core Web Vitals. Fallback JPEG sigue disponible para navegadores sin WebP, con ese peso mayor. El harness histórico sirve WebP como octet-stream: el navegador probado lo decodifica y se validan bytes; no se presenta como configuración de hosting de producción.

Preservación: 2.407 archivos previamente tracked protegidos sin cambios, excluyendo explícitamente el exportador ampliado. Dieciséis HTML históricos H8 coinciden por bytes en el build B2. **No se revalida el pixel lock histórico:** `qa-01` detectó doce hashes Segoe UI cambiados, mismo OS; [drift](../evidence/corrections/b2/qa-01/runtime-drift.json). Se creó un [snapshot B2 separado](../evidence/corrections/b2/runtime.json), reutilizando verificador/runtime compartidos, sin tocar B0/H8 ni fuentes del sistema. La nueva baseline visual es sólo B2. `qa-02` falló al leer un cuerpo CDP después de cinco vistas; se conservan fallo/capturas. Buffer CDP durable corrige el lector; qa-03 y qa-04 pasan las ocho vistas.

La reproducción final materializó el árbol Git preparado **`e89d0689cad30aa36322d0bdf66670b9441a11e2`** en `.tools/corrections/b0/b2-clean/source`, sin `.env`, con fuentes/build/perfil separados y junctions al Node/dependencias/browser verificados. [Materialización](../evidence/corrections/b2/reproduction/materialization.json): SHA del archivo fuente registrado, **cero overlays necesarios**. La receta sólo permite overlays históricos de fin de línea byte-pinned y package manifests, comprobando equivalencia LF; no sobreescribe código del producto. No hay fresh install, descarga o reseal creativo. Los recibos finales y esta actualización del informe se incorporan después de materializar el árbol del motor.

| Verificación final | Resultado y evidencia |
| --- | --- |
| Exportación / check / validate / build | PASS; check cero errores/warnings/hints; seis esquemas nuevos y anteriores preservados; 122 páginas. [post-03/journal](../evidence/corrections/b2/post-03/journal.json). |
| Tests | **365/366**, once B2 PASS; único fallo `LOCK_BROWSER_MISMATCH` en `lock-files.test.ts`, ya presente antes de B2. No se declara suite totalmente verde. |
| Replay B2 | PASS actual y replay histórico separado; dos derivados idénticos regenerados en memoria; 32 necesidades/21 referencias. El actual bloquea permisos vencidos. |
| B1/H2/H3 y verificadores posteriores pertinentes | PASS, sin nuevos recorders creativos; nueve fixtures H2 históricos y permiso H3 conservados. |
| H8 `lock:verify -- --rebuild` | **BLOCKED_HISTORICAL_ENVIRONMENT**, navegador global distinto. No se reseal ni reemplaza evidencia H8. |
| H9 inventario | PASS de inventario; benchmark sigue BLOCKED/NOT_TESTED, cero sitios reales aprobados elegibles. |
| Copia aislada: tests/check/validate/build/replays | Mismos resultados, 365/366 y sólo bloqueo histórico conocido. [clean-01/journal](../evidence/corrections/b2/clean-01/journal.json). |
| QA aislada | Ocho vistas PASS, 16 HTML históricos H8 idénticos y 2.407 archivos protegidos. [clean-qa-01/qa](../evidence/corrections/b2/clean-qa-01/qa.json). |
| Comparación raíz / copia aislada | **8/8 pares idénticos** en HTML, píxeles RGBA y observables estables del DOM/medios, incluyendo SHA de los WebP servidos. [comparison.json](../evidence/corrections/b2/reproduction/comparison.json). Se excluyen tiempos de red y contabilidad de recursos, no geometría/contenido/permisos. |

La nueva baseline B2 usa snapshot runtime `8818373779050bdb597c4e9313a31615c46892046a4572e2113366de11b9040b`. La reproducción es sobre el mismo Windows, fuentes B2 y herramientas existentes; no prueba portabilidad ni identidad de píxeles con B0/H8. El índice Git revisado no contiene `.env`, `.tools`, `node_modules`, builds/perfiles ni caché cruda de Pixabay; se comprobó ausencia del valor privado de la clave sin imprimirlo. [delivery.json](../evidence/corrections/b2/reproduction/delivery.json) conserva la comprobación completa de los 224 archivos del commit previo al recibo: cero coincidencias de la clave y cero rutas privadas. El primer lector del índice excedió el buffer Node por el JSON de runtime; se repitió completo con 32 MiB y se registró la incidencia, sin modificar el producto.

```powershell
$node = '.tools/node-v24.21.0-win-x64/node.exe'
& $node --experimental-strip-types scripts/b2-run.ts <nuevo-id>
& $node --experimental-strip-types scripts/b2-verify.ts --historical-replay
& $node --experimental-strip-types scripts/b2-qa.ts <nuevo-id>
```

`b2-run` ejecuta exportación, tests, check, validación, build y replays/verificadores B1/H2/H3/H4/H5/H6/H7/H8 pertinentes e inventario H9. El gate actual puede bloquear legítimamente después de 30 días; el replay histórico se usa sólo para reproducción. `b2-acquire-usda.ts`, `b2-derive.ts` y `b2-build-library.ts` son writers explícitos que rechazan repetir sus recibos y **no** forman parte del replay. No ejecutarlos para regenerar evidencia histórica.

## Bloqueos y siguiente paso

Falta material documental auténtico de `offering-1`, sucursales/personas y demás sujetos aplicables, con origen, hash, vínculo factual, titular/autorización, cliente/proyecto/usos/transformaciones/alojamiento/fechas, releases cuando procedan y evaluación real de calidad. Las 32 necesidades incluyen objetivos aspiracionales y funciones cuya aplicabilidad aún requiere confirmación; no se afirma que todas sean módulos obligatorios del restaurante actual. No se reemplazan con stock.

Para ampliar Pixabay falta seleccionar/revisar un archivo y su uso, terceros y procesamiento permitido. Para video/audio falta adquisición autorizada e inspección de contenido, pistas y condiciones; B2 no los declara probados por compartir contrato. Para buena estética, demos completas y análisis actual de referencias se requiere el bloque siguiente, sujeto a aprobación del usuario. Las fuentes comerciales y upstream siguen ausentes.

La tarea revisora autorizada emitió PASS técnico tras leer código/informes, ejecutar independientemente 11/11 tests B2 y replay histórico, y revisar las corridas/comparación. [Feedback y límites](../reviews/b2-independent-review.md). Se detiene aquí para revisión humana; el [prompt B3 propuesto](../reviews/b3-proposed-prompt.md) queda preparado **sin ejecutar**. Commit técnico reproducible no equivale a aprobación estética ni a motor de producción. No iniciar B3 sin aprobación.
