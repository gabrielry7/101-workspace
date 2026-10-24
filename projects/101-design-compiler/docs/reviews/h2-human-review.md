# H2 — revisión humana en curso

Fecha: 2026-10-09. Base técnica: `3f2d2f36e1617ae600237b6b289473e8209554bc`.

El usuario solicita revisar H2. Se explican comportamiento y límites y se acumulan notas para el prompt final. No se declara aprobación humana de H0–H2 ni se modifica implementación.

## Comportamiento presentado

H2 convierte input aprobado e interpretación H1 en un plan semántico reproducible. Decide módulos/rutas, referencias y alcance, y conserva requisitos y motivos de exclusión. No elige diseño visual ni implementa reservas/pagos/backend.

Registry compartido: 47 capacidades, 46 con semántica de planificación y gallery diferida. Semántica disponible no equivale a componente operativo. Las mismas colecciones y selectores se parametrizan con ofertas/calendarios/hechos; no hay planner por cliente o plantilla por sector.

## Ejemplo real del fixture sintético inspeccionado

`data/derived/planner-v1/restaurante.json` tiene status READY, dos rutas y dos módulos: identidad global y menú de branch-1, con referencia a offering-1. READY significa que el plan semántico es válido para lo emitido, no sitio completo ni preparado para producción.

- Menú: CONFIRMED_PRESENT, INCLUDED.
- Reservas: CONFIRMED_PRESENT, BLOCKED, falta approved_action_destination; no bloquea el plan restante.
- Delivery: UNKNOWN, BLOCKED, falta approved_capability_assertion; no se afirma ausencia ni presencia.
- Horarios: CANDIDATE_ONLY, UNKNOWN, BLOCKED, falta approved_capability_assertion.

Hay diagnósticos y missing_inputs, pero el primer gate puede expresar sólo el requisito que impide continuar; no sustituye el catálogo exhaustivo de datos por función pedido durante H0.

## Garantías y límites

Conserva referencias aprobadas y vigentes, sucursal exacta, dependencias y módulos obligatorios. Las acciones sólo son intenciones de enlace externo con destino aprobado; no confirman operaciones. Una capacidad confirmada sin contenido puede quedar bloqueada. Si falta contenido central o la clasificación permanece no resuelta, no se emite SitePlan.

Nueve escenarios sintéticos ejercitan restaurantes, gimnasio, ferretería, clínica, híbridos, sucursales y datos incompletos. Ninguno demuestra integración real con upstream. El mismo input/contexto produce el mismo plan, requisitos y diagnósticos.

## Implicaciones de las correcciones ya solicitadas

Estas notas aplican feedback previo H0/H1 a H2; no son nuevas decisiones ratificadas de implementación:

1. Conectar planner y requisitos con el catálogo maestro versionado por tipo/capacidad solicitado en H0: distinguir objetivo completo del plan ejecutable hoy.
2. Mostrar por negocio/sucursal funciones emitibles, pendientes y no aplicables justificadas, con requisitos completos, datos existentes/faltantes, dependencias de plataforma/proveedor y siguiente paso. No limitar la salida humana a códigos como approved_action_destination.
3. Mantener diagnóstico de todos los requisitos de una función aunque su primer bloqueo impida emitirla; conservar diferencia entre disponibilidad factual y soporte real.
4. Consumir la clasificación contextual corregida en H1 cuando esté implementada, preservando procedencia y conflictos; no seguir bloqueando sólo por una categoría desconocida si el resto de evidencia permite resolver la actividad.
5. Explicar READY como plan válido parcial respecto del objetivo funcional, sin sugerir sitio completo, integración operativa o aprobación humana.

## Verificación dirigida

Durante la revisión: 63/63 tests de `tests/planner.test.ts` PASS con Node portable 24.21.0. Se inspeccionó el output restaurante archivado. No se regeneraron planes ni se ejecutó build completo; esta revisión no sustituye los checks de cierre histórico H2.

Decisión posterior del usuario: «eso entonces por ahora este dejémoslo así, y vamos con H3». Se mantiene H2 como está por ahora y se continúa la revisión humana con H3. Las implicaciones del feedback H0/H1 permanecen como notas para el prompt final, no nuevas correcciones específicas H2 ratificadas ni instrucciones para implementarlas ahora.

Estado: H2 revisado en esta ronda y conservado sin cambios por decisión del usuario. Sólo notas, sin cambios funcionales ni commit.
