# Feature Specification: Footer 001 · directorio con marca recortada

**Feature Branch**: `codex/footer-caretta-bones-20261105`
**Created**: 2026-11-05
**Status**: Implementado y verificado técnicamente; revisión visual del usuario pendiente.
**Input**: Reconstruir caretta/08 desde la referencia suministrada, quitar la piel
de marca y conservar estructura y funcionamiento. Registrar también porcentaje
de texto, área sin texto, ocupación y espacio libre siguiendo los límites de Tomás.

Este es el primer hueso concreto pedido por el usuario. Sustituye navegación/hero
como siguiente implementación, sin invalidar el marco de [spec 002](../002-section-bones/spec.md).
Un hueso reconstruido no es código original de Caretta ni aprobación de su apariencia.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reconocer la estructura sin la piel (Priority: P1)

Como responsable de páginas quiero abrir una reconstrucción neutra del footer
y compararla con la captura para identificar sus partes reutilizables.

**Why this priority**: La biblioteca necesita código ejecutable, no sólo una descripción.
**Independent Test**: Abrir referencia y hueso a 1440 px; localizar banda, asistentes,
identidad, respaldos, directorio de cuatro columnas, marca recortada y barra legal.

**Acceptance Scenarios**:

1. **Given** la referencia de 1440 × 806, **When** se abre el hueso neutro,
   **Then** conserva orden, relaciones, columna de identidad y cuatro grupos,
   sin gradiente, fuentes de marca, logos originales ni acabado esmerilado.
2. **Given** la misma base, **When** se reduce a móvil o tablet, **Then** sus
   grupos permanecen legibles sin desbordamiento horizontal ni palabras partidas;
   el comportamiento adaptable propuesto se distingue de la evidencia de escritorio.
3. **Given** movimiento no documentado en la captura, **When** se reconstruye,
   **Then** no se inventan animaciones ni se afirma haberlas observado.

### User Story 2 - Conservar acciones y estados honestos (Priority: P1)

Como visitante quiero reconocer destinos disponibles y elementos futuros, recorrer
el footer con teclado y entender qué acciones requieren una integración del sitio.

**Why this priority**: Una apariencia neutra no debe eliminar la semántica ni crear botones falsos.
**Independent Test**: Verificar destinos públicos, elementos Soon sin enlaces,
accesos de IA sólo por activación del visitante y estado del gestor de cookies.

**Acceptance Scenarios**:

1. **Given** un enlace activo, **When** se consulta o activa, **Then** conserva su
   destino configurado y tiene nombre accesible; las ventanas nuevas están indicadas.
2. **Given** un elemento futuro, **When** se recorre el footer, **Then** informa
   Soon y no tiene un destino inventado o un enlace al comienzo de la página.
3. **Given** ausencia de gestor de cookies, **When** aparece su espacio de acción,
   **Then** queda deshabilitado con su estado explícito; conectar el contrato de
   evento permite que el sitio gestione la acción, sin simular consentimiento.
4. **Given** un acceso de resumen con IA, **When** carga la página,
   **Then** no hay llamadas a modelos; sólo el visitante puede abrir el destino externo.

### User Story 3 - Medir e incorporar el hueso a la biblioteca (Priority: P2)

Como responsable de componentes quiero inspeccionar partes y descargar medidas
reproducibles para comparar distribuciones sin confundir espacio con píxeles blancos.

**Why this priority**: Los números deben ser útiles y tener denominadores conocidos.
**Independent Test**: Medir la sección completa a 1440, 768 y 360 px y descargar
un registro con tamaño, método, partes, fuente y fecha.

**Acceptance Scenarios**:

1. **Given** el render completo, **When** se mide texto, **Then** informa unión de
   cajas de líneas / área del footer y su complemento; no los llama tinta literal.
2. **Given** acciones, logos y marca decorativa, **When** se mide ocupación,
   **Then** diferencia texto, controles, medios funcionales y decoración, e informa
   solapamientos sin sumar porcentajes incompatibles.
3. **Given** el inspector original de Tomás disponible, **When** se mide,
   **Then** reutiliza su módulo para geometría, contraste, superficies y espacio;
   su ausencia se informa y no impide utilizar el footer.
4. **Given** una exportación, **When** se descarga, **Then** incluye ID/versión,
   configuración, viewport, alcance, fecha y limitaciones, sin datos privados de referencia.

### Edge Cases

- Captura histórica frente a sitio actual: conservar el objetivo caretta/08;
  los destinos observados hoy y las diferencias se registran por separado.
- La lista de texto suministrada no incluye toda la marca gráfica: su cobertura
  es parcial y no se presenta como porcentaje completo de texto del original.
- Piel con fuente de respaldo, nombres largos y pantalla baja: lectura y flujo normal.
- Módulo privado del inspector ausente: la extensión propia de texto continúa;
  las medidas compartidas quedan no disponibles, nunca fabricadas.
- Gestor de cookies ausente, logos sin permiso y grupo opcional sin datos:
  estado o ausencia explícitos, sin inventar capacidades o respaldos de otra marca.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Registrar hueso `footer.directory-watermark@0.1.0`, partes, datos,
  procedencia y estado reconstruido/no aprobado. (US1)
- **FR-002**: Preservar las siete regiones observadas y los cuatro grupos; separar
  los valores visuales neutros del contenido y las reglas estructurales. (US1)
- **FR-003**: Ofrecer captura original identificada y preview del componente real;
  la referencia no se sustituye por una segunda aproximación. (US1)
- **FR-004**: Conservar nombres, orden, acciones y estados del objetivo; distinguir
  destinos verificados en HTML público de comportamientos no comprobados. (US2)
- **FR-005**: Validar URLs, IDs y estados antes de renderizar; impedir protocolos
  ejecutables, IDs duplicados, enlaces Soon con destino y datos esenciales ausentes. (US2)
- **FR-006**: Los asistentes sólo serán enlaces externos explícitos; el contrato de
  cookies deberá indicar si hay integración, sin almacenar consentimiento ficticio. (US2)
- **FR-007**: Soportar teclado, tacto, reducción de movimiento, sin JavaScript y fuente
  de respaldo; no introducir punteros contextuales ni movimiento no observado. (US1, US2)
- **FR-008**: Medir cajas de texto con unión sin doble conteo, recortada al footer,
  excluyendo decoración y espacios reservados a logos del texto funcional. (US3)
- **FR-009**: Informar área y porcentaje de texto, sin texto, controles, medios,
  decoración, ocupación combinada y espacio libre, con denominador y limitaciones. (US3)
- **FR-010**: Reutilizar el inspector de Tomás sin duplicarlo ni redistribuir su
  código privado en Git; añadir sólo la extensión de métricas necesaria para este footer. (US3)
- **FR-011**: Inspección y exportación serán herramientas del taller; el consumidor
  del footer no cargará ese instrumental. (US3)
- **FR-012**: Guardar pruebas, capturas y mediciones por tamaño; hacer commit y push
  de la entrega revisada sin tocar cambios previos ni publicar capturas privadas. (US3)

### Key Entities

- **FooterBone**: Identificador/versión, anatomía y reglas de composición.
- **FooterContent**: Identidad, descripción, respaldos, grupos y acciones legales.
- **FooterItem**: ID, etiqueta, icono neutro, estado y destino o integración.
- **FooterObservation**: Fuente histórica o actual, tamaño, método y limitaciones.
- **FooterMeasurement**: Geometría por parte y porcentajes de ocupación con su alcance.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A 1440 px se identifican las siete regiones y cuatro grupos; los
  límites principales reproducen 274/448/84 px salvo crecimiento necesario del contenido.
- **SC-002**: Todos los destinos disponibles del fixture tienen nombre y URL
  válidos; los cinco elementos Soon y la acción sin integrar no navegan.
- **SC-003**: Cero errores de página, palabras partidas artificialmente o
  desbordamientos en 360, 768, 991, 992, 993 y 1440 px y con fuente de respaldo.
- **SC-004**: Texto + sin texto = 100% y ocupación + espacio libre = 100%,
  con tolerancia de redondeo de 0,02 puntos; ningún área de unión supera el footer.
- **SC-005**: Cada tamaño principal tiene medición exportada, screenshot y revisión
  del render. Las capturas quedan separadas de la aprobación visual del usuario.
- **SC-006**: Un consumidor sin inspector muestra los mismos datos y destinos
  esenciales; el material privado de Tomás no entra en el commit.

## Assumptions

- La captura suministrada del 2026-10-19 es el objetivo visual de escritorio.
  La adaptación móvil será una propuesta de este hueso, no una réplica móvil observada.
- Se conservan datos reales de Caretta para que la comparación sea comprobable.
  Los logos se representan por espacios neutros con etiqueta; no se dibujan imitaciones.
- La banda superior y el espacio de marca son parte de la composición observada;
  su color/gradiente y la identidad tipográfica se eliminan en el hueso.
- No se activa un CMP, chatbot, scraping ni publicación comercial en esta extracción.
