# Registro de cambios — Pipeline 101 v2.1.1

**3 de octubre de 2026.** Bases: documento 2.1 y paquete de contratos 2.0 aportados en esta conversación. Este parche corrige la especificación y sus herramientas documentales. No modifica el repositorio, no ejecuta integraciones y no autoriza publicar.

## Correcciones de la auditoría

| Hallazgo | Corrección integrada | Archivos/secciones | Casos del producto |
| --- | --- | --- | --- |
| Documento exige G04a/G04b, esquema y catálogo aceptan G04 | 18 compuertas activas; enum, política, catálogos, ejemplos y validador sincronizados. G04 queda solo en referencias históricas | Fase 3K, catálogo, contratos, migración | T75, T76, T79 |
| Tabla de pruebas inferida del registro y no del catálogo | Selección explícita por capacidad, superficie y momento; tabla generada, sin duplicar listas de aplicabilidad editadas a mano | Mínimo del piloto; perfil y catálogos; generador | T82 |
| T22/T26 mal incluidas; T66 mal excluida | T22/T26 siguen ligadas al pago. T66 sigue en G15 y dentro del piloto | Catálogo, índices y regresiones | T22, T26, T66, T82 |
| Restaurar copia antigua puede reactivar precios/fotos | Reconstruir diseño compatible con datos/derechos actuales, preservar registro manual y probar falta de historial sin republicar copia incierta | Fase 6C; G13 del mínimo; capa C | T12, T48–T51, T63, T70 |
| Seguridad mínima omite controles sobre entradas y dependencias | Conservar saneamiento/inyección, defensa del agente, revisión de dependencias, secretos, permisos y separación del publicador aunque el sitio sea estático | G10 del mínimo; capa B; catálogo | T40, T41, T44, T46, T80, T81 |
| Variedad obligatoria y dos líneas confunden estilo con calidad | Guías con excepciones justificadas y evaluación de tarea; no truncar datos ni alternar por obligación | Fases 3A, 3C, 3F, 3G, 3H, 3K y R5 | T78 |
| Revisión humana se repite solo por composición | Huellas por 14 dimensiones; dependencias de R1–R11, reutilización acotada y registro completo nuevo; ámbito/política desconocidos invalidan todo | Fase 3K; política y contrato de revisión; G12 | T77, T84 |
| G04a llama automático a un orden de lectura claro | Seis aserciones mecánicas con medición y límites; claridad semántica a G04b/G08; falta de detector o evidencia bloquea | Fase 3K; política; G04a | T75 |

## Precisiones necesarias al contrastar los archivos

Estas no se presentan como hallazgos del código: son reconciliaciones explícitas de la especificación.

| Punto | Resolución |
| --- | --- |
| T52 estaba agrupada con pagos/reservas aunque prueba una cola de notificaciones | Requiere `durable_notifications` además de su capacidad original. Queda fuera del perfil manual por ausencia de cola, no por pagos. No se elimina la preservación de decisiones manuales |
| T59 pertenece a G14 y G15, pero requiere producción | Solo después de desplegar. G15 conserva sus pruebas previas y exige las posteriores para completar el piloto. T27 también distingue sus dos momentos |
| Un operador no elimina los conflictos de actualización | T25 se reformula con dos sesiones/procesos del mismo operador y permanece aplicable |
| Una sede no elimina toda validación de identidad ni todos los riesgos compartidos | T07 exige varias sedes; T42 depende de superficies privadas compartidas, incluido el taller. T83 exige rechazar datos ajenos incluso en el perfil de una sede |
| S5 no prueba ausencia universal de tratamiento | Se minimizan conversaciones/datos de comensales, pero se revisan referencias, logs, terceros y datos de autorizantes/operadores. T61/T63/T69 no desaparecen por declarar «solo una referencia» |
| Retención y salida también existen en una operación manual | T63/T70 contemplan los registros realmente mantenidos; no obligan a construir pagos para poder probarlos |
| N0 no ejecuta búsqueda visual | T71 requiere esa superficie y queda fuera del perfil propuesto |
| Una familia tipográfica adicional no demuestra mala lectura | Se ajusta la guía y R5 de forma consistente; se mantiene licencia, cobertura, legibilidad y revisión |
| Una rúbrica no debe cambiar para que gane un referente | La discrepancia inicia investigación y calibración previa; no obliga a asignar «destacado» por reputación |
| Política nueva y perfil explícito cambian el candidato | Se recalculan ejemplos y se documenta la migración; aprobaciones reales previas no se convierten en nuevas por renombrar |

## Qué se conserva

Las siete fases, cuatro capas, capacidades independientes, separación de prospecto/sitio autorizado, once criterios de diseño, dos personas revisoras y niveles N0–N3. El piloto continúa con una sede y cuatro capacidades: información pública, menú HTML, contacto y preparación de solicitud por WhatsApp. No se añaden pagos, reservas automáticas, cuentas, lealtad ni despacho.

Se conservan T01–T74 y sus identificadores. Se modifican explícitamente los escenarios/expectativas de T25, T49, T51, T63, T66 y T70 para reflejar el alcance manual y la recuperación segura. Se añaden condiciones de superficie a T07, T42, T52, T64, T65 y T71. Todos los casos declaran sus contextos por compuerta; las referencias a G04 se migran a G04a donde corresponden, sin migrar resultados.

## Casos nuevos

| ID | Obligación añadida a la especificación |
| --- | --- |
| T75 | Cobertura y límites reales de los detectores de G04a |
| T76 | Dos revisiones humanas completas con evidencia de tareas |
| T77 | Invalidación por cambios visuales aunque no cambie composición |
| T78 | Excepciones estéticas sin pérdida de información o garantías |
| T79 | Rechazo de G04 como identificador activo, sin heredar aprobaciones |
| T80 | Dependencias y recursos ejecutables del sitio estático |
| T81 | Permisos de operador, taller, ejecutor y publicación |
| T82 | Aplicabilidad por perfil y momento, sin circularidad |
| T83 | Identidad y datos ajenos incluso en el caso de una sola sede |
| T84 | Reutilización acotada de evidencia visual, no de aprobación global |

Los 84 casos permanecen `NOT_RUN`, con `implementation_ref=null`, `actual_result=null` y sin evidencia de ejecución. Definir una prueba no la implementa.

## Qué se ejecutó sobre esta entrega

**155 comprobaciones documentales:** esquemas y catálogos, referencias bidireccionales, contextos, selección condicional, huellas de ejemplos, forma de revisión humana, invalidaciones, rechazos esperados, tablas generadas e integridad de fuentes. Resultado en `VALIDACION_ENTREGA.json`.

**17 regresiones documentales:** una copia intacta pasa; 16 mutaciones controladas se rechazan. Incluyen reintroducir G04, excluir T66, convertir T22/T26 en casos de WhatsApp, tratar T52 como pago, exigir T59 antes del despliegue, quitar T40 de G10 aun manteniendo referencias consistentes, olvidar R5 al cambiar tipografía, duplicar revisores, aprobar una revisión sin ejecutar, quitar una condición del perfil, editar la tabla a mano, alterar la fuente, fabricar PASS de producto, usar un contexto desconocido y cambiar entradas bajo una huella vieja. Resultado en `VALIDACION_REGRESIONES.json`.

Cuando corresponde, las mutaciones regeneran índices antes de probar el rechazo: no se limitan a descubrir una tabla desactualizada. Se ejecutan en copias temporales, sin modificar las fuentes de entrada.

**Lo no ejecutado:** los 84 casos del producto, G00 sobre el repositorio, detectores visuales, navegadores, revisiones humanas reales, restaurante piloto, proveedores y despliegues. Los seis supuestos del perfil siguen sin comprobarse. No se revalidaron las referencias externas ni la vigencia normativa.

## Procedencia

`referencia/` preserva el original, el documento 2.1 y los archivos relevantes del paquete 2.0. `especificacion/procedencia.json` registra sus huellas y la del ZIP recibido. `DIFF_2.1_A_2.1.1.patch` permite inspeccionar todos los cambios del documento, incluidos los bloques generados. Las referencias externas y fechas de consulta se atribuyen a las versiones de origen, no a una consulta nueva.
