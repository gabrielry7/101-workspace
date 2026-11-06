# Plan técnico

Implementar un nuevo hueso de footer con el Astro/CSS del compiler y el patrón
existente `src/bones`, `src/components/bones`, `src/pages/bones`. El footer Caretta
conserva su propia composición; no se fuerza esta referencia dentro de ese hueso.
No se modifica el renderer semántico ni se copia el runtime privado de Tomás.

1. Evidencia: inspeccionar capturas desktop/mobile de Footr, HTML oficial,
   `section-footer.css`, `custom.css`, `footer.js` y configuración inline del carril.
   Retener recursos y hashes en `.tools/footer-little-amps/reference` (no publicar).
2. Contrato Zod versionado y fixture neutral; posiciones/IDs fijos generados desde
   anatomía. Textos y destinos son entradas; piel y medios no se mezclan con ellos.
3. `SocialRailFooter.astro` es el único renderer del hueso. Subcomponente pequeño
   para acción/hueco, sin servicio o motor nuevo. Anatomía detallada vive fuera del
   footer; `data-footer-part` permite inspección sin inyectar tablas al cliente.
4. CSS conserva distribución y relaciones, no alturas rígidas de texto. Logo con
   caja 385:156.675; embed 380 px de alto; carril cuadrado. Acordeón nativo móvil,
   menús abiertos de escritorio; mejora JS pequeña para exclusividad y animación.
5. Referencia externa a un lado de la versión neutra en el taller mediante enlaces;
   comparación local puede servir las capturas desde `.tools`, no desde `public`.
   Los medios de la referencia no se transfieren a GitHub. Se ofrece vista aislada.
6. Reutilizar `scripts/lib/local-browser.ts` para compilar e inspeccionar componentes
   reales en Edge. Verificar ambos lados de 750/769/1100/1201, móvil/tablet/desktop,
   fallback, teclado, sin JS, y estados de pausa. Tests de contrato no imitan CSS.
7. Diff acotado y copia revisada a clon limpio del monorepo desde
   `codex/section-bones-20261105`; nueva rama `codex/footer-little-amps-20261105`.

## Constitución y límites

Cumple I–VII: spec previa, hueso separado de piel/contenido, permisos sin duplicar
gates de `src/media/gate.ts`, código existente preservado, verificación observable,
reproducción por versión y alcance limitado. Los medios no se pueden vincular por
URL en esta versión; una futura adaptación debe consumir decisiones del gate y
recibir revisión visual. El embed es un hueco del proveedor, no se simulan sus
controles como operativos. La pausa visible del carril es una mejora de accesibilidad
declarada respecto al original. Las mediciones no equivalen a aprobación humana.
