# Arquitectura y decisiones técnicas de H0

## Una frontera de datos, un shell Astro

Flujo actual: `JSON fixture manual → contratos Zod → validación de referencias/estados → inspector Astro estático`. No hay router de actividad, planner semántico, compositor, renderer comercial ni generador de proyectos por cliente. La única aplicación es este proyecto Astro. El futuro compiler consumirá estos contratos y se adaptará al runtime 101 cuando se pueda verificar su API.

Los datos de prueba no establecen hechos de negocios reales. Los perfiles y planes también son manuales. No llamar «resuelto automáticamente» a `RESOLVED` en un fixture; es una condición de prueba declarada.

## Decisiones

1. **Astro + TypeScript, HTML/CSS primero.** Shell sin JavaScript de cliente, fuentes remotas o UI libraries. No React, Tailwind, DB, API server o monorepo vacío. Fuente de instalación: [documentación oficial Astro](https://docs.astro.build/en/install-and-setup/). Versiones exactas verificadas en package-lock, no selección a cargo de cada sitio.
2. **Zod como fuente única.** Types mediante `z.infer`; exportación JSON Schema 2020-12 para futuros consumidores ajenos a TypeScript. Exportar no equivale a integrar. Guardas entre documentos permanecen en el validador semántico y no se representan por el esquema estructural. No duplicar tipos a mano.
3. **Node 24 LTS, node:test.** Ejecución directa de TS sin build de pruebas, con imports `.ts` y sin sintaxis que requiera transformación. Evita tsx, Vitest y Jest. Node portable oficial local, SHA256 verificado, sin instalación global. [Distribución oficial Node](https://nodejs.org/en/download).
4. **Fact references con autoridad upstream.** `publication_decision_id`, origen, fecha, scope y estado son una proyección contractual, no un nuevo motor Truth. H0 reconoce `capability:<id>` booleano como afirmación sintética específica; el adapter debe traducir explícitamente decisiones upstream reales a esta proyección o acordar una revisión del contrato.
5. **Estado factual independiente del estado técnico.** Cinco estados de evidencia; frontend y backend separados. Todos los fixtures declaran NOT_SUPPORTED_YET y BACKEND_NOT_CONNECTED. Un módulo en SitePlan representa una obligación futura, no acredita implementación de UI.
6. **Identidad de snapshot y alcance explícitos.** Cada artefacto porta versión/business/snapshot y referencias a perfiles. Scope de negocio o branch ID existente. Un hecho de negocio puede servir a una sucursal, pero jamás se hereda la confirmación de una capability de marca como confirmación de sucursal sin estado explícito. Revisar política de herencia con upstream.
7. **Sin estética dentro de SitePlan.** Esquemas estrictos rechazan campos extra como CSS, JS o layout. Los operadores, tokens y arte LLM llegan en DesignPlan/ArtDirection posteriores. Ninguna categoría contiene una elección visual.
8. **Tiempo determinista.** Validación por defecto al corte `input.as_of` para fixtures congelados; consumidores deben suministrar fecha explícita al validar frescura para entrega real. El instante debe ser posterior o igual al corte. No se consulta el reloj escondidamente ni se afirma vigencia actual desde un replay histórico.

## Contratos candidatos 1.0.0

| Contrato | Autoridad / contenido |
|---|---|
| BusinessInputV1 | Upstream: identidad, hechos y decisiones, categorías originales, sedes, ofertas tipadas, estados operativos, destinos, metadata de medios, restricciones |
| BusinessProfileV1 | Interpretación: arquetipos combinables, evidencia/referencias, clasificación o abstención, capacidades candidatas y datos faltantes; sin nueva verdad |
| CapabilityProfileV1 | Estado y evidencia preservados, bindings de ofertas/destinos y ejes de soporte frontend/backend |
| SitePlanV1 | Rutas con contenido, módulos semánticos con bindings y scope, estados de presentación, exclusiones y referencias a perfiles; sin arte |

El sufijo V1 y `schema_version: 1.0.0` identifican una **propuesta local candidata**, no un protocolo ya ratificado con upstream. Se acepta únicamente la versión exacta implementada. Cambios incompatibles requieren una nueva versión mayor, fixtures y migración explícita; cambios aditivos requieren versión menor y soporte consciente de lectores estrictos; correcciones sin cambio del conjunto aceptado pueden incrementar patch. No reescribir silenciosamente fixtures v1 al introducir V2. Cada cambio aceptado debe actualizar esquema exportado, tests y esta decisión.

Los enums de capabilities son nombres de contrato previstos, no un registry implementado. La pequeña matriz de tipos de oferta en `validate.ts` existe para detectar errores de contrato de los fixtures; no selecciona módulos ni rutas. El catálogo completo de reglas se desarrolla en H2. Nombres de proveedores/categorías se conservan abiertos; capabilities nuevas requieren revisión contractual.

Campos desconocidos se rechazan. Campos opcionales no se rellenan; ausencia de precio no es precio cero. Identidades/valores/sesiones de los fixtures son etiquetas genéricas de prueba, sin direcciones, teléfonos, precios ni medios falsamente atribuidos. Las ofertas no cubren todavía toda la diversidad futura (variants, amenidades, paquetes y tarifas); ampliar mediante contratos acordados en H1/H2.

## Guardas implementadas y límites

Se valida estructura, versiones, referencias, snapshots, scopes, evidencia de confirmación, publicación y vigencia, ofertas incompatibles, módulos vacíos, exclusiones, rutas duplicadas, acciones HTTPS y estados falsamente conectados. Los errores incluyen `code`, `path`, `message`. UNKNOWN no es falso ni verdadero; un gimnasio puede tener retail si los datos lo respaldan.

No se verifica autenticidad de fuentes, veracidad del mundo real, firmas de decisiones, licencia efectiva, contenido DOM de clientes, destinos remotos, accesibilidad completa, performance real ni excelencia visual. Fact kinds de la entrada se conservan abiertos para no bloquear futuros upstream; los bindings críticos comprueban los kinds mínimos conocidos. Un `rights_status: DOCUMENTED` necesita referencias documentales pero no habilita render de medios. Estos controles son guardas de contrato, no certificación upstream.

## Protocolo para futura integración

Obtener contratos y snapshots reales de `101-world-model`; registrar commit y consumidor/runtime. Acordar IDs estables, alcance de marca/sucursal, estados, caducidad, campos withheld/conflictivos y vocabulario comercial. Construir **un adapter versionado** desde SiteSpec con pérdida de información explícita y reporte de incompatibilidades. Ejecutar pruebas productor/consumidor y de no-inferencia; no conectar extracción, pagos o reservas para validar un contrato. Preservar trazabilidad hasta DOM posteriormente, sin reutilizar permisos de media implícitos por disponer de URL.

ArtDirectionV1, DesignPlanV1, SiteRequirementsV1, MediaManifestV1, AuditReportV1 y DesignLockV1 están **pendientes**. No existen implementaciones vacías que sugieran que ya funcionan.
