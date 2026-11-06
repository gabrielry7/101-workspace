# Implementation Plan: caretta/08 como hueso neutro

**Branch**: `codex/footer-caretta-neutral-20261105` | **Date**: 2026-11-05
**Spec**: [spec.md](spec.md)

## Summary

Añadir un componente Astro de footer con estructura estable, contrato Zod y
fixture de etiquetas genéricas. La ruta de revisión usa ese componente real,
sin heredar el diseño de Foundation ni los estilos del footer legado.
La piel de la referencia queda en una ficha de observaciones, sin CSS de marca.

## Technical Context

- Astro 7 / TypeScript / Node 24 existentes; sin dependencias nuevas.
- Reutilizar Zod y el renderer/build Astro. `SiteFooter.astro` es una composición
  completa de legado: se conserva y no se altera su salida aprobada.
- No existe aún un dueño ejecutable de footer en el nuevo catálogo. Se incorpora
  una sola receta en `src/components/bones/DirectoryFooter.astro`, sin generador,
  servicio, framework o renderer adicional.
- El handoff de Tomás tiene recetas y anatomía de **reseñas**, no de este footer.
  Se conserva el patrón de partes con IDs y responsabilidades separadas, sin
  copiar ni publicar sus fuentes privadas ni recrear el inspector de reseñas.
- Reutilizar `scripts/lib/local-browser.ts` para Edge nativo, capturas y checks.
- Referencias locales en `.tools/footer-caretta-20261105` sólo para comparación;
  los archivos de referencia y HTML original quedan fuera del commit.

## Constitution Check

Intención previa: spec escrita antes del código. Hueso/estado/contenido/piel
separados. No se atribuyen datos de Caretta al fixture neutro. No se publican medios.
Se preserva el árbol sucio y la demo de reseñas. Verificación proporcional de
contrato y navegador. No se declara aprobación humana ni automatización medida.
Sin desviaciones. La tabla de partes y los contornos son guías del operador.

## Structure and verification

- `src/bones/footer-caretta.ts`: contrato, fixture neutro, registro y anatomía.
- `src/components/bones/DirectoryFooter.astro`: única composición de siete regiones.
- `src/components/bones/FooterEntry.astro`: semántica de destino/ausente/próximo.
- `src/pages/bones/footer-caretta.astro`: taller sin diseño y tabla de partes.
- `docs/bones/footer-caretta.md`: separación observada de piel y correspondencia.
- `tests/footer-caretta.test.ts`: casos positivos y fallos reales de contrato.
- `scripts/audit-footer-caretta.ts`: construir la página Astro real, revisar
  reflujo, IDs, palabras, acciones y capturas mediante el navegador existente.

Reflujo propuesto: debajo de 992 px identidad encima del directorio; debajo de
600 px directorio en dos columnas. Los grupos conservan orden y contenido.
Sin JS de cliente, eventos inventados ni animaciones. El espacio de marca grande
es un hueco identificado, sin crear un wordmark nuevo ni recortar etiquetas.

## Delivery boundary

Transferir sólo estos archivos, README y el enlace de spec 002 revisados a un
worktree limpio del monorepo de destino. El clon existente contiene un borrador
003 sin seguimiento y otra implementación en curso: preservarlos, sin sobrescribirlos.
Usar worktree separado desde `46d3759` y rama `codex/footer-caretta-neutral-20261105`.
No publicar todo el árbol
local ni usar Thomas como destino. Registrar pruebas y SHA en la entrega.
