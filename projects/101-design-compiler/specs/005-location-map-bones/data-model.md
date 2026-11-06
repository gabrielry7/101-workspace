# Modelo de datos

`Location`: contrato original inmutable (business_id, location_id, nombre,
dirección, Google listing, coordinate/purpose/source, binding, publication_allowed).
No se convierte una cámara de revisión en coordenada de negocio.

`LogoEvidence`: asset/grant/usage/inventory/evaluatedAt; rightsGate y suitability
devuelven binding de imagen local autorizada o motivo de pin neutro. La evaluación
comprueba business_id/scope_id de la sucursal. Fixtures requieren opt-in sintético.

`LocationBone`: ID/versión, variante direct/map-led/editorial, partes y estados.
`Skin`: neutral/paper/ink, colores acotados del mapa, logo; nunca coordenadas/POIs.
`Instance`: location + variante + piel + logo binding + proveedor + configuración
Google opcional; recuperación no altera datos ni capacidades.

Estados: fallback → loading → ready; error de imagen conserva ready/pin;
fallo de proveedor → degraded; destroy es terminal. Carga asíncrona destruida no monta.
Inspección registra marcador efectivo, anclaje, POIs, datos y tipo de verificación.
