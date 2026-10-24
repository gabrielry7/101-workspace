# Migración a 2.1.1

## Alcance

La numeración 2.1.1 identifica este parche documental. **No implica compatibilidad automática de esquemas con 2.0.** La versión 2.1 aportó un documento, mientras el paquete de contratos disponible seguía en 2.0; esta entrega sincroniza ambas bases y conserva sus originales en `referencia/`.

Nada de lo siguiente afirma que ya se haya ejecutado sobre el repositorio. El primer paso operativo sigue siendo G00: localizar los modelos, comprobadores, permisos y flujos reales antes de adaptar o reemplazar código.

## Contratos que cambian

| Elemento | Antes | 2.1.1 | Tratamiento |
| --- | --- | --- | --- |
| `schema_version` / versión de política | 2.0 en los archivos del paquete | 2.1.1 | Identificar el formato al cargarlo; no mezclar contratos silenciosamente |
| Identificador de diseño | `G04` | `G04a`, `G04b` | Conservar G04 solo en el historial; rechazarlo como reporte nuevo |
| `GateResult` | Sin momento de evaluación ni perfil explícito | `evaluation_context`, `applicability_profile_hash` | Derivar casos por compuerta y momento; no aceptar una lista elegida por el generador |
| G04b aprobada | Sin contrato de revisión humana | `design_review_ref`, `design_review_hash` | Resolver y verificar el registro completo, sus entradas y su candidato |
| Candidato | Sin huella explícita del perfil | `candidate_inputs.applicability_profile_hash` | Cambia el hash del candidato; las aprobaciones de candidato completo deben renovarse |
| Revisión de diseño | Solo descrita en el documento | `DesignReviewRecord` → `$defs/DesignReview`, `kind=design_review` | Dos personas distintas, once criterios cada una, tareas/dispositivos y huellas |
| Aplicabilidad | Capacidad y clasificación manual aproximada | Condiciones explícitas y `gate_contexts` por caso | Generar índices desde catálogo y perfil; conservar las exclusiones y su fundamento |
| Políticas visuales | Revisión repetida solo por composición | Aserciones D01–D06 y dependencias por dimensión | Repetir G04a y derivar G04b/otros controles afectados |

Los nombres de negocio del documento se mapean a los modelos reales del repositorio; los tipos de referencia no obligan a crear una segunda autoridad de datos. Los catálogos del paquete son obligaciones documentales. Las ejecuciones reales se guardan aparte, con la identidad y permisos del ejecutor.

## No migrar un aprobado con búsqueda y reemplazo

Un reporte `G04` bajo la política 2.0 no se convierte en dos aprobaciones. Algunas comprobaciones mecánicas anteriores podrán reutilizarse al implementar G04a si se demuestra su correspondencia, pero G04b necesita revisión humana y evidencia propias. Conservar el registro histórico, no editarlo.

Toda aprobación del candidato completo referencia su hash exacto. Cambiar esquema, política, perfil, artefactos o las entradas incluidas genera otro candidato. Las aprobaciones por alcance solo conservan validez cuando ese alcance, sus entradas y sus condiciones siguen comprobablemente vigentes.

El verificador de G04b debe comprobar: correspondencia del candidato, hash del archivo de revisión, ámbito, política, once criterios completos por cada una de dos personas distintas, evidencia de tareas/dispositivos, ausencia de fallas y procedencia confiable. Validar la forma JSON no autentica a una persona ni acredita que hizo la tarea.

## Selección de pruebas

`perfil_piloto.json` fija cuatro capacidades, nivel N0 y cinco condiciones de superficie/operación. Sus seis supuestos siguen sin verificar. Un responsable debe documentar que representan el ambiente real antes de justificar una exclusión.

Las comprobaciones reales de supuestos se guardan **aparte**, vinculadas a la huella del perfil: supuesto, actor autorizado, momento, resultado y evidencia. El esquema de esta entrega mantiene `NOT_RUN` para no fabricar esas comprobaciones; no es el formato de un expediente operativo verificado. Verificar un supuesto no exige editar retroactivamente el perfil del candidato. Cambiar una condición declarada sí produce otro perfil y requiere reevaluar las obligaciones.

Una sola sede no implica ausencia de aislamiento: un taller que almacene archivos privados de otros negocios vuelve aplicable `shared_tenant_surfaces` y T42. Un mismo operador puede producir dos actualizaciones concurrentes: T25 sigue dentro. Una referencia manual o los datos de autorizantes/operadores requieren revisar el flujo real, por lo que S5 no excluye automáticamente privacidad, retención y salida.

Cada caso tiene `gate_contexts`. T59 solo se exige después de desplegar en G14 y G15. T27 se ensaya antes en G05 y después en G14. G15 tiene obligaciones previas y posteriores. No exigir la observación del futuro despliegue como condición de ese mismo despliegue; tampoco declarar terminado el piloto sin sus verificaciones posteriores.

T22 y T26 conservan su dependencia de `online_payment`. T52 conserva su relación con WhatsApp y añade la superficie de notificaciones duraderas: se activa por esa cola, no por tener pago. T66 se mantiene en G15. T71 exige búsqueda visual y no aplica al N0 propuesto.

`IN_SCOPE` y `OUT_OF_SCOPE` en el índice son planificación condicional, no resultados de pruebas. Un caso seleccionado permanece `NOT_RUN` hasta ejecutarse. Un `NOT_APPLICABLE` operativo exige condiciones verificadas, motivo, evidencia y un ejecutor autorizado. Datos desconocidos no se convierten en condiciones falsas.

## Recuperación del piloto

Separar lógicamente diseño, catálogo, revisión operativa, derechos y registro manual, aunque la salida del sitio sea estática. Preservar el historial autorizado de cambios y revocaciones fuera de la reversión de presentación.

La prueba no termina cuando una copia vuelve a cargar. Debe conservar COP 28.000 vigentes, agotados/pausas y activos revocados, y mantener intacta una aceptación anterior a COP 25.000. Normalmente eso implica reconstruir la presentación anterior con las autoridades actuales y obtener un nuevo candidato compatible. Si no se puede demostrar vigencia, recuperar en aislamiento y confirmar, corregir hacia adelante o degradar; no republicar a ciegas el HTML viejo.

El registro manual conserva decisión, actor, momento, referencia y condiciones, sin copiar conversaciones innecesarias. No necesita convertirse por ello en una plataforma de pagos. Su restauración, retención y salida sí deben probarse dentro del alcance real.

## Secuencia de adopción

1. Ejecutar G00 en un commit concreto y mapear los contratos; registrar qué ya existe y qué falta.
2. Adaptar lectura de versiones, identificadores y esquemas; rechazar G04 como contrato activo.
3. Integrar derivación de obligaciones por perfil/contexto, verificación de supuestos y procedencia del ejecutor. Las herramientas de este paquete son controles de referencia, no un servicio de autorización de producción.
4. Integrar o implementar D01–D06, revisión humana y huellas. Mantener lo no integrado como bloqueo, no llenar un JSON con `PASS`.
5. Implementar las pruebas aplicables y guardar ejecuciones separadas del catálogo. Conservar las garantías de seguridad y recuperación del piloto.
6. Producir un candidato nuevo, revisar y publicar según sus compuertas; después ejecutar G14 y las obligaciones posteriores de G15.

No ejecutar automáticamente capacidades futuras por aparecer en el catálogo. El piloto sigue sin pagos integrados, reservas automáticas, cuentas de comensales, lealtad o despacho.
