# Implementation Plan: Huesos de ubicación

**Branch**: `codex/location-map-implementation-20261105` | **Date**: 2026-11-05
**Spec**: [spec.md](spec.md)

## Summary

Consumir la API nativa de `packages/location-map` de Tomás, sin copiarla al código
público: el preparador local verifica hashes y compila el dueño privado con un
adaptador propio. Su hook `decorateMap` cambia el visual del marcador existente,
no sus coordenadas. Un wrapper limita presentación y POIs; Google JS es un
adaptador de proveedor del mismo componente. Astro conserva HTML útil sin JS.

## Technical Context

Language/Version: TypeScript/JavaScript ESM, Node 24 para compiler y Node 26 para dueño.
Dependencies: Astro 7.3.7, Zod existente; MapLibre/PMTiles/esbuild fijados del dueño.
Storage: configuración JSON y evidencia local; no nueva base ni servicio.
Testing: node:test, Astro build/check y Edge nativo mediante local-browser.ts.
Platform: web desktop/móvil; WebGL con fallback HTML; Google opcional.
Performance: un marcador, cero llamadas externas en la demo; carga local versionada.
Constraints: código privado sólo .tools, sin claves, sin publicación de builds;
coordenadas restringidas y derechos de logo siguen los gates actuales.
Scope: una familia, tres composiciones existentes; no selector o catálogo masivo.

## Constitution Check

I: spec y tareas preceden código. II: composición/comportamiento separados de piel.
III: logo pasa rightsGate/evaluateSuitability; ubicación se valida por dueño original.
IV: primitiva nativa original y hook existente; no se modifica el original ni se
redistribuye. V: contratos y navegador con fallos, tamaños y preferencias.
VI: synthetic/local/mock/live separados. VII: piloto acotado, sin servicios nuevos.
Gates previos y posteriores al diseño: PASS; Google vivo depende de configuración
externa, no se declara probado por una simulación. No hay hooks de extensión instalados.

## Project Structure

- `src/bones/location-map.ts`: descriptor/partes, validación SSR de medios y piel.
- `src/bones/location-map-runtime.js`: integración del dueño y política sin POIs.
- `src/bones/location-map-marker.js`: visual y anclaje del logo/pin.
- `src/bones/location-map-google.js`: proveedor Google, loader y ciclo de vida.
- `src/bones/location-map-entry.js`: hidratación del componente real.
- `src/components/bones/SingleBusinessLocation.astro`: composiciones y SSR.
- `src/pages/bones/location-map.astro`: taller sin instrumentar componente cliente.
- `tooling/bones/prepare-location-map.mjs`: build local con dueño privado intacto.
- `scripts/audit-location-map.ts`, `tests/location-map*.test.*`: verificación.
- `specs/005-location-map-bones/`: contrato, investigación y tareas.

## Complexity Tracking

No nuevo framework. El build local usa el compiler Astro existente y código real,
no un renderer alternativo. La dependencia privada se prepara sólo para preview;
sin ella el componente mantiene dirección/estado legible y no inventa un mapa.
