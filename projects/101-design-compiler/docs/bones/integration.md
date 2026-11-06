# Integración del nuevo esquema y handoff de Tomás

Fecha: 2026-11-05, zona America/Bogota. Entrada vigente:
[spec 002](../../specs/002-section-bones/spec.md).

## Fuentes fijadas

- [Repositorio de Tomás](https://github.com/thomaspradae/101-world-model).
- [Release de revisión](https://github.com/thomaspradae/101-world-model/releases/tag/review-bones-gabo-20261106).
- [Instrucciones de colaboración, fijadas al commit](https://github.com/thomaspradae/101-world-model/blob/6c0ed29940985bfb1789280c1972e47386775193/packages/gabo-review/design-system/reviews/README.md#start-here-gabo--bones-collaboration).

Se leyó el repositorio mediante GitHub CLI autenticado; el conector de GitHub de
esta sesión devolvía 404 para ese repositorio privado. El código se clonó sin
cambiar el repositorio de Tomás, fijado en
`6c0ed29940985bfb1789280c1972e47386775193`. El tag tiene fecha UTC del 6 de
noviembre; la revisión local ocurrió la noche del 5 en Bogotá.

El archivo `review-bones-demo.tar.gz` coincide con el SHA-256 publicado:
`c5f534ce3b5f475516fc773f9f79c3eae3c666163bad74dd523d0554ed24ab41`.
Se restauraron los archivos retenidos en el checkout privado y se verificaron
sus 44 entradas inmutables antes del build. No se ejecutó scraping nuevo,
llamadas a modelos ni conexión a una base viva.

## Qué aporta y qué sigue pendiente

La demo reúne 14 variantes de **reseñas**: seis de cards/feature/rail con dos
escalas de estrellas, seis Panorama y dos Showcase. Incluye carriles neutro,
marca aplicada y referencia conservada, partes identificables, controles de
taller e importación/exportación de configuración. Las referencias conservan sus
propios testimonios y no se convierten en reseñas del negocio adaptado.

El manifiesto declara `publication_allowed: false`. El código, los medios y los
datos privados del handoff permanecen bajo `.tools/`, fuera de este repositorio
público. Aquí se publica el esquema propio, la correspondencia de responsabilidades
y el recibo resumido; no el paquete de prueba ni sus capturas.

| Estado | Evidencia / límite |
| --- | --- |
| Verificado localmente en Windows | Archivo de release, 44 entradas, 36 pruebas de contrato y construcción nativa de las 14 variantes con Node 26.7.0 |
| Evidencia retenida de Tomás | Informes de checkout limpio, Astro y comprobaciones de navegador incluidos en el handoff; no se presentan como nuevas pruebas locales |
| No realizado en esta entrega | Nueva aprobación visual, prueba local de Astro, auditoría de navegador completa o integración del motor comercial |
| Pendiente del nuevo piloto | Contratos ejecutables, navegación/hero, elección de clientes, selector de secciones y medición de automatización |

El [recibo resumido](verification-20261105.json) registra el alcance de las pruebas
locales sin redistribuir sus datos ni capturas.

## Dueños existentes para el plan técnico

| Responsabilidad | Dueño en `101-world-model` | Uso previsto |
| --- | --- | --- |
| Composición y movimiento | `packages/gabo-review/src/reviews/recipes.js`, `recipes/`, `client.js` | Referencia ejecutable de huesos y perfiles de comportamiento |
| Evidencia y partes | `src/reviews/contract.js`, `parts.js`, `atoms.js` dentro de gabo-review | Reutilizar validación y composición, preservando atribución y destinos |
| Anatomía | `packages/gabo-review/src/reviews/anatomy.js` | Identificar parte, dueño, reutilización y cobertura |
| Perfil visual | `packages/site-runtime/src/bones/` | Piel/superficies; su API `bones` no es todo el hueso del producto |
| Acciones | `packages/site-runtime/src/actions/` | Semántica, apariencia, forma y efecto independientes |
| Pieles | `packages/gabo-review/src/reviews/themes.css` y CSS de cada familia | Aplicar identidad sobre composición conservada |
| Taller/medidas | `packages/component-preview/` y `design-system/reviews/` | Herramientas sólo del operador; mediciones con sus límites |
| Consumo Astro | Componentes existentes de `packages/gabo-review` | Verificar consumo real sin crear otro renderer |

El compiler existente conserva la autoridad del planner semántico, los datos y
los permisos de medios. El nuevo modelo debe conectarse a esos límites y a los
dueños anteriores mediante el plan; no se crea aquí una segunda implementación
de reviews ni una copia de los servicios operativos. Las plantillas completas
anteriores quedan como legado y regresiones, sin imponer su composición al nuevo sistema.

## Reproducción local de lo comprobado

En esta máquina el checkout privado está en
`.tools/bones-handoff-20261105/source`; sus entradas retenidas ya están restauradas.
Node 26.7.0 portable está en `.tools/node-v26.7.0-win-x64/`. Esto no modifica el
Node 24 de la aplicación anterior.

Desde la raíz del checkout de Tomás, con Node 26.7.0 disponible:

```sh
node packages/gabo-review/design-system/reviews/demo.mjs verify
node --experimental-strip-types --test packages/gabo-review/tests/bones.test.ts packages/gabo-review/tests/review-demo.test.ts packages/gabo-review/tests/review-section.test.ts packages/gabo-review/tests/panorama.test.ts packages/gabo-review/tests/showcase.test.ts
node packages/gabo-review/design-system/reviews/demo.mjs build
```

Para inspección local en Windows puede servirse el resultado estático con Python,
sin cambiar el servidor de Tomás ni publicar los materiales:

```powershell
python -m http.server 8773 --bind 127.0.0.1 --directory .tools/bones-handoff-20261105/source/packages/location-map/dist
```

La última orden se ejecuta desde la raíz de este compiler. Galería:
`http://127.0.0.1:8773/honorato/reviews/`; taller:
`http://127.0.0.1:8773/honorato/reviews/chassis/?bones=1`.
Servirla no la publica ni acredita aprobación visual. Los comandos no descargan
automáticamente material privado en otra máquina: primero se necesita acceso al
repositorio y al release y restaurar sus entradas según su README.

## Ruta de trabajo siguiente

1. Recoger feedback sobre spec 002, el límite de una navegación/dos héroes y los
   umbrales propuestos; incorporar ajustes al mismo documento.
2. Preparar `plan.md` con Spec Kit: adaptar contratos existentes, fijar compatibilidad
   y separar estructura/comportamiento de perfil visual sin duplicar dueños.
3. Derivar tareas trazables, analizar consistencia e implementar el piloto acotado.
4. Comparar neutro/original/marca aplicada, verificar accesibilidad y contenido real,
   solicitar revisión visual de versiones concretas y medir esfuerzo manual.

La entrega actual es documental y de reproducción del handoff, no ejecución de
las tareas futuras. Ver [archivo anterior](../../old/README.md) y
[flujo de GitHub](github.md).
