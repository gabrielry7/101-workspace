# B1 — ampliación del objetivo y revisión humana sencilla

Fecha: 2026-10-13, America/Bogota. Base: `2895c825ccc12e78443763483355952a6649e8a5`. Estado: especificaciones ampliadas y panel de revisión; aprobación humana del objetivo y del diseño **pendiente**. B2 no iniciado.

## Por qué se añade este complemento

Durante la revisión, el usuario encontró confuso el inspector técnico. Solicitó una vista general de funciones y datos, y amplió el objetivo para restaurantes. Las 47 capacidades del registry y las 107 variantes B1 continúan intactas: su cobertura técnica no era cobertura exhaustiva del producto deseado.

Se crea un complemento asociado `HumanReviewCatalogV1`, con 47 funciones detalladas, 233 necesidades de información/configuración y 14 agrupaciones: 13 familias de actividad y el modificador de actividad regulada. Los dos números de 47 pertenecen a inventarios distintos: el complemento desglosa experiencias, no reemplaza ni agrega IDs ejecutables al registry. Reutiliza las mismas definiciones por actividad; no contiene código por cliente ni plantillas visuales sectoriales.

El panel `/b1/revision/` muestra primero **qué debería verse → qué necesitamos → qué falta para hacerlo**. El detalle de datos, responsables, integración, pruebas y referencias queda en disclosures. `/b1/revision/food_hospitality/` reúne 30 funciones base, condicionales y opcionales, incluyendo las dependencias del objetivo solicitado.

Esta pantalla es un inspector de especificaciones, no la demo visual final del restaurante. La pregunta de alcance sobre construir además esa demo se presentó al usuario; no se considera respondida por el paso del tiempo. El trabajo independiente se limita al catálogo y su vista de revisión. Las futuras demos deben tener etiqueta visible, datos sintéticos identificados y no emitir solicitudes reales. No se adquieren fotografías ni se rellena el hueco documental H3.

## Solicitudes directas y cobertura

Fuente: mensajes del usuario en esta revisión de B1, no preferencias fabricadas ni una aprobación de diseño. La lista `restaurant_requested_feature_ids` conserva el objetivo solicitado; no es evidencia de que un restaurante concreto lo ofrezca.

| Solicitud | Funciones del complemento | Datos y guardas principales |
| --- | --- | --- |
| Foto y perfil propio de cada plato | `offer_detail`, `media` | ID/sede/oferta, foto auténtica, original/hash, autorización por uso; no usar el pimiento atmosférico como plato |
| Categorías, descripción, búsqueda y filtros | `catalogue`, `search`, `offer_detail` | Categorías y vínculos, campos/valores respaldados, orden, disponibilidad; filtros no deducidos desde fotos |
| Todos los ingredientes y alérgenos | `ingredients` | Recetas/variantes, salsas/acompañamientos, alérgenos y límites/contaminación cruzada documentados; desconocido no equivale a seguro |
| Calorías e historia | `nutrition`, `offer_story` | Porción/unidades, fuente/método/fecha y origen aprobado; no estimaciones inventadas |
| Reseñas del plato y del negocio | `reviews`, `review_submission` | Sujeto exacto, fuente/permiso, autor publicable, fecha, escala y moderación; no fabricar estrellas ni verificación de compra |
| Comprar y pedido online propio | `cart`, `fulfilment`, `checkout`, `order_management` | Variantes/extras/cantidades, precios/cargos, cupones si se ofrecen, modalidad/cobertura/franjas, invitado/cuenta opcional, comprobante, idempotencia, recepción/pago/aceptación diferenciados, estado/cancelación/reembolso/soporte |
| Reservas con personas y celebración | `booking`, `live_booking`, `celebration` | Sede/fecha/duración/zona horaria/grupo, capacidad real, recursos, reglas, depósito/extras cuando correspondan y respuesta a peticiones |
| Plano, mesa elegida y ocupación | `table_map` | Plano auténtico/versionado, IDs/capacidad/combinaciones/accesibilidad, inventario por turno, bloqueo y alternativa textual; preferencia no equivale a asignación |
| Añadir al calendario | `calendar`, `booking_management` | Evento/estado/ID/horas/lugar, cambios y cancelación; descarga de evento distinta de sincronización de cuenta; evento provisional no confirma reserva |
| Fidelización y puntos | `loyalty` | Reglas de acumulación/canje/vigencia, recompensas/elegibilidad, identidad mínima, libro de movimientos y conciliación; no se confunde con membresía |
| Parqueadero | `arrival` | Sí/no/desconocido, propio/cercano, ubicación/costo/cupos/horarios; nada gratuito o disponible por omisión |
| Consulta por WhatsApp | `contact` | Número/destino/finalidad/receptor aprobados; demo sin mensaje ni enlace de prueba operativo |
| Velocidad excelente | `performance`, `usable` | Presupuesto de página/medios, redes/dispositivos, interacción/estabilidad, navegación, accesibilidad y medición real |

## Extensión a otras actividades

Las prioridades son propuestas cualitativas para revisar, no un score ni decisiones automáticas por categoría. `BASE` significa parte del objetivo base propuesto, no función aprobada u operativa. `CONDITIONAL` requiere confirmar que el negocio ofrece ese nivel; `OPTIONAL` requiere una decisión adicional. No hay decisiones `NOT_APPLICABLE` inventadas. Datos desconocidos siguen pendientes. Aplicabilidad con evidencia y diagnóstico automático del complemento quedan para una implementación posterior autorizada.

| Familia | Detalle propuesto, además de la base transversal |
| --- | --- |
| Gastronomía | Plato/categorías/filtros, receta/nutrición/historia, ciclo del pedido, reservas/mesas/grupos/calendario, reseñas/puntos |
| Venta de productos | Ficha/variantes/SKU/especificaciones/compatibilidad, búsqueda/comparación, stock/ciclo de compra/devolución, reseñas y recompensas condicionales |
| Servicios con cita | Servicio/profesional, duración/agenda, solicitud/confirmación/cambio, consulta confidencial cuando proceda |
| Membresías y clases | Planes/renovación/pausa/cancelación, clase/instructor/cupo/inscripción/lista de espera |
| Alojamiento | Habitación/tipo/unidad, noches/ocupación/tarifa total/reglas, fotos auténticas y ciclo de reserva |
| Servicios a domicilio | Alcance/cobertura/costo, cotización/visita técnica, seguimiento/aprobación de cambios y trabajos documentados |
| Vehículos | Compatibilidad, cita/capacidad, presupuesto/diagnóstico/aprobación/estado/garantía documentados |
| Asesoría profesional | Especialidad/credenciales/casos autorizados, consulta mínima y conflicto de interés cuando proceda, agenda y seguimiento privado |
| Educación | Programa/sílabo/modalidad/requisitos/cohorte/cupos/docentes, postulación y certificación respaldada |
| Eventos | Ficha/aforo/categoría/asiento/entrada, accesibilidad, emisión/validación/cancelación/reembolso y calendario |
| Industria B2B | Producto técnico/unidades/tolerancias/certificaciones, volumen mínimo/plazo/logística, cotización y documentación confidencial |
| Inmuebles y espacios | Ficha/área/plano/fotos/precio/modalidad/estado, filtros y agenda de visita con permisos de anuncio |
| Transporte y logística | Ruta/origen/destino/horarios/capacidad/carga/tarifa, cotización y estado/ubicación/ETA sólo con fuente real |
| Actividad regulada | Modificador: revisión competente de actividad/jurisdicción/credenciales/permisos/claims/privacidad; nunca una plantilla de sector |

El catálogo es una propuesta inicial para el universo de arquetipos existente, no cobertura universal de todos los negocios. Tener más funciones no demuestra mejor experiencia. La selección final depende de tareas reales, objetivo aprobado y datos; complejidad, peso y fricción deben revisarse con páginas completas.

## Feedback independiente recibido

Se envió una consulta de **solo lectura** a la tarea revisora existente `01a11911-1da1-73e0-8234-132547fc8f8f`, autorizada por el usuario. Se recibió feedback sobre la brecha entre registry y producto, patrones compartidos, detalles por las 13 familias y el modificador, distinción de testimonios/sistemas de reseñas, datos de sede, derechos y ocupación simulada. Las aportaciones se incorporan como **propuestas del revisor**, no aprobación humana ni una auditoría de esta nueva implementación.

No se crearon agentes ni chats. El feedback recomienda priorizar una demo carta → ficha → carrito y reserva → calendario, pero no autoriza su implementación, adquisición audiovisual ni B2. Una instrucción vieja del coordinador sobre el replay H2 no representa un hallazgo nuevo: R1 ya usa `b1-planner-replay.ts` de sólo lectura bajo permiso de escritura denegado y se vuelve a comprobar.

La revisión previa al commit detectó alcances demasiado generales en reseñas/carrito/profesionales y dependencias excesivas de disponibilidad en vivo/carrito propio. Se corrigieron: los datos se vinculan por ítem a negocio, sede, oferta, persona, reseña individual, sujeto reseñado, recurso/instancia, archivo+sujeto+uso o proyecto. Las credenciales/retratos pertenecen a la persona vinculada a servicio/sede, no a cualquier profesional del mismo servicio. Texto/autor/fecha/permiso pertenecen a la reseña exacta; agregado/escala/cantidad al sujeto reseñado. No se heredan permisos entre reseñas del mismo plato ni precios entre platos. La información de entrega/retiro no necesita carrito y la gestión de una reserva existente puede provenir de un receptor humano/sistema autorizado, con privacidad, sin exigir inventario en vivo. El panel conserva estos scopes y responsables en cada necesidad; una regresión verifica las declaraciones exactas. No se presenta esto como prueba de evaluación de datos reales: el complemento sigue sin ejecutar diagnóstico de BusinessInput.

## Fuentes y límites

Fuente oficial de rendimiento: [Google Web Vitals](https://web.dev/articles/vitals), consultada el **2026-10-13**. Objetivos propuestos: LCP ≤ 2,5 s; INP ≤ 200 ms; CLS ≤ 0,1 en p75, separado por móvil/escritorio. Estos umbrales son objetivos de campo; el panel no los acredita para un restaurante comercial. Carga local/laboratorio y rendimiento de usuarios reales son evidencias distintas.

No hay evaluación legal nueva de proveedores. Se especifica que permisos, datos alimentarios/nutricionales, credenciales, contenido regulado y fuentes de reseñas requieren revisión pertinente antes de publicar/operar. No se afirma que una API permita extracción, almacenamiento, reseñas o automatización. H3 conserva permisos/evidencia/hueco documental; no se cambia la licencia ni se amplía el uso de su JPEG.

## Implementación y verificación

Fuentes: `src/requirements/review-contracts.ts`, `review-catalog.ts`, `review.css`, componente compartido `ReviewFeatureCard.astro` y páginas de `/b1/revision/`. Nuevos contratos asociados: `contracts/requirements/review-v1/`. Se añade su export y un enlace desde `/b1/`; catálogo técnico B1, diagnósticos, registry, runtime y outputs históricos se conservan. Los recibos nuevos fijan sus bytes mediante una excepción `human-review-*`; se conservan las cuatro reglas preexistentes de atributos B1. El revisor detectó antes del commit su eliminación accidental inicial; se restauraron, se comprobaron atributos y se normalizó sólo el exporter editado a LF para evitar ruido de staging. No se normalizan logs ni evidencia histórica.

Los contratos permiten exclusivamente `PROPOSED_FOR_HUMAN_REVIEW`, datos sin evaluar, frontend no construido y operación sin conexión. La validación semántica comprueba checksum, IDs/referencias, cobertura de arquetipos, dependencias sin ciclos y relación parcial con V1 o extensión necesaria. No interpreta ni valida los valores de un negocio: las necesidades son especificaciones legibles, no predicados implementados. La fidelización carece de ID V1; se marca como extensión necesaria.

Pruebas específicas: cobertura de solicitudes, definiciones compartidas y dependencias por perfil, ciclo del pedido, ocupación/calendar sin confirmación ficticia, verdad de oferta/alérgenos/nutrición/parqueadero, scopes por dato y responsable de rendimiento/derechos, estados inventados y referencias/ciclos manipulados. La primera prueba detectó que el selector devolvía objetos previos al parseo en vez de las definiciones canónicas; se corrigió el selector. Son seis pruebas nuevas. Un intento manual de `npm run check` sin PATH portable no pudo encontrar Node; el runner compartido usa el Node/PATH fijados y registra la ejecución válida posterior.

Resultados finales:

| Comprobación | Resultado y evidencia |
| --- | --- |
| Seis nuevas pruebas de especificación | PASS, junto a las regresiones B1 anteriores |
| Suite completa | **354/355**; único FAIL histórico `LOCK_BROWSER_MISMATCH` en `lock-files.test.ts`; no se omite ni se cambia el lock |
| Exportación de contratos | PASS; dos nuevos contratos asociados, sin cambio de los esquemas existentes |
| Check | PASS; 0 errores, warnings e hints |
| Validación y build | PASS; 118 páginas |
| B1 replay y H2 de sólo lectura | PASS; 11 casos B1 y 9 outputs H2; H2 ejecutado con escrituras de filesystem denegadas |
| Medios y demás verificadores/replays | PASS en media, composición, diseño, auditoría y cohortes; `lock:verify` conserva el bloqueo histórico de Edge |
| H9 | Inventario verificado; permanece BLOCKED/NOT_TESTED, sin sitios reales elegibles ni métricas de benchmark fabricadas |
| Panel nuevo en navegador | **32 vistas PASS**: 15 rutas × escritorio/móvil y mesa expandida × ambos; IDs, responsables y scopes de todas las necesidades conservados |
| Geometría y navegación | Cero desbordamientos; mínimo observado 14,4 px; skip link, navegación y disclosure con teclado; sin formularios, scripts ni medios comerciales |
| Peso observado | HTML máximo 114.554 bytes, en restaurante; es peso HTML, no medición de campo ni presupuesto aprobado del sitio final |
| Preservación | 1.330 archivos protegidos intactos y 16 referencias HTML H8 idénticas |
| Reproducción separada | Otras 32 vistas PASS; **32 pares HTML/RGBA/DOM idénticos**, 64 capturas cuyos hashes se recomputan, y dos journals verificados |

Baseline final: [human-review-final-scope/journal.json](../evidence/corrections/b1/human-review-final-scope/journal.json). Capturas finales: [human-review-browser-delivery/qa.json](../evidence/corrections/b1/human-review-browser-delivery/qa.json). Copia: [human-review-clean-pinned/journal.json](../evidence/corrections/b1/human-review-clean-pinned/journal.json), [human-review-clean-pinned-browser/qa.json](../evidence/corrections/b1/human-review-clean-pinned-browser/qa.json). Comparación y recetas: [human-review-reproduction/comparison.json](../evidence/corrections/b1/human-review-reproduction/comparison.json), [compare.mjs](../evidence/corrections/b1/human-review-reproduction/compare.mjs).

Se inspeccionaron manualmente muestras de restaurante en móvil/escritorio y mesa expandida. La introducción inicialmente ocupaba casi el primer viewport móvil; se acortó y su explicación pasó a un disclosure. Las capturas son **sólo de viewport**, con geometría y cobertura DOM del documento completo. No son aprobación estética ni una auditoría WCAG completa; contraste, lector de pantalla y experiencia comercial integral requieren trabajo adicional.

El árbol de fuentes reproducido es `a4d85dcff7257e1761dfcd1aced1c3d98b8df58a`, anterior a los informes/recibos/recetas finales, materializado por Git archive, con fuentes y builds separados y junctions al Node/dependencias/browser ya verificados. La primera copia falló las guardas: archive convirtió saltos de línea de evidencia HTML histórica y package manifests con hash de bytes. Se conserva la evidencia fallida y se documenta en [attempts.json](../evidence/corrections/b1/human-review-reproduction/attempts.json). No se redujeron las guardas ni se editaron los originales.

Para repetir el entorno declarado, [materialize.mjs](../evidence/corrections/b1/human-review-reproduction/materialize.mjs) verifica contra los pins y aplica **58 overlays de bytes**: 56 archivos históricos de evidencia HTML y los dos manifests de paquete. Sólo admite diferencias de saltos de línea con texto LF idéntico y SHA original confirmado. [materialization.json](../evidence/corrections/b1/human-review-reproduction/materialization.json) conserva SHA del archive, antes/después y motivo por archivo. No hay instalación, dependencia nueva ni override de código de producto. Reproducción acotada al mismo host/OS/fuentes/runtime; no portabilidad o instalación fresca.

El comparador de bindings de QA tuvo un falso positivo porque el DOM agrupa funciones por sección y la selección tenía otro orden. Se corrigió comparando ID+owner+scope ordenados por ID, sin debilitar cobertura; la corrida fallida `human-review-browser-final` se conserva. Los otros recibos `human-review-*` anteriores son candidatos documentados, no el resultado final vigente.

No se declara cierre comercial ni aprobación estética o humana del objetivo. Se entrega para revisión; B2 y la demo comercial siguen pendientes de alcance/aprobación explícitos.
