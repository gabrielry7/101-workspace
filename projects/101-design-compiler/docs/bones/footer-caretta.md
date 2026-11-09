# Footer caretta/08 · anatomía sin piel

Hueso `footer.directory-watermark@0.1.0`. Reconstruido para revisión; sin aprobación
humana. [Especificación](../../specs/003-footer-caretta-bones/spec.md).

La [referencia caretta/08](https://www.regards.design/sections/caretta/08) aportada
por el usuario corresponde a una captura de 2026-10-19, escritorio 1440 × 900,
footer de 806 px, posición vertical 10421. Es la fuente de composición, no una
licencia de reutilización de sus logos, fuentes o imágenes.

## Hueso y contenido

| Región | Qué conserva | Qué muestra sin contenido de cliente |
| --- | --- | --- |
| Banda superior | Espacio antes de los accesos | Banda superior sin tratamiento gráfico |
| Asistentes | Invitación y cinco accesos con icono | Texto e icono de IA 1…5 |
| Identidad | Logo y descripción a la izquierda | Logo de marca; texto descriptivo de marca 1 |
| Respaldos | Encabezado y tres logos debajo de identidad | Texto de encabezado; logo de respaldo 1…3 |
| Directorio | Cuatro grupos de 5/4/5/10 enlaces con icono | Texto de título del grupo; texto e icono de cada enlace |
| Marca grande | Región inferior de marca antes del cierre | Espacio de marca gráfica de gran formato |
| Legal/social | Copyright, privacidad, términos, cookies, confianza, red social y correo | Cada texto identificado por función y número |

`Voice AI` y `Compute & Inference` son dos elementos distintos. Los cinco estados
«Soon» corresponden a SDRs, AEs, Voice AI, Customers y Security. No se añaden redes
sociales extra: la referencia tiene LinkedIn y correo. Cada parte, incluidos
texto/icono/estado, tiene un `data-footer-part` estable y una entrada en el inventario.

El fixture sólo contiene etiquetas neutras. Nombres originales aparecen en la
tabla del taller para comprobar la correspondencia, fuera del footer. Los huecos
sin destino no son enlaces. Cookies queda deshabilitado y requiere una futura
integración explícita; no se simula consentimiento. Los accesos a IA no llaman a
modelos. Con datos configurados, las acciones disponibles son enlaces nativos.

Es flujo normal, sin scroll fijado ni movimiento añadido. La captura no acredita
animaciones. El reflujo propuesto pone identidad encima del directorio por debajo
de 992 px, y el directorio en dos columnas por debajo de 600 px. No se presenta
como una réplica del móvil original. Las etiquetas crecen: no se fuerza la altura
de 806 px ni se recortan textos para imitarla.

## Piel observada, separada y sin aplicar

| Tratamiento en la referencia | Registro de piel | Estado del hueso |
| --- | --- | --- |
| Banda tipo puesta de sol, naranja/roja hacia fondo oscuro | Gradiente y colores de superficie | Sin gradiente ni paleta de marca |
| Asistentes redondos y esmerilados | Forma, borde y acabado de controles | Etiquetas/iconos genéricos sin tratamiento |
| Títulos de categoría monoespaciados | Rol tipográfico; familia exacta sin confirmar | Fuente nativa del navegador |
| Logos de Caretta, IA e inversores | Medios/identidad con permisos por verificar | Slots de texto, sin imitaciones |
| Enlaces futuros tenues con «Soon» | El acabado pertenece a piel; el estado pertenece al hueso | Etiqueta de estado legible, sin atenuarla |
| Wordmark enorme, tenue y recortado detrás del cierre | Tratamiento gráfico de marca en una región estructural | Hueco identificado, sin dibujar ni agrandar una marca inventada |
| Rieles laterales y divisiones finas | Tratamiento de bordes | Sólo contornos de anatomía en el taller |

No se infieren códigos de color exactos, familias tipográficas ni intensidades
de efectos a partir del resumen. No se implementa una piel nueva en esta entrega.
Los contornos punteados son instrumentación de revisión y no forman parte de la piel.

## Abrir y reutilizar

Con Node 24 y dependencias existentes: `npm run dev`, ruta `/bones/footer-caretta/`.
La página usa `DirectoryFooter.astro`; no una representación alternativa.
Importar `footerContentSchema` y pasar `content` al mismo componente. El contrato
de esta versión fija las cantidades observadas; cambiar la receta exige versionar.

Comprobar con:

```sh
node --experimental-strip-types --test tests/footer-caretta.test.ts
node --experimental-strip-types scripts/audit-footer-caretta.ts
```

El auditor usa `scripts/lib/local-browser.ts`, construye la ruta real y guarda
un [recibo resumido de verificación](footer-caretta-verification.json), además de
capturas/evidencia locales en `.tools/footer-caretta-20261105/audit`. La referencia
queda local, separada del commit. La anatomía y los controles del taller nunca se
inyectan automáticamente en páginas de clientes. No se copia el renderer privado
de reseñas de Tomás ni se declara integrado el selector del nuevo pipeline.

## Recuperación junto a Little Amps · 2026-11-08

La implementación neutra ya existía en `b0019b3`; el preview local de Caretta
seguía usando el borrador con contenido de marca. Se recuperan sus once archivos
propios sobre la base que contiene Little Amps y mapas, sin tocar esos componentes.
El mismo taller abre también en `/bones/footers/caretta/`; su ruta `instance/`
consume el mismo componente con el mismo fixture neutro, sin instrumentación.
Las tres rutas están incluidas en la auditoría. Pruebas actuales: nueve contratos
de ambos footers y nueve anchos en Chromium. Evidencia local actual en
`.tools/footer-caretta-20261105/audit`; recibo público sin imágenes fuente.
