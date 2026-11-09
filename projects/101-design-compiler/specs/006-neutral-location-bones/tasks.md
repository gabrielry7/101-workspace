# Tareas
## Preparación
- [x] T001 Resolver plantillas y alcance en specs/006-neutral-location-bones/spec.md.
- [x] T002 Registrar plan, investigación, modelo y contrato en specs/006-neutral-location-bones/.
## US1
- [x] T003 [US1] Presentar tres recetas neutras primero en src/pages/bones/location-map.astro y retirar acabado de marca en src/components/bones/SingleBusinessLocation.astro.
- [x] T004 [US1] Versionar/anatomía/persistencia en src/bones/location-map.ts, location-map-runtime.js y location-map-workshop.js.
## US2
- [x] T005 [US2] Dibujar pin con logo/fallback en src/bones/location-map-marker.js; verificar mediante tests/location-map.test.ts y tests/fixtures/location-map-google-browser.js.
## US3
- [x] T006 [US3] Estilo descargable en tooling/bones/prepare-location-map.mjs; procedimiento en docs/bones/location-map.md y taller.
## Verificación
- [x] T007 Contratos, tipos, navegador y capturas mediante scripts/audit-location-map.ts.
- [ ] T008 Revisar diff, converger documentos y verificar commit/push de la rama.

Dependencias: T001 → T002 → T003/T004 → T005/T006 → T007 → T008.
T005/T006 tienen archivos independientes salvo documentación. Implementación no delegada.
MVP: recetas neutras y pin de logo. Google vivo es dependencia externa.

Convergencia técnica: seis pruebas de contrato, check 0 errores/avisos, build privado del mismo componente y auditoría nativa de 17 anchos pasan. Pin/slot/contención/punta, fallos, teclado, sin JS, fuentes de respaldo y preferencias comprobados. Capturas móvil/tablet/escritorio inspeccionadas. Google vivo y aprobación visual humana pendientes. No hay hooks de extensión configurados. Gate posterior de constitución: PASS.
