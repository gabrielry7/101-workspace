# Revisión independiente H7 — entrega inicial

**FAIL — corrección acotada de landmark en `/h7/` antes de avanzar.** Commit auditado `3c8abc53797ede3b8cdebdf901c968beec0c6407`; reserva previa `3ff5356`. HEAD coincidía y Git estaba limpio al iniciar. Revisor nativo `/root/revisor`, con exclusividad de outputs; no modificó implementación ni coordinación.

## Hallazgo que exige corrección

**H7-R1, severidad media: dos landmarks main anidados en la entrada del laboratorio.** `src/pages/h7/index.astro` envuelve el contenido con `<main id="main">`, mientras `src/layouts/Foundation.astro` ya aporta `<main id="contenido">`. El build de `/h7/` conserva ambos. La comprobación real en Edge encuentra `main_count: 2`, `nested_main: true`, IDs `contenido`/`main` y **dos roles main no ignorados en AX tree**. [Sonda reproducible](h7/index-probe-source.txt), [resultado](h7/index-probe.json).

Corrección requerida: mantener un único main mediante Foundation y cambiar/eliminar el wrapper de la página. Verificar la entrada `/h7/` en desktop/móvil con un main y h1, skip link visible/activable al contenido y enlaces alcanzables por teclado. Añadir esa ruta al QA de entrada para evitar que las 60 vistas de candidatos dejen fuera la regresión. No requiere alterar datos, contratos ni arquitectura.

## Comprobaciones que pasan

`scripts/verify-h7.ps1`: **279/279 pruebas**, check **0 errores/warnings/hints**, build **90 páginas**, replays y verificadores H3–H7 correctos. [Log propio](h7/verification.txt). El fallo del índice queda fuera de esa cobertura existente; por eso esos PASS no bastan para el veredicto del hito.

Se inspeccionaron informe, diff, reserva, primera evaluación, inputs/propuestas/provenance, registry/proyección/componentes, versiones artísticas, nullable media, calendario, observador/gates y scripts/tests. Se recapturó el harness en un directorio propio: **60 vistas técnicas PASS**, **3 negativos sembrados FAIL esperados**, diez planes y cinco contextos. Se repitió decodificación y raster de los **63 PNG**, cobertura por ruta/viewport, bindings y selección. [Run propio](h7/run.json), [log browser](h7/browser-run.txt), [replay](h7/independent-replay.txt). Las copias de fuente se archivan como texto: [browser](h7/audit-h7-source.txt), [verificador](h7/verify-h7-source.txt). La evidencia histórica y de entrega H7 quedó intacta.

Cuatro sondas adicionales del revisor pasan: [resultado](h7/probes.json), [fuente](h7/probes-source.txt).

| Criterio | Resultado comprobado |
|---|---|
| Reserva y primera exposición | Los seis JSON y reservation permanecen iguales a `3ff5356`; hashes validados por consumidor y Git diff vacío. Planner/taxonomy intactos. Código de proyección/registry de ese commit cargado aisladamente reproduce **1 PASS / 4 FAIL**, Unknown bloqueado. [Código baseline](h7/baseline-content-source.txt), [registry baseline](h7/baseline-registry-source.txt). Resultados semánticos iniciales iguales a actuales. |
| Cohorte y componentes genéricos | Hotel/lodging; dentista/appointment_service+regulated_services; domicilio/field_service_and_quote; híbrido/membership_and_classes+product_retail; media desconocida. FactCollection y Schedule amplían registry compartido; renderer/search no bifurcan por negocio/arquetipo. Autoría de conceptos/tokens por caso queda en recorder de datos, no código desplegado específico. |
| Cobertura y scopes | Dos finalistas por contexto, todas las rutas y módulos obligatorios preservados. Auditoría DOM verifica textos/IDs/bindings. Sonda propia de scope ajeno rechaza. Location_information tiene entrada genérica pero no se acredita cobertura browser aquí. |
| Calendario | `class_starts_at` y timezone aparecen en DOM y `<time>`; cambios de fecha/zone inválidos no sobreviven como módulo de clase al planner. Representación estática sin inscripción ni backend. |
| Materialidad coherente | Los cinco contextos usan `ArtDirectionV1_1` explícita **1.1.0 typography-only**, sin refs ni imágenes. Contrato/schema histórico 1.0 permanece intacto. Photograph materiality con medio null rechaza antes de render en todos los contextos, sin reinterpretación documental. |
| Medios ausentes/desconocidos | Media null válido; no se presta grant H3. UNKNOWN conserva inventario e intento de usage sin grant, decisión no ALLOWED y gap visible. URI no descargada. Imagen DOM no vinculada dispara MEDIA_WITHOUT_AUTHORIZATION. |
| Unknown | CONTENT_BLOCKED, sin lab/search ni sitio falso identity-only. El índice expone el bloqueo, aunque su landmark necesita la corrección indicada. |
| Preservación y costos | H3–H6 actuales verifican sin recapturar históricos; cero dependencias nuevas/lockfile cambiado/API/media/gasto nuevo. Tiempo observado es corrida browser, tokens/costo monetario de sesión no medidos. Sin métricas p75/beauty/preferencia fabricadas. |

Se inspeccionaron seis capturas nuevas: hotel Flow/Rail desktop, dentista servicios móvil, domicilio cobertura desktop, híbrido calendario móvil y media-unknown servicios móvil. Contenido y límites visibles, sin fotos/acciones operativas, con diversidad estructural desktop de navegación/frame; móvil apila y no se acredita diversidad estructural móvil. Labels de capabilities en inglés son propios del laboratorio, no contenido aprobado inventado.

## Límites y decisión

La cohorte es sintética y ya expuesta tras ajuste; no prueba generalización externa inédita ni sitios de negocios reales. Preferencia humana NOT_COLLECTED, runtime comercial ausente, sin campo p75/red real/accesibilidad exhaustiva. El campo `commercial_audit` de recibos H7 reutiliza la política LAB; no debe interpretarse como prueba de un perfil COMMERCIAL independiente. Informe y gates no afirman producción.

Se repitieron rebuild/replays/recaptura propia y se examinó el clean-index de entrega; no se repitió una segunda reconstrucción CRLF aislada. La auditoría conserva los PASS de candidatos, pero **no permite H8 hasta corregir H7-R1 y reauditar el commit corregido**. No se modifica implementación desde la revisión.
