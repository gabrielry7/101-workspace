# Investigación
- Google Cloud CLI 592.0.0 instalado desde archivo oficial con SHA256 publicado.
- Maps Management v2beta: StyleConfig(json_style_sheet), MapConfig(map_type VECTOR), MapContextConfig(map_config, style_config, map_variants ROADMAP). No método publish en API; asociación se verifica mediante readback y render real.
- Fuente: https://developers.google.com/maps/documentation/mapmanagement/guide-and-examples y referencia RPC oficial.
- Maps JS: servicio maps-backend.googleapis.com; Dynamic Maps US$7/1000 después de tramo gratuito según https://developers.google.com/maps/billing-and-pricing/pricing .
- Las cuotas diarias editables no se asumen: inspeccionar límites reales. La prueba limita cargas en aplicación y solicitudes del agente; las alertas de presupuesto no son un corte duro.
- Clave de navegador restringida por HTTP referrer/origen y API; OAuth sólo servidor local/gcloud.

## Resultados aplicados
- Proyecto dedicado activo y cuenta de facturación vinculada mediante gcloud.
- El readback real expuso `billable_default` con límite `1/d/{project}`; se creó
  override de 10 y se verificó `effectiveLimit=10`. No se inventó el nombre del recurso.
- Google normaliza el orden de las reglas del estilo. La comparación se hace por
  `id` y contenido, no por el orden accidental del array.
- Clave limitada a Maps JavaScript y puerto local 8780, con origen y `/*` explícitos.
- La configuración real funcionó con AdvancedMarker y estilo sin POIs. Headless
  avisó de WebGL no disponible y utilizó el fallback raster de Google.
- Dos cargas reales de verificación; cada auditoría reutilizó una instancia durante
  resize/zoom/pan. Contador persistente total=10 además de la cuota diaria de Google.
- Pin neutro: el paquete retenido no aporta logo con permisos suficientes. No se
  fabrican attestations. La aprobación humana permanece pendiente.
- Evidencia y recibo público: [honorato-google.md](../../docs/bones/honorato-google.md).
