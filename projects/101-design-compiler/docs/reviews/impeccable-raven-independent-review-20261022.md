# Revisión independiente — Impeccable + Raven

Recibida el 2026-10-22 de la tarea revisora `01a11911-1da1-73e0-8234-132547fc8f8f`, autorizada por el usuario. Revisión de solo lectura del commit **2f68b9ef16aed0d2166729d47f2dac91edaaa034**. No es el protocolo formal dual-agent de Impeccable, ni una preferencia humana.

**Dictamen:** checkpoint técnico apto para revisión humana como piloto opt-in. No aprobar producción, ganador estético ni siguiente hito.

La revisora confirmó reutilización de DesignComposition/planes/hechos, extensión de la misma configuración Astro, parches acotados, controles de binding/derechos y hash del original USDA/ARS. Repitió:

- Tests: **423/424**, único fallo histórico `tests/lock-files.test.ts`, `LOCK_BROWSER_MISMATCH`.
- Focales: **10/10**.
- Check: **299 archivos**, sin diagnósticos.
- Build normal **168**, opt-in **189**.
- Replay exacto: **40 vistas finales**, 40 observaciones iniciales, **2.815 protegidos**, 162 archivos sellados.
- Git limpio. Restauró el build opt-in final.

Inspeccionó cuatro capturas móviles de restaurante: C/D envuelven la navegación en dos filas frente a una en A/B, aunque A/B ya tenían cero objetivos menores de 44px. Crédito, aviso y hueco siguen visibles.

## Hallazgos pendientes

**P2 observado — padding sin defecto táctil.** `src/design/evaluators/refinement.css:3-4`, `scripts/quality-prepare.ts:17`. Raven activa comfortable desde el principio previo sin medir un fallo; el padding produce la envoltura móvil. Antes de promover: activar solo con targets insuficientes o añadir un gate explícito de filas/altura de navegación y repetir 390px. No ocultar la regresión ni forzar una puntuación.

**P2 latente — presupuesto acumulado preventivo.** `scripts/quality-audit.ts`, `scripts/quality-repair.ts`, `scripts/quality-judge.ts`, `src/design/evaluators/policy.ts`. Los límites se comprueban por subconjuntos/iteraciones y judge puede devolver keep cuando calls/seconds exceden el presupuesto. El total se verifica después, lo que no impide gastar de más antes de una segunda iteración/refresh. **La corrida actual cumple 183/200 y su recibo no queda invalidado.** Antes de extender el loop: ledger acumulado de preflight, detector, Raven, audit_url y refresh, guardado antes de cada llamada, con negativos de sobrepresupuesto y rollback.

Se conservan ambos como pendientes concretos del piloto apagado. No se inició otra ronda visual ni se reinterpretó el dictamen como autorización para ampliar la automatización.

## Riesgos confirmados

Fixtures sintéticos; faltan dos negocios reales con evidencia. Sin perfil taste, crítica formal Impeccable ni preferencia humana. Original de 2.351.102 bytes sin optimización comercial; LCP/INP/CLS, Safari y dispositivos físicos no medidos. Un JSON exportado desde localStorage no autentica por sí solo la declaración EXPLICIT_HUMAN_INPUT. Mantener opt-in.

## Prompt propuesto para revisión humana

El piloto Impeccable + Raven está técnicamente reproducido, pero no elegí ganador ni lo activé. Abre `/quality/` y compara A/B/C/D en restaurante y hotel, escritorio y móvil; valora lectura, jerarquía, navegación y confianza en avisos, especialmente la nav móvil de C/D. Puedes elegir una versión, empate o ninguna y explicar por qué. La decisión humana no inicia otro hito. Si quieres la crítica formal de Impeccable, autorízala por separado.

Este prompt es una propuesta de la revisora, no una respuesta del usuario ni aprobación de las variantes.
