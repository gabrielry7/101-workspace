# B1 R2 — medio presente no equivale a medio utilizado

Fecha: 2026-10-13, America/Bogota. Base correctiva `d17d1ba51faee94637b78588e6c46ca432a1f0cf`. Se mantiene la corrección R1 y se resuelve el último falso positivo detectado en reauditoría. B2 no se inicia.

## Hallazgo

Una referencia de imagen dentro de una sucursal activaba los requisitos opcionales de medios de opening_hours, aunque la función no utilizara esa imagen. V1 existing_media sólo contiene alcance: no relaciona archivo con capacidad, página, módulo o uso. La presencia del recurso no permite inferir uso ni exigir permiso de una operación inexistente.

## Corrección

Se conserva MEDIA_PRESENT como código legado del catálogo asociado para evitar cambiar el contrato. En B1 ese condicional **no se activa sin un vínculo de uso**, que V1 no aporta. El resultado explica que permanece condicionado a H3/MediaUsage explícito vinculado a la función. El catálogo presenta esa condición en lenguaje claro.

No se elimina el requisito, declara no aplicabilidad ni concede derechos. Gallery y demás requisitos obligatorios de archivo/permiso permanecen pendientes; una imagen DOCUMENTED con ID de documento no los satisface. La integración futura deberá transportar y validar el vínculo real de uso; no se crea ahora una autorización o conector H3.

La regresión compara íntegramente los dos requisitos if_used de horarios antes/después de añadir una foto no vinculada: deben permanecer NOT_REQUIRED_BY_CONDITION. También verifica que media_rights obligatorio de gallery sigue RIGHTS_REVIEW_PENDING. Pasa junto con el lector H2 sin escrituras, la corrupción de bytes y la regresión de precio ajeno.

## Evidencia y límites

Los nuevos derivados B1 se regeneran para conservar la explicación y el diagnóstico corregidos. Las versiones anteriores permanecen en `4360282` y `d17d1ba`; no se sustituyen sus recibos, ni contratos/fixtures/outputs históricos H0–H9. El catálogo mantiene 47 capacidades, 107 niveles y 208 definiciones.

Baseline [r2-final/journal.json](../evidence/corrections/b1/r2-final/journal.json): 348/349 tests; 44 pruebas B1 PASS, único fallo histórico LOCK_BROWSER_MISMATCH. Check sin errores/warnings/hints, validación/build de 103 páginas, contratos, replay B1, lector H2 sin permiso de escritura y verificadores/replays pertinentes PASS. 1.330 archivos protegidos sin cambios. H8 global y H9 NOT_TESTED siguen pendientes.

La explicación visible y los hashes del diagnóstico cambian: se recapturan las 28 vistas del inspector y se comprueba cobertura completa de requisitos, geometría/lectura y teclado, sin formularios, scripts o medios usados. Se conserva evidencia nueva y se reproduce desde un materializado limpio del mismo host; no se recapturan ni reescriben los originales H8. Los recibos finales y la comparación identifican el alcance preciso; no acreditan estética de producto o integración comercial.

Recibos: [r2-browser/qa.json](../evidence/corrections/b1/r2-browser/qa.json), [r2-clean/journal.json](../evidence/corrections/b1/r2-clean/journal.json) y [r2-clean-browser/qa.json](../evidence/corrections/b1/r2-clean-browser/qa.json). El materializado de fuentes previo a informes/recibos nuevos usa el árbol `244ec28cbc0e48b8c05871846d58c15505d7210d`; sigue el procedimiento LF y las dependencias/Node/browser locales de B0, no una instalación nueva. Ambas capturas contienen 28 vistas y 16 equivalencias HTML históricas, con 1.330 archivos protegidos.

La [verificación final](../evidence/corrections/b1/r2-verify/journal.json) pasa las cuatro regresiones, ambos conjuntos de capturas recalculados contra los nuevos derivados y la comparación de 28 pares con HTML/RGBA/observables idénticos. La copia limpia repite 348/349 y los mismos dos bloqueos históricos de tests/lock. Las [muestras manuales](../evidence/corrections/b1/r2-visual/views.json) son sólo de viewport y complementan las capturas completas; se conservan las muestras de versiones anteriores.

Se conserva la excepción local de navegador B0. No hay adquisición, API, gasto autorizado nuevo, operaciones, datos personales, permiso inventado ni modificación del JPEG/avisos H3. Tiempos de máquina se miden; costo total/tokens/trabajo humano siguen desconocidos. Se entrega un commit R2 para reauditoría y se espera revisión/aprobación antes de B2.
