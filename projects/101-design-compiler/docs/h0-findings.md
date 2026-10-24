# H0: lectura íntegra de V0.2 y decisiones pendientes

Fecha del encargo: 2026-10-07. Fuente: `101_business_website_compiler_pipeline_v0_2.md`, secciones 0–30. No se editó el texto fuente ni se trataron referencias históricas como funcionalidades existentes.

## Diferencias y contradicciones que requieren revisión

| Referencia | Hallazgo | Tratamiento de H0 |
|---|---|---|
| Encargo / §24 H0 / §27.7 | El encargo exige Foundation local, contratos y Astro; el documento pide reconciliar repositorios y condiciona el slice a una ruta reutilizable. El usuario confirma que upstream está en otro computador. | Prevalece el encargo explícito. Se crea una frontera candidata y un inspector; no se reimplementan Truth, SiteSpec ni el runtime comercial ausente. Integración pendiente. |
| Ruta solicitada | `docs/pipeline.md` no existía; solo había el archivo largo V0.2 sin tracking. | Punto de entrada con enlace al original, sin duplicar ni reemplazar la especificación. |
| §23.4 vs §24 H3–H5 | §23.4 atribuye tres composiciones a H3 y aceptación de finalistas a H4; el roadmap formal sitúa medios en H3, composiciones en H4 y búsqueda en H5. | Para dependencias se referencia §24. Es una elección provisional documentada, no una corrección silenciosa. Confirmar criterios antes de H3. |
| §3 vs §5.2 | Aparecen `membership_business`, `scheduled_classes`, `local_service`; el inventario formal utiliza `membership_and_classes` y `field_service_and_quote`. | Los contratos candidatos usan §5.2. No hay aliases o normalización automática; acordar crosswalk en H1. |
| §4.6 / §6 / §8.3 | Conviven `catalog`/`product_catalog`, `checkout`/`purchase`, `online_ordering`/`order`. `membership` se usa como necesidad aunque §6.2 lista principalmente `membership_signup`. | Vocabulario candidato explícito: `product_catalog`, `purchase`, `order`, `membership` separado de signup. Nombres alternos se rechazan para evitar cambios silenciosos. Ratificación pendiente H1/H2. |
| §4.4 | La lista técnica mezcla representación frontend y conectividad backend aunque declara dos ejes independientes. | Campos separados `frontend_status` y `backend_status`; H0 no acredita UI comercial ni integración. |
| §4.3 / §4.6 | Se detallan campos mínimos amplios, pero el ejemplo es parcial y no define el esquema contractual final. | Contratos mínimos candidatos, fact references para campos conocidos y ausencia explícita de datos. No afirmar cobertura completa de todas las ofertas. |
| §22.2 / encargo | La cohorte menciona reserva real y medios ricos; el encargo prohíbe integrar reservas y multimedia y no aporta negocios reales. | Fixtures ficticios sin medios ni destinos comerciales; reservas y cotizaciones confirmadas en datos sintéticos se excluyen por falta de destino. |
| §27 / §24 | El primer encargo histórico solicita clasificación, medios y planificación que se distribuyen entre H1–H3. | Solo interfaces, paquetes manuales y guardas de H0. No resolvedor, adquisición ni generator de SitePlan. |

## Cobertura de la lectura

| Secciones | Requisitos preservados / dependencia |
|---|---|
| 0–3 | Base común, evidencia independiente de arte, siete objetos distintos, categorías como hipótesis y arquetipos combinables. No templates por vertical. |
| 4–9 | Contratos versionados, cinco estados de evidencia, separación de conectividad, publicación upstream, sedes y bindings. H0 propone interfaces; H1/H2 implementarán interpretación y planner. |
| 10 | Derechos, veracidad visual y usos son pruebas distintas. MediaAsset/LicenseGrant/MediaUsage y adquisición quedan en H3. Cualquier URI upstream sigue siendo dato, no permiso. |
| 11–12 | Preferencias humanas literales, corpus por vertical, gramática común, operadores y motion condicionados. No convertir ejemplos históricos en un registry certificado. H4. |
| 13–15 | LLM produce declaraciones, nunca código/dependencias. Búsqueda y solver sujetos a constraints. Corpus OSS exige procedencia, licencias y adapters probados. H4/H5. |
| 16–17 | Astro/TS, HTML/CSS, islas justificadas, contenido no confiable, AST y bindings. H0 solo shell Astro; compiler y auditoría DOM pendientes. |
| 18–20 | Presupuestos, Pareto, gates duros, rollback, nueve auditorías independientes, revisión humana incluyendo ninguna. No scores de belleza ni costos ficticios. H5/H6. |
| 21–23 | Directorios lógicos no obligan a clonar upstream; locks con salidas resueltas, fixtures ficticios/reales separados, pruebas ortogonales, costos reales. H7–H9. |
| 24–27 | Roadmap formal, dependencias, inventario primero, entregas con evidencia y decisiones abiertas. Se registran las diferencias con este encargo. H10 permanece posterior. |
| 28–30 | Fuentes históricas no disponibles aquí, términos de proveedores sin aprobación automática, éxito multivertical con una misma máquina. H0 no demuestra calidad final. |

## Decisiones pendientes y evidencia para cerrarlas

Responsables sugeridos como **roles**, aún sin asignación individual. No inventar responsable ni fecha comprometida; la fecha de decisión y conclusión se llenan al revisar evidencia.

| Decisión | Rol propuesto / hito | Evidencia requerida | Estado |
|---|---|---|---|
| Compatibilidad SiteSpec frente a representación intermedia | Integración upstream / H1 | Contratos y snapshots reales, productor/consumidor, comparación de pérdidas de binding | Pendiente; upstream ausente |
| Vocabulario, subtipos, aliases y abstención | Arquitectura / H1–H2 | Inventario completo por proveedor y casos ambiguos | Pendiente; archivo ausente |
| Expiración, decisiones de publicación y alcance de marca/sucursal | Upstream / H1 | PublicationDecision real y reglas de herencia aprobadas | Pendiente; modelo H0 candidato |
| Operadores, UI y corpus realmente reutilizables | Runtime / H4 | Rutas, commits, licencias y tests; tres composiciones con mismos datos | Pendiente; código ausente |
| Proveedores, multi-cliente, automatización y derechos upstream | Medios / H3–H9 | Muestreo y documentos actuales con permisos por uso | Pendiente; ningún proveedor aprobado |
| Derechos del corpus y entrenamiento | Producto/medios / H4–H6 | Política y permisos de capturas/datasets | Pendiente |
| Foto/video, solver CSS frente a optimización y priors | Diseño / H4–H6 | Comparación ciega y benchmarks con contenido fijo | Pendiente |
| Presupuestos por capability y UX honesta sin backend | Runtime/producto / H2–H6 | Lab tests, matriz de estados, revisión de acciones | Pendiente; no métricas inventadas |
| Verticales prioritarias y frontera costo/calidad | Producto / H7–H9 | Conteos por fuente sin sumas deduplicadas falsas y costos medidos | Pendiente |
| Orden de gates §23.4 vs §24 | Responsable de roadmap / antes de H3 | Revisión explícita del documento | Pendiente; uso provisional de §24 |

## Dependencias entre hitos

`H0 → H1 → H2 → H4 → H5 → H6 → H7 → H8`. H3 puede preparar medios con fixtures en paralelo a H1/H2, pero H4/H5 necesitan usos elegibles. H9 requiere pruebas y gastos reales; H10 corresponde a integraciones posteriores. Dirección artística y disponibilidad de medios iteran, no forman una cascada irrevocable.

Para H1 falta `message (4).txt`; no es posible analizar sus 4.582 observaciones desde las cifras citadas. El contrato y los fixtures actuales no constituyen mapping registry, análisis de mercado ni certificación multivertical.
