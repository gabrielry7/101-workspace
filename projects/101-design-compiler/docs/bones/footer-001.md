# Footer 001 · directorio con marca recortada

**Estado**: reconstruido desde caretta/08; verificado técnicamente. La revisión
visual del usuario sigue pendiente. ID: `footer.directory-watermark@0.1.0`.

[Vista estática](https://p.superdesign.dev/draft/43c5cfe6-b15c-437e-b88e-bc8462629985) ·
[spec](../../specs/003-footer-caretta-bones/spec.md) ·
[cómo ejecutarlo](../../specs/003-footer-caretta-bones/quickstart.md) ·
[mediciones de escritorio](../evidence/bones/footer-001/measurements-1440.json).

## Qué se reconstruyó

Un componente Astro nuevo dentro de la aplicación existente, parametrizado por
contenido validado. El sitio no aportó código fuente: la composición se reconstruyó
desde la captura y los datos suministrados. El HTML público actual completó los
destinos; no se copió la implementación original ni se declaró una réplica de sus animaciones.

Se retiraron el gradiente cálido, fuentes de marca, logos originales, acabado
esmerilado y tratamiento de iconos. Se conservaron los espacios y relaciones
que forman el hueso, incluyendo la gran marca decorativa recortada.
Los espacios de logos usan etiquetas neutras, sin imitaciones de activos de marca.
Los textos son los del negocio real de referencia: no un cliente inventado.

| Región | Estructura conservada |
| --- | --- |
| Transición | Banda superior de 274 px a 1440; sin el gradiente |
| Asistentes | Etiqueta y cinco accesos, alineados a la derecha en escritorio |
| Identidad | Espacio de logo y descripción |
| Respaldos | Tres slots de logos/enlaces en dos columnas |
| Directorio | Cuatro grupos; 24 entradas, cinco con estado Soon |
| Marca de fondo | Slot grande recortado, detrás del cierre legal |
| Cierre legal | Franja de 84 px con copyright, enlaces y acción de cookies |

El cuerpo del directorio mantiene 448 px de alto en escritorio. El marco tiene
1088 px máximos y 32 px de gutter. Los cambios a 991/600 px son una adaptación
propuesta para móvil/tablet: sólo se recibió una referencia visual de escritorio.
La banda vacía se conserva deliberadamente para extraer la misma composición;
su utilidad puede revisarse como una decisión estructural posterior.

## Datos medidos

Denominador: **toda el área del footer renderizado**, no la pantalla completa.
Porcentajes redondeados a dos decimales.

| Ancho | Alto real | Texto | Sin texto | Ocupación funcional | Espacio libre |
| --- | --- | --- | --- | --- | --- |
| 1440 px | 806 px | 3,33% | 96,67% | 10,25% | 89,75% |
| 768 px | 860 px | 5,85% | 94,15% | 19,69% | 80,31% |
| 360 px | 1464,75 px | 7,99% | 92,01% | 34,50% | 65,50% |

**Texto** es la unión geométrica de las cajas de líneas de texto funcional,
recortadas al footer y sin doble conteo. No mide píxeles de tinta.
**Sin texto** es su complemento y puede contener botones, logos o decoración.
**Ocupación funcional** une texto, cajas de controles y slots de logos;
**espacio libre** es su complemento, excluyendo fondos decorativos de la ocupación.
Estos porcentajes describen este contenido y tamaño; no son objetivos de diseño.

El JSON también conserva controles, medios y decoración por separado. Esos
porcentajes pueden solaparse: no forman un reparto exclusivo que se sume a 100%.
La captura histórica no tiene un DOM íntegro disponible y la lista de texto
suministrada omite marcas gráficas: no se inventa un porcentaje total del original.

## Instrumental compartido

Se reutilizan `measure.js` y `guides.js` de component-preview de Tomás, fijados en
`6c0ed29940985bfb1789280c1972e47386775193`. Conservan geometría, padding, bordes,
tipografía, contraste sólido, cobertura de superficies y proxy de espacio 40×28.
La extensión propia añade el porcentaje específico de cajas de texto.

La cobertura de superficies de Tomás no es análisis de colores de una fotografía
ni porcentaje literal de letras. Fotos, gradientes y composiciones no resueltas
mantienen su estado desconocido. No se convierte el informe en una nota estética.

Los módulos originales se preparan en `.tools/footer-inspector`, fuera de Git y
del `public` de producción. Sólo el artefacto estático de revisión local los recibe.
El footer del cliente no carga inspector, guías ni medidas. En un checkout sin
ese instrumental, las métricas propias siguen disponibles y la dependencia se
indica como ausente.

## Acciones y verificación

Los enlaces activos mantienen destinos observados en el HTML público. Los cinco
Soon no navegan. Los asistentes son accesos externos que el visitante decide abrir;
no se ejecutó una llamada a modelos. Cookie settings queda sin integración por
defecto; el componente expone un evento para conectar el gestor real del sitio.
El HTML actual añade DPA respecto a la captura: se registró la diferencia y se
conservó el objetivo histórico.

Las comprobaciones cubren 360, 600, 601, 768, 991, 992, 993 y 1440 px, fuente de
respaldo, teclado, reducción de movimiento, lectura sin JavaScript, evento de
cookies y ausencia del módulo compartido. Se inspeccionan las capturas nativas;
la marca decorativa se recorta intencionalmente, los textos funcionales no.

El [recibo](../evidence/bones/footer-001/verification.json) distingue estas pruebas
de la aprobación humana. Las capturas completas permanecen locales bajo
`docs/evidence/bones/footer-001/captures/`.

El build de estas cuatro rutas pasa usando el mismo Astro y copias verificadas
de sus fuentes. El build global sigue bloqueado por el paquete de medios B3 del
legado en el clon; no se cambiaron sus permisos, hashes ni gates para hacerlo pasar.

## Reutilizar

El dueño del hueso es
`src/components/bones/footer/DirectoryFooter.astro`; datos y anatomía están en
`src/bones/footer/`. Cambiar el contenido no requiere regenerar la composición.
Esta versión se ha comprobado con Caretta; cada adaptación a otro negocio debe
satisfacer su contrato y pasar revisión con los datos, medios y capacidades de ese negocio.

## Integración de esta entrega

Rama aislada: `codex/footer-caretta-bones-20261105`, basada en el esquema
publicado en `46d3759`. Mientras se trabajaba aparecieron otra implementación
de Caretta y otro footer en el checkout local compartido. Se preservaron sin
incorporarlos ni sobrescribirlos.

Esta rama es una entrega revisable, no una fusión sobre esos cambios. Antes de
integrar ambas líneas hay que reconciliar el dueño del componente y del ID
`footer.directory-watermark`; no deben coexistir dos implementaciones productivas
con el mismo ID/versión. El taller y las métricas de esta rama conservan su evidencia propia.
