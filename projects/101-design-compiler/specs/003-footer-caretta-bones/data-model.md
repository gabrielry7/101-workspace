# Datos y relaciones

- FooterContent: schemaVersion, source, brand, description, assistants, backers,
  groups[4], legal y cookieAction. Datos reales de la referencia, separados de CSS.
- FooterItem: id único, label, state (available/soon), href sólo si available;
  icon es un espacio neutro, no un logo de proveedor.
- FooterBone: id/version, siete regiones y partes anidadas con dueño/procedencia.
- FooterSkin: fuentes/colores neutros por variables CSS; no elige composición ni scroll.
- FooterMeasurement: schema/version, measuredAt, viewport, footerBounds, metrics
  con área CSS px² y porcentaje, sharedInspector opcional y limitaciones.
- FooterReference: captura, fecha histórica, viewport 1440×900, footer 1440×806
  y límites internos 274/722. Las cajas suministradas son evidencia parcial.

Validación: protocolos https/http/mailto permitidos; ningún javascript/data URL;
IDs no duplicados; cuatro grupos; datos necesarios no vacíos; Soon sin href.
El estado del hueso evoluciona reconstruido → verificado técnicamente → revisado
por humano, sin que el segundo implique el tercero.
