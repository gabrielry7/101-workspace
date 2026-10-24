# Mapa de reutilización

Baseline inspeccionado: `C:/Users/gabri/101-design-compiler`, branch `main`, único worktree, **sin commits** (HEAD unborn, `0000000` en worktree list), `?? docs/`. No había package.json, tests, código ni AGENTS.md aplicable en el repo o ancestros inspeccionados. No se creó commit ni se alteró Git.

| Pieza | Ruta / commit disponible | Estado observado | Prueba / evidencia |
|---|---|---|---|
| Especificación V0.2 | `docs/101_business_website_compiler_pipeline_v0_2.md`; sin commit | EXISTS | Lectura UTF-8 secciones 0–30; texto original intacto |
| Truth / PublicationDecision | No disponible localmente; commit desconocido | MISSING | `rg --files --hidden` del repo solo encontró docs y metadatos Git |
| SiteSpec / Business Genome | No disponible localmente; commit desconocido | MISSING | Mismo inventario; upstream en otro computador según usuario |
| CompilerBindingPlanner / WebsiteCompiler / ConstrainedCompositionEngine | No disponibles; commit desconocido | MISSING | Sin código en baseline |
| `@101/site-runtime` / componentes comerciales | No disponibles; commit desconocido | MISSING | No se instala ni se suplanta un paquete con ese nombre |
| Browser QA / raster critique / screenshot critic | No disponibles; commit desconocido | MISSING | No tests o artefactos históricos locales |
| Operadores / tipografía / motion / topology solver | No disponibles; commit desconocido | MISSING | Solo mencionados en especificación |
| Media analyzer / mutator / rerender | No disponibles; commit desconocido | MISSING | Sin rutas verificables |
| OSS ingester / corpus | No disponibles; commit desconocido | MISSING | No se puede asignar INDEXED_ONLY sin índice local |
| Inventario `message (4).txt` y handoffs | No disponibles; commit desconocido | MISSING | Único documento local en baseline |

Lo creado en H0 no es reutilización de implementación histórica:

| Pieza nueva | Ruta | Estado / comando |
|---|---|---|
| Cuatro contratos candidatos y JSON Schema | `src/contracts/v1/schemas.ts`, `contracts/v1/` | TESTED por `npm test`, `npm run contracts:export` |
| Validador semántico | `src/validation/validate.ts` | TESTED por `npm test` y `npm run validate` |
| Fixtures sintéticos manuales | `fixtures/v1/` | TESTED por `npm run validate` |
| Shell estático Foundation | `src/pages/index.astro`, `src/layouts/Foundation.astro` | Ver resultados concretos en `h0-report.md`; no equivale a runtime comercial |

Ninguna pieza ausente se anuncia como integrada, probada o certificada. Al disponer de upstream se debe reemplazar esta ausencia con rutas/commits y pruebas reales, no con promesas.
