# Protocolo candidato de entrada upstream 1.0.0

Frontera futura: `101-world-model → adapter versionado → UpstreamEnvelopeV1 → validación local → clasificación`. No se conectó el otro computador, no se implementó su adapter SiteSpec, no hay transporte/red/base de datos ni modificación de su autoridad Truth.

## Versionado y compatibilidad

El sobre lleva `protocol_version: 1.0.0`; su payload es **exactamente BusinessInputV1 1.0.0 de H0**. Los cuatro esquemas, tipos y fixtures H0 permanecen intactos. Jerarquía/procedencia y relaciones de actividad viajan en sidecars, sin introducir campos que rompan lectores estrictos V1. Los JSON Schema se exportan a `contracts/upstream/v1/` y `contracts/taxonomy/v1/`.

Se rechazan versiones desconocidas y campos adicionales. `producer.source_schema`, `source_schema_version` y `source_revision` preservan identificadores del productor real: no se presupone versión de SiteSpec. `adapter_version` identifica la traducción acordada, independiente del esquema fuente. Actualmente solo se valida la propuesta 1.0.0; no hay migraciones implícitas ni adapter real probado.

## Sobre

| Campo | Responsabilidad |
|---|---|
| protocol_version | Versión exacta de este protocolo |
| message_id | ID estable del productor para el envío; no generar hechos nuevos en retries |
| producer | Sistema 101-world-model, esquema/revisión de origen, versión del adapter |
| produced_at | Fecha de emisión, posterior o igual al corte factual |
| business_input_sha256 | SHA256 del payload canónico definido abajo |
| business_input | Identidad, snapshots, categorías/evidencia, sedes, oferta, estados operativos, publicación, medios/restricciones; autoridad upstream |
| category_context | Un registro por category_observation_id, con literal/código/normalización/evidence IDs iguales al payload, jerarquía y procedencia |
| activity_relationships | Relaciones COEXISTING/ALTERNATIVE expresamente sustentadas; no capacidades operativas |

Provenance por categoría: `source_record_id`, fuente literal, fecha de observación y URI opcional. Una referencia al inventario puede añadir ID/hash del archivo; no establece un negocio real por pertenecer a una fila agregada. La fuente debe coincidir con la observación y la fecha no superar el corte. Las URIs son metadata, no se descargan ni se ejecutan, y no transfieren derechos de medios.

## Uso local

```ts
import { validateUpstreamEnvelope } from '../src/upstream/v1/protocol.ts';
import { classifyBusiness } from '../src/taxonomy/resolve.ts';
import { loadMappingRegistry } from '../scripts/load-taxonomy.ts';

const accepted = validateUpstreamEnvelope(receivedJson);
if (!accepted.success || !accepted.data) {
  // Devolver accepted.diagnostics, sin corregir hechos ni ejecutar contenido.
} else {
  const registry = await loadMappingRegistry();
  const classification = classifyBusiness(accepted.data.business_input, {
    rules: registry.rules,
    category_context: accepted.data.category_context,
    activity_relationships: accepted.data.activity_relationships,
  });
  // classification.profile cumple BusinessProfileV1 de H0.
  // classification.candidate_capabilities solo representa relevancia.
}
```

`receivedJson` es una variable del futuro consumidor; este ejemplo no configura un endpoint. Los mensajes de tests se construyen desde fixtures H0, identificando origen/esquema como sintéticos. El modo predeterminado rechaza `SYNTHETIC_FIXTURE`; tests deben optar explícitamente por `{allow_synthetic: true}`.

## Checksum y replays

`canonicalJson`: ordenar recursivamente claves de objetos con `Object.keys().sort()`, conservar orden de arrays, serializar strings/boolean/null/números finitos con JSON.stringify y no aceptar undefined ni valores fuera de JSON. UTF-8 del resultado → SHA256 hexadecimal minúsculo. Es una receta propia versionada y probada, **no una afirmación de conformidad RFC 8785 ni una firma**. `inputSha256` implementa exactamente esa receta; no reordenar arrays o normalizar strings antes de cotejar el checksum.

El futuro receptor persistente debe retener message_id/hash/snapshot/revisión y diagnosticar mismo ID con otro contenido; un retry idéntico debería ser idempotente. H1 valida integridad del payload de forma stateless; no implementa almacenamiento, deduplicación de envíos ni detección de collisions entre llamadas. Si se requiere autenticación/firma/transporte, acordarla al integrar, sin confundir checksum con autorización factual.

## Autoridades y guardas

Upstream decide publicabilidad y vigencia. Los estados PRESENT/ABSENT requieren referencias aprobadas a una afirmación específica `capability:<id>` con valor true/false, además de scope correcto. Es una **proyección de contrato** de las decisiones reales; el adapter deberá traducir explícitamente PublicationDecision/Truth sin inventar una confirmación. UNKNOWN/CONFLICTED/WITHHELD se conservan. Una categoría o arquetipo jamás reemplaza esa afirmación.

Se comprueban estructura, IDs, referencias, scopes, corte/fechas, identidad publicable, checksum, evidencia de capabilities, metadata de derechos y sidecars. Una oferta withheld/conflictiva puede viajar como dato conocido sin elevar su autorización. El publisher/planner posterior debe bloquearla al representar contenido: aceptar el paquete no habilita todos sus hechos.

Las capacidades reales siguen en input sin mutación. No se producen CapabilityProfile/SitePlan desde categorías, no se declara soporte frontend ni conectividad. No hay integración operativa ni activación de reservas, delivery, compras, membresías o servicios.

## Errores y acuerdo pendiente

Diagnósticos estructurados `code/path/message`: PROTOCOL_SCHEMA_INVALID, SYNTHETIC_INPUT_REJECTED, INPUT_HASH_MISMATCH, INVALID_PRODUCTION_TIME, DUPLICATE_ID, UNKNOWN_FACT, UNKNOWN_SCOPE, SCOPE_MISMATCH, IDENTITY_NOT_PUBLISHABLE, FUTURE_EVIDENCE, INVALID_VALIDITY, UNVERIFIED_CAPABILITY, CATEGORY_CONTEXT_MISMATCH, MISSING_CATEGORY_CONTEXT, INVALID_PROVENANCE, HIERARCHY_MISMATCH, UNKNOWN_RELATIONSHIP_CATEGORY, UNVERIFIED_ACTIVITY_RELATIONSHIP y MISSING_RIGHTS_REFERENCE.

Pendientes antes de integración: contratos y snapshots SiteSpec reales; cómo preservar PublicationDecision completo/expiración/conflictos; namespaces estables; alcance de sucursal/marca; aliases comerciales sin coerción; fuente/fecha de jerarquías; adapter/protocolo de errores del productor; autenticación y reintentos; actualizaciones y retirada de permisos. No se anuncia compatibilidad probada con 101-world-model hasta ejecutar pruebas reales de productor/consumidor sobre su revisión exacta.
