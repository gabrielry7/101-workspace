# Archivo anterior al nuevo esquema de secciones

Fecha del corte: 2026-11-05. El trabajo vigente empieza en
[spec 002](../specs/002-section-bones/spec.md). El legado puede consultarse o
recuperarse; su existencia no lo convierte en la base obligatoria del nuevo motor.

## Respaldo local verificado

`old/snapshots/pre-section-bones-20261105/` conserva:

- `history.bundle`: historial y referencias Git existentes al realizar el corte.
- `working-changes.zip`: contenidos sin commit, deduplicados por SHA-256.
- `manifest.json`: HEAD, rama, ruta, estado y hash por archivo de cada worktree.
- `documents/`: copias legibles verificadas del README anterior, constitución 1.0.0
  y spec 001 con sus documentos de revisión.
- `retired-active/specs/001-navigation-hero/`: carpeta retirada del árbol de specs activos.

Se inventariaron **21 worktrees**, con **1.383 entradas de archivo cambiadas** y
**960 contenidos únicos**. Se verificó el bundle y se recalculó el hash de cada
contenido del ZIP. Las cifras cuentan archivos por worktree, no características terminadas.
El [resumen público](snapshot-summary.json) conserva los hashes de los dos archivos
de respaldo; el inventario detallado y los respaldos permanecen locales.

Este corte cubre historial y cambios de código/documentos. Los originales de
medios privados, dependencias, herramientas ignoradas y salidas bajo `output`
permanecen en sus ubicaciones; no están incluidos en el bundle/ZIP de fuentes.
Se conserva también el PowerPoint anterior en `output`. Los directorios de la
aplicación no se desplazaron para no romper imports, worktrees y comprobaciones
históricas. Su estado anterior sí está preservado en el respaldo.

## Recuperación

Trabajar siempre en una carpeta nueva, sin sobrescribir el checkout actual:

1. Verificar los SHA-256 de `history.bundle` y `working-changes.zip` contra el
   resumen y ejecutar `git bundle verify` desde un repositorio Git.
2. Clonar el bundle en una carpeta nueva. Para recuperar un worktree concreto,
   consultar su `head` en `manifest.json` y abrir ese commit en modo separado.
3. Para cada cambio elegido, recuperar `blobs/<sha256>` del ZIP y escribirlo en la
   ruta relativa `path` del inventario, comprobando tamaño y hash. Las entradas
   `absent: true` registran eliminaciones; los renombres incluyen `previous_path`.
   No aplicar esas eliminaciones sobre el trabajo actual.
4. Revisar el diff recuperado antes de reincorporar nada. El bundle guarda commits;
   el ZIP y el manifiesto son necesarios para recuperar también lo no confirmado.

El respaldo es **local e ignorado por Git**: un clon de GitHub recibe este índice
y su resumen, pero no el ZIP, los datos privados ni los originales de medios.
Para restaurar en otro equipo hace falta transferir esos respaldos por una vía
autorizada; la publicación de este índice no equivale a una copia remota de ellos.
