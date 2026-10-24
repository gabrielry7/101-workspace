# H4 — Composiciones base sobre el laboratorio compartido

## Resultado

**PASSED en laboratorio, listo para revisión.** Editorial, Split y Rail representan el mismo fixture restaurante, sin modificar SitePlan H2, contenido aprobado ni permisos H3. Se inspeccionaron las seis vistas principales en Edge y se auditaron además las seis vistas de la oferta de sucursal. Build, bindings, uso de medios, geometría, responsive y accesibilidad principal pasan. La evaluación visual de Codex considera las tres composiciones suficientes para este slice controlado; la preferencia/aprobación visual humana queda para la revisión, no se atribuye al usuario.

`@101/site-runtime` y el runtime comercial están **AUSENTES / NOT_TESTED**. Astro local se usa como laboratorio compartido, reutilizando Foundation; no se declara integración ni se crea un backend/runtime alternativo. H4 no demuestra calidad a escala, cobertura multivertical o readiness de publicación. No se inició H5.

Base: **e2b83d441776bcc7d643ffa2f0c3dee4e648b62d**, H3 cerrado, árbol limpio al inicio. Se leyeron pipeline, V0.2, h0-findings, h2-report, h3-report y contratos. Se conserva el roadmap formal §24, como documentó H0; no se reinterpretan referencias históricas como código disponible.

Antes de editar: **232/232 tests**, check 0 errores/warnings/hints, validación, build y media:verify correctos. Logs [tests](evidence/h4-baseline-tests.txt), [check](evidence/h4-baseline-check.txt), [validación](evidence/h4-baseline-validate.txt), [build](evidence/h4-baseline-build.txt), [medios](evidence/h4-baseline-media-verify.txt). La evidencia histórica H3 permanece intacta.

## Inventario probado

[Inventario con rutas y comandos](evidence/h4-runtime-inventory.txt). Búsqueda: workspace, directorios pares del home y listados de Desktop/Documents/Downloads. No se afirma inspección de todos los discos. No se encontraron instrucciones AGENTS aplicables.

| Pieza disponible en H3 | Reutilización y prueba |
|---|---|
| src/layouts/Foundation.astro | Shell HTML/es, viewport, noindex, main y skip link; usado directamente sin editar; build y prueba real de foco |
| src/planner/validate.ts, content.ts | validateSemanticPlan y offeringFactIds; única autoridad de bindings/publicabilidad; pruebas de rechazo y ledger H4 |
| src/media/gate.ts, package.ts | Gate, pertinencia y verificación de archivos reales; media:verify repetido y controles DOM |
| scripts/load-media-pilot.ts | Paquete sellado H3 sin cambios, mismos cliente/proyecto/fecha de evaluación |
| scripts/render-h3-pilot.ts | Técnica de QA Chromium/CDP local disponible y probada en H3; no se altera su captura; H4 añade harness local compartido |
| package.json / lockfile | Astro 7.3.7, Zod 4.6.5, TypeScript 6.0.3, check 0.9.10; npm ls confirma las cinco dependencias directas existentes |
| Operadores/componentes históricos, corpus OSS | Ninguno presente en HEAD H3. Sin adapters certificados, fuentes/licencias o pruebas disponibles; NOT_TESTED |
| Truth, SiteSpec compiler, CompilerBindingPlanner, ConstrainedCompositionEngine, @101/site-runtime | No disponibles aquí; sin imports/paquete en sources/lockfile. No se simulan |

Se añaden primitivas locales de laboratorio propias, no se atribuye su procedencia a operadores históricos ni bibliotecas OSS. Se certifican solo para los contenidos y tamaños medidos. No hay dependencias nuevas ni fuentes descargadas. Comandos de inventario: git ls-tree de H3; rg --files / rg por nombres históricos; npm ls --depth=0. Comandos de prueba: npm test, npm run check/build, composition:audit/verify.

## Separación de contenido, composición y estilos

| Capa | Ruta / responsabilidad |
|---|---|
| Contenido | src/composition/content.ts: proyección de las referencias aprobadas del bundle validado; no modifica hechos o SitePlan |
| Registry | src/composition/registry.ts: versión local 1.0.0, tres operadores/variantes y montaje explícito de rutas |
| Componentes | src/components/composition/: Identity, OfferingCollection, MediaFigure, SiteNavigation y AuditPanel; mismo código en todas las variantes |
| Composición | Composition.astro selecciona el operador y módulos por bindings; no lee categoría ni usa selectores de cliente |
| Estilos | src/composition/styles.css: tokens comunes, proporciones, ritmo y reglas responsive; sin hechos o asset IDs |
| Render | src/pages/h4/[variant]/[...path].astro: genera las dos rutas semánticas por variante; Foundation local compartido |
| Auditoría | audit.ts compara DOM observado con bindings; observe.ts obtiene DOM/geometría; scripts/lib/local-browser.ts controla Edge aislado y dist local |

No se implementan ArtDirectionV1, DesignPlanV1, DesignLock, solver, muestreo ni LLM de H5. El ledger local versionado es [restaurante-bindings.json](../data/derived/composition-v1/restaurante-bindings.json), regenerable y con replay determinista.

| Módulo H2 obligatorio | Scope / ruta semántica | Componente en las tres variantes |
|---|---|---|
| semantic-7bf9d33184f7e923438acadd | fixture-restaurante-001 / / | Identity; f-name |
| semantic-70d73044727ca9b106d272a8 | fixture-restaurante-001-branch-1 / /sedes/s-051d544b94ae77ae0d73a35b/menu | OfferingCollection; offering-1 / f-offering-1 |

Hashes canónicos: SitePlan `4095293f66936680f0de4f49dc03410ec436154e89646da514a5307af8fa5f22`; contenido proyectado `6fbe1021d1e6fd1249c04d4ebf99df477ee49bdb70e3373730d826f7b97d4c8b`; manifiesto H3 `233a731c012e82d0c78836aa715dd215083f9e3e51c0de282283e01378d1d948`. Ledger canónico H4 `f3e78c15be5c2d3e6c412676d0d69414a7f6b423ae30c3f9b32f72567d2b560c`.

`/h4/editorial/`, `/h4/split/` y `/h4/rail/` son montajes locales de la misma página lógica `/`. Cada prefijo conserva el sufijo completo de la ruta de sucursal. No se reescribe el grant para autorizar nuevas páginas comerciales. La foto se vincula exclusivamente al uso H3 de identidad; la página lógica de oferta no tiene foto. Se preservan ambas rutas, sin mover módulos para fabricar una página única más vistosa.

Los dos textos factuales son exactamente “Restaurante — fixture ficticio” e “Ítem de menú de prueba”. Sin precios, horarios, dirección, platos, nombre de sucursal o destinos inventados. Labels editoriales y de laboratorio se distinguen de hechos mediante bindings. El scope de la oferta es visible sin inventar un nombre de sede. Evidencia-only no se convierte en contenido operativo. Diagnósticos, exclusiones, ledger y restricciones permanecen en una disclosure nativa de trazabilidad accesible; el hueco documental y ausencia de funciones operativas son visibles inicialmente.

## Diferencias estructurales y revisión visual

Paleta y componentes iguales; cambian jerarquía, relaciones espaciales y proporciones. DOM conserva orden navegación → contenido → medio → límites, sin CSS order que invierta la lectura.

| Variante | Escritorio | Móvil |
|---|---|---|
| Editorial / Sequence | Título de gran escala en dos líneas, imagen centrada después, pausas amplias; lectura vertical | Título serif dominante, imagen de ancho completo, ritmo amplio |
| Split | Texto en campo izquierdo e imagen simultánea a la derecha, proporción 0,85:1,15; menor altura total | Secuencia compacta, título sans y separación de navegación; sin dos columnas forzadas |
| Rail | Navegación en rail de 13 rem, título compacto, medio reducido desplazado a la derecha; vacío intencional | Rail pasa a navegación marcada a la izquierda, medio al 90% desplazado; jerarquía compacta |

Capturas de las seis vistas principales, revisadas visualmente por Codex: textos íntegros, imagen sin crop ni overlays, avisos legibles y navegación alcanzable. No se rellenó el contenido escaso del fixture para simular un restaurante completo.

| Variante | Escritorio 1280 × 900 | Móvil 390 × 844 |
|---|---|---|
| Editorial | [captura](evidence/h4/editorial-desktop.png) | [captura](evidence/h4/editorial-mobile.png) |
| Split | [captura](evidence/h4/split-desktop.png) | [captura](evidence/h4/split-mobile.png) |
| Rail | [captura](evidence/h4/rail-desktop.png) | [captura](evidence/h4/rail-mobile.png) |

Las otras seis capturas con sufijo `-offering.png` conservan el módulo de oferta; también fueron auditadas en navegador. El [recibo completo](evidence/h4/browser-audit.json) contiene geometría, DOM, recursos, AX tree principal, interacción, SHA de HTML/CSS y SHA de cada PNG. Edge **154.0.4258.62**, captura final **2026-10-08T23:55:42.782Z**, deviceScaleFactor 1; móvil emulado, no dispositivo físico.

| Vista principal | Imagen CSS | Posición imagen x/y | Altura documento |
|---|---:|---:|---:|
| Editorial escritorio | 640 × 431,16 | 312,5 / 503,08 | 1429 |
| Split escritorio | 640 × 431,16 | 568,78 / 228,39 | 1154 |
| Rail escritorio | 480 × 323,38 | 730,61 / 253,84 | 1072 |
| Editorial móvil | 334 × 225,02 | 28 / 366,06 | 1230 |
| Split móvil | 334 × 225,02 | 28 / 301 | 1165 |
| Rail móvil | 300,59 × 202,5 | 61,41 / 308,5 | 1155 |

Sin overflow horizontal o clipping observado en las doce vistas. Prueba adicional: 320 CSS px y ampliación de texto a 200% en las tres páginas principales, sin overflow. Es estrés de texto explícito, no certificación exhaustiva de zoom de navegador. Reduced motion emulado; cero animaciones.

Accesibilidad principal: lang es, un main y un h1 por página, navegación nombrada y aria-current, skip link visible al Tab y activado con Enter, outline de 3 px, disclosure con Space y foco, enlaces informativos activados con Enter llegando al DOM de la otra ruta. Contraste mínimo calculado de texto visible **7,26:1**, comparando estilos efectivos con fondo sólido; mínimo de tipografía auditada 12 px. Links principales/footer/source y summary tienen al menos 44 px de alto; selector de variantes corregido a ancho mínimo 44 px. AX tree de Chromium confirma landmarks, headings, nombres de enlaces e imagen contextual. No es certificación WCAG completa ni prueba con lectores de pantalla humanos.

## Medio H3 y rendimiento observado

Se preservan original, licencia/documentos, revisiones, grants, roles, restricciones y evidencia H3 byte por byte. JPEG original: **2.351.102 bytes**, 2700 × 1819, SHA `ffdb883d56a41ba9a03a51fb7d1bdf8f0b9e30d3946eda180b750620a17c3715`. El navegador lo decodifica y se verifica también el hash de los bytes servidos. Misma imagen en todas las variantes de identidad, dimensiones explícitas, height:auto, sin crop/filter/transcode. CSS responsive cambia solo tamaño de presentación, no crea un derivado.

Crédito exacto: “Photo by Steve Ausmus, USDA Agricultural Research Service.” Etiqueta exacta: “Imagen atmosférica de pimientos; no documenta este negocio ficticio ni sus platos.” Aviso exacto: “USDA ARS no respalda este fixture, producto, empresa ni posición.” Se presentan juntos a la figura. Alt usa la descripción inspeccionada del activo y declara contexto genérico. Se conserva el cliente/proyecto H3 y la página lógica autorizada; ningún stock satisface offering-1.

Se reutiliza la evaluación documental oficial **2026-10-08** de [H3](h3-report.md); no se inventan nuevos permisos ni revisiones jurídicas. No hay adquisición adicional ni llamadas a proveedores. El browser QA bloquea red HTTPS y sirve solo dist local; las fuentes son enlaces que no se abren automáticamente.

Peso observado sin compresión HTTP, sumando cuerpo HTML y recursos decodificados: Editorial identidad **2.363.075 B**, Split **2.363.048 B**, Rail **2.363.041 B**, iguales en escritorio/móvil. Oferta: **11.373 / 11.346 / 11.339 B** respectivamente. CSS común servido: **4.294 B**; cero JS cliente, fuentes externas o embeds. El favicon del servidor de QA devuelve 204 sin cuerpo. Recursos individuales, transferencias y duración de cada request están en el recibo; navegación local principal 18–71,1 ms en esta ejecución, sin throttling.

**Excepción limitada al laboratorio:** el original atmosférico es pesado para móvil. No se crea una versión optimizada porque el grant del piloto deniega transformaciones. El peso se acepta únicamente para probar composición y conservación de permisos con el paquete fijo solicitado; bloquea una afirmación de rendimiento comercial satisfactorio. Una publicación futura requiere revisión de permiso/derivado y presupuesto, fuera de H4. No se prometen LCP/INP/CLS p75 ni desempeño de red móvil desde tiempos localhost.

## Fallos corregidos y cobertura

1. Un import inicial de checksum apuntaba al resolvedor incorrecto; check/build lo detectaron. Se usa inputSha256 compartido del protocolo existente.
2. El enlace corto Rail tenía ancho menor a 24 px: se corrigió el operador compartido con min-width de 44 px para todas las variantes, sin parche de cliente.
3. El harness enviaba Enter sin evento char a summary; no activaba la disclosure en Edge. Se probó la interacción nativa con Space y se registró abierta, con diagnósticos visibles y foco. No se agregó JS para falsear interacción.
4. Tras cerrar disclosure, la captura automática conservaba un área vacía de su altura anterior: se espera layout en dos frames y se captura explícitamente el tamaño cerrado. Se revisaron de nuevo las seis capturas finales.

Siete tests nuevos verifican proyección de rutas y sucursal, doce DOM reales, mutaciones de módulo obligatorio/hechos/scope/contenido inventado, foto en página/rol inválidos, pérdida de crédito/avisos/hash, crop, contexto de otro cliente, diagnósticos/ledger/restricciones/rutas eliminados y falsas funciones comerciales. Componentes no soportados o hechos no representables bloquean; no hay fallback que omita módulos. El registry local solo certifica identity/offering_collection estáticos; no se anuncian las 47 capacidades como UI disponibles.

## Verificación reproducible y límites

| Comprobación final | Resultado | Evidencia |
|---|---|---|
| Tests | **239/239** | [log](evidence/h4-tests.txt) |
| Check | 0 errores/warnings/hints | [log](evidence/h4-check.txt) |
| Validación | 3 H0, 9 H2, 10 H3 | [log](evidence/h4-validate.txt) |
| Build | 9 rutas: inspector H0, H3, índice H4 y 6 rutas de variantes | [log](evidence/h4-build.txt) |
| Bindings y replay | Mismo ledger y checksum | [generación](evidence/h4-bindings.txt), [replay](evidence/h4-bindings-replay.txt) |
| Medios H3 | Archivo/documentos/render original y build intactos | [log](evidence/h4-media-verify.txt), [replay](evidence/h4-media-replay.txt) |
| Composición | 12 vistas, hashes y auditoría DOM válidos contra build | [log](evidence/h4-composition-verify.txt) |
| Navegador | 12 PASSED + 3 estrés PASSED | [recibo](evidence/h4/browser-audit.json) |
| Base H0–H3 protegida | Sin diff contra e2b83d4; lockfile y 18 contratos intactos | [receipt](evidence/h4-verification.json) |
| Checkout Git | LF y hashes de ledger, recibo y 12 capturas conservados con core.autocrlf=true | [log](evidence/h4-git-repro.txt) |
| Reconstrucción limpia | Checkout del índice, build y ambos verificadores PASSED; HTML/CSS iguales a la evidencia | [log](evidence/h4-clean-build-repro.txt) |

Node 24.21.0 / npm 11.19.0. Reproducción sin red ni recaptura: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify-h4.ps1`, con dependencias existentes del lockfile. No modifica evidencia H3. Para visualizar: npm run dev y abrir /h4/. Para repetir QA: npm run build y npm run composition:audit; requiere Edge instalado o H4_BROWSER_PATH a Chromium compatible. Cambia fecha/capturas, no datos factuales. composition:verify compara hashes HTML/CSS actuales con lo capturado, y bytes PNG con recibo: una captura antigua no aprueba un build cambiado.

La reconstrucción limpia usó un directorio ignorado bajo .tools y una junction local a las dependencias existentes fijadas por el lockfile; sin descarga, sin incorporarlas al commit. No confundir esta reproducción de código/artefactos con recapturar idénticos píxeles en cualquier sistema operativo.

Los hashes y bindings son reproducibles; píxeles y tiempos de una captura nueva pueden variar con OS/fuentes/browser. No hay baseline visual universal, servicio de monitorización jurídica, pruebas de red real, Safari/Firefox, dispositivo físico o accesibilidad exhaustiva. La evidencia de navegador es un recibo de confianza de esta revisión, no una firma autenticada. La revisión humana de preferencia y la integración comercial permanecen pendientes, sin bloquear la demostración de laboratorio autorizada.

Commit solo de fuentes/configuración H4, ledger y evidencia intencional, excluyendo .tools, dist, .astro y node_modules. Sin H5, probabilística, LLM, más medios, backend o integración upstream. **H4 se detiene aquí para revisión.**
