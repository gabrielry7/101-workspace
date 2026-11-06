# Feature Specification: caretta/08 como hueso neutro

**Feature Branch**: `codex/footer-caretta-neutral-20261105`
**Created**: 2026-11-05
**Status**: Implementado y verificado técnicamente; aprobación humana pendiente.
**Input**: Incorporar el footer caretta/08 a los huesos sin diseño añadido,
identificando cada parte con textos genéricos, incluidas redes sociales.

Amplía spec 002 con un footer concreto; no ejecuta el piloto de navegación/hero.
La petición prioriza una anatomía sin marca. La frase final «pases a piel» se
interpreta junto al resto: separar la piel observada, sin aplicarla ni inventar otra.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Identificar todas las partes (Priority: P1)

Como responsable de páginas quiero ver la estructura del footer sin Caretta ni
apariencia de un cliente para reconocer sus espacios reutilizables.

**Why this priority**: El usuario pide partes explícitas, no una propuesta visual.
**Independent Test**: Abrir el hueso y localizar las siete regiones, cuatro grupos,
24 enlaces de directorio, cinco accesos de IA, tres respaldos y barra legal/social.

**Acceptance Scenarios**:

1. **Given** la captura caretta/08 de 1440 × 806, **When** se abre el hueso,
   **Then** conserva el orden y las relaciones de sus regiones, con etiquetas
   como «Texto del enlace 1, grupo 1» y «Texto de red social 1».
2. **Given** la vista neutra, **When** se inspecciona, **Then** no hay logos,
   degradados, tipografías de marca, efectos esmerilados ni ilustraciones inventadas.
3. **Given** una parte repetida, **When** se consulta su identificador,
   **Then** tiene un ID estable y correspondencia con la referencia.

### User Story 2 - Reutilizar sin fingir capacidades (Priority: P1)

Como integrador quiero vincular datos y destinos a la misma composición,
manteniendo estados honestos y la piel separada.

**Why this priority**: Las etiquetas neutras no deben convertirse en enlaces falsos.
**Independent Test**: Vincular un destino válido; rechazar URL ejecutable y enlace
en estado próximo; comprobar que los huecos no navegan ni llaman a una IA.

**Acceptance Scenarios**:

1. **Given** un espacio sin destino, **When** se recorre, **Then** es una etiqueta
   sin enlace; los cinco elementos próximos conservan una etiqueta de estado.
2. **Given** una acción de cookies sin integración, **When** se abre el hueso,
   **Then** figura deshabilitada, sin fingir guardar consentimiento.
3. **Given** una pantalla estrecha o fuente de respaldo, **When** se consulta,
   **Then** mantiene palabras completas y todos los grupos accesibles en flujo normal.

### Edge Cases

- La captura sólo demuestra escritorio estático. El reflujo móvil es una
  adaptación funcional declarada, no una observación del sitio original.
- El sitio actual y la captura histórica pueden diferir: manda el caretta/08 aportado.
- Logos y texto gráfico: huecos etiquetados; no reproducir activos sin permiso.
- No hay evidencia de animación: no añadir scroll fijado, hover, cursor ni transiciones.
- Fuente de respaldo o etiqueta demasiado extensa: permitir crecer, sin recortar texto.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Registrar `footer.directory-watermark@0.1.0`, origen, partes y estado de revisión. (US1)
- **FR-002**: Mantener siete regiones y cantidades observadas, con IDs y etiquetas de cada texto, icono, logo y estado. (US1)
- **FR-003**: Separar composición, fixture neutro y ficha de piel observada; no inventar estilo. (US1)
- **FR-004**: Validar estructura, IDs y destinos; rechazar protocolos ejecutables y destinos en elementos próximos. (US2)
- **FR-005**: No activar IA, consentimiento ni enlaces sin datos; conservar semántica de acciones configuradas. (US2)
- **FR-006**: Verificar móvil, tablet, escritorio, bordes de distribución, teclado, sin JS, movimiento reducido y fuente alternativa. (US2)
- **FR-007**: Comparar localmente referencia y hueso; no publicar sus imágenes ni datos privados del handoff. (US1)
- **FR-008**: Revisar diff, hacer commit/push acotado al GitHub del usuario y verificar SHA remoto. (US2)

### Key Entities

- **FooterBone**: ID/versión, regiones y contrato de contenido.
- **FooterContent**: Etiquetas o contenido vinculado, IDs, estados y destinos.
- **ReferenceSkin**: Acabados observados y límites de evidencia, sin implementación visual.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Todas las partes del inventario aparecen una vez en el componente;
  cuatro grupos con 5/4/5/10 elementos, cinco estados próximos y seis acciones finales.
- **SC-002**: Cero desbordamientos horizontales, palabras partidas o texto recortado
  a 360, 768, 1440 y a ambos lados de los breakpoints, incluida fuente alternativa.
- **SC-003**: Ningún enlace de marcador, petición a modelos ni código privado en la entrega.
- **SC-004**: Versión revisable, evidencia de navegador y commit remoto trazables.

## Assumptions

- El entregable es la anatomía ejecutable y la separación de piel; no una réplica
  aprobada, una identidad nueva, un selector ni un gestor de consentimiento.
- Las medidas de ocupación de un borrador local anterior no forman parte de esta
  petición. Se conserva ese borrador local, sin adoptarlo como requisito.
