# 101 Design Compiler

Colaboración Codex ↔ Claude Code: [configuración, tareas aisladas y verificación](tooling/claude-code/README.md). Codex conserva la orquestación; Claude se invoca mediante su CLI oficial y la integración exige autenticación antes de delegar.

Motor multivertical de UnoCeroUno. **H0–H3 cerrados; H4 verificado en laboratorio para revisión**. Produce planes semánticos, manifiestos de medios y composiciones base compartidas; conserva los huecos documentales y no genera sitios comerciales operativos.

La especificación principal está en [docs/pipeline.md](docs/pipeline.md). El documento V0.2 original permanece intacto. Consultar [hallazgos H0](docs/h0-findings.md), [informe H0](docs/h0-report.md), [protocolo upstream](docs/upstream-protocol-v1.md), [taxonomía](docs/taxonomy-v1.md), [informe H1](docs/h1-report.md) e [informe H2](docs/h2-report.md).

## Desarrollo

Requiere Node **24 LTS** y npm. Las versiones exactas de dependencias están en `package.json` y `package-lock.json`.

```sh
npm ci
npm run validate
npm test
npm run check
npm run build
npm run planner:fixtures
npm run dev
```

`npm run dev` abre el servidor local de Astro; `npm run preview` sirve el build. La página inicial es un inspector estático de contratos y fixtures, etiquetado como desarrollo. No publica ni ofrece operaciones comerciales.

En este computador se preparó Node portable en `.tools/`, sin cambiar el PATH global. Para esta sesión PowerShell:

```powershell
$env:PATH = "$PWD\.tools\node-v24.21.0-win-x64;$env:PATH"
npm.cmd run check
```

`.tools/` está ignorado y no se distribuye. En otra máquina instalar Node 24 LTS desde su distribución oficial. No se necesita Python para usar el proyecto.

## Estructura

```text
contracts/v1/               JSON Schema exportado; frontera portable
src/contracts/v1/          Zod y tipos TypeScript; fuente única de esquemas
src/validation/            validación semántica de paquetes y referencias
src/layouts/               shell Astro para inspección de Foundation
src/pages/                 inspector de fixtures; no templates comerciales
fixtures/v1/               tres paquetes ficticios congelados y manuales
scripts/                   carga, validación y exportación de contratos
tests/                     pruebas de contratos y fallos sembrados
src/taxonomy/              parser de inventario y clasificación determinista
src/planner/               registry compartido, elegibilidad, requisitos y SitePlan
src/upstream/v1/           sobre contractual y validación local, sin conector
taxonomy/v1/               mapping registry declarativo versionado
data/reference/            archivo de categorías original preservado
data/derived/taxonomy-v1/   cobertura/unresolved reproducibles, solo con inventario
data/derived/planner-v1/    planes y bloqueos de nueve escenarios sintéticos
docs/                      especificación, inventario, decisiones y evidencia
```

`npm run contracts:export` regenera los 18 JSON Schema. Se versionan junto a su fuente. No editar los JSON Schema a mano; las pruebas detectan divergencias. La validación estructural por sí sola no demuestra verdad/publicabilidad: ejecutar también `validateBundle`.

## Implementado, simulado y pendiente

| Estado | Alcance |
|---|---|
| Implementado | Astro/TypeScript, contratos candidatos V1, JSON Schema, taxonomía auditada, clasificación y abstención, protocolo candidato, registry semántico, CapabilityProfile y SitePlan deterministas, prioridades/dependencias/bindings y diagnósticos |
| Simulado | Evidencia/publicación y planes manuales H0; casos taxonómicos y mensajes upstream de pruebas, explícitamente ficticios |
| Pendiente | Ampliación revisada del crosswalk, adapter SiteSpec real, runtime comercial 101, cobertura documental de medios, arte LLM, representación visual, composición, auditorías visuales y Design Lock |

No hay pagos, reservas operativas, llamadas LLM ni conectores. H3 conserva un único medio gratuito autorizado para inspección. Ningún fixture representa un negocio real. Precios, contactos, direcciones, instalaciones y fotografías no se rellenan para parecer completos.

## Auditoría H1 y siguiente revisión

```sh
npm run taxonomy:audit
npm run taxonomy:audit -- data/reference/archivo.txt
```

El inventario original está en `data/reference/message (4).txt`. El comando produce `coverage.json` y `unresolved.json` con filas/procedencia/estado por proveedor, ponderaciones separadas por campo y hashes verificables. Sus filas y conteos no representan negocios únicos. Si falta el archivo, retorna código **2** y `MISSING_REFERENCE_INVENTORY`, sin crear cobertura ficticia. Consultar resultados y límites en `docs/h1-report.md`.

El protocolo actual es una propuesta local compatible con V1, no una integración verificada con `101-world-model`. H2 aporta el registro semántico y el planner; las capacidades candidatas no activan funcionalidades. Los cierres H1/H2 y su evidencia están registrados en sus informes.

## H3: medios y permisos

Los contratos asociados de medios viven en `src/media/` y `contracts/media/v1/`. `buildMediaManifest(bundle, requirements, inventory, context)` valida H2, genera necesidades y evalúa cada propuesta de uso. El consumidor debe comprobar `validateMediaManifest` con su contexto esperado y fecha explícita. Revisiones y documentos son entradas de confianza externas; una URL o `DOCUMENTED` no acreditan derechos. No hay conector de descarga ni conexión a upstream. El piloto incluye un archivo real inspeccionado y evidencia oficial archivada.

```sh
npm run media:fixtures
npm run media:replay
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify-h3.ps1
```

Los controles positivos son permisos/inspecciones sintéticos, bloqueados por defecto y habilitados solo expresamente en tests. El paquete mínimo real USDA/ARS tiene cierre **AUTHORIZED_PILOT_PACKAGE_WITH_GAPS**: una imagen atmosférica y un hueco documental conservado. La ruta /h3-media-pilot/ muestra crédito, etiqueta y aviso. Para aceptar el cierre, además de validación semántica se exige verifyPackageFiles sobre los bytes y evidencia; REAL/VERIFIED por sí solos no acreditan derechos. npm run media:verify comprueba el paquete y HTML del build sin red. Ese informe conserva el cierre histórico de H3. Ver [informe H3](docs/h3-report.md) y [evaluación de proveedores](docs/h3-providers.md).

## H4: composiciones en laboratorio compartido

`/h4/` enlaza Editorial, Split y Rail: tres composiciones del mismo SitePlan H2, con sus dos rutas originales montadas bajo cada prefijo de preview. Comparten proyección de contenido, componentes Astro y gramática CSS; ninguna categoría o cliente elige un template. Solo identidad muestra el original atmosférico autorizado de H3. La oferta de sucursal permanece sin foto documental. El runtime comercial `@101/site-runtime` está ausente: esta es una prueba local, sin integración ni backend.

```sh
npm run composition:bindings
npm run composition:replay
npm run build
npm run media:verify
npm run composition:verify
```

`composition:verify` compara el build con evidencia de navegador y conserva bindings, restricciones y hashes. `npm run composition:audit` repite la inspección con Edge local (o `H4_BROWSER_PATH` a Chromium compatible), doce vistas y estrés de texto a 200%; cambia las capturas y fecha de la evidencia. Sin dependencias nuevas o red de proveedores. Ver [informe H4](docs/h4-report.md). Reproducción completa sin recapturar: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify-h4.ps1`. No se implementa H5.
