# Contrato de componente 0.1.0

Astro: `input` ligado por `bindLocationBone(owner, location, logoEvidence)`, id único,
variant, skin, runtimeURL local opcional, provider maplibre/google_js, basemap y
google opcionales. Sin runtime, SSR sigue útil.
No acepta callbacks/HTML externo en datos. El entrypoint confiable conecta el dueño.

Runtime: mountSingleBusinessLocation(root, config, owner) → inspect, setPresentation,
destroy. `owner` contiene la API nativa y los contratos originales. POIs sólo none;
presentación no puede incluir coordinate/provider/contextPreview/decorateMap.
Google exige enabled, apiKey, mapId y styleReview con referencia/fecha/POIs ocultos;
el registro de revisión no equivale a comprobación remota del estilo.

Inspección: versión, source/expected_coordinate/marker_coordinate, provider,
state/reason, marker_kind/logo_reason, marker_anchor_offset_px, rendered_poi_ids,
verification (native/mock/live-unverified), publication_allowed. Nunca serializar
claves, documentos de derechos o evidencias privadas en reportes.
