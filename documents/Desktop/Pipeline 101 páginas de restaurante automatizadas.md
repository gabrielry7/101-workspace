# Pipeline 101: páginas de restaurante automatizadas

Oct 1, 2026 · @Someone

## Punto de partida

Sí hay avance, y es bastante: Thomas ya tiene casi todas las piezas, pero sueltas y sin un solo sitio listo para un cliente real. Este pipeline no arranca de cero; ordena lo que existe, marca lo que falta y lo enfoca en restaurantes.

| Pieza | Qué hace hoy | Qué le falta |
| --- | --- | --- |
| Pipeline de producción (`101-world-model`) | Evidencia → Truth → SiteSpec → compilador → sitio Astro → QA en navegador | 0 de 3 y 0 de 9 sitios quedaron listos para cliente; falta contenido publicable |
| Design Compiler (experimental, v0.1 a v0.12) | Operadores de composición, render en Chromium, crítica por captura, mutación, corpus de componentes OSS | No está integrado al pipeline de producción; calidad visual sin validar por humanos |
| Restaurant Commerce V4 | Menú, carrito, pagos, reservas, lealtad, domicilios; 79 tests | No está integrado; Wompi, Uber Direct y Mensajeros Urbanos sin adaptadores reales |
| Inventario de Bogotá | 114.028 candidatos comerciales desde Overture | No son negocios verificados; sin filtro por restaurantes aún |

Tres límites de este documento:

- Se basa en los resúmenes de los chats de Thomas, no en el código. Antes de construir hay que revisar el repo y `docs/SYSTEM_REGISTRY.md`.
- El resumen del 1 de octubre dice que solo 2 de 7 servicios aprobados llegan al HTML. Otro del 28 de septiembre dice que eso ya se reparó (commit `9f7cefd`). Hay que confirmarlo con Thomas.
- Los documentos de Thomas dicen que el diseño se integra cuando existan sitios «veraces pero feos». Para restaurantes ese orden se puede acortar, porque el dueño puede entregar los datos directamente.

## Qué es una página GOAT para un restaurante

Una página GOAT es la que convierte a un visitante con hambre en un pedido, una reserva o una visita, y lo hace mejor que Rappi, Instagram o el perfil de Google. Bonita es una condición, no la meta.

Se puede medir en cinco capas, de la más básica a la más difícil. Una página no sube de capa si falla la anterior.

| Capa | Pregunta que responde | Cómo se verifica |
| --- | --- | --- |
| 1. Verdad | ¿Todo lo que dice es cierto y actual? | Cada dato visible tiene fuente: horario, dirección, precios, platos |
| 2. Utilidad | ¿El visitante resuelve lo que vino a hacer? | En celular y sin hacer scroll: qué es, dónde queda, si está abierto y un botón de acción |
| 3. Función | ¿Puede pedir, reservar o escribir sin fricción? | Flujo completo probado: menú → carrito → pago o WhatsApp → confirmación |
| 4. Descubrimiento | ¿Google y los asistentes de IA la encuentran y la entienden? | Datos estructurados válidos, velocidad en celular, coherencia con el perfil de Google |
| 5. Estética | ¿Se ve como hecha por un estudio y se siente de ese restaurante? | Crítica visual automatizada y, sobre todo, juicio humano comparando contra referentes |

Lo que casi siempre separa una página de restaurante buena de una mala:

- **Celular primero.** La mayoría llega desde el teléfono, con prisa y una mano.
- **Menú en HTML, nunca en PDF.** Con precios, fotos y categorías; se puede buscar, leer e indexar.
- **Una acción principal clara.** Pedir, reservar o WhatsApp, visible siempre.
- **Fotos reales de la comida y del lugar.** Es lo que más pesa en la decisión y lo más difícil de automatizar.
- **Canal propio.** El pedido directo le ahorra al restaurante la comisión de las plataformas; ese es el argumento de venta.

La capa 5 es la única sin respuesta conocida. «Cómo saber que un diseño es bueno» es un paso de investigación del pipeline, no un supuesto.

## Principios del pipeline

El pipeline mezcla tres tipos de paso, y cada paso de este documento lleva su etiqueta. Así caben pasos abiertos como «averiguar cómo hacer que el layout se vea bien» sin fingir que ya están resueltos.

| Tipo | Qué es | Cómo termina |
| --- | --- | --- |
| **\[I\] Investigación** | Pregunta abierta; nadie sabe aún la respuesta | Con un hallazgo escrito y una regla o un experimento que la pruebe |
| **\[C\] Construcción** | Se sabe qué hacer; falta hacerlo | Con código, tests y un caso real funcionando |
| **\[G\] Compuerta** | Verificación que decide si se avanza | Con pasa o no pasa, y la razón |

Reglas que aplican a todo:

1. **Los pasos se pueden partir.** Un paso \[I\] que resulta grande se divide en sub-pasos; el número de pasos no es fijo.
2. **Nada se inventa.** Viene de `AGENTS.md`: un dato sin fuente no se publica. En restaurantes la fuente más fuerte es el dueño.
3. **Compuertas duras, composición libre.** Sin texto cortado, sin solapes, sin datos falsos: eso es determinista. El estilo, la asimetría y la tipografía se exploran.
4. **Una página fea y cierta vale más que una linda y falsa.** El orden de las capas GOAT manda.
5. **Reusar antes de construir.** Antes de cada paso \[C\], revisar si Thomas ya lo tiene en el repo.
6. **Humano en el circuito al principio.** Las primeras páginas las aprueba una persona; la autonomía del agente se gana con evidencia.
7. **Horizontal por dentro, restaurante por fuera.** `AGENTS.md` prohíbe lógica tipo `if restaurante:`. Lo específico de restaurantes vive en datos y configuración, no en ramas de código.

## Mapa general

El pipeline tiene siete fases y cada una entrega un archivo concreto a la siguiente. Encima corren cuatro capas transversales: plataforma, seguridad, infraestructura y legal. Suman unos 110 pasos hoy; los de investigación se irán partiendo en más a medida que se entiendan.

&#91;embedded content: mapa del pipeline · 7 fases, 2 ciclos\]

Las fases 1 a 4 producen la especificación; la 5 construye y repara hasta pasar las compuertas; la 7 devuelve lo aprendido al inicio.

## Fase 1 — Datos del restaurante

La salida de esta fase es un **paquete de datos del restaurante**: un archivo estructurado con todo lo que la página necesita, cada dato con su fuente y su estado. Sin este paquete completo, las demás fases no arrancan.

| Bloque | Datos | Obligatorio | Fuente más probable |
| --- | --- | --- | --- |
| Identidad | Nombre, tipo de cocina, descripción corta, historia | Sí (nombre y tipo) | Dueño, Google, Instagram |
| Ubicación | Dirección, coordenadas, barrio, cómo llegar, sedes | Sí | Google Places, dueño |
| Horarios | Por día, festivos, cocina vs. local | Sí | Google Places, dueño |
| Contacto y acción | Teléfono, WhatsApp, reservas, domicilios | Sí (al menos una acción) | WhatsApp Business, Instagram, dueño |
| Menú | Categorías, platos, descripciones, precios, modificadores, alérgenos | Sí | Dueño, foto o PDF de la carta, plataformas de domicilios |
| Fotos | Platos, local, equipo, logo | Sí (mínimo de platos y local) | Dueño, Instagram, Google |
| Marca | Logo, colores, tono, referentes que le gustan | No | Dueño, Instagram |
| Reputación | Calificación, reseñas, platos más mencionados | No | Google, reseñas |
| Operación | Zonas de domicilio, medios de pago, tiempos, capacidad | Solo si hay pedidos o reservas | Dueño |

### Pasos

1. **\[I\] Definir el esquema del paquete.** Qué campos, cuáles son obligatorios, cómo se representa un menú con modificadores. Revisar qué ya cubren `SiteSpec` y los modelos de Restaurant Commerce V4.
2. **\[I\] Decidir la puerta de entrada.** ¿El restaurante ya es cliente y entrega datos, o la página se arma sola desde fuentes públicas para vendérsela? Cambia toda la fase.
3. **\[C\] Captura automática desde fuentes públicas.** Reusar lo de Thomas: Google Places, Instagram, WhatsApp, reseñas.
4. **\[I\] Extraer el menú de una foto o un PDF.** Probar lectura con modelo de visión sobre cartas reales y medir errores en precios.
5. **\[C\] Formulario de captura para el dueño.** Corto, por WhatsApp o web, que solo pida lo que falta y pida confirmar lo capturado.
6. **\[I\] Derechos y calidad de las fotos.** Cuáles se pueden usar, cuáles sirven, qué hacer si no hay ninguna buena.
7. **\[C\] Clasificar y puntuar fotos.** Plato, local o gente; nitidez, luz, encuadre; punto focal para recortes.
8. **\[C\] Extraer marca.** Colores dominantes del logo y de las fotos; tono a partir de los textos del restaurante.
9. **\[G\] Compuerta de datos.** El paquete pasa si tiene nombre, dirección, horario, una acción, menú con precios y un mínimo de fotos. Si no pasa, vuelve al paso 5 con la lista de faltantes.

## Fase 2 — Estrategia y contenido

Esta fase decide qué dice la página y en qué orden, antes de decidir cómo se ve. La salida es un **plan de sitio**: páginas, secciones por página y el texto de cada sección, todo atado a datos del paquete.

### Pasos

1. **\[I\] Arquetipos de restaurante.** Una cafetería de barrio, un restaurante de manteles y una hamburguesería de domicilios necesitan páginas distintas. Definir entre 4 y 6 arquetipos y qué los distingue.
2. **\[C\] Clasificar el restaurante en un arquetipo.** A partir del paquete: precio promedio, tipo de cocina, si hay domicilios o reservas.
3. **\[C\] Elegir la acción principal.** Pedir, reservar o escribir por WhatsApp. Una sola manda; las demás son secundarias.
4. **\[I\] Catálogo de secciones posibles.** Portada, menú, platos destacados, historia, ubicación y horario, reseñas, galería, reservas, eventos, preguntas frecuentes. Para cada una: qué datos exige y cuándo se omite.
5. **\[C\] Armar la arquitectura del sitio.** Qué páginas existen y qué secciones lleva cada una. Regla heredada de Thomas: una sección sin datos aprobados no se emite.
6. **\[I\] Cómo escribir textos que suenen al restaurante.** El modelo redacta, pero solo puede reorganizar hechos del paquete. Definir cómo se verifica que no agregó nada.
7. **\[C\] Redactar los textos.** Titular, descripción, descripciones de platos, textos de botones, textos para buscadores.
8. **\[C\] Elegir platos destacados.** Con reseñas y fotos: los más mencionados que además tienen buena foto.
9. **\[G\] Compuerta de contenido.** Cada frase visible se rastrea a un dato del paquete. Sin frases genéricas de relleno ni afirmaciones sin fuente.

## Fase 3 — Diseño

Esta es la fase con más pasos de investigación, y es donde vive el Design Compiler de Thomas. La salida es una **especificación de diseño**: dirección de arte, tipografía, color y composición de cada sección en celular y escritorio.

La tesis de Thomas se mantiene: ni «el modelo escribe HTML y a rezar» ni «plantilla fija». Se generan varias composiciones legales, se renderizan, se miran y se elige o se muta.

### 3A. Dirección de arte

1. **\[I\] Qué hace que una página de restaurante se vea bien.** Reunir de 30 a 50 páginas referentes, anotarlas y sacar patrones. Este es el paso que define «GOAT» en la capa estética.
2. **\[I\] De arquetipo a estilo.** Qué dirección visual le corresponde a cada arquetipo: cálida, editorial, minimalista, popular. Cuántas direcciones bastan para no parecer plantilla.
3. **\[C\] Generar el ADN de dirección de arte.** Los parámetros que Thomas ya definió: espacio en blanco, asimetría, escala del título, agresividad del recorte. Se derivan del arquetipo y de la marca.

### 3B. Color y tipografía

1. **\[I\] Paleta desde la marca.** Cómo pasar de un logo y unas fotos a una paleta completa con contraste legible. Qué hacer si no hay logo.
2. **\[C\] Generar la paleta y validarla.** Fondo, texto, acento, estados; verificación automática de contraste.
3. **\[I\] Parejas tipográficas.** Qué combinaciones de fuentes libres funcionan por estilo. Thomas ya tiene cinco voces; probar si alcanzan para comida.
4. **\[C\] Escala tipográfica.** Tamaños, interlineado y ancho de línea por dispositivo.

### 3C. Composición

1. **\[I\] Cómo hacer que el layout se vea bien.** El paso más abierto. Evaluar los operadores de Thomas (Split, Stage, Editorial y demás) sobre secciones reales de restaurante y ver cuáles sirven.
2. **\[I\] La sección de menú.** Es el corazón de la página y no se parece a nada del compilador actual: listas largas, precios, fotos opcionales, categorías. Merece su propia investigación.
3. **\[C\] Generar candidatos por sección.** Varias composiciones por sección dentro de las reglas duras.
4. **\[I\] Componentes: construir o reusar.** Cuáles del corpus OSS de Thomas sirven para restaurante (navegación, acordeón, carrusel, formulario) y cuáles hay que hacer.
5. **\[C\] Ritmo de página.** Que las secciones no se repitan, que haya respiro, que el cierre se relacione con la portada.
6. **\[C\] Diseño para celular.** No es la versión encogida del escritorio; se compone primero.

### 3D. Fotos

1. **\[C\] Asignar fotos a secciones.** La mejor foto a la portada; recortes según el punto focal.
2. **\[I\] Qué hacer cuando las fotos son malas o pocas.** Diseño tipográfico sin fotos, mejora automática o pedirle más al dueño. Las fotos generadas de platos que no existen violan la capa de verdad.

### 3E. Movimiento

1. **\[C\] Animación sobria al final.** Solo cuando la composición estática ya pasa, y sin afectar la velocidad.

### Compuerta

1. **\[G\] Compuerta de diseño.** Reglas duras: sin solapes, sin texto cortado, tamaño mínimo legible, contraste suficiente, botón principal visible en el primer pantallazo del celular.

## Fase 4 — Funcionalidad

La funcionalidad se entrega por niveles, y el nivel 1 ya hace útil la página. Cada nivel superior depende de datos de operación que el dueño debe dar y de integraciones que hoy no existen.

| Nivel | Qué incluye | Depende de |
| --- | --- | --- |
| 1. Informativa | Menú en HTML, mapa, horario con «abierto ahora», llamar, WhatsApp con mensaje prellenado | Solo el paquete de datos |
| 2. Pedido por WhatsApp | Carrito en la página que arma el pedido y lo envía por WhatsApp | Menú con precios y modificadores |
| 3. Reservas | Formulario con fecha, hora y personas; confirmación | Capacidad y reglas del restaurante |
| 4. Pedido con pago | Carrito, pago en línea, seguimiento | Restaurant Commerce V4 integrado y adaptador real de Wompi |
| 5. Domicilios y lealtad | Despacho con mensajería, puntos, promociones | Adaptadores de Uber Direct o Mensajeros Urbanos |

### Pasos

1. **\[I\] Qué nivel necesita cada arquetipo.** Y cuál es el mínimo que un dueño pagaría. El nivel 2 puede ser el punto dulce en Bogotá: sin pasarela, sin comisiones.
2. **\[C\] Menú interactivo.** Categorías, búsqueda, filtros, fotos, platos agotados.
3. **\[C\] Horario vivo y mapa.** Estado abierto o cerrado según la hora de Bogotá; enlace a indicaciones.
4. **\[C\] Botones de acción.** Llamar, WhatsApp, reservar; barra fija en celular.
5. **\[C\] Carrito con envío por WhatsApp.**
6. **\[I\] Integrar Restaurant Commerce V4.** Revisar con Thomas qué falta: migraciones, PostgreSQL, adaptadores reales, secretos. Está documentado en `INTEGRATE_INTO_101.md`.
7. **\[C\] Datos estructurados para buscadores.** Restaurante, menú, horario y dirección en el formato de schema.org.
8. **\[C\] SEO local básico.** Títulos, descripciones, coherencia de nombre, dirección y teléfono con el perfil de Google.
9. **\[C\] Panel para el dueño.** Cambiar un precio, marcar un plato agotado, cambiar el horario. Sin esto la página se desactualiza y falla la capa de verdad.
10. **\[C\] Analítica.** Medir visitas, clics en la acción principal, pedidos y reservas. Sin medición no hay fase de aprendizaje.
11. **\[G\] Compuerta funcional.** Cada flujo se prueba de punta a punta en un navegador real, en celular y escritorio.

## Fase 5 — Construcción, QA y crítica

Aquí la página se construye de verdad y entra en un ciclo: renderizar, revisar, reparar y volver a renderizar hasta pasar todas las compuertas. Casi todo existe en el repo de Thomas; el trabajo es conectarlo y cerrar el ciclo, que él llama P1-6 y sigue incompleto.

### Pasos

1. **\[C\] Compilar el sitio.** Plan de sitio + especificación de diseño → sitio Astro. Reusar `WebsiteCompiler` y `@101/site-runtime`.
2. **\[C\] Renderizar en navegador.** Chromium, celular y escritorio, con capturas de cada sección.
3. **\[G\] QA técnico.** Desbordes, texto cortado, enlaces rotos, imágenes que no cargan, errores de consola.
4. **\[G\] QA de verdad.** Todo dato aprobado aparece en el HTML y nada aparece sin estar aprobado. Thomas tiene abierto este punto: 32 pérdidas sin explicar.
5. **\[G\] QA de rendimiento y accesibilidad.** Velocidad en celular, peso de imágenes, contraste, navegación por teclado, textos alternativos.
6. **\[I\] Un crítico visual confiable.** Thomas mide masa visual, balance y espacio muerto sobre la captura. Falta saber si esas medidas coinciden con el gusto humano. Probar también un modelo de visión que critique la captura con una rúbrica.
7. **\[C\] Crítica visual automatizada.** Aplicar el crítico elegido a cada captura y producir hallazgos concretos.
8. **\[C\] Mutación y re-render.** Cada hallazgo se traduce en un cambio de parámetros; se vuelve a renderizar y se compara.
9. **\[I\] Cuándo parar.** Límite de iteraciones, de costo y de tiempo por página; qué hacer si no converge.
10. **\[G\] Compuerta humana.** Al principio, una persona ve cada página antes de publicarla y deja un veredicto con razón. Esos veredictos son el dato más valioso del proyecto: hoy hay cero.
11. **\[C\] Reporte de la página.** Qué se usó, qué se omitió por falta de datos, qué compuertas pasó, capturas finales.

## Fases 6 y 7 — Publicación, medición y aprendizaje

Una página publicada que nadie mide ni actualiza deja de ser GOAT en semanas. Estas dos fases cierran el ciclo observar → actuar → medir → aprender que es la razón de ser de 101.

### Fase 6 — Publicación

1. **\[C\] Vista previa con enlace.** Para que el dueño la vea antes de publicarla.
2. **\[C\] Aprobación del dueño.** Confirma datos y diseño; sus correcciones vuelven al paquete como la fuente más fuerte.
3. **\[I\] Dónde se aloja y cuánto cuesta por sitio.** Hosting estático, dominio propio o subdominio, certificados.
4. **\[C\] Despliegue y dominio.**
5. **\[C\] Conectar con el perfil de Google.** Que el enlace del sitio y los botones de pedir o reservar apunten a la página.
6. **\[G\] Verificación en producción.** La página carga, los flujos funcionan y la analítica registra.

### Fase 7 — Medición y aprendizaje

1. **\[C\] Tablero por restaurante.** Visitas, clics en la acción principal, pedidos, reservas.
2. **\[C\] Mantener la verdad.** Detectar cuando cambian el horario, los precios o el menú y actualizar la página.
3. **\[I\] Qué cambios de diseño mejoran la conversión.** Con varios restaurantes publicados, comparar variantes. Aquí entran los métodos de los informes de mercado: pruebas A/B, uplift, inferencia causal.
4. **\[C\] Devolver lo aprendido al pipeline.** Los resultados ajustan arquetipos, direcciones de arte y el crítico visual.
5. **\[I\] El argumento económico.** Cuánto le ahorra o le suma la página al restaurante frente a las plataformas. Es lo que sostiene el precio.

## Capa transversal A — Plataforma: módulos y roles

Desde el nivel 2 de funcionalidad, 101 deja de entregar un sitio y pasa a operar una plataforma con muchos restaurantes adentro. Eso exige definir quién entra, qué puede hacer y qué módulos existen. Las tres capas transversales no son fases: aplican a todas.

### Roles

| Rol | Quién es | Qué puede hacer | Qué nunca puede hacer |
| --- | --- | --- | --- |
| Visitante | Cualquiera que abre la página | Ver menú, pedir como invitado, reservar | Ver pedidos de otros |
| Cliente con cuenta | Visitante que se registra (opcional) | Historial, direcciones, puntos | Ver datos de otros clientes |
| Personal del restaurante | Cajero, cocina, mesero | Ver y avanzar pedidos y reservas del día | Cambiar precios, ver reportes, tocar pagos |
| Dueño o administrador | Responsable del restaurante | Menú, precios, horario, fotos, personal, reportes | Ver otros restaurantes |
| Operador 101 | Gabriel, Thomas o su equipo | Todos los restaurantes, revisión de páginas, soporte, cobro | Actuar sin dejar registro |
| Agente | El pipeline automatizado | Generar, proponer y reparar páginas | Publicar o cobrar sin pasar compuertas |

### Módulos

| Módulo | Para quién | Contenido | Estado según los resúmenes |
| --- | --- | --- | --- |
| Sitio público | Visitante | Páginas, menú, carrito, reserva, seguimiento del pedido | Sitio Astro existe; carrito en demo de V4 |
| Cuentas de cliente | Cliente | Registro, ingreso, historial, lealtad | Clientes y lealtad en V4; sin ingreso real |
| Panel del restaurante | Dueño y personal | Menú, horario, pedidos, reservas, domicilios, reportes | Pantallas demo en V4 (`admin`, `growth`, `delivery`) |
| Consola 101 | Operador 101 | Lista de restaurantes, cola de revisión de páginas, compuertas, soporte | Solo revisores locales de Thomas |
| Pedidos y pagos | Sistema | Estados del pedido, pasarela, reembolsos | Núcleo en V4; sin pasarela real |
| Notificaciones | Todos | Confirmaciones por WhatsApp, correo o SMS | Estructura en V4; sin proveedor |
| Suscripción y cobro | Operador 101 | Plan de cada restaurante, facturas, mora | No existe |
| Auditoría | Operador 101 | Quién cambió qué y cuándo | Parcial: eventos en V4 |

### Pasos

1. **\[I\] Matriz de permisos.** Para cada acción del sistema, qué rol la puede ejecutar. Es la base de toda la seguridad.
2. **\[I\] Invitado o cuenta obligatoria.** Pedir sin registrarse convierte más; la cuenta habilita lealtad. Recomendación: invitado primero, cuenta opcional.
3. **\[C\] Modelo de varios restaurantes.** Cada dato pertenece a un restaurante y toda consulta filtra por él. V4 ya usa `business_id`.
4. **\[C\] Ingreso y sesiones.** Reemplazar el token de desarrollo de V4 (`dev-operator`) por autenticación real con roles.
5. **\[C\] Panel del restaurante.** Empezar por lo que mantiene la verdad: precios, platos agotados, horario.
6. **\[C\] Consola 101.** Alta de restaurantes, cola de revisión humana, estado de compuertas por página.
7. **\[C\] Alta y baja de un restaurante.** Crear, suspender por mora, exportar sus datos y eliminar.
8. **\[C\] Registro de auditoría.** Toda acción de dueño, operador y agente queda escrita.
9. **\[G\] Compuerta de aislamiento.** Prueba automatizada: un usuario del restaurante A no puede leer ni cambiar nada del restaurante B.

## Capa transversal B — Seguridad

El riesgo crece con el nivel de funcionalidad: una página informativa estática casi no tiene superficie de ataque; el panel, los pedidos y los pagos sí. La regla es no subir de nivel sin los controles de ese nivel.

| Área | Riesgo principal | Control | Desde qué nivel |
| --- | --- | --- | --- |
| Aislamiento entre restaurantes | Un dueño ve o cambia datos de otro | Filtro por restaurante en toda consulta, con prueba automatizada | Panel |
| Autenticación | Robo de la cuenta del dueño | Código de un solo uso o contraseña fuerte; segundo factor obligatorio para operadores 101 | Panel |
| Pagos | Fraude, fuga de tarjetas | Nunca tocar datos de tarjeta: pago en la página de la pasarela; avisos firmados y verificados | 4 |
| Datos personales | Fuga de nombres, teléfonos, direcciones | Guardar lo mínimo, cifrar en tránsito y en reposo, borrar a pedido | 2 |
| Entradas del visitante | Inyección, scripts en campos de texto | Validación estricta, escape de todo texto mostrado, política de contenido | 1 |
| Abuso | Pedidos falsos, spam de reservas, robots | Límite de solicitudes, verificación del teléfono, captcha solo si hace falta | 2 |
| Secretos | Llaves de pasarela o de proveedores filtradas | Variables de entorno y gestor de secretos; nunca en código ni registros | Siempre |
| Dependencias | Librería o componente OSS comprometido | Versiones fijadas, escaneo en cada cambio, componentes con procedencia y hash | Siempre |
| El agente | Texto de una reseña o de Instagram que le da órdenes al modelo | Todo texto externo es dato, no instrucción; permisos mínimos; no publica sin compuerta | Siempre |
| Disponibilidad | Caída o pérdida de datos en hora pico | Respaldos probados, monitoreo, plan de recuperación | 2 |

Restaurant Commerce V4 ya trae varios de estos controles, según su reporte: avisos firmados y a prueba de repetición, tokens para ver pedidos, límite de solicitudes por proceso, cabeceras de seguridad, entradas validadas y arranque que falla sin secretos fuertes. El mismo reporte aclara lo que falta: límite distribuido, gestor de secretos, escáneres de dependencias, respaldos probados y una revisión externa.

### Pasos

1. **\[I\] Modelo de amenazas por nivel.** Qué puede salir mal en cada nivel de funcionalidad y qué tan grave es.
2. **\[C\] Escaneo automático.** Dependencias, secretos en el repo y análisis estático en cada cambio.
3. **\[C\] Gestión de secretos.** Un gestor, rotación y separación por entorno. Coincide con `AGENTS.md`, sección 7.
4. **\[C\] Defensa del agente.** Separar instrucciones de datos, limitar herramientas por fase y registrar cada acción.
5. **\[C\] Saneamiento del contenido generado.** El texto del menú y de las reseñas se escapa antes de llegar al HTML.
6. **\[C\] Respaldos y restauración.** Respaldo diario y una restauración de prueba; un respaldo sin probar no cuenta.
7. **\[C\] Monitoreo y alertas.** Errores, caídas, intentos de ingreso fallidos, pagos anómalos.
8. **\[I\] Plan de respuesta a incidentes.** Quién hace qué si hay fuga o caída, y a quién se le avisa.
9. **\[G\] Compuerta de seguridad por página.** Antes de publicar: HTTPS, cabeceras, sin secretos en el código entregado, formularios protegidos.
10. **\[G\] Revisión externa antes de cobrar.** Una prueba de penetración hecha por un tercero antes de mover dinero real.

## Capa transversal C — Infraestructura y alojamiento

La recomendación es separar tres cosas que hoy viven juntas en la máquina de Thomas: los sitios públicos, el servidor de la plataforma y el taller donde el agente genera páginas. Si el servidor se cae, las páginas informativas siguen en línea.

| Componente | Qué es | Dónde conviene alojarlo | Candidatos a evaluar |
| --- | --- | --- | --- |
| Sitios públicos | Archivos estáticos que genera Astro | Red de distribución con nodos cerca de Bogotá | Cloudflare Pages, Netlify, Vercel |
| Servidor de la plataforma | La aplicación Python de V4: pedidos, reservas, panel | Contenedor gestionado, mínimo dos instancias | Cloud Run, Fly.io, Render, o un servidor virtual propio |
| Base de datos | PostgreSQL, como espera V4 en producción | Servicio gestionado con respaldos automáticos | Neon, Supabase, Cloud SQL, RDS |
| Imágenes | Fotos de platos y del local | Almacenamiento de objetos con redimensionado | Cloudflare R2 e Images, S3 con CloudFront |
| Taller del agente | Modelos, renders en Chromium, crítica visual | Trabajos en cola, separados del servidor que atiende clientes | Cola con trabajadores en contenedores |
| Dominios | Dirección de cada restaurante | Subdominio de 101 por defecto; dominio propio opcional; certificado automático | El proveedor del sitio público suele incluirlo |
| Observabilidad | Registros, métricas, alertas, disponibilidad | Servicio externo al servidor | Sentry, Grafana, un monitor de disponibilidad |

Los candidatos son puntos de partida, no una decisión: no verifiqué precios ni límites vigentes. Ese es el primer paso de investigación.

### Pasos

1. **\[I\] Elegir proveedores y estimar el costo por restaurante.** Con precios vigentes, para 10, 100 y 1.000 restaurantes. Define el precio mínimo del producto.
2. **\[I\] Región y latencia.** Medir desde Bogotá contra las regiones disponibles; el servidor importa más que el sitio estático.
3. **\[C\] Tres entornos.** Desarrollo, pruebas y producción, con datos y secretos separados.
4. **\[C\] Infraestructura como código.** Que todo se pueda recrear desde el repo, no desde la memoria de alguien.
5. **\[C\] Despliegue automatizado.** Cada cambio pasa pruebas y se publica solo; con vuelta atrás en un paso.
6. **\[C\] Migraciones de base de datos.** Llevar el esquema de V4 a la cadena de Alembic del repo, como pide `V4_SCHEMA_DELTA.md`.
7. **\[C\] Publicación por restaurante.** Un restaurante nuevo queda en línea sin intervención manual: sitio, subdominio, certificado.
8. **\[C\] Cola del agente con límites.** Tope de costo y de tiempo por página; reintentos; nada corre sin presupuesto.
9. **\[I\] Prueba de carga.** Un viernes en la noche con varios restaurantes recibiendo pedidos a la vez.
10. **\[G\] Compuerta de producción.** Respaldo restaurado, alertas funcionando y vuelta atrás probada antes del primer cliente que paga.

## Capa transversal D — Legal, operación y negocio

Son los temas que no son código y que igual frenan un lanzamiento. No soy abogado: los puntos legales son para validar con uno antes de recibir datos o dinero de clientes reales.

| Tema | Pregunta que hay que responder |
| --- | --- |
| Datos personales | Cómo se cumple la ley colombiana de protección de datos (Ley 1581 de 2012): autorización, política de tratamiento, derecho a consultar y borrar |
| Quién responde por los datos | Qué papel tiene 101 y cuál el restaurante frente a los datos de los comensales |
| Contrato con el restaurante | Qué se promete, qué pasa si no paga, cómo se termina |
| Propiedad | De quién son el dominio, las fotos, los textos y la lista de clientes si el restaurante se va |
| Fotos y contenido de terceros | Qué se puede tomar de Instagram o Google y con qué permiso |
| Facturación | Cómo factura 101 su servicio y qué obligaciones tiene el restaurante sobre los pedidos |
| Consumidor | Qué debe mostrar una página que vende: precios finales, condiciones, reclamos |
| Soporte | Quién atiende al dueño un viernes a las 8 p. m. cuando algo falla |
| Modelo de cobro | Mensualidad fija, por pedido, o mixto; y qué incluye cada plan |

### Pasos

1. **\[I\] Revisión legal.** Privacidad, contrato y consumidor con un abogado colombiano, antes del primer cliente.
2. **\[C\] Textos legales por página.** Política de datos, términos y autorización en formularios, generados desde plantillas aprobadas.
3. **\[C\] Derechos del titular.** Mecanismo para consultar, corregir y borrar datos de un comensal.
4. **\[I\] Política de propiedad y salida.** Qué se lleva el restaurante si cancela y en qué formato.
5. **\[I\] Precio y planes.** Cruzar el costo por restaurante de la capa C con lo que un dueño pagaría.
6. **\[C\] Soporte.** Canal, tiempos de respuesta y guías para el dueño.
7. **\[C\] Accesibilidad e idioma.** Español primero; inglés para zonas turísticas si el arquetipo lo pide.

## Cómo trabaja el agente

El agente no es un modelo que escribe una página de una sola vez; es un orquestador que recorre las fases, llama herramientas y no avanza si una compuerta falla. La calidad sale de las compuertas y del ciclo de reparación, no de un prompt mejor.

| Quién decide | Qué |
| --- | --- |
| Código determinista | Compuertas duras, validación de datos, legalidad del layout, pruebas de flujo |
| Modelo de lenguaje | Redacción desde hechos, clasificación de arquetipo, lectura de cartas, crítica visual con rúbrica |
| Búsqueda y optimización | Elegir entre composiciones candidatas, mutar parámetros |
| Persona | Aprobar las primeras páginas, confirmar datos, resolver conflictos, juzgar estética |

### Pasos

1. **\[C\] Definir los contratos entre fases.** Qué archivo entra y sale de cada fase: paquete de datos, plan de sitio, especificación de diseño, sitio, reporte.
2. **\[C\] Orquestador.** Corre las fases en orden, guarda el estado y puede retomar donde quedó.
3. **\[C\] Manejo de fallos.** Si una compuerta no pasa, el agente sabe a qué paso volver y con qué información.
4. **\[I\] Cuánta autonomía y cuándo.** Qué tasa de aprobación humana justifica quitar la revisión manual.
5. **\[I\] Costo y tiempo por página.** Llamadas a modelos, renders, iteraciones. Define si el negocio escala.
6. **\[C\] Banco de pruebas.** Un conjunto fijo de 10 a 20 restaurantes reales de distintos arquetipos para medir cada cambio del pipeline.

Los pasos \[I\] también los puede correr un agente: investiga, propone una regla y la prueba contra el banco de pruebas. La decisión de adoptarla es de ustedes.

## Por dónde empezar

El primer hito recomendado es una sola página de restaurante real, hecha a mano con ayuda del agente, que pase las cinco capas GOAT. Esa página se vuelve el patrón contra el que se mide la automatización; sin ella, el pipeline optimiza hacia un objetivo que nadie ha visto.

1. **Revisar el repo con Thomas.** Confirmar qué existe de verdad y qué es reusable. Corrige este documento donde los resúmenes estén desactualizados.
2. **Investigar referentes.** Fase 3A, paso 1: de 30 a 50 páginas de restaurante buenas, anotadas. Produce la rúbrica de «GOAT».
3. **Elegir un restaurante piloto.** Uno real, idealmente con dueño dispuesto a dar menú y fotos.
4. **Llenar el paquete de datos a mano.** Revela qué campos faltan en el esquema.
5. **Construir la página patrón.** Nivel 1 o 2 de funcionalidad. A mano, sin automatizar.
6. **Sacar las reglas.** De cada decisión tomada a mano sale un paso \[C\] o \[I\] del pipeline.
7. **Automatizar de adelante hacia atrás.** Primero compilar desde un paquete completo; después la captura de datos; al final el diseño exploratorio.
8. **Repetir con 5 restaurantes de arquetipos distintos.** Ahí se ve qué generaliza.

## Decisiones abiertas

Estas cinco decisiones cambian el pipeline y son de ustedes, no del agente.

- [ ] **Puerta de entrada.** ¿El restaurante entrega sus datos como cliente, o 101 arma la página sola desde fuentes públicas y luego la ofrece?
- [ ] **Nivel de funcionalidad del primer producto.** ¿Informativa, pedido por WhatsApp o pedido con pago?
- [ ] **Reparto de trabajo.** ¿Qué fases lleva Gabriel y cuáles Thomas? ¿Mismo repo en rama aparte?
- [ ] **Qué pasa con el Design Compiler.** ¿Se integra tal cual, se simplifica para restaurantes o se usa solo su crítico visual?
- [ ] **Restaurante piloto.** ¿Cuál, y quién habla con el dueño?
- [ ] **Alojamiento.** ¿Qué proveedores, y quién administra las cuentas y los secretos?
- [ ] **Cuentas de comensal.** ¿Pedido como invitado desde el inicio, o registro obligatorio?
- [ ] **Propiedad del dominio y los datos.** ¿Del restaurante o de 101?
- [ ] **Modelo de cobro.** ¿Mensualidad, por pedido o mixto?
