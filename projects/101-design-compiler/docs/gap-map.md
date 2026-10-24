# Brechas y siguiente cambio mínimo

| Brecha | Frontera preparada H0 | Trabajo posterior |
|---|---|---|
| Upstream ausente | BusinessInputV1 con snapshot, fact IDs, decisiones y scopes | H1: obtener SiteSpec y PublicationDecision reales; adapter versionado con pruebas de productor/consumidor. No nuevo crawler o base Truth. |
| Inventario ausente | Categorías originales abiertas a proveedores desconocidos | H1: procesar archivo íntegro por fuente/campo/código; no sumar candidatos de proveedores como negocios únicos. |
| Taxonomía sin resolver | BusinessProfile manual con RESOLVED/UNRESOLVED/NON_BUSINESS | H1: mapping registry y abstención; no usar confianza como autorización comercial. |
| Registry y planner ausentes | CapabilityProfile y SitePlan declarativos manuales | H2: frontend contracts, requisitos, diagnósticos y planner; preservar estados y omitir rutas sin datos. |
| Runtime 101 ausente | Shell Astro de inspección sin componentes de negocio | H4: confirmar API y reutilizar runtime/componentes reales; adaptar una frontera, no clonar todo el sistema. |
| Medios y permisos ausentes | Entrada de metadata con derechos desconocidos/documentados/bloqueados | H3: MediaAsset/LicenseGrant/MediaUsage, rights gate, calidad; DOCUMENTED aquí no acredita elegibilidad. |
| Arte y búsqueda ausentes | SitePlan estricto sin tokens, operadores o código | H4/H5: composiciones certificadas y LLM estructurado bajo presupuesto. |
| Auditorías y lock ausentes | Pruebas de contratos y guardas básicas de bindings | H6–H8: DOM/browser/performance/visión y reconstrucción; no afirmar visual quality desde tests de datos. |

Siguiente cambio acotado propuesto **tras revisión de H0**: incorporar el inventario de categorías y acordar fixtures reales del protocolo upstream, conservando el original y añadiendo tests de mapping/abstención. La integración remota efectiva sigue pendiente hasta disponer del otro sistema.
