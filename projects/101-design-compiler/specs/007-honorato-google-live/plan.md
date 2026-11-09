# Plan — Honorato Google real
**Spec**: [spec.md](spec.md)
## Summary
Google Cloud CLI oficial y OAuth. Proyecto dedicado; Maps JavaScript, Map Management y API Keys. API v2beta para StyleConfig/MapConfig/MapContextConfig cuando esté disponible. Clave limitada al puerto local 8780 y maps-backend.googleapis.com.
## Technical Context
Node 24/Astro/Python estándar existentes. Sin framework nuevo ni publicación.
Privados: .tools/honorato-google-live; cliente: mismo SingleBusinessLocation y adaptador Google.
Pruebas: REST readback, test de cupo, Chromium local y revisión visual.
Hasta diez cargas iniciales; precio de referencia máximo Dynamic Maps US$7/1000 antes de impuestos, sin asumir tramo gratuito. No Places/Street View. No atribuir coste cero a cargas reales sin verificar.
## Constitution Check
Spec antes de código/recursos. Reutilización de dueños, gates y procedencia. Google real separado de mocks; presupuesto explícito; sin otro motor ni datos privados en Git. Gate previo: PASS.
## Structure
tooling/bones/prepare-honorato-google.mjs: consumidor privado del componente.
tooling/bones/serve-honorato-google.mjs: servidor local y cupo de configuración.
Recursos/configuración privada fuera de Git; reports no sensibles tras verificación.
scripts/audit-honorato-google.ts: comprobación explícita --live; una sola carga para
todos los anchos, zoom, arrastre y fuente alternativa. No forma parte del test unitario.
tooling/bones/provision-google-cloud.py: crea/relee recursos del proyecto dedicado
ya creado y autenticado; lee OAuth en memoria y conserva la key fuera de Git.
tooling/bones/google-trial-budget.mjs: reserva persistente y rechazo de la carga 11.
## Dependencies
Cuenta/facturación/permisos; API Maps Management en Preview; logo puede no tener permiso para presentación comercial y debe conservar fallback.

## Final Constitution Check
PASS: mismo componente y dueños; paquete privado sin redistribución; coordenadas
Google en Google; pin neutro por LOGO_MISSING; OAuth sólo en gcloud/memoria.
Verificados cuota efectiva 10/día, contador local total 10 y origen/API de la key.
Google real y límites automáticos comprobados; aprobación visual humana pendiente.
