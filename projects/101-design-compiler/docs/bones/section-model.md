# Esquema de secciones: huesos, comportamiento, piel y contenido

Estado: contrato conceptual propuesto, 2026-11-05. Requisitos normativos en
[spec 002](../../specs/002-section-bones/spec.md). No hay todavía un nuevo
validador, selector automático ni renderer implementado con este esquema.

```text
Datos y medios del negocio ──→ comprobar suficiencia y permisos
                                      ↓
Familia → elegir hueso + versión → configurar comportamiento permitido
                                      ↓
Identidad de marca ──────────→ aplicar piel + contenido
                                      ↓
                         instancia de sección reproducible
                                      ↓
                         componer secciones compatibles
                                      ↓
                         verificar → revisar → completar pendientes
```

La generación normal compone código reutilizable y configura sus entradas. La IA
puede ayudar a interpretar una necesidad, proponer la piel o crear un hueso nuevo
mediante SDD. Instanciar un hueso existente no consiste en volver a pedir a un
modelo que invente el código de toda la web con un único prompt.

## Responsabilidades del contrato

| Registro | Campos conceptuales | No debe decidir |
| --- | --- | --- |
| `SectionBone` | ID, versión, familia, partes, slots, composición adaptable, requisitos, comportamientos admitidos, límites y alternativas | Qué hechos son ciertos para un negocio |
| `BehaviorProfile` | Navegación, scroll, fijación/liberación, transiciones, tiempos acotados, estados, tacto/teclado y movimiento reducido | Colores oficiales o fuentes de marca |
| `BrandSkin` | ID/versión, tipografías por función, paleta semántica, logo, superficies y tratamientos gráficos permitidos, procedencia y estado de confirmación | Cambiar el orden de partes o introducir otra receta de scroll |
| `BusinessContent` | Textos, datos, acciones, medios, fuente/fecha/sucursal, permisos y huecos | Alterar la identidad del autor de una reseña o prometer capacidades ausentes |
| `SectionInstance` | Hueso/versión, comportamiento, piel/versión, referencias de datos/medios, razones, alternativas y resultado de revisión | Regenerar silenciosamente código de composición |
| `PageComposition` | Orden de instancias, anclas, dependencias, capacidades y restricciones compartidas de contenedor/scroll | Duplicar la autoridad de reservas, pagos o loyalty |

Estos nombres describen responsabilidades para el plan; no sustituyen contratos
operativos existentes ni son APIs publicadas. La versión de un hueso y su revisión
humana se registran por separado: pasar pruebas no lo convierte en aprobado.

## Qué cambia la piel y qué cambia el hueso

| Cambio | Responsable |
| --- | --- |
| Sustituir la fuente por una confirmada del negocio | Piel; volver a verificar ajuste y palabras completas |
| Cambiar color de texto, acento, fondo, borde o radio permitido | Piel / perfil visual validado |
| Ajustar separación dentro de límites que mantienen la receta | Opción visual acotada; comprobar restricciones |
| Pasar de hero con imagen lateral a imagen de fondo | Otro hueso o variante estructural versionada |
| Hacer que el fondo se expanda durante el scroll | Hueso y perfil de comportamiento |
| Elegir avance manual frente a desplazamiento ligado al scroll | Variante de comportamiento del hueso |
| Cambiar una foto por un video en un slot que admite ambos | Contenido/medios; carga, reproducción y fallback siguen el contrato del hueso |
| Cambiar el efecto funcional de un botón | Opción de comportamiento admitida, no consecuencia automática del color de marca |

La distribución tiene límites propios: la piel no puede eliminar el espacio
necesario para leer ni convertir un cambio de fuente en una modificación oculta
de estructura. Si una identidad exige algo incompatible, se explica y se elige o
especifica otro hueso.

## Encaje con la implementación de Tomás

### Familia de ubicación incorporada (2026-11-05)

La [ficha de mapas](location-map.md) aplica esta separación al componente existente
de Tomás: un destino real por sucursal, ningún negocio ajeno en el mapa y logo propio
como marcador preferido. Ocultar POIs es una regla del hueso; la piel no puede
reactivarlos. Paleta y logo son piel/medios validados; coordenada y destino son datos
con evidencia. Cambiar logo no mueve el anclaje geográfico ni cambia el proveedor.

El `google_embed` actual no permite controlar sus etiquetas o reemplazar el pin
desde la página. El [piloto ejecutable de mapas](../../specs/005-location-map-bones/spec.md)
usa la API nativa original y añade un adaptador Google JS; no declara verificado
su estilo vivo sin configuración. La piel nunca se aplica como un logo fijo sobre el iframe.

### Correspondencia existente

La palabra del producto **hueso** corresponde principalmente a su `chassis`, las
recetas y el comportamiento. El directorio `site-runtime/src/bones` y el parámetro
`bones` existentes representan **perfiles visuales**: forma, superficies, colores,
padding y otras opciones. No deben confundirse con el contrato estructural nuevo.

Se conserva esa API mientras el plan estudia su integración; no se renombra ni se
copia a otro renderer. Las opciones de acción —semántica, apariencia, forma y
efecto— siguen ejes independientes. El esquema debe componer esos dueños reales,
no recrearlos bajo un nombre nuevo.

## Ejemplo de selección, sin datos inventados

Una receta de hero admite título, propuesta, acción y un medio autorizado. Su
comportamiento especifica si la imagen permanece en flujo o se fija y libera con
el scroll. La piel decide las fuentes y colores. El negocio aporta título, enlace,
foto o video y sus evidencias. Si el medio es esencial y falta, no se rellena con
el de otra empresa: se registra incompatibilidad o se elige una alternativa permitida.

En el futuro, un selector filtrará elegibilidad y justificará su ranking. Esta
entrega define la información que necesita, sin atribuirle implementación ni
resultados de selección automática.
