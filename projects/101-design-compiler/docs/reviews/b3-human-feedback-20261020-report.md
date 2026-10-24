# B3 — valoración humana y ampliación editorial del 20 de octubre

Fecha de evaluación: **2026-10-20, America/Bogota**. Base `a3f86dc` (iteración revisada `fa0735a` + `24e2bfc`). Alcance: continuar exclusivamente B3, sin B4, Design Lock, backend, nueva adquisición de medios o integración upstream.

**Seguimiento vigente tras revisión independiente:** corregidos self-links sociales, binding por tarjeta editorial y evidencia visual vacía. [Hallazgos y respuesta](b3-human-feedback-20261020-independent-review.md). Conjuntos actuales **R3**, 88+16 vistas y 136 capturas no vacías comprobadas por píxeles; 405/406 tests (único H8 heredado), 11/11 nuevos, check256/validate/build168/replay/medios PASS. Los resultados R2 y 403/404 que aparecen más abajo son históricos de `b0eefce`, no la evidencia final actual.

## Valoración registrada

El usuario expresó que le gusta mucho **La mesa abierta**, especialmente su home, elegancia, tipografía y paleta; situó **Mucho apetito** al mismo nivel, quizá algo por encima según gusto, con carácter más americano. Pidió preservar y mejorar ambas como buenas direcciones generales, añadir contacto/redes, opiniones y contenido visual debajo de la portada, retirar el texto de pausa del vídeo y rehacer 03/04 con mayor intención artística.

`data/design/experience-v1.1/human-feedback.json` conserva el mensaje literal, commit de origen y las dos direcciones apreciadas. **No se inventó una nota, ganador, aprobación final ni entrenamiento.** El registro anterior de rechazo queda intacto; describe otra entrega. `design_status` distingue refinamientos de direcciones apreciadas de nuevas propuestas artísticas aún no valoradas. El contrato V1 anterior no fue sustituido por una aprobación implícita.

## Cambios revisables

Abrir [comparador B3](http://127.0.0.1:4331/b3/). Hay **once páginas por dirección, 44 rutas**. Se añaden `/contacto/`, `/opiniones/` y `/diario/`; carta, reserva y pedido mantienen rutas propias. El home muestra selecciones editoriales y enlaces, sin reunir los formularios o acciones de esas páginas.

| Dirección | Conservado / nuevo | Composición |
| --- | --- | --- |
| 01 · La mesa abierta | Se conservan hero Immersive, Georgia, WhiteInk y Spread | Portada elegante, diario fotográfico en cuatro columnas, dos opiniones de muestra y llamada a contacto/redes |
| 02 · Mucho apetito | Se conservan Masthead, tipografía Condensed, Vermilion y Rows | Cabecera roja, diario visual, opiniones y contacto coherentes con esa identidad |
| 03 · El arte de quedarse | Nueva propuesta Collage / BordeauxPaper / EditorialTable | Papel y burdeos, tipografía de gran escala, ritmo de revista, imágenes desiguales, círculo y arco, numeración editorial y opiniones entre líneas |
| 04 · Fuera del reloj | Nueva propuesta Poster / CobaltButter / PosterSequence | Cobalto y amarillo suave, cartel monumental, banda audiovisual, marcos gráficos y fotos a alturas alternas; opiniones sobre azul |

El texto visible «Pausar vídeo» se reemplazó por un icono circular discreto de **44×44 px**, con nombre accesible, tooltip, estado y pausa/reanudar reales. Se conserva la posibilidad de detener movimiento automático; [W3C 2.2.2](https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html), consultado 2026-10-20, sustenta ese mecanismo para movimiento prolongado junto a otro contenido. No se afirma conformidad WCAG total. Permanecen muted/loop/playsinline, fallback estático, política de movimiento reducido/ahorro de datos/visibilidad y pausa fuera de vista.

El cambio vive en el renderer compartido `ExperienceComposition.astro`, `CommunitySections.astro`, el cliente compartido y operadores de `rich-experience.css`. No CSS por candidato/cliente, cuatro forks de aplicación, nuevas bibliotecas o nueva búsqueda probabilística. El runtime comercial y `101-world-model` siguen ausentes: se usa el laboratorio Astro compartido.

## Contenido y funciones honestas

`RichExperienceV1` 1.1, `HumanDesignFeedbackV1` y `DemoCommunityV1` son contratos asociados exportados; los V1 históricos se conservan. El contenido editorial nuevo se valida y se fija con SHA, separado del contenido factual H2. Los **42 hechos y siete módulos** del SitePlan se conservan por dirección y viewport. Los usos editoriales se vinculan a `editorial:journal`, sin simular que H2 confirmó un menú en home ni una capacidad de redes/reseñas.

- Opiniones: tres textos propios sintéticos; home muestra dos y la página propia muestra tres. Cada tarjeta dice **Opinión ficticia**, identifica un personaje de muestra y la sección aclara que no son reseñas de clientes. Sin puntuación agregada, estrellas, avatar de stock, cliente verificado o schema.org Review.
- Diario: cuatro imágenes ilustrativas autorizadas, títulos y textos ficticios; se aclara que **no son publicaciones de Instagram ni proceden de una cuenta real**. No likes, métricas, fechas de publicación inventadas, embeds o APIs.
- Contacto: correo de ejemplo `hola@lamesa.example`, sin recepción. WhatsApp es una demostración deshabilitada, sin número; Instagram y Facebook son **placeholders no interactivos «De muestra»**, sin flecha de salida o URL. Sin cuentas reales, envíos o datos personales. El seguimiento eliminó los enlaces locales de la primera entrega.
- No se ejecutan pedidos, reservas, cobros, disponibilidad o contacto real. Los diagnósticos, restricciones y exclusiones se conservan en créditos, accesibles desde cada pie.

Para una futura implementación real faltan datos comprobables:

| Sección | Datos/autorización necesarios |
| --- | --- |
| Contacto | Correo y teléfono aprobados, alcance por sede, canal receptor, horarios y reglas de atención; proveedor/backend y política de datos cuando corresponda |
| Redes | URL oficial y propiedad/alcance de cada perfil; permiso y condiciones vigentes para integración o embed, credenciales sólo privadas |
| Opiniones | Texto y autor publicables, origen/fecha, autorización de reutilización y reglas de proveedor, moderación y procedencia de cualquier rating; sin inferir compra verificada |
| Diario social | Publicaciones reales e IDs, autoría, permiso de cada archivo y personas/marcas, pie/alt/contexto, fecha real y atribución; mecanismo de actualización autorizado |

Estas dependencias quedan pendientes; no se añaden capacidades operativas confirmadas al SitePlan.

## Medios y permisos

**Cero adquisiciones o llamadas a proveedores.** Se reutilizan las cuatro fotos y el MP4 silencioso existentes. Nueva evaluación separada: `data/media/demo-v1/b3-rich-experience-review.json`, proyecto `b3-fictional-experience-rich`, padre autenticado `378c4506…`, **148 usos exactos**, 44 rutas, mismo cliente/negocio/sucursal. SHA revisado `5f114b66dab6e87092e87e5b942135e2a17922330f845f0393d2afcaefed567a`. La evaluación anterior no se amplía en su lugar.

Se reconsultaron los [términos oficiales de Pixabay](https://pixabay.com/service/terms/) el **2026-10-20**; versión visible November 18, 2024. La evaluación contextual y la cadena por archivo se documentan en `human-media-20261020/review.md` y sus padres B2/H3. Se admite crop CSS en diario/collage con crédito enlazado, dentro del contexto ficticio, sin reinterpretar una URL o VERIFIED del fixture como licencia. No se inventan releases ni permiso sonoro/documental/multicliente/IA. La revisión interna anterior vence como máximo en noviembre y no se autorrenueva por esta entrega.

Original/derivados, hashes, restricciones y evidencia B2/H3 no cambian. Vídeo: `149678-silent-1280.mp4`, **1280×720**, 234 frames, 9,36 s, 2.577.142 bytes, SHA `15d8a7edce609b9a48eea6815cd7d1a275610e3bbce9a8488b86ad1548d252c1`. Sigue siendo el mismo clip; los checks no lo convierten en una campaña de alta resolución. El gate nuevo requiere padre actual, documentos y bytes verificados, registro exacto y handle no falsificable; cambios/reseñalados o usos fuera de alcance se bloquean. El hueco documental histórico continúa bloqueado.

## Verificación ejecutada

Baseline: `human-baseline-20261020/journal.json` sobre la entrega previa. Tests 394/395, sólo H8 heredado; export/check/validate/build156/replays/medios y 2.815 protegidos PASS. La receta terminó durante la edición de archivos asociados, por lo que no se atribuye una ejecución totalmente anterior a toda edición; el estado inicial de Git sí era limpio.

Resultado posterior: **403/404 tests**, único fallo heredado `LOCK_BROWSER_MISMATCH` en `lock-files.test.ts`; **9/9 pruebas nuevas**, además de las ocho anteriores. `human-post-20261020-01/journal.json`: exportación de contratos, check **254 archivos, cero errores/warnings/hints**, validación, build **168 páginas**, B3 scenario/proposals, B2/B1, taxonomy/planner, media replay/verify H3, composition/design/audit/cohort y H9 PASS. H8 lock verify permanece bloqueado por entorno, no se elimina ni se anuncia PASS. **2.815 archivos protegidos sin cambios.** Un primer comando de build fuera de la receta no encontró npm en PATH; se corrigió el PATH sólo del proceso con el Node portable existente. No cambio del sistema o dependencia nueva.

`scripts/b3-rich-verify.ts --verify` comprueba la matriz exacta **88 vistas** (4×11×2), **16 portadas responsive** (4×360/768/1024/1920, con dimensiones exactas), hechos/alcances/módulos, oferta→medio, IDs y textos editoriales, opiniones/avisos, créditos, enlaces, DOM, HTML y bytes public/dist; verifica los SHA de observaciones, capturas, interacciones y fuentes. Las pruebas negativas cubren duplicación/sustitución de cobertura, permiso fuera de alcance, handle falso, reseñado de grants, opinión real aparente, rating/cuenta/contacto no permitidos, pérdida de contenido/aviso y control de movimiento sin nombre.

Evidencia inicial `human-iab-r2-20261020`: 88 observaciones y 383 JPEG de zonas visibles. Tras detectar capturas responsive vacías, queda como historial, **sin acreditar cobertura visual completa**. La evidencia vigente es `human-iab-r3-20261020` y `human-responsive-r3-20261020`: **88+16 observaciones y 136 capturas**, con filtro de presencia recalculado y revisión visual de las 16 portadas responsive y muestras originales. Observado en DOM: cero desbordamientos, medios decodificados, controles cubiertos ≥43 px, tipografía calculada ≥14 px y contraste ≥4,5 en selectores auditados. No se asegura inspección ampliada individual de cada imagen ni equivalencia entre el JPEG y toda la geometría del viewport.

La API fullPage falló en varios intentos y la captura de fondo produjo algunos archivos vacíos. La captura con navegador visible dio contenido utilizable, aunque la superficie puede diferir del viewport CSS (por ejemplo 1425×866 frente a 1440×1000) y recortar encuadres anchos. Se guardan originales, sin coser ni fingir una captura completa a píxel. La evidencia vigente es R3; R2 y el intento `human-iab-20261020` se conservan como historial. No se afirma causa raíz confirmada, recaptura Edge, DPR1, WCAG exhaustiva, transferencia fría, LCP/CLS/INP ni todos los recorridos.

Interacciones reales representativas, 01 móvil, en `interactions.json`: pausa con icono y nombre accesible, reanudar muted, enlace Hablemos a contacto, correo reservado y WhatsApp deshabilitado, opiniones con tres tarjetas ficticias, menú móvil y navegación al diario sin iframe/cuenta real. La interacción no representa una reserva ni un contacto enviado.

Peso local verificable tras seguimiento: **44 HTML entre 45.276 y 57.699 bytes**; mismos nueve archivos de medios utilizados, **3.462.266 bytes en total entre todas las rutas**, incluidos dos tamaños por foto y vídeo. No es transferencia inicial de una página. Sin fuentes remotas o nuevos SDK. Las secciones usan derivados WebP y lazy loading; el efecto real sobre Web Vitals requiere medición separada.

Los recibos de la entrega anterior pertenecen a sus commits. No se sobrescriben para hacer pasar el nuevo renderer; el replay vigente es `b3-rich-verify.ts`. Para reconstruir en otra máquina hacen falta el paquete privado autorizado B2 y su original de vídeo; un clon no descarga stock automáticamente. `.env`, originales/derivados privados, dependencias y temporales quedan fuera de Git.

Comandos desde raíz con Node 24.21.0 existente:

```powershell
.tools/node-v24.21.0-win-x64/node.exe --experimental-strip-types scripts/b3-run.ts NUEVO_ID
.tools/node-v24.21.0-win-x64/node.exe --experimental-strip-types scripts/b3-rich-verify.ts --verify
.tools/node-v24.21.0-win-x64/node.exe --experimental-strip-types scripts/b3-remux-video.ts --verify
```

## Punto de revisión

[Dictamen independiente recibido](b3-human-feedback-20261020-independent-review.md) sobre `986e3b2`: **B3 técnicamente listo para revisión humana**, con límites de captura y sin aprobación estética final. Pendiente tu revisión de los refinamientos 01/02 y propuestas artísticas 03/04. Tu valoración anterior es evidencia positiva de esas direcciones anteriores, no una aprobación automática de los cambios nuevos. No B4 ni bloqueo de diseño final.
