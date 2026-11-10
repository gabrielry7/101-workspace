# Tareas
- [x] T001 Registrar alcance/presupuesto y usar OAuth oficial.
- [x] T002 Crear proyecto/servicios, vincular cuenta de facturación accesible y leer cuotas. HG-01/06: cuota efectiva de 10 cargas/día verificada por API.
- [x] T003 Crear estilo/Map ID/asociación y clave web restringida; guardar configuración privada. HG-02/03/07: readback de estilo, asociación y restricciones; sin secretos en Git.
- [x] T004 Preparar consumidor Honorato reutilizando el componente/gates y servidor con cupo persistente. HG-04/05/06: pin neutro, datos privados y dos tests de cupo aprobados.
- [x] T005 Comprobar Google real, móvil/escritorio, anclaje y ausencia de negocios ajenos. HG-03/04: siete anchos, zoom/arrastre y fuente alternativa; anclaje máximo 0.0078125 px; revisión visual del agente, sin aprobación humana implícita.
- [x] T006 Registrar resultados, coste/cargas y commit/push propio. HG-07/08: recibo sin secretos, evidencia privada y entrega en la rama codex/honorato-google-live-20261109.

Orden: T001 → T002 → T003 → T004 → T005 → T006. La preparación local de T004 puede avanzar durante operaciones externas.

## Refinamiento solicitado del marcador
- [x] T007 Registrar la autorización explícita del usuario y verificar/vincular el símbolo de Honorato mediante los contratos existentes (HG-05/07). Declaración, hashes y lineage privados; sin fixtures sintéticos ni auditoría de titularidad inventada.
- [x] T008 Mostrar el logo dentro del mismo pin y desactivar el recuadro del nombre en Honorato, conservando accesibilidad y la etiqueta por defecto para otros consumidores (HG-04/05). Opción markerLabel=false; versión 0.2.1.
- [x] T009 Verificar Google real, logo sin etiqueta, móvil/escritorio y anclaje al mover/ampliar; actualizar resultado y guardar commit/push sin medios privados (HG-03/06/08). Siete anchos Google, fallback por error de imagen, anclaje máximo 0.513 px; regresión offline de 17 anchos y 17 comprobaciones Google aprobada, ocho tests y typecheck sin diagnósticos.

## Controlador en tiempo real
- [x] T010 Añadir panel de operador y validación de opciones visuales, reutilizando pieles, partes y composiciones existentes (HG-04/07). Tres pieles/composiciones, zoom, altura, etiqueta y colores; persistencia estricta sin datos privados.
- [x] T011 Aplicar controles a la misma instancia y permitir etiqueta dinámica; arranque explícito y consulta de cupo sin reservar cargas (HG-04/06). Mismo canvas/controlador; GET status no expone key y no modifica el contador.
- [x] T012 Verificar panel, accesibilidad, persistencia, cupo agotado y ausencia de nuevas cargas con navegador offline; documentar alcance y entregar commit/push (HG-06/08). 45 casos responsive, tres pieles, nombre/foco y 10 tests; typecheck sin diagnósticos. Última carga conservada para el usuario, sin nuevo render Google vivo del panel.
