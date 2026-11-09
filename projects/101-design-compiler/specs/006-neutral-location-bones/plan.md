# Implementation Plan: Mapas como huesos neutros
**Branch**: `codex/location-neutral-bones-20261108` | **Date**: 2026-11-08 | **Spec**: [spec.md](spec.md)

## Summary
Versionar la familia a 0.2.0 y conservar SingleBusinessLocation.astro, dueño privado fijado y adaptadores. Taller con tres recetas neutras primero. Visual compartido de pin con logo y punta anclada inferior.

## Technical Context
**Language/Version**: TypeScript/JavaScript, Node 24, Astro 7.3.7.
**Primary Dependencies**: Existentes; MapLibre/esbuild privados. Sin paquetes nuevos de aplicación.
**Storage**: Configuración de taller existente; reportes locales ignorados.
**Testing**: node:test, build privado y Chromium/CDP mediante scripts/lib/local-browser.ts.
**Target Platform**: Móvil/tablet/escritorio.
**Project Type**: Componentes del compiler.
**Performance Goals**: Un marcador por instancia; cero llamadas Google por defecto.
**Constraints**: No modificar/publicar dueño privado, credenciales o facturación; no resellar locks.
**Scale/Scope**: Tres composiciones, una familia y un taller.

## Constitution Check
I: spec/plan/tareas antes de código. II: receta conservada, piel secundaria. III: gates y etiquetas sintéticas.
IV: mismos dueños Astro/runtime/Google, sin renderer paralelo. V: anclaje, errores, tamaños y revisión visual.
VI: Google vivo pendiente explícito. VII: alcance acotado, sin dependencias nuevas. Gate previo: PASS.

## Project Structure
- src/bones/location-map.ts: versión y partes.
- src/bones/location-map-marker.js: pin con logo y alternativa.
- src/components/bones/SingleBusinessLocation.astro: neutro y regiones existentes.
- src/pages/bones/location-map.astro: taller y preparación Google.
- src/bones/location-map-workshop.js: guías/persistencia.
- tooling/bones/prepare-location-map.mjs y google-no-pois.style.json: descarga del estilo.
- tests/location-map.test.ts, tests/fixtures/location-map-google-browser.js y scripts/audit-location-map.ts: verificación.
- docs/bones/location-map.md: reproducción/estado.

## Complexity Tracking
Sin violaciones. El visual vive dentro del marcador real, nunca sobre un iframe móvil.
El estilo cloud se publica fuera del código; no se mezcla con MapOptions.styles.
