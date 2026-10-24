# B3 — revisión independiente de la aplicación de referencias

Recibida el 2026-10-16, America/Bogota, mediante mensaje de la tarea revisora autorizada `01a11911-1da1-73e0-8234-132547fc8f8f`. Turno `01a144fa-5b69-72e2-b352-381aaab9f25a`, completado según la herramienta de estado. Commits revisados: `a80b7ecd1bb2b4d35b9fffb898c2acb82b26b4bc` y seguimiento `1da1fffb32cd12149b153742ca28d444bf04857d`.

**Dictamen recibido: APTO PARA REVISIÓN VISUAL HUMANA. No aprobación estética, cierre B3 ni autorización B4.**

## Feedback recibido, conservado literalmente

> Revisión independiente de B3 sobre commits a80b7ec y 1da1fff: técnicamente APTO PARA REVISIÓN VISUAL HUMANA, sin aprobación estética ni autorización para B4. Inspeccioné contratos, reglas de composición, asociación oferta→medio, auditoría DOM, ocho capturas completas y playback de muestra. Cuatro relaciones comparten el mismo SitePlan, 42 hechos, siete módulos y medios autorizados; hay variación estructural y reflujo móvil visibles, sin recorte evidente ni invención de funciones. Repetí build/check, 14/14 pruebas B3, replay y comparador canónico 8/8; la suite global deja sólo LOCK_BROWSER_MISMATCH heredado (386/387 en receta actual). Hallazgo resuelto: antes/después marcaba shared_context:false por orden de claves; el seguimiento 1da1fff preserva el original, valida cuatro hashes de forma canónica con negativos y corrige 8/8. El rótulo histórico del comparador se neutralizó; no cambiaron candidatos, CSS ni medios. Límites: Edge controlado no arrancó en dos intentos, así que la inspección visual de esta entrega usa IAB y el replay comprueba evidencia archivada, no recaptura Edge ni mide vitals/red; la foto original de 2,35 MB y la calidad visual final siguen pendientes de decisión humana. No hay voto del usuario ni ganador registrado.

La cita describe lo que la revisora informó repetir; la receta global completa está documentada por el ejecutor en `reference-application-reviewed-01`, no se atribuye una segunda suite global completa a la revisora.

## Hallazgo y corrección

La revisora envió primero este hallazgo específico:

> Hallazgo concreto antes de cerrar: `docs/evidence/corrections/b3/reference-application-iab-02/before-after.json` marca `shared_context:false` en los 8 pares, mientras el informe afirma mismo contexto factual. Revisé qa-08 vs observations: plan/content/media/context tienen los mismos cuatro hashes, pero cambió el orden de claves; parece comparación JSON.stringify sensible al orden. Corrige el comparador/recibo con igualdad canónica y prueba negativa real de hash distinto, o explica explícitamente el campo si significa otra cosa. No uses esa tabla como evidencia de contexto compartido hasta resolverlo. Continúo revisando, sin editar.

Se corrigió en `1da1fff`, preservando el recibo inicial y añadiendo comparación estricta/canónica y prueba negativa. No se cambiaron los cuatro hashes para aprobar. El recibo actual reproduce ocho pares compartidos.

También se notificó una discrepancia del replay durante una edición concurrente del rótulo del índice. La revisora corrigió su interpretación: el fallo coincidió con esa edición y actualización del hash de fuente; no podía atribuirse sólo a dist antiguo. El [delta explícito](../evidence/corrections/b3/reference-application-caption-01/receipt-delta.json) identifica un único hash modificado en `verification.json`: `src/pages/b3/index.astro`. No cambios de candidato, CSS, medios o capturas. La revisión final distingue ese incidente del error real del comparador.

## Alcance de la observación sobre peso

La frase de la revisora sobre la foto **original** no significa que cada página descargue ese JPG. El renderer usa derivados WebP y el clip silencioso permitido. Los `currentSrc` observados y bytes locales se conservan en [verification.json](../evidence/corrections/b3/reference-application-iab-02/verification.json); las URI de las cinco imágenes y sus proporciones se auditan. No se midió transferencia nueva en red ni se convierte el peso del original en peso inicial servido. La suficiencia y calidad estética del paquete siguen a juicio humano.

## Prompt propuesto recibido

> B3 está listo para tu revisión visual, no cerrado estéticamente. Abre /b3/ y mira las cuatro propuestas 01–04 en escritorio y móvil. Indica cuál elegirías (una, varias o ninguna) y, si puedes, puntúa cada una del 1 al 10. Señala qué cambiarías en tipografía, paleta, composición, móvil, vídeo o contenido. Si ninguna convence, di por qué; iteraremos dentro de B3. No iniciaremos B4 ni fijaremos una dirección visual sin tu decisión.

La revisora indicó presentar ese resumen al usuario y esperar su revisión. Se conserva [como prompt de revisión humana](b3-reference-application-human-review-prompt.md), sin ejecución de una fase nueva, ganador supuesto ni registro de preferencias positivas.
