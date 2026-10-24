# H3 — Cierre del paquete mínimo de medios

**Cierre H3 demostrado para revisión: AUTHORIZED_PILOT_PACKAGE_WITH_GAPS.** Una fotografía real autorizada satisface la necesidad atmosférica del piloto restaurante. Su necesidad documental continúa bloqueada: stock no acredita un negocio ficticio. Los otros escenarios mantienen sus huecos. No se inició H4.

## Base y contratos

Se leyeron pipeline, especificación V0.2, informes y contratos. H2 está cerrado en d3c8be9649a6f323ea47fb48ad64af9521cc39e6, tras 161 tests, check, validación y build. Sus contratos, fuentes, fixtures y artefactos protegidos y package-lock.json permanecen sin diff. La implementación inicial H3 pasó 226 tests, pero seguía pendiente; este cierre agrega evidencia real.

Los cinco contratos candidatos 1.0.0 son MediaAssetV1, LicenseGrantV1, MediaUsageV1, MediaManifestV1 y MediaBriefV1. Los 13 contratos anteriores permanecen intactos: 18 esquemas exportados. Las ampliaciones son prueba opcional package_proof, avisos y declaración de no respaldo. MediaBriefV1 conserva PENDING_AUTHORIZED_MEDIA_PACKAGE y admite AUTHORIZED_PILOT_PACKAGE_WITH_GAPS y AUTHORIZED_PILOT_PACKAGE. Los controles anteriores siguen pendientes.

Las necesidades se generan desde SitePlan/SiteRequirements por módulo, finalidad, sujetos y sucursal, distinguiendo DOCUMENTARY, ILLUSTRATIVE y ATMOSPHERIC. El gate determina permisos por activo/hash, cliente, proyecto, scope, finalidad, página, territorio, fecha y transformación. Desconocidos, vencidos, revocados, alcances incompatibles, releases faltantes y restricciones heredadas bloquean. DOCUMENTED y un ID upstream no acreditan autorización. Se conserva procedencia y linaje; ciclos, padres faltantes, IA documental y audio sin derechos aclarados bloquean.

## Fuentes oficiales y permiso concreto

Evaluación y adquisición: **2026-10-08**. La [página oficial USDA/ARS, Bell peppers D255-19](https://www.ars.usda.gov/oc/images/photos/featuredphoto/mar23/bell-peppers/) identifica al autor **Steve Ausmus, USDA Agricultural Research Service**, declara expresamente dominio público y enlaza el [JPEG obtenido](https://www.ars.usda.gov/ARSUserFiles/oc/images/photos/300dpi/kesa/D255-19.jpg). La [política oficial](https://www.ars.usda.gov/oc/images/copyright/) permite uso gratuito salvo indicación contraria, solicita crédito y prohíbe inferir respaldo ARS. Ambas páginas se comprobaron vigentes y se archivaron completas.

No hay versión legal numerada visible. Se registran literalmente sus pies Last Modified 11/6/2023 y 12/10/2020, respectivamente, sin reinterpretar el orden de fechas. Una URL o un VERIFIED del fixture no constituyen prueba: la autoridad es la declaración específica y política conservadas, vinculadas a los bytes.

| Archivo | SHA-256 |
|---|---|
| public/media/h3-pilot/usda-ars-d255-19.jpg | ffdb883d56a41ba9a03a51fb7d1bdf8f0b9e30d3946eda180b750620a17c3715 |
| docs/evidence/h3-pilot/usda-asset-page.html | 362db558cb6b2e96c00e390fe84b2541d711114934f62cf3d700111b8a694bd2 |
| docs/evidence/h3-pilot/usda-policy.html | 37f2a2fb164eab70ce65881a810828faf9ba3935dd7d3d6c21cd2d30e86973ac |
| docs/evidence/h3-pilot/review.md | a94ccf5caebfe48713763f3eb22dce7e765ded6c3c2f6777504c68059968030a |

La [adquisición](../fixtures/media/pilot/acquisition.json), el [inventario revisado](../fixtures/media/pilot/reviewed-inventory.json) y la [revisión](evidence/h3-pilot/review.md) preservan origen, documentos/versiones, autorización, hashes y límites. Hubo una transferencia puntual desde el enlace explícito, sin API, catálogo, cuenta, compra ni automatización recurrente. El replay es local.

| Alcance | Valor |
|---|---|
| Cliente / proyecto | 101-design-compiler-fixture-review / h3-restaurante-media-pilot |
| Negocio / scope | fixture-restaurante-001; ninguna sede real acreditada |
| Página / módulo | / / semantic-7bf9d33184f7e923438acadd |
| Necesidad / uso | need-7bacfc78bdb58db1dd06998a / h3-real-pilot-atmospheric |
| Finalidad / representación | ATMOSPHERIC, generic:atmosphere, GENERIC_CONTEXT |
| Territorio / transformación | CO; original sin recorte ni derivados |
| Crédito | Photo by Steve Ausmus, USDA Agricultural Research Service. |
| Etiqueta | Imagen atmosférica de pimientos; no documenta este negocio ficticio ni sus platos. |
| Restricción y aviso | NO_PROVIDER_ENDORSEMENT; USDA ARS no respalda este fixture, producto, empresa ni posición. |

Dominio público permite uso comercial según las fuentes. El grant interno se limita deliberadamente al piloto: otros clientes/proyectos, multicliente, reutilización, automatización y operaciones IA no están aprobados y permanecen UNKNOWN. Transformaciones y exclusividad son DENIED. No existe vencimiento declarado; adquisición gratuita, sin fabricar importe o moneda.

## Inspección y terceros

Revisión realizada el 2026-10-08T23:11:54Z: se abrió el JPEG local y se decodificó completamente, **2.351.102 bytes, RGB, 2700 × 1819**. Pimientos y follaje; no personas, edificios, logos o marcas visibles. Releases NOT_REQUIRED para este uso genérico limitado, sin afirmar documentos de release existentes. Es revisión de fuentes/archivo registrada por Codex, no certificación del titular ni dictamen jurídico.

Detalle suficiente para presentación sin recorte a 640 píxeles CSS. El fondo ocupado no certifica texto superpuesto ni otros crops. No se afirma que sean ingredientes, platos, instalaciones o productos del restaurante. Calidad y pertinencia se vinculan a este hash y rol. Derivados futuros requieren archivo/hash/revisión propios.

buildMediaManifest y validateMediaManifest validan consistencia semántica, **no autentican archivos ni revisores**. Para aceptar el cierre se exige además verifyPackageFiles: bytes originales/documentales/HTML/PNG/recibo, hashes, contexto, uso ALLOWED y vinculaciones de navegador. loadMediaPilot comprueba también declaración, autor, enlace y política archivados. Sin prueba de paquete, incluso REAL/VERIFIED y grant válido conservan cierre pendiente. Un hash acredita integridad, no autenticidad legal; las fuentes oficiales se comprobaron durante adquisición.

## Render mínimo

Ruta **/h3-media-pilot/**, figura de inspección sin composición H4 ni scripts cliente, con crédito, etiqueta, aviso, fuente y hueco documental visible. Edge **154.0.4258.62**, perfil aislado, decodificó 2700 × 1819, recibió el SHA esperado y mostró **640 × 431,15625 píxeles CSS**. Se comprobaron textos/visibilidad y se inspeccionó la [captura](evidence/h3-pilot/render.png). Corte del piloto: 2026-10-08T23:18:48.258Z.

| Evidencia | SHA-256 |
|---|---|
| [HTML](evidence/h3-pilot/render.html) | 584f76e853db29faa1617456ed00b7ef5b5ac0c9488470441a4648729a24c0e5 |
| [PNG](evidence/h3-pilot/render.png) | 8b88ee6b464011ded71d90b316b5167f4ab8be7e940acee1b4b26703a97a2156 |
| [Recibo](evidence/h3-pilot/render-receipt.json) | 77dfec2e3cf048e23c63667866e598fcde94957cd61966eb3b4dfc0be1b0af24 |

La [prueba sellada](../fixtures/media/pilot/package-proof.json) vincula todos los archivos al cliente/proyecto/fecha/uso. El build actual debe coincidir con el HTML archivado. Render y replay no acceden al proveedor.

## Pruebas y reproducción

Siete escenarios base: **22 necesidades, 22 huecos**. Dos controles sintéticos adicionales, bloqueados por defecto, sin licencias reales y siempre pendientes. Décimo output real-restaurante-pilot: **2 necesidades, 1 ALLOWED real, 1 hueco DOCUMENTARY**. Estos escenarios duplicados no son población de negocios independientes. Los escenarios iniciales conservan corte 2026-10-08T00:00:00Z.

Cobertura: permisos válidos/desconocidos/vencidos/revocados, otro cliente/proyecto/finalidad/página/sucursal, derivados y restricciones heredadas, IA, automatización, atribución, releases, audio/video, calidad/pertinencia desconocidas, representación engañosa y ledger corrupto. Se añaden pruebas de archivos/documentos/render alterados, cierre sin evidencia, pérdida de avisos, respaldo indebido y stock documental. No se mide precisión jurídica ni porcentaje de líneas.

Toolchain: Node 24.21.0, npm 11.19.0, Astro 7.3.7, Zod 4.6.5, TypeScript 6.0.3; sin dependencias nuevas.

| Verificación final | Resultado | Evidencia |
|---|---|---|
| Exportación | 18 schemas sincronizados | [log](evidence/h3-contracts-export.txt) |
| Tests | **232/232**, cero fallos | [log](evidence/h3-tests.txt) |
| Check | 0 errores/warnings/hints | [log](evidence/h3-check.txt) |
| Validación | 3 paquetes H0, 9 escenarios H2, 10 outputs H3 | [log](evidence/h3-validate.txt) |
| Build | 2 rutas estáticas del inspector | [log](evidence/h3-build.txt) |
| Generación/replay | 10 outputs idénticos byte por byte | [generación](evidence/h3-media-fixtures.txt), [replay](evidence/h3-media-replay.txt) |
| Paquete/render actual | Bytes, documentos, usos y HTML comprobados | [log](evidence/h3-pilot-verify.txt) |
| H0–H2 y lockfile | Sin modificaciones | [receipt](evidence/h3-verification.json) |

Reproducción offline: powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify-h3.ps1. Bypass se limita al proceso. Requiere Node 24 y dependencias del lockfile disponibles; no descarga medios ni realiza commits. Los tiempos de logs varían; el replay compara datos deterministas. .gitattributes preserva bytes HTML/JPEG y LF de documentos con hashes.

Captura opcional nueva con Edge: npm run build, npm run media:render, npm run media:seal, npm run media:fixtures, npm run media:replay, npm run media:verify. Una nueva captura modifica fecha/recibo y exige actualizar evidencia; no hace falta para verificar lo archivado.

## Límites y siguiente paso

El hueco documental necesita fotografía auténtica de offering-1, vinculación factual y autorización verificable del negocio/titular. Siguiente paso: recibir materiales de un caso real autorizado y revisar archivo, terceros y uso; no generarlos ni reemplazarlos con esta foto. Las demás necesidades/sedes siguen sin activos autorizados.

La [matriz oficial](h3-providers.md) separa comercial, multicliente, automatización, modificaciones, IA, atribución, releases, costos y restricciones. No hay conectores ni permiso comprobado de automatización. Cambios de términos, errores de revisión y terceros no visibles requieren reevaluación; no hay monitorización jurídica automática. 101-world-model sigue ausente. Sin H4, arte LLM, componentes definitivos, pagos, reservas o runtime comercial. **Trabajo detenido para revisión de H3.**

Reproducción de Git comprobada con checkout del índice y core.autocrlf=true: hashes de original, fuentes, revisión y render conservados; [evidencia](evidence/h3-git-repro.txt).
