# Escenarios controlados H2

Todos los datos de estos seis archivos son **SYNTHETIC_FIXTURE**. Nombres, direcciones y objetos son ficticios; `example.invalid` representa destinos de prueba, sin integración ni operación real. No publicar estos paquetes como negocios.

El loader suma estos escenarios a los inputs originales de restaurante, gimnasio y ferretería H0. Ignora sus planes manuales al probar H2 y pasa los nueve inputs al mismo `planBusiness`.

- `hibrido-gimnasio-tienda`: membresías, clases y productos con coexistencia aprobada explícita.
- `hibrido-sin-evidencia`: mismos objetos, sin relación de coexistencia; clasificación bloqueada.
- `hotel-restaurante-sucursales`: habitaciones en dos sedes; menú en una, UNKNOWN en la otra. Direcciones ficticias separadas.
- `clinica`: servicios y profesionales; destino externo sintético aprobado para solicitar consulta.
- `servicios-profesionales`: servicios y contacto publicables, citas UNKNOWN.
- `informacion-incompleta`: catálogo PRESENT sin objetos; CONTENT_BLOCKED.

El metadata `expected_status` pertenece al harness de pruebas, no al protocolo upstream. `npm run validate` comprueba tanto los planes READY como los bloqueos esperados. `npm run planner:fixtures` conserva resultados en `data/derived/planner-v1/`.
