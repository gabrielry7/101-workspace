# Tasks: Footer 001

## Phase 1: Setup

- [x] T001 Fijar captura, fuentes y diferencias en `specs/003-footer-caretta-bones/research.md`.
- [x] T002 Resolver spec/plan oficiales y definir contrato en `specs/003-footer-caretta-bones/contracts/footer.md`.

## Phase 2: Foundational

- [x] T003 Escribir pruebas de contrato y unión en `tests/footer-bones.test.ts`; comprobar fallo previo.
- [x] T004 Implementar contrato y fixture real en `src/bones/footer/contract.ts` y `caretta.ts`. FR-001/004/005.

## Phase 3: US1 · hueso neutro

Prueba independiente: comparar captura y componente a 1440 y comprobar el flujo móvil.

- [x] T005 [US1] Registrar partes/dueños en `src/bones/footer/anatomy.ts`. FR-001/002.
- [x] T006 [US1] Construir `src/components/bones/footer/DirectoryFooter.astro` sin piel Caretta. FR-002/007.
- [x] T007 [US1] Añadir consumidor y taller en `src/pages/bones/footers/caretta/`. FR-003.

## Phase 4: US2 · acciones

Prueba independiente: enlaces con nombres/destinos, cinco Soon, integración de cookies explícita.

- [x] T008 [US2] Renderizar enlaces/estados en `src/components/bones/footer/FooterItem.astro`. FR-004/005.
- [x] T009 [US2] Conectar contrato de evento opcional en `DirectoryFooter.astro`. FR-006/007.
- [x] T010 [US2] Verificar acciones y teclado en `scripts/audit-footer-bones.ts`. FR-004–007.

## Phase 5: US3 · medidas

Prueba independiente: medir y exportar sección completa con métodos/denominadores.

- [x] T011 [US3] Añadir unión de áreas y cobertura en `src/bones/footer/measure.ts`. FR-008/009.
- [x] T012 [US3] Preparar dueño compartido fijado en `tooling/bones/prepare-inspector.mjs`. FR-010.
- [x] T013 [US3] Conectar medición, guías y descarga en `src/bones/footer/workshop.ts`. FR-009–011.
- [x] T014 [US3] Registrar medidas y evidencia por tamaño en `docs/evidence/bones/footer-001/`. FR-012.

## Phase 6: Verificación y entrega

- [x] T015 Ejecutar check, tests y build; inspeccionar capturas en `docs/bones/footer-001.md`.
- [x] T016 Actualizar entrada, restricciones y siguiente trabajo en `README.md` y `AGENTS.md`.
- [x] T017 Revisar alcance y publicar commit/push; registrar SHA en el recibo local de entrega.

## Dependencies

T001→T002→T003→T004. US1 y US2 comparten contrato/componente; US3 requiere el
consumidor US1 para el taller. T015 requiere US1/2/3. T016→T017 cierra la entrega.

## Parallel opportunities

Tras T004, anatomía T005 y extensión de áreas T011 son independientes.
La revisión de enlaces US2 y de fórmulas US3 puede realizarse por separado.
No se requiere delegación ni se lanzan agentes para este piloto.

## Implementation strategy

MVP US1: hueso + captura + adaptación propuesta. Después, estados y medición.
Las pruebas del contrato se ejecutan primero en rojo y después sobre el
componente real. No se publica un sitio comercial.
