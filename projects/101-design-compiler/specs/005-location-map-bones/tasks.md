# Tareas — ubicación

- [X] T01 — Spec/plan y dueños inspeccionados; investigación Google resuelta (LM-01,05).
- [X] T02 — Contrato de hueso, datos y logo mediante gates existentes (LM-03,04).
- [X] T03 — Integración API original, logo anclado y política fija sin POIs (LM-01,02,03).
- [X] T04 — Adaptador Google con configuración/carga/fallback/cleanup (LM-05).
- [X] T05 — Astro reutilizable, taller, tres recetas y comparación privada (LM-06).
- [X] T06 — Pruebas positivas/negativas y navegador con fallos/tamaños/preferencias (LM-07).
- [X] T07 — Revisión de diff, convergencia documental, commit/push y vista local (LM-08).

Consistencia previa: LM-01..08 tienen tarea; las rutas del plan reutilizan los dueños
documentados. No hay checklists de aprobación pendientes ni hooks instalados.
La prueba viva de Google se informa como dependencia externa, no como tarea simulada cumplida.

Evidencia: `docs/bones/location-map-verification.json`. Pruebas propias 5/5;
contratos Google offline y recorridos nativos incluidos en el recibo. Build/check
global pasan; suite general 525/528, con tres fallos de locks históricos sobre
trabajo ya modificado al inicio. No se resellan esos locks ni se corrigen cambios ajenos.
