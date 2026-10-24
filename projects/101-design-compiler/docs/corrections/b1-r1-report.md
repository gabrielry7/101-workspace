# B1 R1 — replay en lectura y precios vinculados

Revisión inicial: commit `43602823fda67d63937e86ddc0bf0ab457417f78`. El revisor independiente repitió los verificadores, igualdad de capturas y 40 pruebas B1, y encontró dos defectos materiales antes de aprobar. Esta corrección permanece dentro de B1; B2 no se inicia.

Fecha de la corrección: 2026-10-13, America/Bogota.

## Hallazgos y cambios

1. `planner-replay` ejecutaba `plan-fixtures.ts`, que siempre llama writeFile. Aunque los outputs quedaron idénticos, podía sustituir un artefacto alterado antes de comprobarlo. B0 también empleaba ese generador con un --replay ignorado. Se preservan esos recibos y el script histórico, y se retira su uso en el runner B1.
2. PRICES_PRESENT aceptaba cualquier precio del scope, incluso ajeno al menú. Ahora sólo evalúa referencias de precios de ofertas elegibles para la capacidad concreta; un precio de otra función o no vinculado no crea el faltante.

El nuevo `b1-planner-replay.ts` recalcula resultados H2 en memoria, lee los nueve outputs, compara los bytes completos y comprueba mtime/tamaño/inode. No crea directorios, repara archivos ni exporta. El runner lo ejecuta con el modelo de permisos de Node que permite leer y **deniega escritura de filesystem**. El generador antiguo sólo sigue disponible como generador explícito; su --replay no está reparado ni se presenta B0 como revalidado por esta entrega.

El resto de replays media/composition/design/cohort ya usa ramas de lectura. Taxonomy:audit y contracts:export son operaciones explícitas de generación/auditoría, no se describen como replay de sólo lectura. La preservación posterior de hashes confirma sus bytes; esa igualdad no prueba ausencia de escrituras.

## Verificación

Tres negativos/guardas nuevos en `tests/b1-replay.test.ts` comprueban: ejecución con escrituras denegadas y bytes/mtime intactos; whitespace/corrupción rechazada sin reparar la copia temporal; precio no vinculado que deja intacto el diagnóstico de moneda. Pasan 3/3 y el replay B1 verifica que los once outputs siguen iguales sin regenerarlos.

La suite corregida tiene 43 pruebas B1 y 348 totales: el único bloqueo admitido sigue siendo LOCK_BROWSER_MISMATCH histórico. Los recibos nuevos conservan salidas reales y tiempos de máquina; no se editan corridas anteriores. Check/validación/build/exportación/replays/verificadores y preservación se repiten en [r1-final/journal.json](../evidence/corrections/b1/r1-final/journal.json).

Resultado: 347/348 tests; check sin errores/warnings/hints, build 103 páginas, 17 de 19 comandos PASS y los dos bloqueos históricos de tests/lock. La copia limpia del árbol `95b7d75645ff084e113f3582887a25e937d0ebf5` repite el mismo resultado y conserva 1.330 archivos: [r1-clean/journal.json](../evidence/corrections/b1/r1-clean/journal.json). Como en B0/B1, usa fuentes separadas y dependencias/Node locales verificados; no es instalación nueva ni prueba de otro host.

La [comprobación final R1](../evidence/corrections/b1/r1-verify/journal.json) tiene cinco PASS: tres regresiones nuevas, lector H2 sin permiso de escritura, verificación de las 28 vistas del workspace y las 28 de la copia, e igualdad de los 28 pares HTML/RGBA/funcionales. La reproducción anterior se conserva como evidencia de UI y se revalida; no se recapturan páginas cuyos datos y HTML no cambiaron.

No cambian contratos, catálogo, fixtures, salidas derivadas ni UI para los casos existentes: las diferencias afectan la verificación y un caso de contaminación de datos. Las capturas finales y de copia limpia de la entrega previa permanecen válidas para esos casos y se vuelven a verificar contra el diagnóstico corregido; no se afirma nueva inspección visual de páginas que no cambiaron. El Node que deniega escrituras y la comparación de bytes son el nuevo control del replay.

La autorización citada corresponde al «Apruebo B1» directo en la tarea implementadora. El revisor retiró su observación documental al comprobar que la cita no procedía del coordinador. Se aclara el origen en el informe sin sustituir la cita correcta.

Se conserva el bloqueo H8 global y H9 NOT_TESTED. No se adquieren medios, amplían derechos, conectan sistemas, recogen preferencias ni declaran aprobación estética. Se entrega commit correctivo para reauditoría independiente y se mantiene la parada antes de B2.
