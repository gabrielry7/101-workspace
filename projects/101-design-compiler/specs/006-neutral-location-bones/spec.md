# Feature Specification: Mapas como huesos neutros con pin de logo

**Feature Branch**: `codex/location-neutral-bones-20261108`
**Created**: 2026-11-08
**Status**: Implementado y verificado localmente; Google vivo y aprobación visual humana pendientes.
**Input**: Conservar las bases de mapas, mostrar sólo el negocio, usar su logo dentro de un pin y dejarlas como huesos, igual que Little Amps.

## User Scenarios & Testing

### User Story 1 — Elegir la estructura sin marca aplicada (Priority: P1)
El operador abre tres composiciones de ubicación, ve sus espacios identificados y prueba el mapa sin confundir una piel decorativa con el hueso.
**Why this priority**: La muestra anterior comenzaba comparando una piel.
**Independent Test**: Reconocer nombre, dirección, acciones, mapa, pin, logo y créditos en las tres recetas.
**Acceptance Scenarios**:
1. **Given** el taller, **When** se abre, **Then** muestra primero tres composiciones neutras y el espacio de logo dentro del pin.
2. **Given** una receta, **When** se activan guías, **Then** identifica partes sin añadir controles de revisión a la sección del cliente.
3. **Given** el mapa de muestra, **When** se consulta su procedencia, **Then** distingue cartografía sintética y ubicación real.

### User Story 2 — Un único negocio y su pin con logo (Priority: P1)
El logo ocupa el interior del pin y su punta sigue la coordenada de la misma sucursal.
**Independent Test**: Pan, zoom y resize conservan destino y ausencia de negocios ajenos.
**Acceptance Scenarios**:
1. **Given** logo permitido, **When** carga, **Then** queda contenido sin deformación y la punta permanece anclada.
2. **Given** logo ausente/fallido, **When** se dibuja el marcador, **Then** conserva pin neutro y ubicación.
3. **Given** coordenada no utilizable, **When** se abre la sección, **Then** conserva datos/acciones válidos sin inventar un destino.

### User Story 3 — Preparar Google real (Priority: P2)
El operador entiende cómo publicar su estilo sin negocios alrededor y qué falta para probarlo.
**Independent Test**: Consultar procedimiento y descargar estilo inicial sin configuración ni llamadas a Google.
**Acceptance Scenarios**:
1. **Given** configuración ausente, **When** consulta Google, **Then** ve el pendiente y procedimiento sin confundir simulación con mapa real.
2. **Given** configuración publicada posteriormente, **When** se integre, **Then** conserva un negocio, elegibilidad, logo validado y créditos.

### Edge Cases
Logo horizontal/vertical/fallido, falta de coordenadas, fuente de respaldo, pantallas estrechas, teclado, sin JavaScript, colores forzados y configuración Google ausente.

## Requirements

### Functional Requirements
- **FR-001**: Presentar primero las tres recetas existentes como estructuras neutras con espacios identificados.
- **FR-002**: Retirar tipografía, paleta y acabado de marca del estado neutro sin alterar composición ni alternativas.
- **FR-003**: Contener el logo autorizado dentro del pin; conservar la punta anclada.
- **FR-004**: Mantener política fija sin establecimientos ajenos y rechazar su reactivación por piel.
- **FR-005**: Separar guías/controles del componente; inventariar pin y espacio de logo.
- **FR-006**: Distinguir mapa sintético, adaptador Google y verificación viva; cero llamadas Google sin configuración.
- **FR-007**: Ofrecer estilo inicial descargable y procedimiento para publicarlo/asociarlo al mapa propio.
- **FR-008**: Conservar permisos/procedencia/accesibilidad y entregar mediante commit/push.

### Key Entities
Composición de ubicación; pin de negocio; espacio de logo; estilo del proveedor; estado de verificación.

## Success Criteria

### Measurable Outcomes
- **SC-001**: Tres recetas inspeccionables en móvil/tablet/escritorio sin overflow ni palabras partidas.
- **SC-002**: Exactamente un pin por instancia utilizable, cero establecimientos ajenos en la muestra compatible.
- **SC-003**: Error de anclaje máximo 1 px CSS estable tras pan/zoom/resize, con logo y alternativa.
- **SC-004**: Cero solicitudes Google sin configuración; pendiente y procedimiento visibles.
- **SC-005**: Dirección/acciones o alternativa útil con teclado y sin JavaScript.

## Assumptions
El usuario confirmó que todavía no dispone de proyecto/Map ID/estilo. Cuenta, facturación y prueba viva son dependencias externas.
Se reutilizan los tres layouts y dueños actuales. No hay negocio real nuevo; muestras sintéticas identificadas.
La piel de prueba queda secundaria; aprobación visual pendiente. Medios históricos de restaurantes fuera de prioridad.
