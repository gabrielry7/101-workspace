# B3 · Revisión independiente de la iteración de referencias

Tarea revisora autorizada: `01a11911-1da1-73e0-8234-132547fc8f8f`. Primera pasada: commit `26e1960710bf2b1bc5439c125c35384a4312dc75`. Fuente: mensajes de esa tarea durante esta sesión, no una votación del usuario. No se cambió código desde la tarea revisora.

## Pasada inicial

La revisora reprodujo **411/412 tests** (único H8 `LOCK_BROWSER_MISMATCH`), check268 sin diagnósticos, validate/build168 y replay B3 de 88+16 vistas/44 rutas, con los mismos 3.462.266 bytes de medios. Inspeccionó 01–04 en escritorio/móvil, 03/04 a 360/1920, galerías, visita, reserva demo, menú y lectura. Consideró observables las diferencias estructurales 03/04 y la conservación de portada/tipografía/paleta 01/02, sin aprobar su estética.

Contrastó en sitios oficiales Pizza 4P’s (`/kh/`, `/kh/menu/`) y Artek (`/en/`, Stool 60) la navegación, carta e información desplegable atribuidas. La matriz 28=11+2+13+1+1 y las 14 referencias visitadas parcialmente coincidían con datos. No interpretó esas URLs como licencias o capacidades del fixture.

Reportó dos **P2**:

1. El gate no fijaba identidad/orden/estado humano: 03/04 podían pasar como dirección valorada si se modificaba el artefacto. El estado del archivo actual era correcto; era un hueco de validación.
2. Al filtrar el diario, la única tarjeta conservaba la posición/ancho original: alrededor de un cuarto de columna en 01/02, media columna en 03 y un cuarto a la derecha en 04. Conteo, contraste y overflow no detectaban el vacío/composición deficiente.

La pasada inicial quedó cerrada con esos dos hallazgos y a la espera del seguimiento, sin otros hallazgos accionables en ese momento. También conservó los límites de full-page/vitals/Edge no medidos, stock repetido y ausencia de aprobación humana.

## Corrección y evidencia nueva

El contrato ahora exporta una tupla de IDs y estados literales vinculados al feedback. El diario filtrado usa un operador compartido de lectura, con dos columnas en escritorio y una en móvil. Un negativo rechaza anchos/posiciones estrechos; los cuatro filtros y el reset se comprobaron para los cuatro candidatos en ambos viewports.

Se recapturó **R3 completa**, porque el segundo arreglo cambia HTML, CSS, cliente y observador. R2 y su recibo siguen históricos en `26e1960`; no se declara igualdad de render para reutilizarlos. [Informe y pruebas del seguimiento](b3-reference-depth-20261021-report.md), [recibo R3](../evidence/corrections/b3/depth-iab-r3-20261021/verification.json).

Inspección provisional comunicada por la revisora: las lecturas de 01/04 escritorio R3 muestran dos columnas con ancho útil; el reset de 04 recupera su composición escalonada y contador cuatro. Esto no sustituye el dictamen sobre el commit de seguimiento.

**Dictamen final sobre `f69cb195361a99614df9fc1041935473728b9c9a`: técnicamente listo para revisión humana. Los dos P2 quedaron corregidos.** Sin aprobación estética, B4 ni Design Lock.

La revisora repitió desde Git limpio: **413/414 tests**, único fallo histórico `tests/lock-files.test.ts` por `LOCK_BROWSER_MISMATCH`; **19/19 focales**; check de **269 archivos sin diagnósticos**; validate/build de **168 páginas**; replay actual **88+16 observaciones, 44 rutas y 3.462.266 bytes de medios**. Git continuó limpio después del build. Verificó la tupla exportada y sus negativos, y las muestras R3 de lectura/restauración descritas arriba.

Confirmó el prompt humano siguiente. Permanecen los límites materiales: muestras de viewport, sin full-page ni inspección exhaustiva de píxeles; sin vitals/red fría/Edge nuevos; cuatro fotos de stock y un clip; 13 patrones con datos pendientes, uno fuera del caso y uno con observación limitada. Las fuentes oficiales sostienen las observaciones acotadas de navegación/carta/ficha, sin conferir derechos, capacidades o preferencia humana al fixture.

## Prompt propuesto por la revisora para revisión humana

> Revisa esta nueva iteración B3 en `/b3/` en escritorio y móvil. 03 La mesa, en escena y 04 Índice de sobremesa sustituyen las dos propuestas artísticas que rechazaste; 01/02 conservan sus direcciones y ahora también comparten navegación, directorio y lecturas. Recorre la portada y el contenido inferior, abre Explorar, filtra y lee un relato, y revisa carta, visita y reservas de muestra. Para cada dirección dime qué conservarías, qué sigue pareciendo plano o mal compuesto —qué aparece, cómo aparece y simetría— y ejemplos concretos de referencias que aún echas de menos. Puedes rechazar 03/04 de nuevo; no pondré nota ni elegiré ganador por ti. Las funciones sociales/comerciales siguen siendo demostraciones o datos pendientes. No iniciar B4 ni Design Lock sin tu valoración explícita.

El prompt queda propuesto; no se interpreta como respuesta, puntuación o aprobación del usuario.
