# 101 Design Compiler · secciones reutilizables

Dirección vigente, 2026-11-05: construir páginas mediante **huesos de secciones**
reutilizables y aplicar la **piel de cada marca**. Los huesos incluyen estructura,
composición adaptable, scroll, movimiento e interacciones. La piel aporta fuentes,
colores, logotipo y tratamiento gráfico; datos y medios conservan su procedencia.

## Empezar aquí

1. [Spec 002: alcance, ejemplos de uso y aceptación](specs/002-section-bones/spec.md).
2. [Esquema: huesos, comportamiento, piel y contenido](docs/bones/section-model.md).
3. [Handoff de Tomás, dueños existentes y verificaciones](docs/bones/integration.md).
4. [Reglas del proyecto](.specify/memory/constitution.md) y
   [uso de GitHub Spec Kit](docs/spec-kit-adoption-20261104.md).
5. [Archivo `old` y recuperación](old/README.md) ·
   [entregas con commit y push](docs/bones/github.md).

## Estado real

Familia añadida a los requisitos: [mapa de un solo negocio con su logo](docs/bones/location-map.md),
reutilizando el componente de Tomás. Ubicación real y sin establecimientos ajenos;
colores por marca. Logo e integración configurable de Google siguen pendientes de
implementación y revisión; el iframe actual no ofrece esos controles.

| Entregado | Pendiente |
| --- | --- |
| Especificación y separación de responsabilidades, constitución 2.0.0, respaldo verificado del legado y documentación conectada a GitHub | Plan y tareas del nuevo piloto, contratos ejecutables e integración del motor |
| Handoff privado de Tomás restaurado: 44 entradas verificadas, 36 pruebas locales y build de 14 variantes de reseñas | Navegación/hero del nuevo modelo y comprobación de reutilización con clientes reales |

Las 14 variantes son de reseñas, no héroes. La biblioteca amplia y el objetivo de
aproximadamente 90% de una página automática siguen siendo metas por implementar
y medir. No hay aprobación visual nueva ni publicación comercial en esta entrega.

La primera implementación propuesta se limita a una navegación y dos huesos de
hero, utilizando las reseñas existentes como referencia de separación y taller.
Puede ajustarse durante la revisión de la spec; no se generan 1.000 variantes.

## Código anterior y herramientas

Se conservan las fuentes Astro/CSS, contratos, planner semántico y controles de
medios en sus rutas actuales para mantener dependencias y regresiones. El estado
anterior, incluidas ramas y cambios sin commit de 21 worktrees, queda respaldado
en `old/snapshots`. Los materiales privados y el respaldo completo son locales;
GitHub recibe el esquema y el índice, no esos archivos.

El runtime anterior utiliza Node 24 LTS. Sus comandos existentes siguen siendo:

```sh
npm ci
npm run check
npm test
npm run build
```

Estas órdenes no implementan el nuevo pipeline. El handoff de Tomás se reproduce
por separado con Node 26.7.0 según su [guía local](docs/bones/integration.md).

Para reconstruir el CLI oficial de Spec Kit en otro equipo, ejecutar
`tooling/spec-kit/setup.ps1`. El flujo general es especificar → aclarar → planificar
→ preparar tareas → implementar → verificar y cerrar brechas. Se aplica también
a backend, loyalty, correos, integraciones y herramientas.

La colaboración con Claude, cuando se solicite, conserva su
[puente CLI real](tooling/claude-code/README.md). Este cambio no lo invoca.

Histórico del motor: [pipeline anterior](docs/pipeline.md),
[H0](docs/h0-report.md), [H1](docs/h1-report.md), [H2](docs/h2-report.md),
[H3](docs/h3-report.md) y [H4](docs/h4-report.md). Son antecedentes del proyecto;
el punto de entrada del nuevo trabajo es la spec 002.
