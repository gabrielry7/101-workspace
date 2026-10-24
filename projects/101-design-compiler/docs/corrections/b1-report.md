# B1 — catálogo maestro y comprensión contextual

Fecha de trabajo: 2026-10-12, America/Bogota; recibos en UTC del 2026-10-13. Base `0fa10bc08f5ef47b499af125c80378087e7ed0de`; rama `codex/corrections-b1-catalog-context`.

**B1 implementado para revisión técnica y humana.** El motor dispone de un catálogo único de requisitos y puede interpretar categorías, descripción y ofertas aprobadas sin convertir esa interpretación en una operación confirmada. El usuario autorizó implementar este bloque mediante «Apruebo B1» directamente en la tarea implementadora `01a11b10-d0bd-7c43-b76d-45f7a03d8574`; eso no se interpreta como aceptación de su resultado posterior ni de una web final. B2/H3 adicional, diseño, pagos, reservas conectadas, producción y H10 no se iniciaron.

**Revisión inicial de `4360282`: requiere corrección.** Se detectaron dos defectos: planner-replay escribía los archivos H2 y un precio no vinculado activaba un faltante de moneda. Los resultados originales de este informe corresponden a esa primera entrega; la corrección, sus límites y pruebas adicionales están en [b1-r1-report.md](b1-r1-report.md). La igualdad previa de bytes no demuestra que el procedimiento fuera de sólo lectura.

La reauditoría confirmó R1 y encontró una tercera condición incorrecta: un medio presente se trataba como utilizado. La entrega más reciente y sus pruebas están en [b1-r2-report.md](b1-r2-report.md); se conservan los informes/recibos de las versiones anteriores.

## Cómo revisarlo

Abrir [inspector B1](http://127.0.0.1:4331/b1/), [restaurante](http://127.0.0.1:4331/b1/restaurante/) y [catálogo maestro](http://127.0.0.1:4331/b1/catalogo/). El servidor Astro local fue comprobado con HTTP 200; necesita seguir ejecutándose para abrir estos enlaces.

En el restaurante: revisar «Qué entiende el motor», abrir las evidencias, elegir Sucursal 1 y comparar los cuatro niveles de Reservas. Cada nivel muestra todos los faltantes, responsable y siguiente paso. Los datos ya disponibles aparecen después. «Datos que pediría esta función al visitante» especifica campos de una operación futura, no solicita datos personales en B1.

El caso [reserva-enlace](http://127.0.0.1:4331/b1/reserva-enlace/) demuestra que una intención de enlace externo no es una mesa confirmada. [Sucursales](http://127.0.0.1:4331/b1/sucursales/) distingue gastronomía de alojamiento y conserva menú sólo donde tiene respaldo. Los ejemplos son sintéticos; no representan negocios autorizados reales ni aprobación estética.

## Catálogo y diagnóstico

[catalog.ts](../../src/requirements/catalog.ts) define 47 fichas, 107 niveles y 208 requisitos reutilizables. Las fichas toman selector, módulo, objetos, arquetipos y dependencias del registry H2. Los grupos orientan qué investigar; no son plantillas visuales ni confirman servicios. Todos los restaurantes consultan la misma definición; cambian datos, evidencia, decisiones y alcance.

Cada nivel especifica comportamiento, datos/evidencias/permisos/configuración, responsable, condiciones, dependencias, estados y criterios de aceptación. Distingue SPECIFIED, primitiva informativa LAB, intención semántica de enlace y especificación futura. Todos conservan backend NOT_CONNECTED y verificación operacional pendiente. Que exista una primitiva compartida no acredita cada función o todos sus niveles en producción.

Reservas separa contacto, solicitud, enlace externo y confirmación conectada. La confirmación necesita reglas/turnos/zona horaria/capacidad/disponibilidad/límites/confirmación/cancelación/privacidad, autorización y configuración del sistema, frontend y backend comprobados. Un sistema conectado no exige necesariamente un enlace público externo: esa exigencia pertenece al nivel external_link. La configuración futura sólo refiere autenticación privada; no almacena secretos. Los campos de visitantes se describen por separado del formulario/configuración que debe preparar la plataforma.

FunctionalDiagnosticV1 conserva el inventario aunque H2 se detenga en su primer bloqueo. Hay 47 entradas de negocio y 45 por sucursal: identidad y directorio de sucursales son globales. UNKNOWN, WITHHELD, CONFLICTED, vencido, falta de datos, soporte y permiso pendiente tienen resultados separados. No aplicable o rechazado requieren una decisión respaldada, exacta y vigente; ausencia factual no equivale a no aplicable. Una decisión que ocultaría un módulo ya emitido se rechaza como conflicto, sin alterar el planner ni inventar ausencia de la capacidad.

Importes/moneda y detalles de colecciones se evalúan por oferta vinculada: otro producto, profesional o sucursal no rellena el dato faltante. Se conserva la herencia factual explícita de H0 cuando un objeto referencia un hecho global; sólo identidad comparte dependencia entre sucursales. Los medios existentes no se consideran bytes inspeccionados ni derechos verificados. DOCUMENTED y IDs de documentos siguen pendientes de H3.

La [matriz B1](b1-matrix.md) relaciona H0-C01…C06 y H1-C01…C04 con implementación y evidencia. El catálogo cubre todo el vocabulario V1 disponible; no se anuncia como inventario definitivo de cualquier funcionalidad futura.

## Interpretación contextual y compatibilidad

[context.ts](../../src/taxonomy/context.ts) conserva categorías originales, alternativas, señales/ref IDs, scope, motivos de exclusión, evaluación temporal y solicitud concreta de aclaración. Usa evidencia aprobada/vigente, ofertas de tipos válidos y una política finita de sujetos ES/EN; nombres sugestivos o palabras sobre negocios cercanos no bastan. Se prueban negaciones, afirmaciones contradictorias, texto de convivencia explícita y alternativas con «o». La convivencia puede sustentarse en una descripción aprobada del mismo sujeto, además de links de actividad respaldados.

La política interpreta 13 modelos de negocio por descripciones explícitas; regulated_services es un modificador con respaldo independiente, no una licencia inferida. Texto no soportado queda registrado y puede requerir una afirmación más precisa. No es un modelo lingüístico universal ni una medida de precisión con datos reales. No llama LLM ni procesa imágenes/audio/video. Observaciones textuales de recursos aprobadas por upstream son hechos recibidos, no inspección realizada por este compilador. URLs, nombres de archivos y dimensiones no aportan actividad o permisos.

Los artefactos nuevos están asociados en `contracts/requirements/v1` y `contracts/taxonomy/context-v1`: diez esquemas JSON exportados y comprobados contra Zod. BusinessInputV1, BusinessProfileV1, CapabilityProfileV1, SitePlanV1 y el protocolo upstream permanecen sin cambios. El perfil contextual usa confidence=0 como sentinel de compatibilidad V1; el artefacto nuevo declara calibrated_confidence=null. No se presenta ese cero como probabilidad medida.

El único ajuste H2 es una opción explícita `classification_mode: 'CONTEXTUAL_V1'`, con vínculo al hash de la interpretación. Sin ella se conserva el resultado anterior: nueve fixtures H2 se comparan íntegramente con los derivados históricos. No se reescriben planificación, dependencias, publicación, alcance, validadores o estados de backend. READY conserva su significado de plan válido de lo emitible, no objetivo completo ni integración conectada.

## Pruebas y evidencia

| Comprobación | Resultado final |
| --- | --- |
| Baseline previo | 304/305; único FAIL histórico LOCK_BROWSER_MISMATCH. Resto de checks/replays pertinentes PASS. |
| Suite final | 344/345; 40 pruebas B1 PASS, un fallo histórico de navegador. No se declara suite completamente verde. |
| Check / validate / build | PASS; cero errores, advertencias o hints; 103 páginas. |
| Exportación de contratos | PASS; diez esquemas nuevos, sin cambios en los anteriores. |
| B1 replay y validación semántica | PASS; 11 casos con resultados/hashes reproducibles y diagnósticos recalculados. |
| H2/taxonomía/medios/composición/diseños/auditoría/cohorte | Replays y verificadores PASS; preservación histórica sin redecisión ni adquisición. |
| lock:verify -- --rebuild | BLOCKED_HISTORICAL_ENVIRONMENT: Edge global actualizado, como B0. |
| QA navegador final | 28 vistas: 13 rutas desktop/mobile más reserva expandida en ambas. Bindings completos, un main/h1, skip/disclosure/navegación, legibilidad y ausencia de overflow. |
| HTML histórico H8 | 16 referencias de originales coinciden por bytes en el build nuevo. No es una nueva prueba de rollback ni aprobación integral H8. |
| Preservación | 1.330 archivos protegidos sin cambios; únicas fuentes anteriores modificadas deliberadamente: planner/plan.ts y export-contracts.ts. |
| H9 inventory | Verificado; benchmark BLOCKED/NOT_TESTED, cero sitios reales aprobados elegibles y p50/p90 null. |

La corrida final es [post-07/journal.json](../evidence/corrections/b1/post-07/journal.json). La captura actual es [browser-04/qa.json](../evidence/corrections/b1/browser-04/qa.json). `b1-verify.ts` recalcula diagnósticos, valida cobertura, logs, hashes PNG/HTML/RGBA, DOM de requisitos, gates, equivalencia histórica, runtime y preservación. La suite nueva incluye cobertura de registry/versiones, requisitos borrados, corrupción de diagnóstico, scopes, UNKNOWN con contexto, híbridos/alternativas/negaciones/proximidad, vencimiento/withholding, tipos, medios no inspeccionados y backend ficticio.

La copia final repite 344/345 tests, check/validate/build/replays y las 28 vistas: [clean-final/journal.json](../evidence/corrections/b1/clean-final/journal.json) y [clean-final-browser/qa.json](../evidence/corrections/b1/clean-final-browser/qa.json). El comparador auxiliar añadido después de materializar las fuentes del motor verifica 28 pares con HTML, RGBA y observables funcionales idénticos. Los recibos de comprobación final están en [final/journal.json](../evidence/corrections/b1/final/journal.json).

La copia limpia final materializa el árbol preparado `dae0315178b6054990b92039075a3de4b03d36ac` antes de informes/recibos nuevos. Usa `git -c core.autocrlf=false archive` y junctions a Node/dependencias/browser cuyos bytes se verifican. Fuentes, perfiles y builds son separados. Esto verifica reproducción en el mismo host/fuentes/OS, no instalación fresca o portabilidad. Recibos finales limpios y comparación de capturas se conservan en la entrega; el materializado anterior fue una corrida de un candidato previo, no cierre de la versión final.

El navegador reutiliza el harness compartido y la copia Edge 154 de B0. Conserva su excepción explícita --no-sandbox para páginas locales fijas; no se utiliza para proveedores. Se guardan todas las capturas completas y observaciones automatizadas. Las muestras manuales son adicionales y sólo de viewport; no se afirma revisión humana de cada campo oculto ni una auditoría WCAG completa.

Las [muestras de entrega](../evidence/corrections/b1/visual-delivery/views.json) incluyen restaurante desktop/móvil, reserva abierta y catálogo móvil. La geometría final no detectó overflow; la tipografía visible mínima fue 13,6 px y el contraste mínimo observado superó 6,8:1. Las primeras muestras se conservaron para mostrar el cambio a faltantes primero. Estas mediciones locales no equivalen a aceptación estética humana.

La superficie es un inspector técnico: mantiene en HTML el inventario completo y puede rondar 2 MB sin imágenes ni JavaScript del cliente. No es presupuesto ni rendimiento de un sitio comercial; LCP/INP/CLS de campo y calidad estética final no se midieron. Esta densidad es un límite de la revisión, no evidencia de páginas finales de calidad. El runtime comercial y 101-world-model siguen ausentes.

## Correcciones y límites de las corridas

Se conservaron primeras pruebas y fallos: dos supuestos erróneos en tests dirigidos; resolución de archivos relativa a import.meta.url que fallaba al prerenderizar; propiedad duplicada de traducción; reconocimiento de un negocio cercano al extender conjunciones. Se corrigieron sin relajar gates o cambiar evidencia histórica. La corrida post-04 tiene dos fallos de tests, incluido el nuevo: el marcador de bloqueo del journal compartido no sustituye el conteo/exit real; el runner la rechazó y las corridas finales sólo aceptan el único fallo histórico conocido.

Las primeras capturas motivaron poner faltantes primero y excluir correctamente descendientes de detalles cerrados de las mediciones de visibilidad. Después se completó la especificación de campos del visitante y de integración futura. Recibos anteriores identifican versiones de trabajo; el verificador de la entrega usa la última corrida. El primer QA grande se conserva comprimido sin pérdida en [qa.json.gz](../evidence/corrections/b1/browser-01/qa.json.gz), con hashes y tamaño original en archive.json; no se incluye su duplicado temporal partial.json ni perfiles/builds/dependencias.

Todos los inputs de prueba son SYNTHETIC_FIXTURE con procedencia explícita. No se fabricaron negocios reales, autorizaciones, inspección de archivos, releases, autenticación de proveedor, aprobación estética, datos personales, tarifas, tokens o costos totales. Se mide duración de máquina de comandos/capturas; tiempo humano, costo total, moneda y tokens siguen null. No se usa ese inventario para calcular H9.

H3 original conserva permisos y bytes: JPEG atmosférico `ffdb883d56a41ba9a03a51fb7d1bdf8f0b9e30d3946eda180b750620a17c3715`; el hueco documental sigue bloqueado. B1 no reevaluó términos legales ni amplió su uso. La clave de Pixabay no se usó ni guardó.

## Reproducción y parada

Desde la raíz, con Node portable/dependencias existentes:

```powershell
$node = '.tools/node-v24.21.0-win-x64/node.exe'
& $node --experimental-strip-types scripts/b1-fixtures.ts --verify
& $node --experimental-strip-types scripts/b1-run.ts nuevo-baseline
& $node --experimental-strip-types scripts/b1-qa.ts nueva-captura
& $node --experimental-strip-types scripts/b1-verify.ts nueva-captura nuevo-baseline
```

IDs nuevos evitan sobrescribir evidencia. El runner conserva salidas 1 de tests/lock históricos y falla ante errores adicionales; no transforma los comandos subyacentes en PASS. Para abrir el inspector: Node ejecuta `node_modules/astro/bin/astro.mjs preview --host 127.0.0.1 --port 4331` después del build.

Se entrega commit/informe/pruebas al revisor autorizado y se espera feedback/prompt propuesto. La aprobación independiente y el acuse se comunican por separado; este documento no los presume. Detención al terminar B1: revisión humana del catálogo y diagnóstico; B2 requiere autorización nueva antes de adquisición audiovisual u otro bloque.
