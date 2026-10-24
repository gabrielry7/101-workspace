# H0 — revisión humana en curso

Fecha: 2026-10-09. Base inspeccionada: `3f2d2f36e1617ae600237b6b289473e8209554bc`.

Esta revisión recoge feedback directo del usuario. No declara aprobación humana global de H0 ni modifica los cierres técnicos históricos. No implementa otro hito.

## Requisito solicitado por el usuario

La plataforma debe conservar un objetivo funcional de lo que debería ofrecer una página si dispusiera de todos los datos necesarios. Una entrega válida con pocos datos puede seguir siendo funcionalmente insuficiente. En su aclaración posterior, el usuario prioriza saber qué falta, qué se puede agregar después y qué datos hacen falta; la nota de 1 a 10 queda secundaria y no es requisito de esta corrección.

Las funciones deseadas que no puedan habilitarse deben permanecer pendientes, con motivo y siguiente paso. La plataforma debe documentar cómo incorporar esas funciones de forma reutilizable para futuros clientes, aunque no se activen para el cliente actual. El usuario señala reservas como función importante para evaluar un restaurante.

## Lo que existe y lo que falta

H0 separa datos, perfil, capacidades y plan, con cinco estados de evidencia. H2 incorpora un registry semántico, prioridades, dependencias, requisitos y omisiones por scope. Esas prioridades ordenan planificación; no son pesos de una nota funcional ni un baremo de excelencia.

El planner exige datos/evidencia antes de emitir módulos y conserva bloqueos. Actualmente reserva es una intención de acción externa, no un motor de reservas ni una implementación conectada. La ausencia del runtime comercial y backend permanece explícita.

Falta comprobar y completar un inventario reutilizable de requisitos para todas las capacidades, además del diagnóstico particular de lo que puede emitirse hoy. Debe relacionarse con el registry y los requisitos existentes, evitando una segunda lista desconectada. Esta revisión no afirma que el inventario completo esté implementado.

## Propuesta para revisar

Separar corrección técnica, funciones disponibles, funciones futuras y estado de preparación de cada función. Una capacidad planificada o un botón renderizado no equivale a una función operativa.

El objetivo puede componerse desde arquetipos y necesidades aprobadas, usando capacidades compartidas; no requiere una plantilla o código por sector. La aplicabilidad debe declararse y justificarse por negocio/sucursal. No se exige domicilio a todo restaurante, ni se infieren permisos o capacidades desde un objetivo editorial. UNKNOWN permanece como pendiente de aclaración, sin retirarlo del objetivo para inflar la nota. Una exclusión por no aplicabilidad necesita evidencia y una versión nueva del objetivo.

La propuesta anterior de puntos por función no fue ratificada y se retira del alcance principal tras la aclaración del usuario. El resultado importante es una lista accionable, no un número.

La evaluación debe conservar versión del catálogo de requisitos, objetivo y scope, evidencia de cada resultado, bloqueos e incertidumbre. No esconder necesidades desconocidas ni presentar promesas como funciones construidas.

## Fichas reutilizables de implementación futura

Por función: objetivo del usuario, variantes y nivel ofrecido, datos/evidencias/permisos mínimos, dependencias de UI e integración, estados pendientes/error/éxito, alcance de sucursal, criterios de prueba y siguiente paso. Distinguir diseño documentado de implementación probada e integración operativa.

Para reservas, diferenciar contacto o solicitud, enlace aprobado a un proveedor externo y confirmación gestionada por un sistema conectado. No anunciar confirmación en una mera solicitud. El flujo conectado debe especificar sucursal, fecha/hora/zona horaria, comensales, disponibilidad, confirmación, cancelación, errores y tratamiento de datos personales. Es una especificación futura; no prueba implementación actual ni autoriza construir backend, compras o integraciones.

## Correcciones acumuladas para el prompt final

El usuario pide anotar las correcciones durante la revisión humana y preparar un prompt único para Codex al terminar. Se documentan requisitos ahora; implementación, cambios contractuales, integraciones y commits de corrección quedan para esa instrucción consolidada. No se interpreta este feedback como aprobación global de H0.

- H0-C01: inventariar requisitos de datos, evidencias y permisos por cada capacidad y nivel de servicio del registry; no limitar la lista a los datos presentes en el fixture.
- H0-C02: generar una comparación por negocio/sucursal entre objetivo funcional, datos existentes y requisitos faltantes. Conservar función pendiente y siguiente paso; separar no aplicable justificado de desconocido.
- H0-C03: distinguir datos que debe aportar/verificar el negocio o upstream, configuración del proyecto, permisos de terceros e implementación/conectividad que debe aportar la plataforma. Tener datos suficientes no demuestra software ni integración disponibles.
- H0-C04: documentar una ficha reutilizable por función con comportamiento esperado, variantes, dependencias y pruebas de aceptación. Marcar explícitamente especificado, implementado y verificado; no afirmar que sabemos implementarla por tener una lista de campos.
- H0-C05: presentar una lista accionable de qué funciona hoy, qué puede agregarse, qué falta y cómo completarlo. El score no es prioritario.
- H0-C06: definir una sola vez un catálogo maestro reutilizable de requisitos por tipo de página/negocio. Todos los restaurantes consultan el mismo catálogo y las mismas reglas de función/nivel; cada negocio aporta valores y evidencia distintos. No generar o redactar nuevamente los requisitos para cada cliente. El catálogo debe cubrir el objetivo completo, no sólo lo emitible con los datos actuales.

La aclaración del usuario es que debemos saber por adelantado qué datos pedir para cada tipo de página. Implementar este criterio posteriormente como una base común más requisitos compartidos por capacidad, agrupados por tipo/arquetipo, con versión y condiciones explícitas. Es una plantilla de requisitos de datos, no una plantilla visual ni código específico por sector. Datos de sucursal y variantes de servicio usan las mismas definiciones. Una condición no aplicable debe justificarse; la falta de datos permanece pendiente y no modifica la lista maestra. Funciones compartidas, como contacto o reservas, reutilizan su definición entre tipos, evitando catálogos duplicados que diverjan.

Ejemplos iniciales para orientar el inventario, no lista exhaustiva ni esquema aprobado:

| Función | Datos/configuración que deben especificarse | Dependencias y verificaciones |
|---|---|---|
| Menú/precios | Ofertas por sucursal, nombres/descripciones aprobados, precios vigentes y moneda si se muestran importes, restricciones/alérgenos sólo si están documentados | Permiso de publicación, referencias correctas, render fiel y sin datos inventados |
| Ubicación | Sucursal, dirección aprobada, coordenadas cuando correspondan, instrucciones de llegada | Destino cartográfico verificado si se usa, política/permisos del proveedor si hay mapa integrado |
| Horarios | Horario por sucursal, zona horaria, fechas de vigencia, excepciones y festivos conocidos | Interpretación temporal y actualización verificables |
| Contacto | Canal por sucursal, teléfono/correo/URL aprobados, destino y finalidad | Navegación válida; formulario requiere recepción real, gestión de errores y tratamiento de datos |
| Solicitud de reserva | Sucursal, canal receptor aprobado, campos necesarios, reglas del negocio y texto que explica que falta confirmación | Recepción real y respuesta/errores; no prometer mesa confirmada |
| Reserva confirmada | Sucursal, turnos/zona horaria, capacidad y disponibilidad, comensales, reglas, datos mínimos del solicitante y cancelación | Sistema autorizado conectado, prevención de doble reserva, confirmación verificable, errores y privacidad |

Al revisar H1 y siguientes, ampliar y contrastar este inventario con sus capacidades reales. No construir las funciones futuras durante esta toma de notas.

## Evidencia y estado

Durante la preparación de esta revisión pasaron las 32 pruebas actuales de `tests/contracts.test.ts`. Los tres fixtures manuales se inspeccionaron y el inspector local respondió correctamente. Eso verifica guardas de H0, no el baremo solicitado.

Hallazgo documental: el inspector actual mezcla información de H0 y avances posteriores y mantiene textos de pendientes desactualizados. Queda anotado para una corrección acordada; la revisión no modifica evidencia histórica.

Estado: criterio del usuario registrado y aclarado; inventario exhaustivo y fichas deben concretarse en la corrección posterior. H0 sigue en revisión humana. No se inicia H1 ni otro hito desde esta revisión.
