# Entrega H0 Foundation

## Resultado

**H0 Foundation del encargo: PASSED.** Se deja una base verificable para revisar H1; no se inició H1. **Reconciliación/integración con upstream del H0 histórico: NOT_TESTED**, porque `101-world-model`, su runtime y los prototipos están en otro computador y no están disponibles. No se anuncia integración ni certificación visual.

Baseline: branch `main` sin commits, único worktree, solo documento V0.2 sin tracking. No había tests, código, dependencias ni Node/npm en PATH. Se preservó el documento original y se añadió `docs/pipeline.md` como entrada estable. Hash SHA256 del original al entregar: `022cf7b56585a8cc8f3aca96543211ca46d3725073bcf00c5cf4c541ebbd732c`.

## Archivos y comportamiento entregados

- `.gitignore`, `.node-version`, `package.json`, `package-lock.json`, `tsconfig.json`, `astro.config.mjs`: proyecto único y toolchain fijado.
- `src/contracts/v1/schemas.ts` y `contracts/v1/{BusinessInputV1,BusinessProfileV1,CapabilityProfileV1,SitePlanV1}.schema.json`: cuatro contratos candidatos, tipos derivados y formatos portables.
- `src/validation/validate.ts`: guardas de esquema, referencias, evidencia, publicación, vigencia, scope y disposición de capabilities; diagnósticos accionables.
- `fixtures/v1/{restaurante,gimnasio,ferreteria}.json`: paquetes sintéticos congelados con perfiles y planes manuales. Menú; membresías/clases; catálogo. Reservas/cotizaciones sin destino se excluyen por MISSING_INPUT; delivery UNKNOWN nunca se habilita.
- `scripts/{load-fixtures,validate-fixtures,export-contracts}.ts`: validación automática y exportación.
- `tests/{contracts,schema-export}.test.ts`: errores sembrados y sincronización de esquemas.
- `src/pages/index.astro`, `src/layouts/Foundation.astro`: inspector estático de desarrollo, sin operaciones comerciales ni diseño por categoría.
- `README.md`, `docs/{pipeline,h0-findings,reuse-map,gap-map,integration-boundaries,h0-report}.md`: comandos, inventario, brechas, contradicciones, decisiones y evidencia.

Reutilizado: únicamente la especificación local; no se encontró código histórico reutilizable. Añadido: Foundation mínima, sin sustituir Truth, SiteSpec, extracción ni runtime comercial 101. No se realizaron commits, publicación ni cambios en servicios externos. `.tools/`, `node_modules/`, `.astro/` y `dist/` son locales e ignorados por Git.

## Evidencia de ejecución

Entorno: Windows/PowerShell; Node **24.21.0 LTS**, npm **11.19.0**, Astro **7.3.7**, Zod **4.6.5**, TypeScript **6.0.3**, `@astrojs/check` **0.9.10**, `@types/node` **24.19.1**. Node descargado desde distribución oficial y cotejado con SHASUMS256 antes de extraer. Dependencias directas fijadas y lockfile generado.

| Comando / verificación | Resultado final | Evidencia |
|---|---|---|
| `npm run contracts:export` | PASSED | Cuatro JSON Schema 2020-12 exportados |
| `npm run validate` | PASSED | Restaurante, gimnasio y ferretería válidos |
| `npm test` | PASSED | **36/36**, 0 fallos, 0 omitidos |
| `npm run check` | PASSED | Astro check y tsc: **0 errores, 0 warnings, 0 hints** |
| `npm run build` | PASSED | Validación previa y una ruta estática `/index.html` construida |
| Inspección del HTML generado | PASSED | 5.255 bytes, los tres fixtures y etiquetas ficticias presentes, **0 scripts de cliente** |
| `npm ls --depth=0` | PASSED | Cinco dependencias directas sin problemas de resolución |
| Auditoría durante instalación npm | PASSED en esa ejecución | 0 vulnerabilidades reportadas; no es una garantía futura |
| Integración con upstream/runtime histórico | NOT_TESTED | Sistemas ausentes; sin rutas o commits verificables |
| QA visual/browser, performance y accesibilidad completa | NOT_TESTED | Fuera del slice; el inspector no demuestra calidad de sitios de clientes |

Cobertura funcional de las pruebas: cinco estados factuales, no-inferencia por categoría y aceptación de híbridos verificados; evidencia faltante/incompatible; ofertas incorrectas, identidad y contenido faltantes; referencias inexistentes; datos withheld/expirados; alcance entre sucursales; snapshots/versiones; código arbitrario en planes; rutas vacías/duplicadas; abstención; destinos inseguros; soporte e integraciones falsamente declarados; etiquetas sintéticas; exclusiones y JSON Schema sincronizado. No se midió porcentaje de cobertura de líneas y no se inventa una cifra.

## Errores encontrados y correcciones

1. El ejecutor restringido no inicializó (`helper_unknown_error`, setup refresh). Las operaciones de shell necesarias se realizaron con aprobación; no fue un fallo del proyecto.
2. `docs/pipeline.md` no existía. Se localizó y leyó el V0.2 con otro nombre, conservándolo y añadiendo un enlace estable.
3. Node/npm no existían en PATH. Se preparó Node portable local, ignorado por Git, sin cambiar instalación global.
4. Npm seleccionó TypeScript 7 inicialmente; `astro check` rechazó esa versión. Se fijó TypeScript 6 y tipos de Node 24; el chequeo final pasa sin advertencias. Se eliminó además el uso de una API Zod deprecada que producía un hint.
5. El primer build falló ENOENT al cargar fixtures usando `import.meta.url` desde chunks reubicados por Astro. El inspector ahora importa JSON estáticamente; el loader de scripts sigue leyendo archivos originales. Build final pasa.
6. Npm informó un aviso de install scripts de esbuild; no fue bloqueo de instalación o build. No se instalaron runtimes de UI ni se amplió el scope para resolverlo.
7. La comprobación auxiliar inicial del HTML mediante Python tuvo un error de paréntesis. Se corrigió ejecutando una inspección PowerShell con assertions; el resultado final confirma tres fixtures, etiquetas sintéticas y cero scripts. No afectó el build ni las pruebas.

## Límites y próximos hitos

Implementado: contratos candidatos y guardas deterministas, fixtures, shell y comandos. Simulado: contenido/evidencia/publicación/arquetipos/perfiles/planes. Pendiente: acuerdos upstream, adaptación real, taxonomía, registry/planner, medios/permisos, componentes comerciales, composición/LLM, auditorías y lock.

Los JSON Schema no sustituyen la validación semántica. Las guardas no autentican decisiones upstream. La vigencia se evalúa al corte del snapshot salvo fecha explícita; una entrega real necesita validar frescura con esa fecha. El vocabulario y las ofertas V1 son una propuesta mínima que requiere acuerdo en H1/H2. Nada de esto acredita calidad visual excepcional, costos de construcción a escala ni conformidad WCAG.

Comparación contra baseline: de una especificación sin infraestructura a cuatro interfaces portables, tres paquetes multiverticales válidos, 36 pruebas y un build estático. No se añade código específico para renderizar un negocio ni se crean plantillas sectoriales.

El siguiente cambio acotado, **solo tras revisión**, es H1: inventario íntegro de categorías, protocolo upstream y mapping/abstención. Falta `message (4).txt`; sus conteos citados no permiten reconstruirlo. Las diferencias con el roadmap están registradas en `h0-findings.md`. **Se detiene el trabajo al finalizar H0.**

## Cierre posterior autorizado para iniciar H1

H0 quedó cerrado en commit `ec306f28fcbca5123e111d3f6ca58e536769a4f3` (`chore: close H0 foundation with versioned contracts and fixtures`). Antes de ese commit se ejecutó `npm ci` desde el lockfile, 36/36 pruebas, chequeo sin diagnósticos y build exitoso. Solo se incluyeron los 30 archivos de fuente/contratos/fixtures/documentación; herramientas, dependencias y salida generada permanecieron ignoradas. El árbol quedó limpio. Las líneas anteriores describen la entrega original, previa al commit; el usuario autorizó H1 después de esa revisión.
