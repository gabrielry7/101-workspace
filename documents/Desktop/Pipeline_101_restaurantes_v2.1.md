# Pipeline 101: páginas de restaurante automatizadas

**Versión 2.1 — 3 de octubre de 2026**  
Documento original: 1 de octubre de 2026. Versión 2.0: 3 de octubre de 2026.  
Cambios de la 2.1: fase 3 reescrita con rúbrica de calidad, G04 dividida en G04a y G04b, y sección nueva «Mínimo del piloto».  
**Estado: especificación corregida; implementación y validación del producto pendientes de comprobar en el repositorio.**

## Punto de partida

101 busca producir y mantener sitios de restaurantes que permitan consultar información confiable y realizar una acción que el negocio pueda atender. La unidad de entrega no es solamente una página: es una versión publicable, su evidencia, una operación definida y un mecanismo para actualizarla sin romperla.

Esta revisión conserva las siete fases, las cuatro capas transversales y la separación entre investigación, construcción y compuertas del original [D0]. Integra las correcciones de la auditoría en cada fase; no es un apéndice que deje vigentes las reglas anteriores.

### Qué sabemos y qué falta verificar

| Pieza | Lo reportado por el documento original | Tratamiento en esta versión |
| --- | --- | --- |
| `101-world-model` | Evidencia → Truth → SiteSpec → compilador → Astro → QA; resultados históricos de 0/3 y 0/9 sitios listos | Reporte histórico, no diagnóstico actual. Verificar código, rama, commit y pruebas reproducibles |
| Design Compiler | Experimentos v0.1–v0.12, operadores de composición, crítica visual y corpus de componentes de código abierto | Candidato a reutilización; no se da por integrado ni validado por humanos |
| Restaurant Commerce V4 | Menú, carrito, pagos, reservas, lealtad y domicilios; reporte de 79 pruebas | No equivale a integración operativa ni a pruebas actuales contra proveedores reales |
| Inventario de Bogotá | 114.028 candidatos comerciales desde Overture | Cifra del original. No equivale a restaurantes activos, clientes autorizados ni negocios verificados |
| Integridad de contenido | Versiones contradictorias sobre 2/7 servicios, 32 pérdidas y reparación `9f7cefd` | Estado **no verificado**. Se resuelve reproduciendo el problema sobre el commit seleccionado, no eligiendo un resumen |

Las menciones a `AGENTS.md`, `docs/SYSTEM_REGISTRY.md`, `INTEGRATE_INTO_101.md`, `V4_SCHEMA_DELTA.md`, `WebsiteCompiler` y `@101/site-runtime` provienen de [D0]. Esta revisión no certifica su contenido ni compatibilidad actuales.

**Convenciones de evidencia.** “Reportado” significa que aparece en el original; “propuesto” significa una decisión de esta especificación; “verificado” exige una ejecución o revisión identificada y evidencia accesible. Una tarea escrita, un esquema válido y una prueba definida no son una funcionalidad implementada. Todas las pruebas del catálogo adjunto empiezan como `NOT_RUN`.

### Alcance inicial adoptado

El primer producto será un sitio autorizado de **una sede**, en español, con menú en HTML, horarios, ubicación, contacto y mantenimiento de contenido. El piloto incorpora una solicitud de pedido por WhatsApp con recepción y aceptación registradas por el restaurante; no promete envío automático ni cobro integrado.

Quedan fuera del primer hito: pagos integrados, confirmación automática de reservas, despacho de domicilios, cuentas de comensales, puntos y promociones complejas. Sus contratos se definen aquí para no construir callejones sin salida, pero no bloquean el piloto mientras estén deshabilitados y no se anuncien.

El prototipo comercial elaborado para un prospecto es otra modalidad: **vista previa privada, sin ventas, sin reservas reales y sin presentarse como el sitio oficial**. Puede mostrar faltantes expresamente; no puede saltarse los permisos necesarios para usar contenido de terceros. Pasar de prototipo a sitio público requiere autorización verificable del negocio.

## Qué es una página GOAT para un restaurante

“GOAT” se conserva como nombre del objetivo del proyecto, no como certificación ni afirmación de superioridad sobre Rappi, Instagram o Google. El objetivo es que la persona encuentre lo que necesita y que el restaurante pueda cumplir la acción ofrecida. Una mejora comercial se demuestra; no se deduce de que el sitio sea atractivo.

| Capa | Pregunta | Evidencia de aceptación |
| --- | --- | --- |
| 1. Verdad | ¿Las afirmaciones tienen respaldo vigente, sede correcta y permiso de publicación? | Cobertura de afirmaciones, vigencia, conflictos resueltos y ausencia de filtraciones |
| 2. Utilidad | ¿La persona encuentra menú, precio, sede, horario y acción principal? | Tareas de uso observadas, en móvil, teclado y tecnologías de asistencia |
| 3. Función | ¿La acción llega al estado que la interfaz afirma? | Evidencia de recepción, aceptación y cumplimiento cuando corresponda; fallos controlados |
| 4. Descubrimiento | ¿La información pública es accesible y comprensible para buscadores? | HTML, enlaces, metadatos y datos estructurados coherentes; indexación observada por separado |
| 5. Estética | ¿La composición es legible, consistente y se reconoce de ese restaurante? | Piso automático (G04a) y rúbrica de once criterios aplicada por personas (G04b, fase 3L); comparación ciega cuando haya con qué comparar |

Estas capas no se promedian: una buena estética no compensa un precio falso, un dato privado filtrado o una reserva inexistente. La accesibilidad, la seguridad y la operación atraviesan todas las capas. Verdad verificable tampoco significa certeza absoluta: el sistema puede comprobar trazabilidad, coherencia y vigencia registrada; necesita confirmación humana para hechos que no observa directamente.

Decisiones del producto: diseño móvil primero; menú legible en HTML con PDF opcional como descarga, nunca como único acceso; una acción principal por contexto; fotos auténticas cuando existan derechos suficientes; alternativa tipográfica cuando no las haya. El canal directo tiene costos y no se venderá como “sin comisiones” o “ahorro garantizado”.

## Principios del pipeline

| Tipo | Qué es | Cómo termina |
| --- | --- | --- |
| **[I] Investigación** | Una incertidumbre técnica, de uso o de negocio | Hallazgo, límites y decisión o experimento reproducible |
| **[C] Construcción** | Una obligación definida que falta implementar o integrar | Código identificado, pruebas ejecutadas y evidencia del comportamiento |
| **[G] Compuerta** | Regla que autoriza o bloquea una transición | Resultado, versión evaluada, evidencia, motivo y ruta de reparación |

1. **Reusar antes de construir.** Inspeccionar el repositorio y registrar qué se reutiliza, adapta o descarta. No reconstruir módulos basándose únicamente en resúmenes.
2. **Ninguna afirmación factual se inventa.** Tener una fuente no basta: importan su fecha, alcance, autoridad y restricciones. La aprobación del dueño es evidencia pertinente, no permiso universal sobre obras o datos ajenos.
3. **Público no significa todo lo conocido.** Se publica una proyección permitida del paquete; nunca el paquete completo.
4. **Capacidades antes de composición.** Se eligen en la fase 2; se implementan en la fase 4. No son niveles obligatorios.
5. **Actualizar no es rediseñar.** Cambiar un precio conserva el diseño y ejecuta las comprobaciones afectadas; no activa exploración estética.
6. **Aprobar una versión, no una idea.** Cada aprobación y cada reporte se vinculan a contenido y artefactos concretos. No se reutilizan tras un cambio incompatible.
7. **La operación confirma sus propios resultados.** Un clic, un mensaje preparado, un pago y un pedido aceptado son hechos distintos.
8. **Compuertas duras; exploración acotada.** No se relajan los controles para que una iteración pase. Los presupuestos de generación se fijan antes de ejecutar.
9. **Humano en el circuito.** Al inicio se aprueban datos, publicación y diseño. El modelo que genera no autoriza su propia publicación.
10. **Horizontal por dentro, restaurante por configuración.** Las capacidades usan contratos generales; sedes, menú, modificadores y reglas operativas se expresan en modelos y configuración. La compatibilidad con las reglas reales de `AGENTS.md` se verifica en G00.
11. **Fallar de forma segura.** Una dependencia desconocida no cuenta como aprobada. Se retira la capacidad afectada o se bloquea la publicación, según su impacto.
12. **No confundir especificación con ejecución.** `NOT_RUN`, evidencia inexistente o prueba vacía no son `PASS`.

## Mapa general

Se mantienen siete fases y cuatro capas transversales: A, plataforma; B, seguridad; C, infraestructura; D, legal, operación y negocio. Antes de integrar se verifica el estado real del repositorio mediante G00.

```text
G00: inventario técnico y compatibilidad
          ↓
1. Evidencia y datos del restaurante
          ↓
2. Capacidades, estrategia y contenido
          ↓
3. Diseño dentro de esas capacidades
          ↓
4. Implementación funcional y contratos operativos
          ↓
5. Compilación → pruebas → reparación acotada
          ↓
6. Aprobación de versión → publicación → comprobación real
          ↓
7. Medición, actualización y aprendizaje
          ├─ cambio de datos → 1 → comprobaciones afectadas → 6
          ├─ cambio de capacidades → 2 → 3/4/5 → 6
          └─ experimento de diseño → 3 → 5 → aprobación → 6
```

| Fase | Entrada | Salida identificada y versionada |
| --- | --- | --- |
| 1 | Evidencia permitida, autorización y datos del negocio | `RestaurantDataBundle`, `AssetRightsManifest`, `PublicationProjection` |
| 2 | Paquete y restricciones operativas | `CapabilityPlan`, `SitePlan`, `ClaimMap`, `OperationsPolicy` |
| 3 | Plan de sitio, capacidades y activos permitidos | `ArtDirection`, `DesignSpec` y registro de decisiones visuales |
| 4 | Contratos de datos, capacidades y diseño | Implementaciones/configuraciones y `BackendContract` |
| 5 | Entradas anteriores y versiones de código | Artefactos, `ReleaseManifest` y `GateReport` |
| 6 | Candidato, reportes y aprobación vigente | `ApprovalRecord`, `DeploymentRecord`, evidencia de producción |
| 7 | Eventos operativos, analítica y correcciones | `MeasurementReport`, `ChangeRequest`, experimentos y nuevo paquete |

Los nombres anteriores son contratos de esta versión, **no afirmaciones de que ya existen clases con esos nombres**. Los esquemas adjuntos formalizan un subconjunto crítico; la integración debe mapearlos a los modelos reales sin mantener dos fuentes competidoras.

## Fase 1 — Datos del restaurante

**Salida:** paquete verificable y una proyección pública. El paquete no debe contener “todo completo” para investigar o diseñar un borrador. Debe contener lo indispensable para las capacidades que se pretendan publicar.

### 1A. Identidad y autorización

Distinguir `business_id` —negocio— y `location_id` —sede—, con identificadores estables que no dependan de un nombre editable. Un `site_id` puede representar varias sedes, pero el piloto usa una. Toda oferta, horario y destino de pedido indica a qué sede aplica. No se heredan precios u horarios entre sedes sin una regla explícita y aprobación.

Registrar modalidad `prospect_private` o `authorized_live`, persona autorizante, alcance de su autoridad, canal de verificación, fecha y evidencia. Verificar un dominio demuestra control de ese dominio, no por sí solo representación del restaurante. No recopilar documentos de identidad por defecto si un mecanismo menos invasivo resuelve la verificación.

### 1B. Datos por capacidad

| Bloque | Requisito | Cuando falta |
| --- | --- | --- |
| Identidad | Nombre público y sede inequívoca; descripción solo respaldada | Sin identidad verificable no se publica como sitio oficial |
| Ubicación | Dirección confirmada para visita, recogida o atención presencial; coordenadas opcionales verificadas | No inventar marcador. Un negocio sin atención presencial no ofrece “visítanos” |
| Horarios | Zona horaria, intervalos por día, excepciones y distinción local/cocina/pedidos | Mostrar incertidumbre y deshabilitar “abierto ahora” o recepción automática afectada |
| Contacto | Al menos una acción verificada y un responsable que la atienda | No activar el botón ni aceptar solicitudes sin destino válido |
| Menú | Categorías, platos, variantes, precios por sede y reglas de modificadores | No habilitar pedido de productos incompletos; catálogo parcial solo si se declara y aprueba |
| Alérgenos e ingredientes | Afirmaciones explícitamente confirmadas, por plato y variante | “No informado” no equivale a “no contiene”; nunca inferir ausencia desde una foto |
| Fotos y marca | Activos con derechos y calidad suficientes para el diseño escogido | Elegir composición sin fotos; no bloquea por sí sola un sitio informativo |
| Reputación | Fuente, fecha, alcance y permiso/restricciones de presentación | Omitir; no inventar estrellas, testimonios ni posición en rankings |
| Operación | Receptor, tiempos de respuesta, capacidad, disponibilidad y contingencias | Desactivar la capacidad dependiente, no simular su funcionamiento |
| Condiciones comerciales | Precio mostrado, costos adicionales, condiciones y responsable definidos | Bloquear la transacción afectada hasta resolverlos |

### 1C. Contrato de hechos y evidencia

Cada hecho conserva: `fact_id`, clave de campo, valor y unidad, negocio y sede, referencias de origen, fecha de observación, fecha de verificación, persona o proceso verificador, vigencia, fecha límite de revisión, estado de conflicto y aprobación del valor exacto. Los campos modificados crean una revisión; no sobrescriben la evidencia anterior.

Separar cuatro dimensiones:

| Dimensión | Estados o contenido |
| --- | --- |
| Verificación | `unverified`, `verified`, `disputed`, `stale`, `rejected` |
| Publicación | `public_required`, `public_optional`, `internal` |
| Uso permitido | Decisión registrada por activo/dato y superficie de uso |
| Aplicabilidad | Sede, canal, producto, período y capacidad correspondientes |

La publicación se decide en el contexto del plan de sitio: un teléfono puede ser obligatorio en una página de contacto sin ser obligatorio en todas las secciones. Un dato interno jamás se convierte en público por estar “aprobado”. `null` significa desconocido, no falso, cero ni ausencia confirmada.

Conservar el origen crudo solo cuando esté permitido y sea necesario, con control de acceso y retención. Un enlace o una huella criptográfica —identificador calculado del contenido— ayuda a rastrear evidencia, pero no concede derecho a almacenar o publicar la obra. Los registros privados de autorización no se incluyen en el HTML ni en los archivos públicos de auditoría.

**Conflictos:** la fuente más reciente no gana automáticamente. Comparar sede, canal y autoridad; pedir confirmación a la persona pertinente; guardar la resolución y el valor descartado. Una confirmación del precio directo no modifica retrospectivamente el precio de una plataforma de domicilios. La generación puede proponer una resolución, nunca marcarla como confirmación humana.

### 1D. Vigencia y mantenimiento

Política inicial propuesta para el piloto, modificable mediante decisión versionada: revisar precios del catálogo al menos cada 30 días; horarios regulares cada 14 días; identidad y contacto cada 90 días. Son plazos de control, no garantías de que no haya cambios entre revisiones. Un cambio notificado invalida de inmediato el dato anterior para nuevas operaciones, aunque no haya vencido el plazo.

Las excepciones de horario tienen fecha concreta. Las disponibilidades operativas se consultan al confirmar una solicitud y, con operación integrada, inmediatamente antes de reservar inventario o cobrar. El objetivo de actualización en clientes conectados es de 60 segundos como máximo, más una revalidación obligatoria al actuar; es una política a probar, no una promesa de sincronización instantánea.

Al vencer una revisión, un dato obligatorio para una promesa operativa no puede seguir sosteniéndola: se confirma, se retira o se sustituye la acción por un contacto explícitamente sujeto a confirmación. El vencimiento por sí solo no obliga a borrar toda la página. Si se desconoce identidad o autorización, sí se bloquea la publicación oficial.

### 1E. Menú y dinero

Usar identificadores estables de producto, variante y modificador. Registrar mínimos/máximos de selección, combinaciones válidas, disponibilidad por sede y canal, y si un precio es fijo o depende de una configuración. Un “desde” requiere que exista una configuración realmente comprable por ese valor.

El importe se almacena como entero con moneda y escala explícita; no como texto formateado ni número de coma flotante. En este contrato `amount_minor` usa centavos para COP: COP 25.000 corresponde a `2500000`, con `minor_unit_exponent = 2`. El adaptador debe comprobar esta unidad; Wompi documenta `amount_in_cents` [S7]. La interfaz presenta pesos colombianos, no centavos.

El total separa productos, modificadores, descuentos, impuestos o cargos aplicables y domicilio. La política tributaria y de presentación requiere aprobación legal; no se inventa desde el tipo de cocina. Las reglas de redondeo son únicas, documentadas y probadas. No se agrega una propina ni un cargo no aceptado.

Extraer un menú desde imágenes o PDF produce **borradores**: revisar precios, símbolos, variantes y notas contra el original y con el negocio. Una confianza alta del modelo no reemplaza esa verificación. Una carta legible no prueba que siga vigente.

### 1F. Derechos de uso

`AssetRightsManifest` registra identificador, procedencia, titular o fundamento de uso, evidencia, superficies autorizadas, atribución, restricciones de almacenamiento y transformación, plazo y estado. Se aplica a fotos, reseñas, logos, textos, tipografías y componentes de terceros.

Google Places impone requisitos propios de presentación, atribución y almacenamiento; encontrar allí contenido no autoriza a descargarlo y convertirlo sin más en un activo del restaurante [S2]. El dueño tampoco puede conceder derechos que no tiene. Para cada proveedor se verifica el uso concreto; no se crea un permiso genérico “tomado de internet”.

Estados: `cleared`, `pending`, `denied`, `expired`, `revoked`. Solo `cleared`, dentro de su alcance y con sus condiciones cumplidas, permite uso. Una revocación abre una retirada que incluye copias públicas, miniaturas, cachés controlables y composiciones derivadas. No se promete borrar copias ajenas fuera del control de 101.

### Pasos y compuertas

1. **[C]** Mapear el esquema propuesto a los modelos reales, con G00 y sin duplicar catálogos.
2. **[C]** Verificar modalidad, identidad y autorización; registrar sedes y destinos.
3. **[I]** Evaluar extracción de cartas con errores medidos por campo, especialmente precios.
4. **[C]** Capturar evidencia permitida y solicitar únicamente los faltantes al dueño.
5. **[C]** Resolver conflictos, asignar vigencia, clasificar publicación y confirmar valores.
6. **[C]** Revisar derechos, clasificar fotos y extraer marca sin convertir inferencias en hechos.
7. **[G] G01 — Datos e identidad.** Están completos y vigentes los campos obligatorios de las capacidades solicitadas; no hay mezcla de sedes ni conflictos críticos abiertos.
8. **[G] G02 — Derechos.** Todo recurso usado tiene permiso suficiente y condiciones satisfechas. Si faltan fotos, se vuelve al diseño compatible, no se inventan.

**Aceptación clave:** introducir un precio erróneo, un horario vencido, una nota interna y una foto sin permiso debe producir cuatro hallazgos distintos y ninguna publicación silenciosa.

## Fase 2 — Capacidades, estrategia y contenido

**Salida:** `CapabilityPlan`, `OperationsPolicy`, `SitePlan` y `ClaimMap`. Aquí se define qué podrá hacer el visitante y qué debe existir del lado del restaurante antes de decidir el diseño.

### 2A. Capacidades, no escalera de niveles

| Identificador | Capacidad | Dependencias necesarias | No demuestra por sí misma |
| --- | --- | --- | --- |
| `public_info` | Identidad, ubicación aplicable, horarios y contacto | Datos y autorización | Disponibilidad en tiempo real |
| `menu_html` | Menú público legible | Catálogo confirmado y proyección pública | Existencias reservadas |
| `whatsapp_contact` | Abrir conversación | Número verificado y texto de interfaz correcto | Envío o lectura de un mensaje |
| `whatsapp_request` | Preparar solicitud desde carrito | `menu_html`, `whatsapp_contact`, reglas de pedido y receptor | Recepción, aceptación o pago |
| `reservation_request` | Solicitar una reserva | Canal de recepción, reglas y responsable | Cupo confirmado |
| `reservation_confirmed` | Confirmación de reserva controlada | Autoridad sobre cupos, concurrencia, vencimiento y sincronización de otros canales | Que nunca haya inasistencia |
| `online_payment` | Pedido y pago integrado | Catálogo autoritativo, gestión de pedidos, proveedor validado y conciliación | Aceptación o entrega del pedido |
| `delivery_dispatch` | Solicitar y seguir un despacho | Pedido aceptado, zona/costo, proveedor probado y contingencias | Entrega efectiva |
| `customer_accounts` | Acceso e historial personal | Autenticación, privacidad, recuperación y aislamiento | Consentimiento para marketing |
| `loyalty` | Reglas de beneficios | Identidad o mecanismo equivalente, libro de movimientos y reglas aprobadas | Ventas adicionales causadas por el programa |

Una reserva no depende del carrito por WhatsApp. El despacho no exige que el pago haya sido en línea si existe una política válida de otro medio. Lealtad y domicilios son capacidades distintas. Cada dependencia adicional se declara expresamente; la interfaz nunca anuncia capacidades deshabilitadas.

Toda capacidad tiene: estado solicitado/habilitado, sedes, dependencias, modo manual o automático, responsable, datos necesarios, timeout operativo, mensaje al visitante, procedimiento de contingencia y pruebas obligatorias. Sus límites no se adivinan desde un arquetipo.

### 2B. Política operativa mínima

Antes de habilitar solicitudes, el dueño debe aprobar quién recibe y quién reemplaza a esa persona, en qué horario, cómo acepta/rechaza, qué hace si no puede cumplir, y cómo informa al cliente. Se documentan tiempos objetivo internos y cualquier tiempo comunicado al público. No se publica “confirmación en cinco minutos” sin capacidad y aprobación para sostenerlo.

Sin respuesta, la solicitud permanece sin confirmar y vence según la política elegida; **nunca se acepta por silencio**. Si un proveedor cae, se pausa la acción automática y se muestra un canal alternativo confirmado, no un botón que simule éxito.

### 2C. Estrategia y arquitectura

1. **[I]** Investigar entre cuatro y seis arquetipos como hipótesis de necesidades, no como plantillas rígidas.
2. **[C]** Clasificar con posibilidad de corrección humana; un dato desconocido no se rellena para encajar.
3. **[C]** Elegir la acción principal y sus estados: disponible, fuera de horario, pendiente, error y sin conexión.
4. **[C]** Definir capacidades y aprobar su política operativa antes de componer.
5. **[I]** Mantener un catálogo de secciones con requisitos y razones de omisión.
6. **[C]** Armar páginas y secciones desde la proyección pública permitida.
7. **[C]** Redactar textos y metadatos desde hechos confirmados y microtextos funcionales revisados.
8. **[C]** Seleccionar destacados mediante decisión del negocio o evidencia admisible. “Más vendido” exige datos de ventas; “recomendado” no significa lo mismo.

### 2D. Afirmaciones, omisiones e información interna

`ClaimMap` vincula cada afirmación factual publicada con hechos y transformaciones verificables. Incluye texto visible, títulos de buscadores, descripciones, datos estructurados, textos alternativos y mensajes de estados. “Ver menú” es una instrucción, no una afirmación factual que necesite una fuente. “100 % orgánico” sí la necesita. Una afirmación derivada, como “abierto ahora”, registra los hechos de horario, la hora de evaluación, la zona horaria y la regla utilizada.

Definir tres conjuntos por superficie:

- **Públicos obligatorios:** deben aparecer correctamente en el lugar o flujo estipulado; no basta esconderlos en HTML o metadatos.
- **Públicos opcionales:** pueden omitirse con razón explícita, por ejemplo falta de relevancia, espacio o derechos. La omisión no implica pérdida accidental.
- **Internos:** no salen a HTML, JSON del navegador, registros públicos, mapas de fuentes, archivos de compilación descargables ni eventos analíticos públicos.

Un hecho obligatorio en el menú no tiene que repetirse en la portada. La cobertura se mide sobre la especificación de publicación, no sobre “todos los datos aprobados”. Una reescritura que cambie el sentido factual invalida la aprobación del texto afectado.

**[G] G03 — Capacidades y contenido.** Dependencias resueltas; acción principal respaldada; afirmaciones trazables; obligatorios cubiertos; omisiones justificadas; ausencia de datos internos y promesas de funciones deshabilitadas.

## Fase 3 — Diseño

**Salida:** `DesignSpec`, con dirección de arte, tokens visuales, composición por ruta y estado, reglas responsivas, activos autorizados, versiones y el registro de decisiones. Se conserva la tesis del Design Compiler: generar composiciones legales, renderizar, comparar y mutar, sin permitir que la exploración cambie los hechos.

El diseño tiene un **piso** y un **techo**. El piso es lo que no puede estar roto: texto cortado, solapes, contraste insuficiente, acción escondida. Se comprueba por máquina. El techo es que la página se vea hecha por un estudio y se sienta de ese restaurante. Se juzga con una rúbrica y lo deciden personas. La versión 2.0 solo definía el piso; esta fase define los dos y los separa en dos compuertas, G04a y G04b.

Todo lo numérico de esta fase es una **propuesta inicial** para el piloto, no un estándar. Se ajusta por decisión versionada después de ver páginas reales, nunca para hacer pasar un candidato.

### 3A. Qué se considera buen diseño aquí

Ocho criterios de producto. Son la respuesta de este proyecto a «qué es una página GOAT» en la capa estética, y de ellos sale la rúbrica de 3L.

1. **La comida y el lugar hablan; la interfaz se calla.** Lo que el visitante recuerda es un plato, un espacio o un nombre, no un botón ni un efecto.
2. **Una sola cosa domina cada pantalla.** En cada viewport hay un elemento principal evidente; lo demás se subordina en tamaño, peso o posición.
3. **El menú se lee como una carta bien compuesta.** Nombre, descripción y precio se distinguen de un vistazo, y recorrer cincuenta platos no cansa.
4. **Se reconoce de quién es.** Si se cambia el logo por el de otro restaurante y la página sigue pareciendo válida, falló. Esta es la prueba del intercambio.
5. **La audacia se gasta en un solo lugar.** Una decisión memorable (una tipografía de titulares, un color, un tratamiento de foto, una retícula) y todo lo demás en silencio.
6. **Pocas decisiones, repetidas con disciplina.** Dos familias tipográficas como máximo, una escala de espacios, una paleta corta. La consistencia es lo que se percibe como acabado.
7. **Se usa con una mano y con prisa.** El visitante típico está en la calle, con el teléfono, decidiendo dónde comer en los próximos minutos.
8. **Nada finge.** Sin fotos de archivo que pasen por platos propios, sin testimonios decorativos, sin urgencia fabricada. Coincide con la capa de verdad.

### 3B. Niveles de automatización del diseño

El diseño no se automatiza de una vez. Cada nivel se habilita cuando el anterior produce páginas que pasan G04b con revisión humana; reducir esa revisión exige G16.

| Nivel | Qué decide una persona | Qué decide el sistema | Cuándo |
| --- | --- | --- | --- |
| N0. Patrón a mano | Dirección de arte, tokens, composición | Nada; el agente ayuda a construir | Hito 1 |
| N1. Tokens sobre patrón | Aprueba dirección y resultado | Paleta, pareja tipográfica y escala derivadas de la marca, sobre composiciones ya aprobadas | Hito 2 |
| N2. Variantes por sección | Aprueba resultado | Además, elige la variante de cada sección según contenido y activos | Después del hito 2 |
| N3. Exploración | Aprueba resultado y fija presupuesto | Además, genera y muta composiciones con el Design Compiler | Cuando G00 confirme qué módulos sirven |

El piloto se hace en N0. Lo que se aprende al diseñar a mano la primera página, es decir, qué decisiones se tomaron y por qué, es el insumo de N1.

### 3C. Sistema base

Antes de cualquier dirección de arte existe un sistema de tokens común. Es el vocabulario dentro del cual el agente elige; la calidad viene de que el vocabulario sea bueno, no de que la búsqueda sea amplia.

| Token | Propuesta inicial | Por qué |
| --- | --- | --- |
| Texto corriente | 16 a 18 px CSS en móvil; interlineado 1,5 a 1,6 | Lectura cómoda de descripciones de platos |
| Titulares | Interlineado 1,05 a 1,2; máximo tres líneas en móvil | Evitar bloques de título que empujan el contenido fuera de pantalla |
| Escala tipográfica | Razón 1,2 en móvil y 1,25 a 1,333 en escritorio; cinco o seis pasos | Jerarquía clara sin tamaños arbitrarios |
| Medida | 45 a 75 caracteres por línea en texto corrido | Líneas más largas cansan; más cortas cortan el ritmo |
| Espaciado | Escala única en píxeles CSS: 4, 8, 12, 16, 24, 32, 48, 64, 96 | Todo espacio sale de la escala; ninguno se inventa por sección |
| Márgenes | 16 a 20 px en móvil; columna de contenido de 1120 a 1200 px como máximo; columna de texto hasta 680 px | Alineaciones estables entre secciones |
| Retícula | 4 columnas en móvil, 12 en escritorio | Permite asimetría sin perder alineación |
| Radios y bordes | Una sola familia de radios por dirección; el radio comunica jerarquía, no se aplica igual a todo | Evitar el aspecto de «tarjetas por todas partes» |
| Sombras | Ninguna por defecto; una como máximo si la dirección la justifica | La profundidad compite con la foto |
| Proporciones de imagen | Un conjunto cerrado por sitio, por ejemplo 4:5, 1:1 y 3:2 | Miniaturas de menú consistentes |

Los tokens se guardan en `DesignSpec` con nombre de rol, no de valor: `color.accion`, `espacio.seccion`, `tipo.plato`. Cambiar la dirección cambia valores, no componentes.

### 3D. Dirección de arte

**Entradas:** activos de marca con derechos (logo, carta impresa, letrero, fachada, vajilla, empaques), fotos disponibles y su calidad, rango de precio, tipo de cocina, referentes que le gustan al dueño, arquetipo de la fase 2 y capacidades habilitadas.

**Salida:** `ArtDirection`, un registro corto que fija estos ejes y la razón de cada uno:

| Eje | Valores de referencia | De dónde sale |
| --- | --- | --- |
| Temperatura | Cálida, neutra, fría | Materiales y luz del lugar; colores de la comida |
| Densidad | Aireada, media, compacta | Tamaño de la carta y rango de precio |
| Contraste | Suave, medio, alto | Marca existente y calidad de las fotos |
| Formalidad | Popular, casual, formal | Cómo habla y cómo se viste el restaurante |
| Dependencia de foto | Ninguna, apoyo, protagonista | Cantidad y calidad de fotos con derechos |
| Voz tipográfica | Pareja concreta de familias y su papel | Letrero, carta impresa, época y tono |
| Elemento firma | Una sola decisión memorable | Lo más característico del mundo de ese restaurante |

La dirección se deriva del mundo del restaurante, no de una lista de estilos. El letrero pintado de una fritanguería, el mantel de un restaurante de manteles o el tablero de tiza de una cafetería dicen más sobre cómo debe verse la página que el arquetipo. Los arquetipos de la fase 2 orientan necesidades; no asignan un estilo.

**Valores por defecto que se evitan.** Son las salidas a las que tiende un generador cuando no decide nada, y por eso hacen que todas las páginas se parezcan:

- Fondo crema con serif de alto contraste y acento terracota, aplicado a cualquier cocina.
- Fondo casi negro con un único acento ácido.
- Contenido partido en tarjetas idénticas con el mismo radio y la misma sombra gris.
- Etiqueta pequeña en mayúsculas espaciadas encima de cada título.
- Degradados como decoración y una palabra del titular en otro color o en cursiva.
- Animación de entrada en cada sección.

Ninguno está prohibido si el restaurante lo pide o su marca ya lo usa. Están prohibidos como elección por omisión: usarlos exige una razón registrada en `ArtDirection`.

**Procedimiento.**

1. **[C]** Reunir los activos de marca permitidos y describir en una frase el mundo del restaurante.
2. **[C]** Proponer dos o tres direcciones distintas. Cada una se muestra como un tablero con su paleta, su pareja tipográfica, una portada y un tramo de menú, todo con contenido real del restaurante.
3. **[C]** Revisar cada dirección contra la lista de valores por defecto y contra la prueba del intercambio; descartar o corregir la que no la pase.
4. **[C]** Elegir una con la persona revisora y el dueño. Registrar la elegida, las descartadas y los desacuerdos, separados de la aprobación factual del dueño.

### 3E. Color

1. **Origen.** Los colores salen de activos permitidos: logo, carta, fachada, fotos. Sin logo, salen de las fotos y de la dirección elegida. Un color tomado de un activo sin derechos no se vuelve problema legal por sí mismo, pero el activo sigue sin poder publicarse.
2. **Construcción.** Trabajar en un espacio perceptual (OKLCH) para que los pasos de claridad sean uniformes. Elegir un acento; construir los neutros ligeramente teñidos hacia la temperatura de la dirección; generar una rampa corta por rol.
3. **Roles.** Fondo, superficie, texto, texto secundario, borde, acción, y estados (agotado, error, confirmación). Los estados no reutilizan el color de acción.
4. **Contención.** El acento se reserva para la acción principal y uno o dos énfasis. Guía inicial: no más de una décima parte del área de un viewport.
5. **Convivencia con la comida.** Probar la paleta al lado de las fotos reales. Un fondo frío o un acento saturado pueden apagar o ensuciar el color de un plato; si ocurre, cede la paleta, no la foto.
6. **Comprobación.** Contraste de cada par texto/fondo usado, según 3F y G08. La información no depende solo del color: un plato agotado también lo dice con texto.
7. **Variante oscura.** Fuera del piloto. Si se ofrece, se diseña y se prueba como variante propia.

### 3F. Tipografía

1. **Familias.** Una o dos. Si son dos, claramente distintas y con papeles fijos: una para titulares y nombres, otra para lectura.
2. **Licencia.** Abierta o adquirida para uso web, registrada en `AssetRightsManifest` como cualquier otro recurso.
3. **Cobertura.** Español completo: tildes, ñ, ü, signos de apertura ¿ ¡, y el signo de pesos. Se prueba con los nombres reales de la carta.
4. **Precios.** Cifras tabulares, para que las columnas de precios alineen. Formato local, sin decimales y con separador de miles: $28.000.
5. **Jerarquía del menú.** Categoría, nombre del plato, descripción y precio son cuatro niveles distintos, diferenciados por tamaño, peso o color, no por adornos.
6. **Detalles.** Sin palabras huérfanas en titulares; sin mayúsculas sostenidas para texto de lectura; sin titulares que dependan de un ancho exacto para verse bien.
7. **Carga.** Fuentes alojadas con el sitio, recortadas a los caracteres usados, cuatro archivos como máximo, y una fuente de respaldo de métricas parecidas para que el texto no salte al cargar. Entra en el presupuesto de G09.

**Base de accesibilidad:** objetivo WCAG 2.2 nivel AA, con evaluación de los criterios aplicables. Como controles explícitos se comprueban contraste de texto normal de al menos 4,5:1 y grande de al menos 3:1, además de los controles de interfaz pertinentes; «grande» usa la definición de la norma, no una etiqueta inventada por el generador [S3]. No se afirma conformidad completa por pasar un escáner.

Políticas adicionales del producto, no requisitos universales de WCAG: texto corriente de al menos 16 píxeles CSS y área preferida de acción de 44 × 44 píxeles CSS. Una excepción exige revisión documentada y no puede contradecir un criterio aplicable.

### 3G. Composición

Cada sección tiene un trabajo, los datos que exige y dos o tres variantes. Una sección sin sus datos no se emite; no se rellena.

| Sección | Su trabajo | Exige | Variantes |
| --- | --- | --- | --- |
| Portada | Decir qué es, dónde está y qué se puede hacer | Nombre, una línea respaldada, acción principal | Foto protagonista; tipográfica; partida texto/foto |
| Estado y horario | Responder «¿puedo ir o pedir ahora?» | Horarios vigentes; regla de «abierto ahora» si está habilitada | Línea en portada; bloque propio |
| Destacados | Mostrar por qué ir | Selección según fase 2; fotos con derechos si la variante las usa | Tres a seis platos con foto; lista tipográfica |
| Menú | Dejar elegir | Catálogo confirmado | Lista compacta; tarjetas con foto; mixta |
| Ubicación | Llevar al lugar | Dirección confirmada | Mapa enlazado; texto con indicaciones |
| Historia | Dar carácter | Texto respaldado | Párrafo con foto; solo texto |
| Galería | Mostrar el lugar | Fotos con derechos y calidad | Retícula; tira horizontal |
| Reputación | Dar confianza | Fuente, fecha y permiso de presentación | Cifra con fuente; cita atribuida |
| Pie | Contacto, horarios y avisos legales | Datos de contacto y textos aprobados | Única |
| Barra de acción | Mantener la acción a mano en móvil | Capacidad habilitada | Fija inferior; ausente |

**Portada.** Abre con lo más característico del restaurante en la forma que mejor lo muestre: una foto, el nombre compuesto con su tipografía o un plato. La acción principal debe encontrarse en el primer viewport de la prueba móvil normal (referencia inicial: 360 × 800 píxeles CSS), pero no se exige que toda la información quepa allí. Texto sobre foto solo si el contraste se sostiene en toda el área del texto y en todos los recortes.

**Ritmo de página.** Dos secciones seguidas no usan la misma composición. A una sección densa le sigue una con aire. El elemento firma aparece pocas veces; si está en todas partes deja de ser firma. El ritmo no justifica retirar precios ni información necesaria para decidir.

**Móvil primero.** Se compone primero en 360 píxeles de ancho y después se adapta. Con zoom o textos grandes prevalecen legibilidad y acceso sin obstrucción; no se reduce el texto para «pasar». La barra fija es opcional y no tapa contenido, controles ni mensajes.

**Componentes.** Reusar componentes de terceros solo tras revisar licencia, mantenimiento, accesibilidad, seguridad y peso. Aportan comportamiento (foco, teclado, diálogos); el aspecto lo ponen los tokens del sitio.

### 3H. El menú

Es la sección que más se usa y la que menos se parece a una página de marketing. Tiene reglas propias.

1. **Anatomía del plato.** Nombre, descripción de dos líneas como máximo, precio, etiquetas y foto opcional. El precio nunca se separa visualmente de su plato ni se parte en dos líneas.
2. **Alineación.** Los precios forman una columna a la derecha con cifras tabulares. Los nombres largos se parten con sangría; no empujan el precio.
3. **Navegación.** Categorías visibles y siempre a mano: en móvil, una fila de categorías que se queda fija al desplazarse y marca la actual. Cada categoría tiene su propio enlace.
4. **Densidad según la carta.** Lista compacta para cartas largas; tarjetas con foto para cartas cortas con buenas fotos; mixta cuando solo algunos platos tienen foto. Hipótesis a probar: por encima de unos cuarenta platos conviene la lista compacta con búsqueda.
5. **Fotos.** Si un plato tiene foto y el vecino no, la composición debe verse bien igual. Miniaturas de una sola proporción. El menú sigue siendo utilizable sin fotos y con imágenes que fallen.
6. **Etiquetas.** Vegetariano, picante, nuevo: con texto, no solo con icono o color, y solo si el dato está confirmado. «No informado» no se muestra como ausencia.
7. **Variantes y modificadores.** En móvil se eligen en una hoja inferior, con el total actualizado a la vista. Mínimos y máximos se explican antes del error, no después.
8. **Estados.** Agotado, no disponible a esta hora y precio actualizado tienen cada uno su apariencia y su texto.
9. **Descarga.** El PDF de la carta es una descarga opcional, nunca el único acceso.

**[I]** Evaluar estas reglas con cartas reales de distinto tamaño. La tarea de medición es concreta: una persona encuentra un plato dado y su precio. Se registran tiempo, errores y abandono, por variante.

### 3I. Fotos

1. **Selección.** Por pertinencia, calidad y punto focal, no solo por una puntuación estética. La mejor foto va a la portada.
2. **Calidad mínima.** Resolución suficiente para el ancho de destino al doble de densidad, foco en el plato y luz legible. Una foto por debajo del mínimo no se usa grande; puede servir de miniatura o descartarse.
3. **Tratamiento.** Recorte por punto focal en las proporciones del sitio. Se permite corregir exposición y balance de blancos de forma uniforme para que el conjunto se vea coherente. No se cambia el plato: ni porciones, ni ingredientes, ni elementos añadidos o borrados.
4. **Entrega.** Formatos modernos con respaldo, varios tamaños por imagen, dimensiones declaradas para que la página no salte, y carga diferida fuera de la primera pantalla. Entra en G09.
5. **Texto alternativo.** Describe lo que se ve, con el nombre del plato si corresponde. Es una afirmación factual y entra en `ClaimMap`.
6. **Registro.** Se guarda el original permitido y la transformación aplicada.
7. **Sin fotos.** Se elige una dirección tipográfica que no las necesite, y se diseña como decisión, no como plan B con huecos. Cambiar después a una composición dependiente de fotos reactiva sus requisitos de datos y derechos. No hay un mínimo universal de imágenes.

No se generan platos inexistentes ni se presenta una imagen decorativa como evidencia del plato servido.

### 3J. Texto de interfaz, movimiento y estados

**Texto de interfaz.** Un botón dice exactamente lo que pasa al tocarlo, y la acción conserva su nombre en todo el flujo: si el botón dice «Continuar en WhatsApp», el mensaje siguiente no habla de «pedido enviado». Los errores dicen qué pasó y qué hacer. El tono es el del restaurante, sin frases de relleno. Estos textos se revisan por función en la fase 2D.

**Movimiento.** Después de aprobar la composición estática. Un solo momento orquestado, si acaso, al cargar la portada. El movimiento que responde a una acción de la persona (abrir, agregar, confirmar) es bienvenido cuando muestra qué cambió. Se respeta la preferencia de movimiento reducido y no se afecta G09.

**Estados.** Se diseñan como parte de la fase, no como mensajes improvisados al final: carga, error, sin conexión, agotado, cierre temporal, fuera de horario, carrito desactualizado, solicitud pendiente, reserva no confirmada y fallo de proveedor.

### 3K. Proceso y compuertas

1. **[C]** Fijar el sistema base (3C) y registrarlo en `DesignSpec`.
2. **[C]** Producir `ArtDirection` según 3D y obtener la elección registrada.
3. **[C]** Derivar paleta y tipografía (3E, 3F) y comprobar contraste y cobertura de caracteres con el contenido real.
4. **[C]** Componer cada ruta en móvil y luego en escritorio (3G, 3H), con todos los estados de 3J.
5. **[C]** Asignar y tratar fotos (3I), o confirmar la dirección sin fotos.
6. **[G] G04a — Piso de diseño.** Automática. Sin recortes de texto, solapes u obstrucciones; orden de lectura claro; todo espacio y tamaño sale de los tokens; recursos permitidos; acción coherente con la capacidad y presente en el primer viewport móvil; todas las rutas y estados críticos representados. Los umbrales de accesibilidad se verifican además en G08 y los de rendimiento en G09.
7. **[G] G04b — Calidad de diseño.** Humana, con la rúbrica de 3L. No reemplaza a G04a ni puede compensar un fallo suyo.
8. **[I]** Medir si el crítico automático de la fase 5D coincide con los veredictos humanos de G04b. Hasta que coincida de forma demostrada, el crítico sirve para buscar, no para aprobar.

Una reparación visual de la fase 5 vuelve a pasar G04a siempre, y G04b cuando cambia la composición de una ruta.

### 3L. Rúbrica de calidad de diseño

Cada criterio tiene tres niveles con anclas observables. No se suman ni se promedian en un puntaje: la decisión sale de una regla. Esto mantiene la prohibición de puntajes arbitrarios que el original atribuye a `AGENTS.md`.

| Criterio | Qué se mira | Falla | Aceptable | Destacado |
| --- | --- | --- | --- | --- |
| R1. Jerarquía | Qué se ve primero en cada pantalla | No se sabe dónde mirar, o dos elementos compiten | Hay un elemento principal claro en cada pantalla | En cinco segundos una persona dice qué restaurante es, qué sirve y qué puede hacer |
| R2. Protagonismo | Quién se lleva la atención | La interfaz o un efecto pesan más que la comida o el lugar | La comida o el lugar son lo más visible | Se recuerda un plato, un espacio o el nombre, no la página |
| R3. Menú | Encontrar un plato y su precio | Hay que leer todo para encontrarlo, o el precio se confunde de plato | Se encuentra recorriendo la categoría correcta | Se encuentra de un vistazo; la carta completa se recorre sin cansancio |
| R4. Carácter | Prueba del intercambio | Con otro logo serviría para cualquier restaurante | Se percibe un tono propio | Hay una decisión firma identificable que viene del mundo de ese restaurante |
| R5. Tipografía | Familias, escala, detalles | Más de dos familias, tamaños sin sistema o texto incómodo de leer | Escala coherente y lectura cómoda | La tipografía carga la personalidad; sin huérfanas ni saltos |
| R6. Color | Paleta y uso del acento | Colores que compiten entre sí o con las fotos | Paleta corta y acento reservado a la acción | El color hace ver mejor la comida y refuerza el carácter |
| R7. Espacio y alineación | Ritmo, márgenes, bordes | Espacios irregulares o elementos casi alineados | Espaciado de la escala y bordes alineados | El aire está donde ayuda; el ritmo entre secciones se nota intencional |
| R8. Consistencia | Secciones y estados entre sí | Una sección o un estado parece de otro sitio | Mismos tokens en todo el sitio | Los estados de error, agotado y pendiente se ven tan cuidados como la portada |
| R9. Móvil | Uso con una mano | Desplazamiento horizontal, controles pequeños o acción fuera de alcance | Todo se alcanza y se lee sin ampliar | Parece diseñado para el teléfono, no adaptado |
| R10. Contención | Lo que sobra | Decoración sin función, o un valor por defecto de 3D sin razón registrada | Nada estorba | No se puede quitar nada sin perder algo |
| R11. Acabado | Detalles | Imágenes pixeladas, iconos de familias mezcladas o foco invisible | Sin descuidos visibles | Los detalles aguantan la mirada de cerca |

**Regla de decisión, propuesta para el piloto.** G04b pasa cuando dos personas revisoras, de forma independiente, no marcan «falla» en ningún criterio. Para declarar una página como referencia de calidad del proyecto se exige además «destacado» coincidente en R3, R4 y al menos otros dos criterios. Un desacuerdo se discute y se registra; no se promedia.

**Protocolo.**

1. Se revisa el sitio renderizado en un teléfono real y en escritorio, no solo capturas.
2. Cada revisor califica solo, antes de ver la calificación del otro y la del crítico automático.
3. Cada «falla» lleva una captura, la región y una frase con la razón, para que sea reparable.
4. R1 y R3 se comprueban con una persona ajena al proyecto y una tarea concreta, no por opinión.
5. Cuando haya más de una página, se comparan a ciegas contra la implementación manual de referencia de la fase 7C, alternando el orden.
6. La calificación del propio agente no cuenta como revisión humana. La aprobación del dueño tampoco la reemplaza: el dueño aprueba que lo representa, no que esté bien compuesto.

En el piloto, con dos fundadores como revisores, la independencia es limitada. Se registra así y no se presenta como evaluación ciega.

### 3M. Referentes

1. **[I]** Para el piloto, analizar de ocho a diez páginas de restaurante bien resueltas, de varios tipos de cocina y rangos de precio, con al menos tres de la región. El programa de investigación completo son treinta a cincuenta y no bloquea el piloto.
2. Por cada referente se anota lo mismo: cuál es su elemento firma, cómo resuelve el menú en móvil, tipografía y color, uso de foto, qué haría fallar la prueba del intercambio, y qué tareas resuelve bien o mal.
3. Se registran decisiones y razones, no capturas para imitar. No se copian activos, composiciones exactas ni textos.
4. Cada referente se califica con la rúbrica de 3L. Si los referentes que todos consideran buenos no salen «destacado», la rúbrica está mal y se corrige antes de usarla para aprobar.
5. Esta fase no nombra referentes concretos: elegirlos y verificarlos es el primer paso de investigación.

## Fase 4 — Funcionalidad e integridad operativa

**Salida:** capacidades implementadas o explícitamente deshabilitadas, contrato del servidor (`BackendContract`), políticas versionadas y evidencia de pruebas. Las demos y los simuladores no habilitan capacidades públicas reales.

### 4A. Una autoridad de datos, varias representaciones

Debe existir una autoridad definida para cada dominio: catálogo, disponibilidad, horarios, reservas, pedidos y pagos. El panel modifica esa autoridad; el HTML, el carrito y los datos estructurados son representaciones derivadas, no catálogos independientes. El proveedor de pagos aporta evidencia sobre su transacción; no decide si la cocina aceptó el pedido.

Distinguir versiones:

| Versión | Qué cambia | Qué no debe hacer |
| --- | --- | --- |
| `catalog_version` | Productos, variantes, precios y reglas comerciales | Reescribir pedidos ya confirmados |
| `operational_revision` | Agotados, pausa de pedidos y disponibilidad | Activar capacidades no aprobadas |
| `content_version` | Textos, datos públicos y horarios publicados | Dar por aprobados nuevos hechos |
| `design_version` | Composición y tokens visuales | Cambiar precios, horarios o condiciones |
| `backend_contract_version` | Semántica de operaciones y formatos | Romper sitios publicados sin migración |
| `release_id` | Combinación concreta publicada | Referirse ambiguamente a “lo último” |

Las actualizaciones operativas autorizadas pueden circular sin generar un sitio nuevo cuando el contrato publicado ya contempla esos campos dinámicos. Conservan actor, revisión, hora, política y trazabilidad propia. No son una puerta para cambiar diseño, identidad, términos o cobros sin la aprobación pertinente.

### 4B. Contrato de actualización

**Secuencia:** propuesta → validación y autorización → revisión nueva → pruebas afectadas → preparación de representaciones → activación controlada → comprobación → auditoría. Un cambio iniciado por el dueño puede ser su aprobación del valor exacto, si la interfaz le mostró qué cambiaba y tenía permiso. Un agente no puede atribuirle esa aprobación.

Preparar la versión nueva sin sobrescribir la publicada. Al activarla, comprobar que la versión base sigue siendo la esperada; si otra persona editó antes, presentar el conflicto en lugar de perder su cambio. La operación de activación debe poder retomarse sin duplicarse.

No es realista prometer que todas las pestañas y cachés cambian en el mismo instante. Se distinguen la versión servida, la versión observada por cada cliente y la versión autoritativa usada para decidir. Las cachés tienen invalidación o vencimiento configurado; los clientes revalidan al recuperar foco y antes de enviar una solicitud. Si no pueden verificar un precio o cupo necesario, no muestran confirmación automática.

**Caso del precio:** una hamburguesa pasa de COP 25.000 a COP 28.000. Un carrito abierto con la versión anterior recibe el cambio y exige reconfirmación del total. No se le cobra silenciosamente el nuevo valor. Un pedido ya aceptado conserva su fotografía de precios y condiciones. Una cotización todavía válida conserva el precio únicamente si el negocio aprobó expresamente una política de reserva de precio; de lo contrario se recalcula y se pide nueva aceptación antes de crearla.

Toda cotización vinculante tiene `quote_id`, sede, líneas, moneda, importes, versión, vencimiento y condiciones de disponibilidad. Para pago integrado se necesita una política compatible de reserva de inventario/capacidad y vencimiento de pago. Un pago aprobado después de vencer la reserva entra en revisión/compensación: no resucita automáticamente inventario ni pedidos cancelados.

**Cambio de contenido no es rediseño:** cambiar precio ejecuta datos, contenido, integridad de render, total, caché, analítica afectada y aprobación. Cambiar tipografía ejecuta diseño, accesibilidad, rendimiento y regresión de contenido. El sistema puede reutilizar evidencia solo si verifica que sus entradas exactas no cambiaron; la decisión de reutilización queda registrada.

### 4C. Estados de solicitudes y pedidos

Separar tres procesos; sus estados no se deducen entre sí:

| Proceso | Estados de referencia | Autoridad |
| --- | --- | --- |
| Solicitud | `draft` → `created` → `received`; después `accepted`, `rejected` o `expired` | Servidor para creación; negocio o integración confiable para recepción/decisión |
| Cumplimiento de pedido aceptado | `accepted` → `preparing` → `ready` → `fulfilled`; también cancelación según reglas | Personal autorizado o proveedor con evidencia suficiente |
| Pago | No iniciado, pendiente, aprobado, rechazado/error; anulación, reembolso o disputa como operaciones propias | Adaptador y conciliación con el proveedor; nunca el navegador |

La tabla expresa procesos de referencia, no un único enum lineal. Definir transiciones permitidas por capacidad, actor y estado anterior; rechazar saltos no autorizados. Registrar motivo y evidencia de cancelación. Un reembolso parcial lleva importe y un movimiento independiente, no borra el pago original. Un estado tardío no hace retroceder una transacción confirmada sin una transición válida.

Cada pedido confirmado conserva sede, cantidades, variantes, precios, cargos, condiciones aceptadas y referencias de aprobación. No se modifica al actualizar el catálogo. Un cambio solicitado después se tramita como ajuste explícito, con nueva aceptación cuando corresponda.

### 4D. WhatsApp: preparar no es enviar

El enlace de conversación con texto prellenado abre el chat y pone el texto en el campo de escritura; no demuestra que el visitante lo haya enviado [S1]. Por tanto, el botón dice “Continuar en WhatsApp” o “Preparar solicitud”, no “Pedido confirmado”. La página informa que la recepción y aceptación deben confirmarse por el restaurante.

El evento del navegador es `whatsapp_handoff`. Para registrar `request_received`, el negocio debe confirmar que recibió la solicitud o debe existir evidencia de una integración autorizada. Para `order_accepted` hace falta una decisión del negocio. La recepción manual indica actor, hora y referencia; no se cuenta como observación automática independiente.

El piloto puede incluir una referencia de solicitud en el texto para asociar el resultado sin copiar conversaciones completas. No se almacenan nombres, teléfonos o direcciones para medir un simple clic. El texto del mensaje no se manda a herramientas de analítica como parte de la URL o de un evento.

Probar abrir/cancelar, WhatsApp no instalado, WhatsApp Web, número incorrecto, mensaje excesivamente largo, caracteres especiales, modificación del texto por el usuario y restaurante que no responde. Si no se puede saber el desenlace, se registra **no observado**, no “fallido” ni “vendido”.

### 4E. Reservas

`reservation_request` y `reservation_confirmed` son productos distintos. La primera muestra “solicitud recibida; pendiente de confirmación”. La segunda requiere autoridad real sobre el inventario de cupos o aceptación humana que contemple también teléfono, visitas y otros canales.

Una reserva confirmada necesita sede, zona horaria, fecha, duración o intervalo de ocupación, personas, restricciones de mesa/capacidad, condiciones y referencia. Definir reservas temporales, vencimiento, cancelación, no presentación y sobreventa. Una retención de cupo no es todavía una confirmación.

La asignación de capacidad se realiza de forma atómica en la autoridad de reservas. Dos solicitudes simultáneas sobre el último cupo no pueden confirmarse ambas. Contar filas disponibles y después insertar sin control de concurrencia no satisface el contrato.

Si otros canales no están sincronizados ni un humano los concilia, deshabilitar confirmación automática. Un formulario bonito no resuelve ese límite operativo.

### 4F. Pagos integrados: capacidad posterior al piloto

1. El servidor recibe identificadores y cantidades, valida sede, catálogo, modificadores y disponibilidad, y recalcula el total. No acepta un importe arbitrario del navegador.
2. Crea una intención ligada a pedido/cotización e identificador idempotente: repetir la misma operación devuelve su resultado existente, no crea un segundo cobro. Reusar una clave con contenido distinto es un error.
3. Usa el mecanismo de pago aprobado y evita que los sistemas de 101 reciban datos de tarjeta innecesarios. Alcance de seguridad y obligaciones del proveedor se revisan antes de activarlo.
4. La redirección de regreso a la página no demuestra pago. El adaptador verifica el evento o consulta el estado por un canal autenticado del servidor.
5. Valida correspondencia con comercio, entorno, pedido, referencia, moneda e importe esperados. Los campos no cubiertos por la verificación del proveedor no se consideran confiables solo por venir en el JSON.
6. Persiste el evento autenticado antes de confirmarle recepción al proveedor; su procesamiento y los efectos posteriores se recuperan desde almacenamiento duradero. Notificaciones y otras tareas pendientes se registran junto con el cambio de estado para no perderlas entre procesos.
7. Deduplica de forma duradera, tolera eventos tardíos y maneja orden no garantizado. Si falta un identificador de evento, el adaptador define una identidad estable apropiada y controla los efectos por transacción/transición.
8. Un timeout después de solicitar un cobro produce “resultado pendiente de verificar”; se concilia antes de volver a intentar crear otro cobro.
9. Rechazos operativos posteriores al pago activan el procedimiento explícito de compensación o reembolso. No se marca “reembolsado” hasta contar con evidencia suficiente del movimiento.

Wompi documenta reintentos de sus eventos y un procedimiento de checksum que usa las propiedades indicadas en cada evento; no debe sustituirse por un algoritmo inventado ni fijar una lista de propiedades que la documentación declara variable [S6]. Una ventana de antigüedad demasiado corta no debe descartar reintentos legítimos: el diseño combina verificación, deduplicación persistente y conciliación.

No se presupone que todos los métodos, reembolsos o funciones del proveedor estén habilitados en producción por aparecer en documentación o sandbox. La matriz de integración identifica función, cuenta, entorno, versión y prueba real controlada. Wompi, Uber Direct y Mensajeros Urbanos siguen siendo integraciones por verificar, como en el original.

### 4G. Disponibilidad, contingencias y operación cotidiana

El restaurante puede pausar nuevas solicitudes, marcar agotados y cerrar temporalmente una capacidad sin recompilar el diseño. La pausa afecta nuevas operaciones; no elimina pedidos aceptados. Las alertas tienen responsable principal y sustituto. Definir qué ocurre fuera del horario de soporte.

No afirmar inventario reservado cuando solo existe una señal manual de “disponible”. Cuando se ofrezca reserva cuantitativa, probar dos compras simultáneas de la última unidad, expiración de la reserva y liberación tras cancelación. Domicilios agregan zona, tarifa, responsable, seguimiento y contingencia, no solamente un botón de proveedor.

### Pasos y compuerta funcional

1. **[C]** Implementar menú HTML y contacto usando la proyección pública.
2. **[C]** Calcular horarios según zona de la sede, excepciones, cierre temporal e intervalos que cruzan medianoche; distinguir abierto al público de cocina/pedidos disponibles.
3. **[C]** Implementar carrito y solicitud por WhatsApp con estados y textos correctos.
4. **[C]** Implementar actualización de precio, agotados y horario desde un panel mínimo o una operación de soporte autenticada y trazable.
5. **[I]** Inspeccionar V4 y sus documentos de integración; adoptar su núcleo solo donde cumpla los contratos.
6. **[C]** Integrar por separado cada capacidad adicional, deshabilitada hasta superar sus pruebas.
7. **[C]** Generar datos estructurados y metadatos desde la misma versión pública. La optimización para buscadores —SEO— no habilita promesas de indexación, resultados enriquecidos o aparición en asistentes [S5].
8. **[C]** Instrumentar eventos y conciliación con las definiciones de la fase 7.
9. **[G] G05 — Funcionalidad.** Probar cada capacidad habilitada desde la intención hasta su estado verificable, incluyendo la operación del restaurante, concurrencia, repetición y fallos. El navegador por sí solo no basta.

## Fase 5 — Construcción, QA y crítica

**Salida:** candidato inmutable, reportes y evidencias. QA significa aseguramiento de calidad. Reutilizar `WebsiteCompiler` y `@101/site-runtime` si G00 confirma compatibilidad. No afirmar que el ciclo P1-6 ya está cerrado: demostrarlo sobre el repositorio seleccionado.

### 5A. Contrato común de compuerta

Cada definición tiene identificador y versión de política, propósito, ámbito, condición de aplicabilidad, entradas requeridas, regla de aceptación, ejecutor, evidencia exigida, gravedad, responsable, ruta de reparación y condiciones que invalidan un resultado anterior. El catálogo `especificacion/compuertas.json` fija esas obligaciones.

Cada ejecución registra `gate_id`, `run_id`, contexto evaluado, huellas de entrada, versión del comprobador, ambiente, inicio/fin, resultado, hallazgos, pruebas aplicables y referencias de evidencia. El contexto puede ser un paquete, candidato de publicación, despliegue o experimento; no se inventa un `release_id` antes de que exista.

| Resultado | Significado | ¿Permite avanzar cuando la compuerta es obligatoria? |
| --- | --- | --- |
| `PASS` | Todas las comprobaciones aplicables ejecutadas y satisfechas | Sí, mientras sus entradas y condiciones sigan vigentes |
| `FAIL` | Incumplimiento demostrado | No |
| `NOT_RUN` | No se ejecutó | No |
| `INCONCLUSIVE` | La ejecución no permite decidir o falta evidencia | No |
| `NOT_APPLICABLE` | La política demuestra que la capacidad o caso no aplica | Solo con derivación y motivo verificables; no es una aprobación |

Severidad: `BLOCKER` impide la transición; `MAJOR` también exige resolución para publicar; `MINOR` permite continuar únicamente con responsable y motivo registrados. No se rebajan violaciones de verdad, permisos, seguridad, dinero o confirmación a “menores” para pasar. Una prueba vacía, un comprobador que se cayó o una lista incompleta de pruebas generan bloqueo, no éxito.

Los reportes confiables los emite el ejecutor autorizado y se guardan fuera del alcance de escritura del agente generador. Un JSON que diga `PASS` no constituye evidencia auténtica. El código puede verificar consistencia del reporte; la identidad y procedencia de quien lo emite necesitan control de acceso o firma en la integración.

### 5B. Integridad del contenido publicado

**[G] G06 — Verdad de la entrega.** Verificar por ruta y estado:

- Todos los públicos obligatorios aparecen accesibles en el contexto definido, con valor, unidad, moneda y sede correctos.
- Los opcionales omitidos tienen motivo; no se fuerza publicación de datos irrelevantes.
- Cada afirmación factual emitida tiene respaldo vigente y permitido; los estados calculados registran sus entradas.
- Los internos no aparecen en HTML, respuestas del navegador, metadatos, archivos de depuración ni registros públicos.
- HTML, menú, carrito y datos estructurados no sostienen valores incompatibles. Las diferencias de versión observadas se manejan como en 4B.

Comparar valores normalizados, no únicamente buscar cadenas exactas. El compilador emite un mapa de afirmaciones y el comprobador inspecciona también el render y los archivos entregados. Si aparece texto factual que el mapa no cubre, no se da por inocuo: se clasifica o revisa. Una prueba de DOM no certifica por sí sola que toda afirmación de lenguaje natural sea verdadera.

### 5C. Navegadores, accesibilidad y rendimiento

**[G] G07 — QA técnico.** Probar Chromium, Firefox y WebKit con versiones fijadas en el reporte, más comprobación manual de los flujos críticos en Safari/iOS y Chrome/Android disponibles para el piloto. WebKit automatizado no se presenta como sustituto exacto de un iPhone real. Registrar limitaciones de cobertura, no “todos los dispositivos”.

Matriz inicial de viewports: 320, 360, 390, 768 y 1440 píxeles CSS de ancho. Probar orientación, nombres largos, menú extenso, categorías vacías, fotos ausentes, carga lenta, JavaScript o terceros fallidos cuando la función deba degradarse, enlaces rotos, consola y navegación de ida/vuelta. El contenido informativo esencial debe seguir accesible cuando falle la capa interactiva.

**[G] G08 — Accesibilidad.** Comprobaciones automáticas más revisión manual de teclado, foco, lector de pantalla, formularios, errores, diálogos, estados anunciados, zoom al 200 %, reflujo, contraste y preferencias de movimiento. Definir los criterios aplicables de WCAG 2.2 AA, sus pruebas y cualquier incumplimiento; no reducir la revisión a una puntuación de herramienta [S3].

**[G] G09 — Rendimiento.** Antes de publicar, medir al menos cinco ejecuciones en un perfil móvil reproducible con caché fría y registrar dispositivo, red, CPU y versiones. Política inicial: mediana de LCP ≤ 2,5 s, CLS ≤ 0,1 y tiempo total de bloqueo ≤ 200 ms en laboratorio; además, registrar rango y valores individuales. Presupuestos iniciales del proyecto: carga inicial ≤ 1,5 MB transferidos y JavaScript inicial propio ≤ 200 KB comprimidos. Son límites propuestos para el piloto y deben ajustarse por decisión previa, nunca después de ver un fallo para ocultarlo.

En producción, medir LCP —carga del elemento principal—, INP —respuesta a interacciones— y CLS —desplazamientos visuales—. Los umbrales publicados de Core Web Vitals son 2,5 s, 200 ms y 0,1 en el percentil 75, separando móvil/escritorio [S4]. El resultado de laboratorio no se presenta como resultado real. Sin suficientes observaciones de campo, registrar “sin evidencia suficiente”, no cumplimiento o incumplimiento imaginario. INP no se reemplaza por una puntuación de Lighthouse.

### 5D. Crítica visual y reparación

**[I]** Evaluar si masa visual, balance, espacio vacío y una rúbrica de modelo coinciden con juicios humanos. El crítico es una herramienta de búsqueda, no una autoridad factual ni una aprobación comercial.

**[C]** Registrar hallazgos con región, criterio, evidencia y propuesta de parámetro. Reparar únicamente dentro del contenido aprobado y capacidades habilitadas. Volver a ejecutar las compuertas afectadas; una mejora de composición puede crear un recorte, una regresión de contraste o una pérdida de precio.

Política inicial: máximo tres candidatos visuales por dirección y tres rondas de reparación. Antes de empezar, el operador fija presupuesto monetario, límite de tiempo de cómputo y número máximo de renders; se cuentan intentos fallidos y reintentos. Sin presupuesto explícito no corre exploración. Guardar también versiones de modelo, instrucciones y semilla cuando exista; no prometer determinismo exacto del modelo.

Al agotar el presupuesto: conservar el mejor candidato que haya pasado controles duros y enviarlo a revisión humana, o usar una composición previamente aprobada. Si ninguno pasa, bloquear. No relajar la compuerta ni entrar en un bucle ilimitado.

### 5E. Reporte del candidato

El reporte incluye entradas y versiones, afirmaciones publicadas, omisiones, derechos, capturas, pruebas, fallos, limitaciones, decisiones humanas, costo y tiempo. Las versiones públicas de reportes eliminan secretos, datos internos e información de comensales. Una captura o hash no reemplaza los registros operativos necesarios para comprobar recepción y aceptación.

## Fase 6 — Publicación

**Salida:** una versión identificable en producción y evidencia de que opera allí. Publicar no equivale a terminar el trabajo.

### 6A. Vista previa y autorización

La vista previa requiere autenticación o un mecanismo de acceso restringido con vencimiento y revocación. `noindex` es una defensa adicional, no control de acceso. No debe recibir pedidos o pagos reales ni modificar perfiles públicos. Usar datos de prueba cuando se prueben flujos.

Para publicar, verificar representación del negocio, sede, dominio o subdominio autorizado, condiciones del servicio, derechos y responsable operativo. La conexión con el perfil de Google requiere permiso y mecanismos admitidos; no se hace automáticamente porque se encontró un perfil público.

### 6B. Qué se aprueba exactamente

`ReleaseManifest` identifica artefactos por huella, versiones de contenido/catálogo/diseño, capacidades, sedes, política operativa, contrato del servidor, compilador, dependencias, esquema y configuración. No incluye secretos ni datos personales. El conjunto publicado no apunta a archivos mutables llamados “latest”.

Definir `candidate_hash` a partir del JSON canónico de las entradas del candidato y sus hashes, **sin incluir aprobaciones ni reportes posteriores**. Esos registros referencian el candidato; así se evita una definición circular. En el paquete adjunto, JSON canónico significa claves ordenadas, UTF-8, sin espacios entre separadores y sin números no finitos; los importes y contadores son enteros. La integración debe conservar esa convención o migrarla explícitamente.

El dueño aprueba datos públicos y alcance de la operación; una persona revisora aprueba composición y uso; el responsable de publicación comprueba controles técnicos y operativos. Pueden coincidir algunas personas en el piloto, pero las funciones y decisiones se registran por separado. El agente generador no se registra como representante humano ni como aprobador de su propia propuesta.

Cada `ApprovalRecord` contiene actor, rol y alcance verificados, decisión, huella exacta aprobada, momento, vencimiento o condición de revocación y evidencia de lo que vio. Una modificación posterior invalida la aprobación cuyo alcance cambió. El agregado final solo es elegible cuando **todos** los alcances necesarios siguen cubiertos por aprobaciones válidas. Una aprobación de diseño sin cambios puede mantenerse; una aprobación del candidato completo no se arrastra a otro hash.

**[G] G12 — Aprobación y correspondencia.** Las entradas del despliegue coinciden con las evaluadas, las aprobaciones están vigentes y los permisos pertenecen a la sede correcta. No se autoriza que un agente “termine de retocar” después de aprobar y publique otra cosa.

### 6C. Despliegue, concurrencia y recuperación

Preparar el sitio, comprobar dependencias, activar un puntero de versión y verificar su correspondencia. Cuando catálogo/servidor y red de distribución no compartan una transacción, la estrategia debe manejar el desfase de forma explícita: compatibilidad de versiones y revalidación antes de acciones comerciales. No se finge atomicidad global entre proveedores.

La unidad de vuelta atrás es una versión compatible de sitio, configuración y contrato, **no restaurar indiscriminadamente una base de datos antigua**. Pedidos, pagos y auditoría se conservan. Revertir un diseño no reactiva precios, fotos revocadas o inventario vencido. Si el paquete anterior ya no es legal o compatible, se prepara una corrección hacia adelante o se desactiva la capacidad afectada.

Las migraciones conservan compatibilidad durante la transición; las destructivas requieren un plan explícito y no entran en la ruta de vuelta atrás automática. Registrar versión previa/nueva, operador, motivo y resultados.

### 6D. Verificación en producción

**[G] G14 — Producción.** Probar dominio, certificado, enlaces, sede, contacto, versiones, funciones habilitadas, alertas y eventos. Incluir un caso controlado que reciba realmente el restaurante y cuya condición de prueba conozca; no enviar pedidos falsos masivos. Confirmar que una caída de la plataforma no hace que el sitio prometa operaciones que no puede completar.

Un despliegue puede haber pasado las pruebas previas y fallar G14. En ese caso se retira o degrada la capacidad, se informa al responsable y se repara; no se marca el hito como terminado. El registro de pruebas en producción distingue simulaciones, sandbox y operaciones reales controladas.

## Fase 7 — Medición, actualización y aprendizaje

**Salida:** reportes con denominadores, trazabilidad y límites; solicitudes de cambio; experimentos protegidos. Medir intención, operación y economía por separado.

### 7A. Diccionario de eventos

| Evento | Qué demuestra | Fuente válida |
| --- | --- | --- |
| `page_view` | Página observada por la instrumentación | Navegador, con sus límites de cobertura |
| `menu_view` | Acceso a la ruta o sección de menú definida | Navegador |
| `primary_action_click` | Intención de actuar | Navegador |
| `whatsapp_handoff` | Salida hacia el chat preparado | Navegador; no confirma envío |
| `request_created` | Solicitud persistida o identificada por el sistema | Servidor o registro manual identificado |
| `request_received` | Restaurante recibió la solicitud | Personal autorizado o integración con evidencia |
| `order_accepted` | Restaurante aceptó condiciones concretas | Decisión operativa registrada |
| `reservation_confirmed` | Cupo confirmado, no solo formulario enviado | Autoridad de reservas o persona autorizada |
| `payment_approved` | Proveedor confirmó un pago conciliado | Servidor; no la página de retorno |
| `order_fulfilled` | Pedido cumplido según la evidencia registrada | Negocio/proveedor; distinguir declaración de verificación independiente |
| `refund_completed` | Reembolso registrado con evidencia suficiente | Proveedor o conciliación autorizada |

Cada evento tiene identificador, versión, ambiente, negocio/sede, momento ocurrido y recibido, origen y referencias de solicitud/pedido cuando correspondan. El resultado de negocio no nace de un evento del navegador. Repetir recepción o recargar una página no debe duplicar ventas.

Excluir tráfico de pruebas, trabajadores, agentes y robots identificados con criterios documentados; reportar lo que no se puede filtrar. No registrar cuerpos de mensajes, teléfonos, direcciones ni URLs que los contengan en analítica. Separar analítica agregada de registros operativos con permisos más estrictos.

Mostrar números absolutos junto con tasas y definir denominadores antes de comparar: clics/sesiones observadas, aceptados/recibidos y cumplidos/aceptados son métricas distintas. Identificar solicitudes pendientes, vencidas y de desenlace no observado. La ausencia de consentimiento o bloqueo de instrumentación cambia la cobertura; no se interpreta como cero demanda.

**[G] G15 — Medición.** Casos controlados se reflejan exactamente una vez en las métricas correctas; cerrar WhatsApp sin enviar no crea pedido; los resultados manuales están etiquetados; no hay datos personales en la telemetría general.

### 7B. Mantener la verdad

Registrar cada cambio y su propagación. Revisar campos al vencer, tratar avisos del dueño como prioritarios y observar errores de sincronización. Una extracción pública que detecta una diferencia crea una propuesta/conflicto; no sobrescribe silenciosamente la autoridad del negocio. Vigilar también derechos revocados, destino de WhatsApp, horarios especiales y capacidades pausadas.

El tablero muestra fecha de última verificación y lista de pendientes por responsable. Las actualizaciones normales siguen la ruta corta de contenido y las compuertas afectadas; cambios de capacidad, diseño o condiciones vuelven a sus fases correspondientes.

### 7C. Banco de pruebas y examen protegido

Conservar la idea original de 10–20 restaurantes de arquetipos diferentes. Como diseño inicial del banco, proponer 20: 12 para desarrollo y 8 reservados para evaluación. Son cantidades de planificación, no una muestra ya recolectada ni garantía de potencia estadística.

Separar por negocio y marca para evitar que sedes casi idénticas aparezcan en ambos grupos. Congelar entradas, criterios y versiones; los casos protegidos no alimentan prompts, reglas ni selección de componentes durante el ajuste. Los casos sintéticos de robustez son otro conjunto y no sustituyen datos reales.

Comparar contra una implementación manual sencilla con el mismo contenido y capacidades. Evaluar por separado: exactitud, finalización de tareas, tiempo, errores, intervención humana, costo y preferencia estética. Presentar composiciones sin revelar cuál es la automatizada cuando sea posible y alternar el orden.

Incluir menú de cientos de elementos, nombres largos, ninguna foto, horarios partidos y nocturnos, varias sedes con precios distintos, inventario desconocido, errores del proveedor y revisiones simultáneas. Una revisión del propio agente no cuenta como etiqueta humana. La aprobación del dueño no reemplaza una prueba con usuarios.

Si se usa un fallo protegido para mejorar reglas, ese caso deja de ser evaluación independiente para el siguiente ciclo; conservar su historial y crear un nuevo conjunto no usado. No mirar repetidamente el examen para escoger la mejor versión y seguir llamándolo independiente.

**[G] G16 — Evaluación y autonomía.** Esta compuerta se exige para declarar generalización o reducir revisión humana, no para publicar el primer piloto con revisión completa. Requiere separación de conjuntos, comparación, resultados desagregados y límites de incertidumbre. Una muestra pequeña sin incidentes no justifica autonomía de pagos ni eliminación automática de controles humanos.

### 7D. Experimentos y argumento económico

No atribuir diferencias entre restaurantes al diseño: cambian ubicación, demanda, oferta, precios y operación. Antes de una prueba aleatoria A/B, definir unidad de asignación, métrica principal, duración/criterio de parada, tamaño requerido, exclusiones y efectos adversos. La asignación debe ser consistente y evitar que la misma operación cambie de variante a mitad del flujo. Sin tráfico suficiente, usar tareas de uso y observaciones descriptivas; no fabricar significancia o “uplift”.

Separar tres cuentas:

1. **Margen del canal para el restaurante:** ingresos efectivamente reconocidos menos devoluciones, costos de producto y empaque, pago, entrega, trabajo incremental y servicio de 101 asignado. Definir tratamiento de descuentos e impuestos para no contarlos dos veces.
2. **Margen de 101:** ingresos del servicio menos proveedores, alojamiento, generación, incorporación, corrección humana, soporte, incidentes y mantenimiento; los costos iniciales se amortizan con un horizonte explícito cuando corresponda.
3. **Efecto incremental atribuible al sitio:** diferencia contra un contrafactual creíble, no todo el margen observado por el canal. Una venta desplazada desde otro canal no es automáticamente una venta adicional.

Guardar minutos reales de incorporación, carga de menú, corrección, revisión, soporte y actualización, con la tarifa o costo horario asumido. No vender “ahorro de comisión” sin restar costos directos y cambios de volumen. Los reportes separan datos medidos, estimaciones y supuestos, y muestran escenarios cuando el desenlace no se observa.

## Capa transversal A — Plataforma: módulos y roles

El sitio público, el panel y los procesos operativos son superficies diferentes. Tener varios restaurantes exige aislamiento desde el primer dato privado compartido; no aparece mágicamente al llegar a un “nivel 2”.

### Roles y permisos

| Rol | Permisos de referencia | Límites |
| --- | --- | --- |
| Visitante | Consultar, iniciar solicitud y seguir únicamente la propia cuando corresponda | Sin acceso a otras solicitudes ni funciones internas |
| Comensal con cuenta, opcional | Sus datos e historial según alcance autorizado | No accede a otro comensal; registro no implica autorización comercial |
| Personal | Recibir y actualizar pedidos/reservas de sus sedes | Permisos específicos; no cambia precios o reembolsa por pertenecer al equipo |
| Dueño/administrador | Catálogo, horarios, personal y aprobación de su negocio | No accede a otros negocios; acciones financieras requieren permiso separado |
| Operador 101 | Incorporación, soporte y revisión dentro de su asignación | Acceso mínimo; elevación excepcional con motivo, vigencia y auditoría |
| Agente generador | Leer proyección autorizada, generar propuestas y reparar candidatos | No se concede permisos, no aprueba por humanos, no cobra ni publica directamente |
| Ejecutor de controles/publicación | Emitir reportes confiables o promover una versión elegible | Credenciales separadas del generador y permisos acotados a su función |

La identidad de negocio/sede se deriva de la sesión y permisos confiables, no de un `business_id` que mande el navegador. Los filtros por negocio ayudan, pero también hay que aislar cachés, archivos, colas, búsquedas, exportaciones, tokens, registros y notificaciones. Probar autorización para leer y escribir cada objeto, no solo esconder botones.

### Módulos y secuencia

Para el piloto: sitio público, captura/corrección autorizada de datos, cola de aprobación, registro mínimo de solicitudes, auditoría y métricas. Un panel completo no es obligatorio antes de demostrar la operación; una consola mínima o soporte autenticado puede resolver cambios, con tiempos y costos medidos.

Después: servidor operativo completo, reservas, pagos, notificaciones y eventualmente cuentas, lealtad y suscripción automatizada. El cobro del servicio de 101 es distinto del pago del comensal al restaurante. No se mezclan fondos, credenciales ni libros de movimientos.

**[C]** Implementar matriz de permisos por acción y sede; ingreso y revocación de sesiones; invitaciones; mínimo privilegio; consola; alta/baja; auditoría de quién cambió qué, valor anterior/nuevo y motivo. Sustituir tokens de desarrollo antes de cualquier ambiente público con datos reales, tras verificar qué usa realmente V4.

**[G] G10 — Seguridad y aislamiento.** Un usuario o proceso de A no puede acceder a B manipulando identificadores, archivos, cachés o tareas. El agente no puede emitir una aprobación confiable ni obtener secretos del despliegue.

## Capa transversal B — Seguridad

Una página estática tiene menos operaciones de servidor, pero todavía puede filtrar datos o entregar scripts maliciosos. Los controles dependen de las superficies y capacidades realmente habilitadas.

| Área | Control exigido | Evidencia |
| --- | --- | --- |
| Autenticación | Sesiones revocables; segundo factor para operadores privilegiados; recuperación segura | Prueba de permisos, expiración y recuperación |
| Aislamiento | Autorización por negocio, sede y objeto; archivos/cachés/colas aislados | Pruebas cruzadas de lectura, escritura y exportación |
| Datos personales | Minimización, finalidad, acceso limitado, retención definida y transporte protegido | Inventario de datos, flujo y pruebas de acceso/borrado aplicable |
| Entradas y contenido | Validación, escape, saneamiento de recursos y política de contenido | Intentos controlados de inyección en menú, reseña y archivos |
| Abuso | Límites compartidos entre instancias, cuotas y controles proporcionales | Pruebas de repetición y saturación sin afectar terceros |
| Secretos | Separación por ambiente/comercio, gestor de secretos y rotación | Escaneo de repositorio, artefactos públicos y registros |
| Dependencias | Versiones fijadas, procedencia, licencia y revisión de cambios | Inventario y análisis de vulnerabilidades con resolución de hallazgos |
| Agente | Evidencia externa tratada como datos; herramientas y red restringidas | Pruebas de instrucciones maliciosas dentro de fuentes |
| Pagos | Verificación del proveedor, correspondencia, idempotencia y conciliación | Casos financieros del catálogo en el entorno correspondiente |
| Continuidad | Respaldos, restauración, alertas y procedimientos escritos | Simulacros con resultados medidos |

Una reseña, carta o página externa que contenga instrucciones para el modelo no cambia sus permisos ni reglas. Restringir descargas a destinos permitidos y prevenir acceso a servicios internos mediante URLs manipuladas. Los archivos subidos tienen límites de tamaño/tipo y se procesan separados del servidor de clientes.

Los reportes del original sobre controles presentes en V4 siguen como **reportados**. Antes de reutilizarlos, comprobar alcance: un límite por proceso no es un límite distribuido; una firma verificada no garantiza idempotencia; una copia de respaldo no demuestra restauración.

**[I]** Mantener modelo de amenazas por capacidad y plan de incidentes con personas responsables. **[C]** Automatizar controles repetibles, notificar incidentes según el procedimiento legal aprobado y revisar accesos. **[G]** Antes de habilitar pagos integrados de comensales, completar una revisión de seguridad independiente con hallazgos críticos/altos resueltos y pruebas de conciliación. Una revisión externa no sustituye pruebas continuas ni garantiza ausencia de fallos.

## Capa transversal C — Infraestructura y alojamiento

Separar sitios públicos, servidor operativo y taller del agente. Una caída del taller no debe tumbar sitios ni pedidos. Una caída del servidor puede dejar información estática disponible, pero las acciones que dependan de él deben degradarse explícitamente.

| Componente | Contrato de infraestructura | Candidatos heredados del original, por evaluar |
| --- | --- | --- |
| Sitios públicos | Versiones inmutables, activación controlada, certificados y caché verificable | Cloudflare Pages, Netlify, Vercel |
| Servidor operativo | Almacenamiento duradero, límites, salud y despliegue compatible | Cloud Run, Fly.io, Render o servidor gestionado |
| Base de datos | Transacciones, aislamiento, migraciones y recuperación probada | PostgreSQL; Neon, Supabase, Cloud SQL o RDS |
| Activos | Acceso privado/público separado, derivados rastreables, revocación | R2/Images, S3/CloudFront u opción equivalente |
| Taller del agente | Cola, presupuesto, reintentos acotados y aislamiento de secretos | Trabajadores separados de producción |
| Observabilidad | Registros y alertas accesibles aunque caiga el servidor | Sentry, Grafana o solución equivalente |
| Dominios | Titularidad, renovación, salida y permisos explícitos | Proveedor por decidir con el negocio |

No se verificaron tarifas ni límites comerciales de estos candidatos en esta revisión: se conservan como opciones, no como selección vigente. La compra exige comparación actual y costos para 10, 100 y 1.000 restaurantes. No imponer “mínimo dos instancias” como sustituto de medir capacidad y recuperación.

### Construcción y objetivos operativos

1. **[I]** Elegir proveedor/región mediante medición desde la población atendida, costo y operación necesaria; registrar impuestos y moneda del presupuesto.
2. **[C]** Separar desarrollo, pruebas y producción, con datos y secretos propios; no copiar datos de comensales a pruebas sin una política autorizada.
3. **[C]** Recrear infraestructura desde configuración versionada; documentar las acciones externas que todavía sean manuales.
4. **[C]** Integrar migraciones de V4 únicamente tras revisar esquema real y compatibilidad; no aplicar a ciegas un delta citado en un resumen.
5. **[C]** Persistir progreso del orquestador y claves de efectos externos; reanudar sin doble sitio, cobro, pedido ni mensaje.
6. **[C]** Probar activación, interrupción, reanudación y vuelta atrás con datos actuales.
7. **[I]** Definir y ejecutar carga según un volumen explícito; un viernes de demanda alta debe representarse con solicitudes/segundo, concurrencia y mezcla de operaciones, no una frase.
8. **[C]** Configurar alertas que tengan destinatario, suplente y acción de recuperación, no solo un tablero.

`RecoveryPolicy` debe especificar tiempo objetivo de recuperación y pérdida máxima tolerable de datos —RTO y RPO, respectivamente— por componente. Propuesta inicial para validar en el piloto: información estática recuperable en 60 minutos con pérdida máxima de 24 horas de cambios recuperables; si se persisten pedidos, RTO de 60 minutos y RPO de 5 minutos, más conciliación obligatoria de operaciones y movimientos externos. Estos valores son objetivos de diseño, **no acuerdos de servicio ni resultados demostrados**. Deben endurecerse o reducirse capacidades si el negocio no puede tolerarlos.

Toda operación confirmada que pueda haberse perdido necesita investigación y conciliación con evidencia disponible; el objetivo de RPO no autoriza a ignorarla. Si la arquitectura no permite ese tratamiento, no habilitar la capacidad. No guardar pruebas o secretos en el único servidor cuyo fallo se pretende recuperar.

**[G] G13 — Recuperación.** Restaurar una copia, comprobar contenido y operación, medir pérdida/tiempo, probar pausa/reanudación y demostrar que la vuelta atrás conserva pedidos y políticas actuales. Sin simulacro válido para el alcance publicado, no pasa.

## Capa transversal D — Legal, operación y negocio

Esta sección es un conjunto de requisitos de revisión y de producto; no certifica cumplimiento jurídico. Conservar la revisión por un profesional colombiano antes de tratar datos personales o habilitar operaciones que lo requieran. La decisión legal se documenta con versión, alcance y responsable, no con un texto genérico generado por el modelo.

El original identifica la Ley 1581 de 2012 como marco de datos personales [D0]. Su vigencia y reglamentación aplicable deben verificarse en la revisión legal; no se declara completa esa verificación en esta entrega. Para comercio electrónico, la revisión incluye el Estatuto del Consumidor, la regulación aplicable y sus modificaciones, no solo copiar una plantilla de términos [S8].

| Tema | Decisión/documento necesario | Bloqueo correspondiente |
| --- | --- | --- |
| Representación | Quién autoriza sitio, sede y dominio, y con qué alcance | Sin autoridad suficiente no hay sitio oficial público |
| Datos personales | Finalidades, base aplicable, autorizaciones cuando correspondan, responsables/encargados y derechos | Sin revisión del flujo no se recolectan datos del comensal |
| Retención y supresión | Plazos por categoría, obligaciones de conservación y procedimiento de atención | No se promete “borrar todo inmediatamente” ni se conserva indefinidamente por defecto |
| Proveedores y transferencias | Qué recibe cada tercero, dónde, para qué y bajo qué condiciones | No enviar datos al proveedor no aprobado |
| Derechos de contenido | Permisos, atribuciones, usos y revocación | Activo pendiente/denegado no se publica |
| Venta y consumidor | Identificación, información de producto, precios/costos, condiciones, reclamos y evidencia de aceptación | No cobrar ni confirmar con condiciones indeterminadas |
| Facturación y fondos | Responsabilidad de 101 y del restaurante; quién recibe qué pago | No mezclar cobro del servicio con dinero de pedidos |
| Dominio y salida | Titularidad, acceso, exportación, transición y uso posterior de activos | No asumir que 101 retiene dominio o lista de clientes |
| Soporte | Canal, horarios, responsable, suplente y alcance | Capacidad operativa sin responsable permanece deshabilitada |
| Plan comercial | Precio, límites, cambios, mora y cancelación | No prometer funciones aún no integradas |

La suspensión por mora o la salida no debe borrar pedidos pendientes, impedir resolver pagos/reclamos ni convertir activos revocados en públicos. El procedimiento define qué se desactiva, qué conserva acceso restringido y qué se exporta en formato utilizable. Respetar derechos de terceros: no todo recurso puede transferirse porque estaba en el sitio.

**[C]** Implementar avisos y consentimientos desde plantillas aprobadas, registro de aceptación, atención de solicitudes y eliminación/anonimización conforme al plan legal. Inglés es una capacidad de contenido adicional cuando se solicite; las traducciones conservan hechos, moneda, condiciones y alcance, y requieren revisión.

**[G] G11 — Legal y operación.** Para el alcance concreto existen autorizaciones, tratamiento de datos, condiciones y responsable operativo aprobados. Un formulario generado no basta; tampoco se exige una integración futura que esté deshabilitada.

## Cómo trabaja el agente

El agente propone y compone; un orquestador controla estado y herramientas. La producción no depende de que el modelo recuerde restricciones escritas en un prompt.

| Quién decide | Responsabilidad |
| --- | --- |
| Código y ejecutores confiables | Esquemas, coherencia, permisos, versiones, pruebas y autorización mecánica de transiciones |
| Modelo de lenguaje/visión | Borradores, extracción, arquetipo, propuestas de diseño y hallazgos sujetos a verificación |
| Búsqueda y optimización | Candidatos dentro de un espacio y presupuesto aprobados |
| Persona del negocio | Confirmación de hechos y condiciones que le competen; recepción y aceptación operativa |
| Revisión humana de calidad | Uso, estética y aspectos no cubiertos automáticamente |
| Responsable de publicación | Asegurar que la versión elegible es la desplegada, con permisos y recuperación |

### Estado, repetición y reparación

El orquestador guarda `run_id`, negocio/sede, fase, entradas, intento, costos, estado y artefactos. Estados de referencia: `queued`, `running`, `waiting_for_human`, `blocked`, `failed`, `completed`. Una tarea puede reintentarse; sus efectos externos requieren una clave idempotente y verificación de estado. No se promete ejecución “exactamente una vez” por usar una cola.

Después de una interrupción, verificar si el efecto ocurrió antes de repetirlo. Un resultado desconocido de despliegue o pago requiere consulta/conciliación, no una segunda operación ciega. Reintentar errores transitorios con espera y límite; errores de permisos, datos inválidos o rechazo humano vuelven a su responsable.

| Fallo | Regresa a | Acción |
| --- | --- | --- |
| Dato faltante, vencido o contradictorio | Fase 1 | Solicitar confirmación o reducir capacidad con aprobación |
| Activo sin derechos | Fase 1/3 | Retirar/sustituir activo o cambiar composición |
| Promesa sin capacidad | Fase 2/4 | Corregir plan/texto o implementar y validar capacidad |
| Precio o contenido perdido | Fase 4/5 | Reparar representación y repetir integridad |
| Problema visual | Fase 3/5 | Mutar parámetros sin cambiar hechos |
| Falla de pago o reserva | Fase 4 | Contener, conciliar y no fabricar éxito |
| Aprobación desactualizada | Fase 6 | Obtener aprobación del alcance cambiado |
| Falla en producción | Fase 6/C | Pausar capacidad, volver a versión compatible o corregir |

### Contratos adjuntos y límite de su validación

`especificacion/contratos.schema.json` contiene esquemas JSON de hechos, derechos, plan de capacidades, candidato, aprobación y resultado de compuerta. Son contratos de referencia que deben mapearse al código existente. JSON Schema valida forma, campos y algunas condiciones; **no prueba que una foto tenga derechos, una persona tenga autoridad o un pago haya ocurrido**.

`especificacion/compuertas.json` y `especificacion/pruebas_aceptacion.json` convierten reglas en obligaciones identificables y comprobables. Cada prueba define preparación, estímulo, resultado esperado y evidencia. Su implementación y ejecución en el repositorio siguen pendientes; los archivos no contienen resultados de producto inventados.

`herramientas/validar_especificacion.py` comprueba los esquemas, ejemplos, referencias cruzadas y cobertura de la entrega documental. No inspecciona Astro, no llama proveedores y no habilita publicaciones. Una validación correcta de esta entrega no cambia `NOT_RUN` en las pruebas del producto.

## Catálogo de compuertas

El catálogo detallado y legible por máquina se incluye en el paquete. La aplicabilidad se deriva de la modalidad y capacidades, no de la preferencia del agente.

| ID | Qué controla | Momento | Si falla |
| --- | --- | --- | --- |
| G00 | Inventario técnico, versiones y compatibilidad real | Antes de integrar; repetir al cambiar dependencias pertinentes | No afirmar integración ni reutilizar sin revisar |
| G01 | Identidad, datos, sede, aprobación y vigencia | Fase 1 y cambios de datos | Confirmar/corregir o deshabilitar dependencia |
| G02 | Derechos y restricciones de recursos | Antes de usar/publicar; revocaciones | Retirar o sustituir recurso |
| G03 | Capacidades, contenido, promesas y omisiones | Fase 2 y cambios de alcance/texto | Reparar plan o contenido |
| G04a | Piso de diseño: legalidad de la composición y estados, automática | Fase 3/5 y toda reparación visual | Reparar diseño sin alterar hechos |
| G04b | Calidad de diseño: rúbrica de 3L, humana | Fase 3/5 cuando cambia la composición de una ruta | Volver a dirección o composición; no compensa un fallo de G04a |
| G05 | Operación funcional y casos de fallo | Fase 4/5; por capacidad | Bloquear capacidad o reparar |
| G06 | Integridad factual y privacidad de lo entregado | Fase 5 y cambios de representaciones | Bloquear artefacto y localizar divergencia |
| G07 | Navegadores, recursos, rutas y errores técnicos | Fase 5 | Reparar y volver a probar |
| G08 | Accesibilidad automática y manual | Fase 5 | Resolver barreras y repetir pruebas |
| G09 | Presupuestos de rendimiento y plan de medición real | Fase 5; observación en fase 7 | Optimizar o revisar alcance antes de aprobar |
| G10 | Seguridad, permisos, aislamiento y secretos | Toda superficie expuesta y cada cambio relevante | Contener, reparar y revisar permisos |
| G11 | Autorización, datos, condiciones y operación legal revisada | Antes de exposición/operación aplicable | No recolectar, cobrar o publicar fuera de alcance |
| G12 | Aprobaciones vigentes y correspondencia de versión | Inmediatamente antes de promover candidato | Nueva aprobación o candidato válido |
| G13 | Recuperación, reanudación y vuelta atrás compatible | Antes del piloto y cambios relevantes de infraestructura | Resolver recuperación o reducir alcance |
| G14 | Funcionamiento observado en producción | Después de desplegar | Retirar/degradar y reparar |
| G15 | Eventos, deduplicación y métricas con límites | Antes y después de publicar | No declarar resultados comerciales confiables |
| G16 | Evaluación independiente y límites de autonomía | Antes de afirmar generalización o quitar revisión | Conservar revisión humana y ampliar evaluación |

**Elegibilidad previa a publicación:** G00–G13 (con G04a y G04b) y G15 deben contar con evidencia pertinente y vigente; el alcance de cada una en el piloto está fijado en «Mínimo del piloto»; los casos de capacidades deshabilitadas se excluyen por política. G14 es posterior y no puede exigirse como evidencia de un despliegue aún no ocurrido. G16 no bloquea el piloto revisado por personas, pero sí afirmaciones de autonomía o generalización. Los reportes globales se reutilizan solo si las versiones, el entorno y el alcance coinciden y no han vencido.

## Mínimo del piloto

El catálogo exige G00 a G13 y G15 antes de publicar. Para el piloto eso se mantiene, pero cada compuerta se evalúa con el **alcance del piloto**, que es mucho menor que el del producto completo. Esta sección fija ese alcance para que «aplicable» no se decida caso por caso ni lo decida el agente.

### Supuestos que reducen el alcance

Son decisiones propuestas. Si una cambia, la compuerta correspondiente vuelve a su alcance completo.

| Supuesto | Qué implica | Qué compuertas reduce |
| --- | --- | --- |
| S1. Un solo negocio y una sola sede | No hay datos de dos restaurantes en el mismo sistema | G10 (aislamiento), G01 (mezcla de sedes) |
| S2. Sitio estático con catálogo en un archivo versionado | El navegador compara `catalog_version` antes de preparar la solicitud; no hay servidor de pedidos | G05, G10, G13 |
| S3. Las actualizaciones las aplica un operador de 101 autenticado, con aprobación del dueño registrada | No hay panel ni cuentas del restaurante todavía | G10, capa A |
| S4. El restaurante registra recepción y aceptación a mano, con la referencia de la solicitud | No hay integración con WhatsApp ni cola de pedidos | G05, G15 |
| S5. Los sistemas de 101 no guardan datos personales de comensales | La conversación ocurre en WhatsApp; 101 solo ve una referencia | G11, capa B |
| S6. Diseño en nivel N0 | Sin exploración automática ni Design Compiler | G04, G00 |

Con S2 se cumple la condición del precio del hito 1: el carrito abierto detecta la versión nueva y pide reconfirmar. Lo que S2 no da es un registro de servidor de `request_created`; en el piloto ese evento es un registro manual identificado, como permite la fase 7A.

### Alcance por compuerta

| Compuerta | En el piloto | Evidencia mínima | Fuera del piloto |
| --- | --- | --- | --- |
| G00 Inventario | Aplica, solo a lo que se reutiliza: compilador, runtime del sitio y QA de navegador | Commit fijado, pruebas existentes ejecutadas, lista de qué se reutiliza y qué no | Restaurant Commerce V4 y Design Compiler |
| G01 Datos e identidad | Aplica completa para una sede | Paquete con evidencia, vigencia y aprobación del dueño por valor | Reglas entre sedes |
| G02 Derechos | Aplica a cada recurso usado | Manifiesto con estado `cleared` para fotos, logo, fuentes y componentes | Reseñas de terceros, si no se usan |
| G03 Capacidades y contenido | Aplica a `public_info`, `menu_html`, `whatsapp_contact` y `whatsapp_request` | `CapabilityPlan`, política operativa firmada por el dueño, `ClaimMap` | Las otras seis capacidades, deshabilitadas |
| G04a Piso de diseño | Aplica completa | Reporte automático por ruta, viewport y estado | — |
| G04b Calidad de diseño | Aplica; dos revisores | Rúbrica de 3L diligenciada, con capturas de cada «falla» | Comparación ciega contra referencia |
| G05 Funcionalidad | Aplica a horario, menú, carrito, preparación de la solicitud y cambio de precio | Casos de WhatsApp de 4D; caso de COP 25.000 a 28.000; estados de error | Reservas, pagos, inventario, domicilios, concurrencia de cupos |
| G06 Verdad de la entrega | Aplica completa | Comparación de la proyección pública contra HTML, carrito y datos estructurados; búsqueda de datos internos | — |
| G07 QA técnico | Aplica completa; pocas rutas | Tres motores automatizados y prueba manual en un iPhone y un Android | — |
| G08 Accesibilidad | Aplica completa | Escáner más una revisión manual de teclado, lector de pantalla y zoom | — |
| G09 Rendimiento | Aplica en laboratorio | Cinco ejecuciones en perfil móvil con los presupuestos de 5C | Datos de campo, hasta tener tráfico |
| G10 Seguridad | Reducida por S1 a S3 | Escaneo de secretos en repositorio y artefactos; segundo factor en las cuentas de operador; vista previa con acceso restringido; cabeceras del sitio | Aislamiento entre restaurantes, sesiones de dueño y personal: `NOT_APPLICABLE` con motivo S1 y S3 |
| G11 Legal y operación | Reducida por S5 | Autorización del dueño; acuerdo del piloto; revisión legal breve que confirme S5 y los avisos necesarios; responsable operativo y suplente | Tratamiento de datos de comensales, condiciones de venta en línea |
| G12 Aprobación | Aplica completa | `ReleaseManifest` con huella; aprobaciones de dueño, revisor y responsable de publicación sobre esa huella | — |
| G13 Recuperación | Reducida por S2 | Un simulacro: volver a la versión anterior del sitio y restaurar el paquete de datos desde copia | Recuperación de base de datos de pedidos |
| G14 Producción | Aplica después de desplegar | Una solicitud controlada que el restaurante recibe y acepta de verdad | — |
| G15 Medición | Reducida por S4 | Eventos de navegador más recepción y aceptación manuales; un caso controlado contado una sola vez; abrir y cerrar WhatsApp no crea pedido | Pagos, reservas, cumplimiento |
| G16 Evaluación | No se exige | — | Se exige para afirmar generalización o reducir revisión humana |

Un `NOT_APPLICABLE` de esta tabla solo vale mientras su supuesto sea cierto, y se registra con el supuesto como motivo. En el hito 2, con un segundo restaurante, S1 deja de ser cierto y G10 recupera las pruebas de aislamiento.

### Pruebas del catálogo

Esta revisión no tuvo acceso a `especificacion/pruebas_aceptacion.json`; la asignación siguiente se basa solo en el registro de cambios de la versión 2.0 y debe confirmarse contra el catálogo.

| Grupo | Casos según el registro | En el piloto |
| --- | --- | --- |
| Evidencia, vigencia y proyección pública | T01 a T08, T72 | Sí |
| Afirmaciones y microtextos | T09, T20, T57, T73 | Sí |
| Derechos | T10 a T12 | Sí |
| Capacidades y dependencias | T13, T14 | Sí |
| WhatsApp y estados de solicitud | T17 a T19, T22, T27, T59, T62, T74 | Sí |
| Cambio de precio y versiones | T23 a T26 | Sí |
| Prospecto frente a sitio oficial | T06, T43, T69 | Sí |
| Aprobación y compuertas | T45 a T47, T68, T71 | Sí |
| Recuperación | T48 a T51, T63, T70 | Sí, con el alcance reducido de G13 |
| Navegadores, accesibilidad y rendimiento | T53 a T57 | Sí |
| Medición | T60, T61 | Sí |
| Reservas y pagos | T21, T28 a T39, T52 | No: capacidades deshabilitadas |
| Banco de evaluación y argumento económico | T64 a T66 | No: G16 no se exige |

Unos 17 de los 74 casos quedan fuera por política. Los casos que el registro no menciona (T15, T16, T40 a T42, T44, T58 y T67) se clasifican al revisar el catálogo. Los excluidos conservan `NOT_RUN` y no se cuentan como aprobados.

### Orden de trabajo

1. G00 sobre el repositorio, limitado a lo que el piloto reutiliza.
2. Elegir restaurante y obtener autorización; acordar S1 a S6 con el dueño.
3. Llenar a mano el paquete de datos y el manifiesto de derechos; pasar G01 y G02.
4. Definir capacidades, política operativa y plan de sitio; pasar G03.
5. Referentes (3M) y dirección de arte (3D); elegir una.
6. Diseñar y construir la página patrón en N0; pasar G04a.
7. Implementar menú, carrito, preparación de la solicitud y lectura del catálogo versionado; pasar G05.
8. Compilar el candidato; pasar G06 a G09.
9. Revisión de diseño con la rúbrica; pasar G04b. Si falla, volver al paso 6.
10. Pasar G10, G11 y G13 con el alcance reducido; instrumentar y pasar G15.
11. Aprobaciones sobre la huella del candidato; pasar G12 y publicar.
12. Verificar en producción con una solicitud real controlada; pasar G14.
13. Escribir qué decisiones de diseño se tomaron a mano y por qué. Es el insumo del nivel N1.

Los pasos 5 y 6 pueden avanzar en paralelo con 3 y 4 usando contenido provisional marcado como tal, pero G04b se evalúa con el contenido aprobado.

## Por dónde empezar

### Hito 0 — Saber qué hay

Verificar repositorio y documentos citados; fijar commit; ejecutar pruebas existentes; reproducir o descartar las pérdidas de contenido históricas. Entregar inventario de módulos reutilizables, incompatibilidades y tareas. Ninguna cifra de un chat sustituye este paso.

### Hito 1 — Un restaurante real operando

Elegir una sede con persona autorizada y receptor dispuesto. Capturar manualmente datos y derechos. Aprobar menú, condiciones y acción principal. Construir el patrón con ayuda del agente sin exigir todavía diseño autónomo. Configurar mantenimiento, registro mínimo de resultados y contingencia.

**Condición de terminado del piloto — todas deben cumplirse:**

1. El sitio público autorizado pasa sus compuertas aplicables y corresponde al candidato aprobado.
2. Una persona puede consultar menú, precio, ubicación/horario y preparar una solicitud sin barreras críticas.
3. Una solicitud controlada llega al restaurante, se acepta o rechaza con evidencia, y se registra el resultado; cerrar WhatsApp antes de enviar no cuenta como pedido.
4. Cambiar COP 25.000 por COP 28.000 se propaga según el contrato: carrito abierto reconfirma; pedido aceptado conserva precio; diseño no se regenera.
5. Una interrupción de la capacidad produce un mensaje y una contingencia correctos, sin falsa confirmación.
6. Una interrupción del pipeline puede retomarse sin duplicar efectos y una vuelta atrás conserva datos operativos vigentes.
7. Se han registrado minutos humanos, costos de herramientas, soporte y límites de medición. No es obligatorio demostrar una mejora causal de ventas para declarar el piloto técnico completo.
8. El negocio puede corregir un agotado u horario y existe un responsable para revisiones, incidentes y vencimientos.

### Hito 2 — Repetibilidad con otros restaurantes

Repetir con cinco negocios de necesidades distintas, registrando excepciones y costos. Automatizar primero compilación desde datos completos y actualización segura; después captura y extracción; finalmente exploración de diseño. No automatizar una regla que aún no está clara. Construir en paralelo el banco de evaluación protegido sin convertir los cinco pilotos en una prueba universal de calidad.

### Hito 3 — Capacidades transaccionales adicionales

Añadir reservas o pagos solo cuando exista demanda y operación responsable. Implementar pruebas de concurrencia, conciliación, seguridad y recuperación correspondientes. Cuentas, lealtad y despacho requieren sus propios contratos; no llegan automáticamente con una integración de pago.

## Decisiones adoptadas y decisiones realmente abiertas

| Tema | Decisión de esta versión | Lo que todavía requiere selección o evidencia |
| --- | --- | --- |
| Entrada | Prototipo privado separado de sitio autorizado | Restaurante piloto y persona autorizante |
| Primer alcance | Una sede, menú, contacto, actualización y solicitud por WhatsApp | Receptor, tiempos y política operativa concreta |
| Capacidades | Independientes con dependencias explícitas; elegidas antes del diseño | Cuáles solicitará cada cliente después del piloto |
| Fotos | Condicionales al diseño; derechos obligatorios para las utilizadas | Activos aprobados de cada negocio |
| Datos y publicación | Públicos obligatorios/opcionales/internos; versiones y vigencia | Mapeo de campos con modelos reales |
| Aprobación | Alcance y versión exactos; agente no aprueba por humanos | Identidades y permisos operativos |
| Cuentas | No obligatorias para el piloto | Justificación futura y flujo de privacidad |
| Diseño | Piso automático y techo con rúbrica humana; niveles N0 a N3; piloto en N0 | Dirección de arte del piloto; ajuste de la rúbrica con referentes |
| Design Compiler | Reutilización condicionada a inspección; entra en el nivel N3; composición patrón como respaldo | Qué módulos cumplen contratos y rúbrica |
| Infraestructura | Sitio, servidor y taller separados lógicamente | Proveedores, región, costos y recuperación medida |
| Propiedad/salida | Debe acordarse antes de publicar; exportación y responsabilidades explícitas | Titularidad contractual de dominio, datos y activos |
| Precio y equipo | No se inventan valores, responsables ni reparto Gabriel/Thomas | Costos reales, plan comercial y asignación acordada |
| Autonomía | Revisión humana al inicio; pagos no dependen de un umbral estético | Evidencia independiente suficiente para cualquier reducción de revisión |

## Fuentes y procedencia

Las referencias externas justifican hechos específicos de proveedores o estándares. Las políticas internas, plazos, presupuestos y decisiones de arquitectura son **propuestas de esta revisión**, no exigencias atribuidas a esas fuentes. Consulta técnica: 3 de octubre de 2026. No se hizo una auditoría del repositorio ni una certificación legal.

- **[D0] Documento base del usuario:** `referencia/Pipeline_101_original.md`, “Pipeline 101: páginas de restaurante automatizadas”, 1 de octubre de 2026. SHA-256: `0019fe79ce07f24d05620bae7843ffd2cbd8cca0e05b984c61dbf072c1005837`. Contiene reportes previos de código y cifras que aquí se mantienen como históricos no verificados.
- **[S1] WhatsApp Help Center:** [How to use click to chat](https://faq.whatsapp.com/5913398998672934). Respalda la distinción entre texto prellenado y envío/recepción.
- **[S2] Google Maps Platform:** [Policies and attributions for Places API](https://developers.google.com/maps/documentation/places/web-service/policies). Respalda la necesidad de revisar condiciones de presentación, atribución y almacenamiento por uso.
- **[S3] W3C:** [Web Content Accessibility Guidelines 2.2](https://www.w3.org/TR/WCAG22/). Base de los criterios de accesibilidad; las metas adicionales de tamaño del producto están identificadas como tales.
- **[S4] web.dev / Google:** [Web Vitals](https://web.dev/articles/vitals). Definiciones, umbrales y distinción entre observación de campo y laboratorio.
- **[S5] Google Search Central:** [General structured data guidelines](https://developers.google.com/search/docs/appearance/structured-data/sd-policies). Correspondencia con contenido visible y ausencia de garantía de resultados enriquecidos.
- **[S6] Wompi:** [Eventos](https://docs.wompi.co/docs/colombia/eventos/). Reintentos, ambientes y procedimiento de verificación de checksum. La arquitectura de idempotencia/conciliación es una decisión de este pipeline.
- **[S7] Wompi:** [Transacciones](https://docs.wompi.co/docs/colombia/transacciones/). Unidad `amount_in_cents` y contrato de transacciones; verificar de nuevo al implementar el adaptador.
- **[S8] Ministerio de Comercio, Industria y Turismo:** [Protección del consumidor](https://www.mincit.gov.co/minindustria/estrategia-transversal/regulacion/proteccion-del-consumidor). Marco general y regulación relacionada. Esta referencia no sustituye comprobar el texto consolidado y las obligaciones concretas con asesoría jurídica.

Las consultas directas a los textos consolidados de las leyes en Función Pública y Secretaría del Senado no pudieron completarse durante esta revisión. Por eso esta entrega no declara verificación integral de vigencia normativa ni fija plazos legales de atención o retención. G11 exige resolver ese punto antes de las operaciones afectadas.
