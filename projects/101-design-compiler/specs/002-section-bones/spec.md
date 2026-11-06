# Feature Specification: Biblioteca de secciones, huesos y piel de marca

**Feature Branch**: `codex/section-bones-20261105`

**Created**: 2026-11-05

**Status**: Draft 0.1. Dirección incorporada; requisitos preparados para revisión y planificación.

**Input**: Construir páginas por secciones reutilizables. Los huesos comprenden la
estructura y el funcionamiento, incluido scroll, movimiento e interacciones. La
piel aplica fuentes, colores y apariencia coherentes con cada negocio. Partir del
trabajo compartido por Tomás, conservar el trabajo anterior en `old` y versionar
las entregas en el repositorio de GitHub del usuario.

## Objetivo y vocabulario

Una página se compone de secciones útiles: navegación, hero (primera sección
principal), oferta o menú, reservas, mapa, galería, reseñas y otras familias que
se incorporen sucesivamente. Cada familia puede tener muchos huesos distintos.

| Concepto | Qué contiene | Ejemplo |
| --- | --- | --- |
| Hueso de sección | Partes, composición, relaciones, distribución adaptable, estados, interacciones y movimiento | Hero con imagen lateral; hero con fondo que crece al hacer scroll |
| Comportamiento del hueso | Desplazamiento, fijación, entrada/salida, navegación, transiciones y alternativas accesibles | Scroll vertical que desplaza una colección horizontal y libera la sección al terminar |
| Piel de marca | Fuentes, paleta por función, logotipo y tratamiento gráfico dentro de los límites del hueso | Aplicar la tipografía y los colores del negocio al mismo hero |
| Contenido y medios | Textos, acciones, datos, imágenes y videos propios del negocio, con su procedencia | Propuesta del negocio y fotografía autorizada para esa sucursal |
| Composición de página | Selección y orden de secciones compatibles con el negocio y entre sí | Navegación → hero → menú → reservas → ubicación |

En este proyecto, decir que un hueso está «sin diseño» significa que no tiene
todavía la identidad visual de un cliente. Sí tiene una composición y un
funcionamiento definidos. Cambiar la piel no convierte una cuadrícula en un
carrusel ni añade una animación: eso exige elegir o versionar otro comportamiento
del hueso. Una fotografía o video se coloca en un espacio de medios previsto; el
movimiento de ese espacio pertenece al hueso.

El objetivo de escala es una biblioteca amplia, incluso del orden de 1.000 opciones
de hero. No es el tamaño del primer piloto ni un inventario existente. Los huesos
deben reutilizarse de manera continuada, sin límite predeterminado de marcas
compatibles. Dos marcas iniciales son una muestra de prueba, no ese límite.

### Alcance inicial propuesto

Este documento establece el contrato común de la biblioteca y un primer piloto
de navegación y hero: una base de navegación y dos huesos de hero con diferencias
estructurales o de comportamiento reconocibles. Las primeras pruebas usarán dos
negocios reales con información suficiente; una incorporación posterior verificará
que no se codificaron excepciones dependientes de esos dos negocios.

Las 14 variantes de **reseñas** del paquete de Tomás son una referencia técnica
reproducible para separación, composición, taller y verificación. No se cuentan
como héroes, aprobación del usuario ni integración del nuevo motor de páginas.

Quedan fuera de esta entrega documental la generación masiva de variantes, el
selector automático completo, implementar todas las familias, migrar todo el
runtime, publicar webs y activar reservas, loyalty o correos operativos. El trabajo
actual entrega el esquema y la conexión documental con GitHub; la implementación
del piloto seguirá el plan y las tareas que se deriven de esta especificación.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Entender y probar un hueso sin identidad de cliente (Priority: P1)

Como responsable de construir páginas, quiero consultar una sección neutra y
probar sus partes y movimientos para elegir cómo funcionará antes de aplicar una marca.

**Why this priority**: Una biblioteca de paletas no resuelve la reutilización de
composiciones e interacciones. La unidad elegida debe tener un funcionamiento identificable.

**Independent Test**: Abrir cada hueso inicial en vista neutra, identificar sus
partes y ejecutar sus acciones, scroll y alternativas accesibles sin una piel de cliente.

**Acceptance Scenarios**:

1. **Given** un hueso registrado, **When** se abre su ficha, **Then** muestra familia,
   identificador, versión, partes, datos requeridos, comportamiento y compatibilidad.
2. **Given** un hueso con movimiento ligado al scroll, **When** se avanza y retrocede,
   **Then** se observa el comportamiento descrito, su liberación y su reversión.
3. **Given** el mismo hueso sin movimiento permitido, **When** se usa reducción de
   movimiento o falla el recurso que lo habilita, **Then** su alternativa documentada
   conserva contenido, lectura y acciones esenciales.

### User Story 2 - Aplicar la marca sin reconstruir el funcionamiento (Priority: P1)

Como responsable de preparar páginas, quiero aplicar la identidad de negocios reales
al mismo hueso para obtener resultados personalizados y reproducibles.

**Why this priority**: La apariencia debe atraer, transmitir personalidad y contribuir
a la confianza, manteniendo una base útil y reutilizable.

**Independent Test**: Aplicar dos identidades reales al mismo hueso, comparar vista
neutra y versiones de marca al mismo tamaño y reincorporar sus configuraciones guardadas.

**Acceptance Scenarios**:

1. **Given** una identidad con fuentes, paleta y logotipo documentados, **When** se
   aplica, **Then** cambia la piel y el contenido del negocio conservando el hueso y
   su comportamiento, salvo alternativas compatibles registradas expresamente.
2. **Given** un color o fuente inferido de una referencia visual, **When** se propone
   como piel, **Then** se distingue de una decisión de marca confirmada y se conserva
   la fuente de la inferencia.
3. **Given** una nueva marca compatible, **When** se incorpora, **Then** sigue el
   mismo procedimiento sin reconstruir la base ni añadir condiciones por nombre de cliente.
4. **Given** una identidad con textos largos o fuentes no disponibles, **When** se
   visualiza, **Then** conserva palabras completas y legibilidad o informa la incompatibilidad.

### User Story 3 - Componer una página útil y reconocer sus límites (Priority: P2)

Como responsable de preparar una web, quiero seleccionar secciones compatibles
con los datos y las tareas del negocio, entendiendo qué falta para completarla.

**Why this priority**: El sistema debe permitir ensamblar páginas con intención,
en lugar de añadir bloques de adorno o acciones que no funcionan.

**Independent Test**: Preparar una composición de navegación y hero, con una acción
principal y destinos reales; retirar un dato esencial y comprobar el diagnóstico.

**Acceptance Scenarios**:

1. **Given** datos y acciones utilizables, **When** se compone la página, **Then** el
   visitante reconoce el negocio, entiende su propuesta y encuentra su siguiente acción.
2. **Given** una sección que necesita un video esencial ausente, **When** se intenta
   seleccionarla, **Then** explica su ineligibilidad o utiliza una alternativa permitida
   expresamente, registrando la elección.
3. **Given** dos secciones con exigencias incompatibles de scroll, **When** se ensamblan,
   **Then** la combinación se rechaza con un motivo o se usa una combinación compatible registrada.
4. **Given** una reserva demostrativa, **When** aparece su acción, **Then** su estado
   es comprensible y no promete confirmar reservas ni enviar mensajes.

### User Story 4 - Retomar el trabajo y colaborar desde GitHub (Priority: P2)

Como responsable del proyecto, quiero distinguir el esquema vigente del anterior,
recuperar el trabajo archivado y revisar los cambios entregados en mi repositorio.

**Why this priority**: Cambiar de rumbo debe conservar el trabajo y dejar una base
única y rastreable para la colaboración.

**Independent Test**: Seguir el README hasta la spec vigente, consultar el inventario
del respaldo y abrir el commit remoto de esta entrega.

**Acceptance Scenarios**:

1. **Given** el trabajo anterior, **When** se archiva, **Then** conserva historial,
   cambios sin commit e instrucciones de recuperación, sin romper sus dependencias.
2. **Given** una entrega acotada, **When** se termina, **Then** hay un commit y push
   verificables en una rama del repositorio del usuario, sin incluir cambios ajenos.
3. **Given** referencias o medios de uso privado, **When** se publica el esquema,
   **Then** permanecen fuera del repositorio público y se conserva sólo su referencia técnica permitida.

### Edge Cases

- Sin logotipo o fuentes confirmadas: registrar la ausencia y usar sólo alternativas
  declaradas; una fuente visualmente parecida no se declara la fuente oficial.
- Sin medios esenciales: ineligibilidad o alternativa explícita; nunca una foto
  de otra marca que aparente pertenecer al negocio.
- Scroll anidado, contenedores transformados, pantallas bajas o varias secciones
  fijadas: verificar el contexto del contenedor, la salida del recorrido y la lectura.
- Teclado, tacto, reducción de movimiento, colores forzados o ausencia de ejecución
  interactiva: conservar alternativas documentadas y destinos esenciales.
- Contenido largo, palabras extensas, cambio de idioma o fuente de respaldo:
  conservar palabras completas y evitar desbordamiento o reducción ilegible.
- Referencias con testimonios de otro negocio: conservarlos en su carril de referencia;
  no convertirlos en evidencia del negocio adaptado.
- Fuente caducada, discrepancia entre datos o acceso a base viva sin confirmar:
  hacer visible la incertidumbre; un archivo local no demuestra conexión operativa.
- Cambio incompatible de hueso: crear versión y migración, sin modificar
  silenciosamente las instancias existentes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Cada hueso DEBE pertenecer a una familia y tener identificador y versión,
  partes nombradas, propósito, datos, estados y límites de compatibilidad consultables. (US1)
- **FR-002**: El hueso DEBE describir composición, respuesta al tamaño, scroll,
  movimiento, interacción y alternativas; estas decisiones no DEBEN trasladarse a la piel. (US1)
- **FR-003**: La vista neutra DEBE permitir probar el comportamiento sin depender
  de la identidad de un cliente; la ausencia de decoración no elimina acciones ni contenido esencial. (US1)
- **FR-004**: La piel DEBE expresar fuentes, paleta por función, logotipo y tratamiento
  gráfico mediante opciones acotadas que respeten las restricciones del hueso. (US2)
- **FR-005**: Datos y medios del negocio DEBEN conservar procedencia, fecha, sucursal
  y estado de uso; observación, inferencia y decisión confirmada DEBEN distinguirse. (US2)
- **FR-006**: Una instancia DEBE registrar versiones de hueso y piel, referencias de
  contenido y medios, configuración de comportamiento y razones de selección para reproducirse. (US2)
- **FR-007**: Aplicar otra marca NO DEBE regenerar la composición ni reescribir las
  interacciones. Una necesidad incompatible DEBE seleccionar otro hueso o producir una nueva versión. (US2)
- **FR-008**: La comparación DEBE mostrar hueso neutro y marca aplicada con iguales
  datos, tamaño y condiciones de prueba; la referencia original, si existe, DEBE estar identificada aparte. (US2)
- **FR-009**: Las primeras pruebas DEBEN usar negocios reales con fuentes utilizables.
  Una incorporación adicional DEBE seguir el mismo procedimiento sin lógica por cliente. (US2)
- **FR-010**: El catálogo DEBE distinguir familia, hueso, variante y estado de revisión;
  una prueba técnica no DEBE equivaler a aprobación visual ni a disponibilidad en producción. (US1)
- **FR-011**: La composición DEBE registrar orden y compatibilidad entre secciones,
  incluidas restricciones de contenedor, desplazamiento y capacidades del negocio. (US3)
- **FR-012**: La falta de datos, funcionalidad o medios esenciales DEBE producir un
  motivo comprensible o una alternativa permitida registrada, sin inventar contenido. (US3)
- **FR-013**: Navegación y hero DEBEN identificar el negocio, comunicar su oferta y
  ofrecer una acción principal con etiqueta y destino coherentes con su estado real. (US3)
- **FR-014**: Los huesos DEBEN ser utilizables con teclado y tacto y ofrecer una
  alternativa legible con reducción de movimiento y sin mejoras interactivas. El scroll
  DEBE permitir continuar y retroceder sin atrapar al visitante. (US1, US3)
- **FR-015**: Las instancias DEBEN conservar palabras completas y legibilidad en
  móvil, tablet, escritorio, límites de distribución y fuente de respaldo. (US2)
- **FR-016**: El taller DEBE permitir inspeccionar partes y guardar/recuperar
  configuraciones versionadas; sus guías y controles de operador no DEBEN aparecer
  en la página del cliente ni modificar evidencia factual. (US1, US2)
- **FR-017**: Una adaptación DEBE conservar las partes y el funcionamiento declarados
  del original. Los cambios intencionales DEBEN identificarse antes de compararlos. (US2)
- **FR-018**: El trabajo anterior DEBE quedar recuperable bajo `old`, incluyendo
  historial y cambios sin commit. Conservar fuentes en su ubicación por dependencia
  DEBE documentarse como preservación del legado, no adopción del nuevo pipeline. (US4)
- **FR-019**: Las entregas DEBEN guardarse mediante commit y push al repositorio
  del usuario, limitadas al alcance revisado, conservando cambios ajenos y sin fusionar
  ramas automáticamente. Las restricciones de material privado DEBEN respetarse. (US4)
- **FR-020**: El estado DEBE separar esquema escrito, implementación, integración,
  verificación y aprobación humana. La cantidad de variantes y el avance automático
  DEBEN reportarse sólo con su familia y alcance medidos. (US4)

### Key Entities

- **Familia**: Tipo de sección y tarea que resuelve, como hero, navegación o reseñas.
- **Hueso versionado**: Base reutilizable con partes, composición, comportamiento,
  alternativas, condiciones de elegibilidad y estado de revisión de esa versión.
- **Perfil de comportamiento**: Opciones y límites funcionales admitidos por el hueso;
  puede fijar duración, secuencia, navegación o relación con el scroll.
- **Piel de marca versionada**: Apariencia confirmada o propuesta, con sus fuentes
  de evidencia y opciones visuales permitidas.
- **Paquete de negocio**: Datos y medios reales, ámbito, procedencia, permisos e incertidumbres.
- **Instancia de sección**: Unión reproducible de hueso, comportamiento, piel y contenido.
- **Composición de página**: Orden de instancias y decisiones de compatibilidad o exclusión.
- **Registro de revisión**: Versión exacta, condiciones de comparación, resultados
  técnicos y decisión humana separados.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de los huesos incluidos en el piloto tiene los campos de FR-001
  y FR-002 completos y una vista neutra con acciones comprobables.
- **SC-002**: Los dos huesos de hero y la navegación del piloto pueden aplicarse a
  dos negocios reales sin reconstruir su base; una marca adicional compatible se
  incorpora mediante el mismo procedimiento y configuraciones guardadas.
- **SC-003**: Para cada caso del piloto, recuperar la configuración conserva versión,
  contenido, apariencia y comportamiento observados; no hay sustituciones sin registrar.
- **SC-004**: En todos los casos de prueba, retirar datos o medios esenciales produce
  el motivo esperado o una alternativa explícita; no se inventan hechos ni acciones operativas.
- **SC-005**: Todos los recorridos esenciales del piloto se completan con teclado,
  tacto, reducción de movimiento y alternativa sin mejoras interactivas. No hay
  atrapamiento de scroll ni pérdida de acceso al contenido esencial.
- **SC-006**: El piloto se inspecciona a 360, 768 y 1440 píxeles, a ambos lados de cada
  cambio de distribución y con fuentes de respaldo: cero palabras partidas artificialmente,
  desbordamientos horizontales o acciones esenciales ocultas sin alternativa.
- **SC-007**: En una revisión con cinco personas ajenas a la construcción, al menos
  cuatro identifican negocio, propuesta y acción principal en diez segundos. Se registra
  además su percepción de claridad, confianza y coherencia de marca en escala de 1 a 5;
  una media inferior a 4 en cualquiera exige revisar ese caso antes de aprobarlo.
- **SC-008**: El respaldo anterior tiene inventario verificable y una muestra recuperada
  coincide con sus hashes; la entrega documental tiene un commit remoto verificable.
- **SC-009**: Cada piloto registra tiempo total, tiempo de corrección manual, requisitos
  cumplidos y fallos. Si se informa porcentaje automático, se calcula como requisitos
  de aceptación del alcance pactado cumplidos sin corrección manual / total de ese
  alcance × 100, junto al tiempo manual y las exclusiones; no por líneas de código
  ni por porcentaje de pantalla. El 90% sigue siendo una meta a contrastar.

## Assumptions

- Se conserva navegación y hero como primera familia nueva a partir de las conversaciones
  anteriores; las reseñas de Tomás aportan el ejemplo trabajado del modelo y taller.
- Una navegación y dos héroes son el límite inicial propuesto para evitar generar
  cientos de variantes antes de comprobar la separación. Puede ajustarse durante la revisión.
- Los negocios concretos se seleccionarán por suficiencia de datos y permisos antes
  de implementar. No se supone acceso operativo a Facebook, Instagram o base viva
  por el solo hecho de disponer de snapshots o herramientas de extracción.
- La biblioteca no impone un límite de marcas; cada nueva marca debe satisfacer la
  compatibilidad del hueso elegido o registrar una necesidad de ampliación.
- El paquete de referencia tiene material privado. Su disponibilidad para revisión
  local no autoriza publicarlo en el repositorio público ni en una web comercial.
- Se mantienen las reglas vigentes de medios, autoridad factual, puntero, legibilidad
  y aprobación humana por versión. Un taller terminado no completa un sitio comercial.

## Contexto para la siguiente fase

Actualización acotada del 2026-11-05: el usuario solicita incorporar caretta/08
como footer sin diseño y con todas sus partes identificadas. Su implementación
y verificación se siguen en [spec 003](../003-footer-caretta-bones/spec.md).
El piloto de navegación/hero de esta spec sigue pendiente; no se declara completado.

La correspondencia con los paquetes reales, las verificaciones del handoff y la
migración del legado están en [el mapa de integración](../../docs/bones/integration.md).
El contrato propuesto, con ejemplos de responsabilidades, está en
[el esquema de secciones](../../docs/bones/section-model.md). No son una implementación nueva.
