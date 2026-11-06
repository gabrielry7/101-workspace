# Adopción de GitHub Spec Kit en 101

Fecha: 2026-11-04. Estado: herramienta instalada y constitución inicial redactada.
La adopción cambia el método de desarrollo. No declara implementado el nuevo
pipeline de componentes ni una página 90% automática.

## Instalación real

Se instaló el CLI oficial `specify-cli` **1.3.0** desde `github/spec-kit`, tag
`v1.3.0`, commit `91261fdcf1738cb095a31ff5bee145f502e3af91`, en un entorno Python
aislado bajo `.tools/spec-kit-venv`. No se cambiaron el PATH global ni las
dependencias de la aplicación Astro.

El inicializador oficial generó 29 archivos con integración `codex`, modo `skills`
y scripts PowerShell. Se generaron primero en una carpeta aislada y se incorporaron
sólo rutas nuevas, tras comprobar que no había colisiones. Se conservaron los
archivos de configuración existentes y la habilidad Impeccable. No se activaron
extensiones de Git que creen ramas o commits automáticamente.

- `.specify/templates/`: plantillas oficiales de especificación, plan, tareas y listas.
- `.specify/scripts/powershell/`: resolución y preparación de artefactos.
- `.specify/workflows/speckit/`: flujo oficial.
- `.agents/skills/speckit-*/`: nueve habilidades oficiales para el asistente.
- `.specify/memory/constitution.md`: reglas del proyecto; inicial 1.0.0,
  actualizadas a 2.0.0 el 2026-11-05 por la definición de huesos y la entrega a GitHub.

El recibo local con origen, commit y hashes de los archivos generados está en
`.tools/spec-kit-adoption-20261104/installation.json`. La constitución es la única
personalización del contenido generado. Las plantillas y habilidades se mantienen
como las entregó el inicializador oficial.

## Uso

En otro equipo, restaurar el CLI local con Python 3.11 o posterior y Git:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tooling/spec-kit/setup.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File tooling/spec-kit/specify.ps1 version
```

El lanzador transmite argumentos al CLI oficial. No instala silenciosamente otra
versión. Una actualización requiere revisar origen, cambios y compatibilidad.

Las habilidades se invocan en el chat del asistente, no en PowerShell. Deben estar
disponibles en el siguiente turno; si la sesión no refresca sus habilidades, volver
a abrir el proyecto. Puede usarse lenguaje natural indicando el paso deseado.

| Paso | Habilidad | Resultado |
|---|---|---|
| Reglas comunes | `$speckit-constitution` | Constitución del proyecto |
| Especificar | `$speckit-specify` | Alcance, requisitos y aceptación en `spec.md` |
| Aclarar | `$speckit-clarify` | Ambigüedades resueltas o identificadas |
| Planificar | `$speckit-plan` | Plan técnico basado en el código existente |
| Preparar tareas | `$speckit-tasks` | Tareas vinculadas a los requisitos |
| Analizar | `$speckit-analyze` | Consistencia entre spec, plan y tareas |
| Revisar requisitos | `$speckit-checklist` | Lista de calidad de los requisitos |
| Implementar | `$speckit-implement` | Ejecución de las tareas acotadas |
| Cerrar brechas | `$speckit-converge` | Evaluación de cumplimiento y trabajo restante |

El núcleo del proceso es especificar, planificar, preparar tareas, implementar y
converger. Aclaración, análisis y listas se aplican según el riesgo del cambio.
Los bugs pequeños y ajustes documentales conservan un alcance y una verificación
proporcionales. No hay aprobación repetida para acciones rutinarias ya autorizadas.

## Dirección acordada

SDD se aplica al desarrollo general: frontend, backend, loyalty, correos,
integraciones y herramientas. El primer caso propuesto es la biblioteca de
componentes útiles y reutilizables. La nueva unidad de reutilización es el bloque
versionado con sus datos, variantes, estados y reglas de combinación. La identidad
de marca se aplica mediante opciones acotadas.

Esta dirección del usuario sustituye, para el nuevo pipeline, la obligación anterior
de reutilizar exclusivamente composiciones completas. Los originales aprobados
permanecen como referencias y regresiones. Continúan vigentes los permisos de
medios, la procedencia factual, las etiquetas de demo, la accesibilidad, las reglas
de puntero y la revisión humana por versión.

## Especificación vigente y siguiente acción

El nuevo [spec 002](../specs/002-section-bones/spec.md) sustituye el borrador 001
como trabajo activo. Define huesos de sección con estructura y comportamiento,
piel de marca separada, alcance de navegación/hero y referencia ejecutable de
reseñas de Tomás. Véanse [modelo](bones/section-model.md) e
[integración](bones/integration.md). Los documentos anteriores permanecen en `old`.

Tras incorporar feedback, usar `$speckit-plan` y `$speckit-tasks` antes de
implementar el piloto. La constitución no autoriza construir toda la biblioteca
ni diseñar de nuevo las ocho bases en esta adopción.

La intención de obtener aproximadamente 90% de una web automáticamente se medirá
en pilotos. No es un resultado demostrado ni una promesa para cualquier negocio.

## Referencias

- [Repositorio oficial y release 1.3.0](https://github.com/github/spec-kit/releases/tag/v1.3.0)
- [Instalación oficial](https://github.github.com/spec-kit/installation.html)
- [Adopción en proyectos existentes](https://github.github.com/spec-kit/how-to/existing-projects.html)
- [Constitución local](../.specify/memory/constitution.md)

El checkout tenía cambios previos sin commit. No se guardaron en stash, no se
fusionaron ramas y no se hicieron commits o push durante la incorporación inicial
del 4 de noviembre. El 5 de noviembre el usuario pidió entregas con commit y push;
la regla vigente está en [el flujo de GitHub](bones/github.md).
