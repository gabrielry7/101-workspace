# Tareas trazables

- [x] T01 · LA-01/02/03/05/06: registrar evidencia y mapa completo del original.
- [x] T02 · LA-02/04/07: contrato, inventario y fixture sin piel/contenido original.
- [x] T03 · LA-01/04/05/06/08: componente Astro y taller, vista aislada y referencia.
- [x] T04 · LA-07/09: tests del contrato, build y auditoría nativa con capturas.
- [x] T05 · LA-09: revisar capturas, corregir y registrar límites/convergencia.
- [x] T06 · LA-10: revisar archivos, commit/push aislado y verificar SHA remoto.

Consistencia previa: cada LA tiene tareas; no hay dependencia de cambios previos
Caretta ni medios privados. Orden T01 → T02 → T03 → T04 → T05 → T06.

Convergencia: 50 partes en DOM/inventario, once briefs, 15 anchos y bordes de
breakpoint, pruebas con Arial, reducción de movimiento, colores forzados, menús,
enlaces y scroll nativos por teclado incluso sin JS. 5 tests específicos pasan.
Build global: 534 páginas. Check global: 0 errores/avisos. El helper histórico de
navegador conserva sus bytes; el auditor adapta MIME en CDP. Ver recibo en
`docs/bones/footer-little-amps-verification.json`. La suite histórica conserva
tres fallos por el grafo/snapshots previos (FactCollection y ampliaciones de contratos),
independientes de este footer; no se cambian ni se resellan esos locks.

La transferencia revisada se reproduce también desde el clon limpio del destino:
5/5 tests propios y auditoría nativa de 15 anchos/50 partes, sin los medios fuente.
Entrega en rama `codex/footer-little-amps-20261105`, sin merge ni despliegue.

Pendientes externos al alcance: aprobación visual humana, medios de otra marca
autorizados y cualquier integración operativa de Spotify/Instagram.
