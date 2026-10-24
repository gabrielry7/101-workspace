# Registro de cambios — Pipeline 101 v2

**3 de octubre de 2026.** Esta revisión modifica la especificación, no certifica ni modifica el repositorio de 101. Conserva el documento original en `referencia/`.

## Correcciones de la auditoría

| Hallazgo | Corrección integrada | Dónde está | Compuertas | Pruebas representativas |
| --- | --- | --- | --- | --- |
| “Todo dato aprobado aparece en HTML” mezcla validación y publicación | Proyección pública por contexto; datos obligatorios, opcionales e internos; omisiones justificadas; inspección del contenido entregado | Fases 1C, 2D y 5B | G01, G03, G06 | T03, T04, T05 |
| Tener fuente no demuestra vigencia ni verdad | Evidencia por campo, sede, autoridad, fecha y revisión; conflictos explícitos; vigencia y degradación por capacidad | Fases 1A–1D | G01, G06 | T01, T02, T07, T08, T72 |
| “Cada frase” exige fuentes incluso a microtextos funcionales | Trazar afirmaciones factuales, incluidas las derivadas, y revisar instrucciones de interfaz por función | Fase 2D | G03, G06 | T09, T20, T57, T73 |
| Actualizar precios no tiene semántica entre representaciones | Autoridad por dominio, versiones, revalidación de carritos, condiciones inmutables del pedido, conflicto de ediciones y cotizaciones con política explícita | Fases 4A–4B | G05, G06 | T23–T26 |
| Aprobación no queda unida a una versión | Manifiesto inmutable; hash sin circularidad; aprobaciones por alcance; invalidación tras cambios; ejecutor confiable separado del generador | Fases 5A y 6B | G10, G12 | T45, T46, T47 |
| Flujo funcional acaba en navegador, no en operación | Separar solicitud, recepción, aceptación, cumplimiento y pago; responsable, vencimiento y contingencia | Fases 2B y 4C–4G | G05, G14, G15 | T17–T22, T27, T59 |
| WhatsApp se trata como envío o pedido | El enlace prepara un chat; handoff, recepción y aceptación son observaciones diferentes; resultados manuales identificados | Fase 4D y 7A | G05, G15 | T17, T18, T19, T62, T74 |
| Reservas/pagos carecen de casos adversos explícitos | Cupos atómicos, sincronización de canales, cotización, importe autoritativo, deduplicación duradera, eventos tardíos y conciliación | Fases 4E–4F | G05, G10, G13 | T21, T28–T39, T52 |
| Derechos de terceros aparecen como tarea, no como bloqueo | Manifiesto por recurso/uso, evidencia, atribución, plazos y retirada; autorización del dueño no blanquea derechos ajenos | Fases 1F y 6A; capa D | G02, G11 | T10, T11, T12 |
| Prospecto y sitio oficial se confunden | Modos separados: prototipo privado sin operaciones reales; sitio autorizado con representación comprobada | Alcance inicial, fases 1A y 6A | G01, G10, G11, G12 | T06, T43, T69 |
| Compuertas vagas y aprobación silenciosa | Catálogo con entradas, condición, responsable, evidencia, invalidez y reparación; NOT_RUN/INCONCLUSIVE bloquean | Fase 5A; catálogo y herramientas | G00–G16 | T46, T47, T68, T71 |
| Recuperación no define qué se revierte | Activación recuperable; versionado compatible; no restaurar pedidos/precios/derechos antiguos al revertir diseño | Fase 6C y capa C | G13 | T12, T48–T52, T63, T70 |
| Banco de pruebas sin evaluación independiente | Desarrollo y examen protegidos por negocio/marca; baseline manual; tareas, estética y aprobación del dueño separadas | Fase 7C | G16 | T64, T65 |
| Chromium como cobertura suficiente | Matriz de motores/versiones más comprobación manual móvil; accesibilidad automatizada y manual; laboratorio separado de campo | Fase 5C | G07, G08, G09 | T53–T57 |
| Clics y resultados comerciales se mezclan | Diccionario de eventos, deduplicación, pruebas separadas de tráfico real, denominadores y desenlace no observado | Fase 7A | G15 | T17, T59–T62 |
| Ahorro por comisiones se confunde con valor incremental | Costos humanos y proveedores, márgenes del restaurante/101 y efecto causal tratados por separado | Fase 7D | G15, G16 | T66 |

## Las tres contradicciones estructurales

| Antes | Ahora | Prueba |
| --- | --- | --- |
| Fotos obligatorias para avanzar, pero luego se permite diseño sin fotos | Fotos condicionadas al diseño; derechos exigidos para todo recurso usado | T10, T11 |
| Reservas como nivel superior al carrito | Capacidades independientes con dependencias reales | T13, T14 |
| Se diseña antes de decidir funciones | Fase 2 declara capacidades y operación; fase 3 diseña; fase 4 implementa | T13, T14 y validación del CapabilityPlan |

## Otras correcciones de consistencia

Se conservaron siete fases y cuatro capas, corrigiendo la referencia del original a “tres capas”. Se retiraron conteos aproximados de pasos y el encabezado que hablaba de cinco decisiones aunque enumeraba nueve. Las cifras de sitios, candidatos y pruebas históricas dejaron de presentarse como estado actual comprobado.

“Mejor que las plataformas”, “sin comisiones”, “la estética es la única pregunta abierta”, “menú nunca en PDF” y “mínimo dos instancias” dejaron de ser afirmaciones o reglas universales. Se reemplazaron por objetivos medibles, menú HTML con descarga opcional y decisiones técnicas sujetas a evidencia.

Se añadió distinción de moneda/unidad, precios por sede/canal, alérgenos desconocidos, horarios de cocina/local, pausas operativas, aislamiento fuera de la base de datos, conservación de operaciones durante salida y limitaciones de la automatización de QA. No se habilitó ninguna de estas funciones por documentarla.

## Decisiones nuevas, no hechos descubiertos

Las políticas iniciales de vigencia, presupuestos de rendimiento, límite de iteraciones, división 12/8 del banco y objetivos de recuperación son propuestas explícitas de esta versión. No son medidas observadas, estándares universales ni acuerdos comerciales ya aceptados.

El piloto se restringió a una sede, menú/contacto/actualización y solicitud por WhatsApp con recepción operativa registrada. Pagos, reservas automáticas, despacho, cuentas y lealtad permanecen fuera de ese hito. Se conservaron sus contratos para futuras integraciones, sin convertirlos en bloqueos del piloto cuando están deshabilitados.

## Qué se validó en esta entrega

Se ejecutó el validador de la **especificación**: forma de los esquemas, seis tipos de ejemplos sintéticos, referencias y cobertura de compuertas/casos, rechazos estructurales esperados, hash del candidato de ejemplo e integridad del original. El reporte está en `VALIDACION_ENTREGA.json`.

**No se ejecutaron los 74 casos del producto, no se auditó el repositorio, no se probaron restaurantes en producción y no se autorizó ningún despliegue.** Cada caso conserva `NOT_RUN`, sin implementación ni evidencia inventadas. Tampoco se declaró completa la verificación jurídica o de tarifas de proveedores.
