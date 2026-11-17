# Tareas

- [x] T001 Preparar una muestra con fuente OSM, evidencia del logo y paleta documentadas.
- [x] T002 Integrar el mapa vectorial y los controles en el hueso existente.
- [x] T003 Verificar la vista real, las alternativas y el alcance de la entrega.

Chromium cargó la cartografía de OpenFreeMap y mostró un pin con logo y los
créditos de la fuente. El cambio de piel, el zoom y el arrastre reutilizaron el
mapa. El anclaje quedó dentro de 1 px y se verificó el diseño entre 360 y
1440 px. Con la fuente bloqueada, la vista mostró la dirección y el estado de
indisponibilidad. Los resultados detallados y las capturas se guardaron en el
taller privado. Pasaron las comprobaciones de Astro y TypeScript, las diez
pruebas de contrato y controles y la auditoría del taller sintético.

- [x] T004 Vincular todos los campos de edición a la vista y a su persistencia.
- [x] T005 Verificar la aplicación y recuperación de cada grupo, el mapa real y la vista adaptable.

La revisión 0.5.0 se comprobó con 61 campos en Chromium. Se inspeccionaron los
valores de capa, cámara y CSS, el guardado y la recuperación de ajustes nuevos
y de 0.4.0, la recuperación de la vista inicial, el anclaje y la alternativa
con la fuente bloqueada. La misma instancia sirvió para todas las ediciones.
La inspección cubrió 360–1440 px y la fuente de respaldo.

- [x] T006 Añadir y exponer la extrusión y la iluminación en la misma vista.
- [x] T007 Verificar el ejemplo vivo, el modo 2D, los ajustes anteriores y las capturas.

Chromium verificó la muestra 0.6.0 con teselas de OpenFreeMap, luz y extrusión
activas. Cambiar a 2D, modificar escala, color y opacidad, ocultar edificios y
guardar/restaurar conservaron la instancia. Se recuperaron ajustes de 0.5.0 y
se comprobó el anclaje dentro de 1 px y el diseño entre 360 y 1440 px.
Las capturas y los reportes permanecen en el taller privado.
