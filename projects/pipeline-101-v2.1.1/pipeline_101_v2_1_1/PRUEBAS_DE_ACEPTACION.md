# Pruebas de aceptación — Pipeline 101 v2.1.1

**Archivo generado.** No editar las tablas a mano. Regenerar con `python3 herramientas/generar_indices.py`.

**18 compuertas y 84 casos definidos.** Bajo el perfil propuesto: **61 casos dentro del alcance y 23 fuera**. Hay 59 casos con obligaciones previas y 10 con obligaciones posteriores; estos conjuntos se solapan y no se suman. Todos los casos del producto siguen `NOT_RUN`.

La clasificación es condicional: los supuestos del perfil están `NOT_RUN`, no verificados. Este índice no emite `PASS`, `NOT_APPLICABLE` real ni autorización para publicar.

| Selección por contexto | Casos |
| --- | --- |
| Antes | T01, T02, T03, T04, T05, T06, T08, T09, T10, T11, T12, T13, T15, T16, T17, T18, T19, T20, T23, T24, T25, T27, T40, T41, T43, T44, T45, T46, T47, T48, T49, T50, T51, T53, T54, T55, T56, T57, T60, T61, T62, T63, T66, T68, T69, T70, T72, T73, T74, T75, T76, T77, T78, T79, T80, T81, T82, T83, T84 |
| Después | T17, T18, T27, T58, T59, T60, T61, T62, T66, T82 |
| Fuera del perfil propuesto | T07, T14, T21, T22, T26, T28, T29, T30, T31, T32, T33, T34, T35, T36, T37, T38, T39, T42, T52, T64, T65, T67, T71 |

## Casos y razones

Los detalles de preparación, acción, resultado esperado y evidencia están en `especificacion/pruebas_aceptacion.json`. «Antes» y «Después» son obligaciones distintas aun cuando reutilicen el identificador de caso.

| Caso | Qué prueba | Compuertas | Contexto en este perfil | Razón de selección/exclusión | Ejecución |
| --- | --- | --- | --- | --- | --- |
| T01 | Precio incorrecto en salida | G01, G06 | G01: Antes; G06: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T02 | Horario vencido | G01, G06 | G01: Antes; G06: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T03 | Filtración de dato interno | G03, G06, G10 | G03: Antes; G06: Antes; G10: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T04 | Omisión opcional justificada | G03, G06 | G03: Antes; G06: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T05 | Obligatorio oculto o ausente | G06 | G06: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T06 | Aprobador sin autoridad | G01, G12 | G01: Antes; G12: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T07 | Mezcla de sedes | G01, G05, G06 | Fuera de alcance | condición ausente: multi_location | NOT_RUN |
| T08 | Conflicto no resuelto | G01, G03 | G01: Antes; G03: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T09 | Alérgeno inferido | G01, G03 | G01: Antes; G03: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T10 | Foto sin derechos suficientes | G02, G04a | G02: Antes; G04a: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T11 | Diseño sin fotos válido | G02, G04a | G02: Antes; G04a: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T12 | Retirada de activo revocado | G02, G13 | G02: Antes; G13: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T13 | Función anunciada pero deshabilitada | G03, G05 | G03: Antes; G05: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T14 | Reservas independientes del carrito | G03 | Fuera de alcance | capacidad deshabilitada: reservation_request | NOT_RUN |
| T15 | Escala monetaria y modificadores | G01, G05 | G01: Antes; G05: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T16 | Extracción de carta equivocada | G01, G06 | G01: Antes; G06: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T17 | WhatsApp abierto sin envío | G05, G15 | G05: Antes; G15: Antes/Después | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T18 | Recepción manual no es aceptación | G05, G15 | G05: Antes; G15: Antes/Después | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T19 | Negocio sin respuesta | G05 | G05: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T20 | Horario nocturno y excepción | G05, G06 | G05: Antes; G06: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T21 | Último cupo de reserva | G05 | Fuera de alcance | capacidad deshabilitada: reservation_confirmed | NOT_RUN |
| T22 | Última unidad reservable | G05 | Fuera de alcance | capacidad deshabilitada: online_payment | NOT_RUN |
| T23 | Precio cambia con carrito abierto | G05, G06 | G05: Antes; G06: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T24 | Pedido aceptado conserva condiciones | G05 | G05: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T25 | Ediciones simultáneas | G05 | G05: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T26 | Cotización y vencimiento | G05 | Fuera de alcance | capacidad deshabilitada: online_payment | NOT_RUN |
| T27 | Servidor no disponible | G05, G14 | G05: Antes; G14: Después | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T28 | Total manipulado en navegador | G05, G10 | Fuera de alcance | capacidad deshabilitada: online_payment | NOT_RUN |
| T29 | Doble clic idempotente | G05 | Fuera de alcance | capacidad deshabilitada: online_payment | NOT_RUN |
| T30 | Evento de pago repetido tras reinicio | G05, G10 | Fuera de alcance | capacidad deshabilitada: online_payment | NOT_RUN |
| T31 | Checksum inválido | G05, G10 | Fuera de alcance | capacidad deshabilitada: online_payment | NOT_RUN |
| T32 | Reintento legítimo tardío | G05 | Fuera de alcance | capacidad deshabilitada: online_payment | NOT_RUN |
| T33 | Eventos fuera de orden | G05 | Fuera de alcance | capacidad deshabilitada: online_payment | NOT_RUN |
| T34 | Retorno de pago falsificado | G05, G10, G15 | Fuera de alcance | capacidad deshabilitada: online_payment | NOT_RUN |
| T35 | Pago de otro comercio o importe | G05, G10 | Fuera de alcance | capacidad deshabilitada: online_payment | NOT_RUN |
| T36 | Pago tardío tras liberar reserva | G05 | Fuera de alcance | capacidad deshabilitada: online_payment | NOT_RUN |
| T37 | Timeout de resultado desconocido | G05 | Fuera de alcance | capacidad deshabilitada: online_payment | NOT_RUN |
| T38 | Reembolso parcial y repetición | G05 | Fuera de alcance | capacidad deshabilitada: online_payment | NOT_RUN |
| T39 | Reservas externas no conciliadas | G05 | Fuera de alcance | capacidad deshabilitada: reservation_confirmed | NOT_RUN |
| T40 | Inyección en contenido y archivos | G07, G10 | G07: Antes; G10: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T41 | Instrucciones maliciosas para el agente | G10 | G10: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T42 | Aislamiento completo entre negocios | G10 | Fuera de alcance | condición ausente: shared_tenant_surfaces | NOT_RUN |
| T43 | Vista previa privada | G10, G12 | G10: Antes; G12: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T44 | Secretos en artefactos | G10 | G10: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T45 | Cambio posterior a aprobación | G12 | G12: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T46 | Reporte PASS falsificado | G10, G12 | G10: Antes; G12: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T47 | Compuerta vacía o no ejecutada | G12 | G12: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T48 | Interrupción durante despliegue | G13 | G13: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T49 | Rollback de diseño con catálogo actual | G06, G13 | G06: Antes; G13: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T50 | Rollback incompatible con esquema | G13 | G13: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T51 | Restauración medible | G13 | G13: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T52 | Caída entre operación y notificación | G05, G13 | Fuera de alcance | condición ausente: durable_notifications | NOT_RUN |
| T53 | Contenido extremo en navegadores | G04a, G07 | G04a: Antes; G07: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T54 | Teclado, zoom y lector de pantalla | G08 | G08: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T55 | Contraste, barra y movimiento | G04a, G08 | G04a: Antes; G08: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T56 | Presupuesto reproducible de rendimiento | G09 | G09: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T57 | Datos estructurados divergentes | G06, G07 | G06: Antes; G07: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T58 | Dominio y versión en producción | G14 | G14: Después | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T59 | Solicitud real controlada | G14, G15 | G14: Después; G15: Después | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T60 | Eventos duplicados y tráfico de pruebas | G15 | G15: Antes/Después | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T61 | Datos personales en analítica | G10, G11, G15 | G10: Antes; G11: Antes; G15: Antes/Después | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T62 | Desenlace desconocido | G15 | G15: Antes/Después | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T63 | Supresión con retención legítima revisada | G11, G13 | G11: Antes; G13: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T64 | Contaminación de evaluación | G16 | Fuera de alcance | condición ausente: evaluation_program; contexto fuera del perfil: evaluation | NOT_RUN |
| T65 | Uso y estética separados | G16 | Fuera de alcance | condición ausente: evaluation_program; contexto fuera del perfil: evaluation | NOT_RUN |
| T66 | Costos humanos y atribución | G15 | G15: Antes/Después | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T67 | Función del proveedor solo en sandbox | G00, G05 | Fuera de alcance | capacidad deshabilitada: online_payment | NOT_RUN |
| T68 | Cifra histórica de pruebas | G00 | G00: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T69 | Flujo legal sin revisión | G11 | G11: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T70 | Salida o suspensión con operaciones pendientes | G11, G13 | G11: Antes; G13: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T71 | Presupuesto agotado | G04a, G12 | Fuera de alcance | condición ausente: visual_search | NOT_RUN |
| T72 | Agotado con cliente desconectado | G01, G05, G06 | G01: Antes; G05: Antes; G06: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T73 | Cambio de sentido en reescritura | G03, G12 | G03: Antes; G12: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T74 | Handoff largo y sin aplicación | G05, G07 | G05: Antes; G07: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T75 | G04a: cobertura y límites del detector | G04a, G08 | G04a: Antes; G08: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T76 | G04b: dos revisiones completas y tareas | G04b | G04b: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T77 | Cambio visual sin cambio de composición | G04a, G04b, G12 | G04a: Antes; G04b: Antes; G12: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T78 | Preferencias estéticas con excepciones justificadas | G04a, G04b, G06, G08 | G04a: Antes; G04b: Antes; G06: Antes; G08: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T79 | Retiro de G04 sin heredar aprobaciones | G04a, G04b, G12 | G04a: Antes; G04b: Antes; G12: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T80 | Dependencias y activos ejecutables del sitio estático | G10 | G10: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T81 | Permisos del taller y publicación en piloto | G10, G12 | G10: Antes; G12: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T82 | Aplicabilidad por perfil y momento | G12, G15 | G12: Antes; G15: Antes/Después | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T83 | Rechazo de datos ajenos en una sola sede | G01, G06, G10 | G01: Antes; G06: Antes; G10: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |
| T84 | Reutilización acotada de evidencia de diseño | G04b, G12 | G04b: Antes; G12: Antes | Capacidades, condiciones y contexto cubiertos por el perfil propuesto. | NOT_RUN |

## Obligaciones por compuerta

| Compuerta | Antes de publicar | Después de desplegar | Evaluación |
| --- | --- | --- | --- |
| G00 | T68 | No exigida en este contexto/perfil | No exigida en este contexto/perfil |
| G01 | T01, T02, T06, T08, T09, T15, T16, T72, T83 | No exigida en este contexto/perfil | No exigida en este contexto/perfil |
| G02 | T10, T11, T12 | No exigida en este contexto/perfil | No exigida en este contexto/perfil |
| G03 | T03, T04, T08, T09, T13, T73 | No exigida en este contexto/perfil | No exigida en este contexto/perfil |
| G04a | T10, T11, T53, T55, T75, T77, T78, T79 | No exigida en este contexto/perfil | No exigida en este contexto/perfil |
| G04b | T76, T77, T78, T79, T84 | No exigida en este contexto/perfil | No exigida en este contexto/perfil |
| G05 | T13, T15, T17, T18, T19, T20, T23, T24, T25, T27, T72, T74 | No exigida en este contexto/perfil | No exigida en este contexto/perfil |
| G06 | T01, T02, T03, T04, T05, T16, T20, T23, T49, T57, T72, T78, T83 | No exigida en este contexto/perfil | No exigida en este contexto/perfil |
| G07 | T40, T53, T57, T74 | No exigida en este contexto/perfil | No exigida en este contexto/perfil |
| G08 | T54, T55, T75, T78 | No exigida en este contexto/perfil | No exigida en este contexto/perfil |
| G09 | T56 | No exigida en este contexto/perfil | No exigida en este contexto/perfil |
| G10 | T03, T40, T41, T43, T44, T46, T61, T80, T81, T83 | No exigida en este contexto/perfil | No exigida en este contexto/perfil |
| G11 | T61, T63, T69, T70 | No exigida en este contexto/perfil | No exigida en este contexto/perfil |
| G12 | T06, T43, T45, T46, T47, T73, T77, T79, T81, T82, T84 | No exigida en este contexto/perfil | No exigida en este contexto/perfil |
| G13 | T12, T48, T49, T50, T51, T63, T70 | No exigida en este contexto/perfil | No exigida en este contexto/perfil |
| G14 | No exigida en este contexto/perfil | T27, T58, T59 | No exigida en este contexto/perfil |
| G15 | T17, T18, T60, T61, T62, T66, T82 | T17, T18, T59, T60, T61, T62, T66, T82 | No exigida en este contexto/perfil |
| G16 | No exigida en este contexto/perfil | No exigida en este contexto/perfil | No exigida en este contexto/perfil |

## Límites

No hay casos del producto ejecutados en esta entrega. La correspondencia entre archivos no verifica permisos, operación, navegadores, derechos ni la existencia de personas revisoras. La integración debe verificar el perfil y la procedencia de evidencias antes de usar estos resultados como selección operativa. Una omisión de detector o una obligación no ejecutada bloquea la compuerta correspondiente.
