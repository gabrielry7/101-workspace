# Tasks: caretta/08

- [x] T001 (FR-001/002/003) Inventario por región, datos neutros y piel separada.
- [x] T002 (FR-004/005) Contrato validado y casos de URL/ID/estado/dato ausente.
- [x] T003 (FR-002/003/005) Composición Astro y revisión con etiquetas por parte.
- [x] T004 (FR-006/007) Navegador nativo, comparación con referencia y evidencia.
- [x] T005 (FR-008) Revisar archivos, commit/push aislados y comprobar remoto.

La comprobación previa spec/plan/tareas no detectó discrepancias de alcance.
Convergencia T001–T004: 130 partes, siete regiones, 24 entradas de directorio y
cinco estados próximos. Cuatro pruebas de contrato pasan; `npm run check`:
410 archivos, 0 errores/advertencias/hints. Edge nativo pasa en 360, 599, 600, 601,
768, 991, 992, 993 y 1440 px, y fuente Arial con colores forzados/movimiento reducido.
Revisión de capturas en cada ancho: sin clipping, cortes dentro de palabras ni
desbordamiento horizontal. Enlace nativo activado por teclado con JS deshabilitado.
Las capturas y comparación original/hueso son locales. [Recibo](../../docs/bones/footer-caretta-verification.json).
Sin huecos técnicos conocidos dentro del alcance; aprobación humana y aplicar
una piel real permanecen fuera de lo acreditado por estas pruebas.

T005: diff de 13 archivos revisado, sin medios ni material privado. Commit
`d93e34daa93bc4153363254cfbb6c1c6fc718736` subido a
`gabrielry7/101-workspace`, rama `codex/footer-caretta-neutral-20261105`, y
comprobado con la API de GitHub. No se fusionó ni desplegó. El worktree ajeno con
otro borrador permanece intacto. Este cierre documental se versiona por separado.

## Recuperación · 2026-11-08

- [x] R01 (FR-001/002/003) Recuperar los once archivos propios de la rama neutra existente.
- [x] R02 (FR-005) Conservar las dos rutas previas como consumidores del mismo hueso.
- [x] R03 (FR-004/006/007) Repetir contratos, auditoría en nueve anchos, teclado sin JS,
  fuente alternativa, movimiento reducido/colores forzados e inspección visual.
- [x] R04 (FR-008) Transferencia aislada y check final; entrega en `codex/footer-caretta-neutral-20261108` con commit/push y comprobación del SHA remoto al cierre.

La revisión inicial de Astro/TypeScript pasó en el checkout principal: 396 archivos,
cero errores, avisos o hints. Las modificaciones de ubicación paralelas quedan fuera
por selección explícita de archivos y entrega desde un worktree separado.

Transferencia aislada verificada: 398 archivos Astro/TypeScript, cero errores,
avisos o hints; nueve pruebas de contrato pasan también desde el worktree de entrega.
