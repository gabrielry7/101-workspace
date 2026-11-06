# Implementation Plan: Footer 001

**Branch**: `codex/footer-caretta-bones-20261105` | **Date**: 2026-11-05 |
**Spec**: [spec.md](spec.md)

## Summary

Añadir un componente Astro al renderer existente, un fixture real de Caretta y
una ruta de taller aislada. Reconstrucción propia desde la captura, sin copiar
la implementación de la web. El contenido se valida antes del render.
La extensión de texto calcula uniones de rectángulos; el instrumental común se
carga del módulo original de Tomás, preparado localmente e ignorado por Git.

## Technical Context

**Language/Version**: TypeScript, Astro 7.3.7, Node 24 de la aplicación.
**Primary Dependencies**: Astro y Zod existentes; sin nuevas dependencias de runtime.
**Storage**: Fixture y evidencia JSON; snapshots privados en .tools.
**Testing**: node:test para contrato/uniones y script de navegador nativo con
`scripts/lib/local-browser.ts`, astro check y build.
**Target Platform**: Web estática, escritorio/tablet/móvil.
**Project Type**: Componente y taller del compiler existente.
**Performance Goals**: Footer sin JavaScript obligatorio, fuentes o imágenes remotas;
instrumental sólo por petición del operador y sin consultas a proveedores.
**Constraints**: Sin redistribución del módulo privado; fallback explícito al faltar;
ninguna nueva animación inferida de una captura estática.
**Scale/Scope**: Un hueso, un fixture real y tres tamaños de medición, más límites de breakpoint.

## Constitution Check

Antes y después de diseño: PASS. Spec previa y tareas trazables; estructura y
comportamiento separados de piel y hechos; media original sólo en referencia;
fuentes antiguas intactas; un único renderer Astro; módulo de medidas compartido
reutilizado, extensión específica justificada por FR-008/009; comprobaciones
nativas y revisión visual humana separadas; commit/push acotados.
El usuario eligió footer como primer caso concreto, sustituyendo el orden inicial
nav/hero propuesto en spec 002. No se migra el footer ficticio legado ni se lo
declara apto para marcas reales.

En la revisión de integración se detectó trabajo concurrente del mismo footer
en el checkout compartido. Esta entrega permanece aislada; no se copian ni
fusionan fuentes sobre ese trabajo. Reconciliar el dueño/ID es requisito de una
integración posterior, no se presentan dos renderers como una única versión aprobada.

## Project Structure

### Documentation (this feature)

`spec.md`, `research.md`, `data-model.md`, `contracts/footer.md`,
`quickstart.md`, `tasks.md`, `analysis.md`.

### Source Code (repository root)

- `src/bones/footer/`: contrato, anatomía, fixture y extensión de medición.
- `src/components/bones/footer/`: componente Astro y enlace nativo.
- `src/pages/bones/footers/`: índice, taller Caretta y consumidor sin inspector.
- `src/bones/footer/workshop.ts`: iframe, guías, medidas y descarga del operador.
- `tooling/bones/prepare-inspector.mjs`: referencia local fijada, sin copiarla a Git.
- `scripts/audit-footer-bones.ts`, `tests/footer-bones.test.ts`.
- `docs/evidence/bones/footer-001/`: recibo/medidas; capturas completas locales ignoradas.

**Structure Decision**: Seguir el app Astro actual. El footer legado
`src/components/composition/SiteFooter.astro` depende de escenarios ficticios y no
tiene este contrato: se conserva. Los enlaces se apoyan en HTML nativo; no se
crea un motor de acciones ni se reimplementan los perfiles visuales de upstream.
El instrumental de Tomás se prepara bajo `.tools/footer-inspector/`, ignorado,
con hashes y commit de origen. Sólo el build de revisión lo coloca en su directorio
estático temporal; el public del sitio no lo contiene. No es requisito para leer el footer.

## Verification

Contrato positivo/negativo, solapamientos de áreas y límites matemáticos.
Build y chequeo de tipos. Browser: geometría 1440, móvil/tablet, ambos lados de
992, fuente fallback, teclado, enlaces/estados, reducción de movimiento, no-JS,
exportación y dependencia compartida ausente. Capturas reales y porcentaje de
texto por tamaño, indicando que el cambio móvil es propuesto.
