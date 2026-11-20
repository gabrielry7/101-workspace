# Directorio de ubicaciones con mapa jerárquico

`location.directory-map-hierarchy@0.1.0` · 2026-11-20.
Estado: implementado y verificado técnicamente; aprobación visual humana pendiente.
Proceso: [spec 010](../../specs/010-location-directory-bone/spec.md).

Se extrajo la sección de la copia privada de [% Arabica](https://arabica.com/en/locations/)
que el usuario escogió. La copia conservada y el hueso neutro usan el mismo
componente Astro, parcial de vistas y controlador. El encabezado de la página
original permanece fuera de la sección. La fuente previa 0.1.1 se archivó
privadamente antes de refactorizar; el consumidor de referencia pasa a 0.2.0.

## Composición y partes

| Parte | Dueño y comportamiento |
| --- | --- |
| Título | Contenido; tipografía heredada de la piel |
| Espacio de mapa | Integración independiente; conserva su nodo al navegar |
| Directorio | Hueso; superpuesto al mapa en escritorio, debajo en móvil |
| Agrupaciones, entradas y recuentos | Contenido validado; selección explícita por enlace |
| Selección actual | Comportamiento; `aria-current="location"` |
| Aperturas futuras | Contenido; listado con scroll propio y sin destinos supuestos |
| Regreso | Comportamiento; padre real de la vista |
| Carril de locales | Scroll manual horizontal, táctil y paginación móvil |
| Foto, título y acción de cada local | Espacios independientes; un destino sin vincular no crea un enlace |
| Estado accesible | Anuncio de cambios con región viva |

`locationDirectoryAnatomy(content)` enumera las partes y sus dueños; la muestra
tiene 88 partes canónicas entre siete vistas sintéticas. Sus IDs coinciden con
`data-directory-part` en las vistas activas. Las guías del taller sólo son ayudas
de revisión. No son elementos de la sección publicada.

Se conservan el mapa móvil de 300 px, el panel de 230 px en escritorio, la
adaptación del panel entre 781 y 1000 px y las proporciones del carril. El cambio
principal de composición ocurre a 780 px. Navegación, historial, foco de teclado,
selección y carril pertenecen al hueso, con independencia de la piel.

## Contenido, piel y límites

El contrato Zod estricto está en `src/bones/location-directory.ts`. Exige una raíz
`overview`, áreas dependientes de ella y localidades dependientes de un área.
Las localidades pueden enlazar sus hermanas o a sí mismas. Rechaza IDs repetidos,
ciclos, destinos ausentes, niveles incorrectos y recuentos negativos. Un recuento
desconocido se representa como `null`, visible como raya; no se convierte en cero.

Límites: hasta 300 vistas, 50 grupos por vista, 300 entradas por lista/grupo,
100 tarjetas por vista, diez grupos de aperturas con hasta 100 etiquetas y textos
de 180 caracteres. Estos límites de validación no garantizan ajuste visual de
cualquier dato: cada contenido/piel debe pasar la revisión de palabras completas,
legibilidad y desbordamiento. Una palabra más ancha que su contenedor requiere
revisión de compatibilidad; no se parte ni se reduce indefinidamente.

Los datos neutros contienen etiquetas para mapa y fotos, sin coordenadas ni
medios originales. Las acciones admiten estados `unbound` o `available`; sólo el
segundo exige una ruta local o HTTPS segura. No se aceptan HTML, URLs de imágenes
ni booleanos de aprobación de medios en este contrato.

La piel aporta tipografías, colores, logo, iconos y acabados sobre la receta
existente. El CSS base usa selectores de especificidad cero y colores nativos.
La referencia aplica su CSS separado y sus medios privados mediante slots Astro
de autoría confiable. Esto no concede permisos para publicar medios de terceros:
una vinculación de negocio debe pasar por los contratos de medios existentes.

## Consumo y proveedor

```astro
---
import Directory from '../../components/bones/LocationDirectory.astro';
import { neutralLocationDirectory } from '../../bones/location-directory.ts';
---
<Directory id="locations-main" content={neutralLocationDirectory}/>
```

La página debe servir el módulo compartido como `/location-directory.js` o indicar
`runtimeURL`. `autoMount={false}` y `runtimeURL={null}` permiten que un consumidor
importe y monte explícitamente `mountLocationDirectory(root, services)`.
Cada instancia necesita `id` y `queryKey` únicos; por defecto la consulta se llama
`location-${id}`. El historial conserva los parámetros de las demás instancias.
Sin JavaScript se muestran los datos en listas nativas con anclas de respaldo.

Los slots opcionales son `map`, `map-overlay`, `icon(role)` y
`card-media({viewId,cardId,label})`. Los dos últimos son callbacks renderizados por
Astro; no son cadenas HTML suministradas por un negocio.

La integración escucha en la raíz `directory:viewchange`, con
`detail: {viewId, level}`, y puede seleccionar una vista enviando
`directory:select`, con `detail: {viewId}`. También están disponibles
`navigate(id,push)`, `inspect()` y `destroy()` en el controlador. `onViewChange`
conecta al proveedor y `onPush` permite al contenedor controlar el desplazamiento
de la página. Los clics del mapa o de otros controles no seleccionan vistas.

El adaptador privado `arabica-directory-map.js` conserva la carga explícita de
Google, sus marcadores, la cámara, los gestos y el presupuesto existente. El hueso
neutro no importa ese adaptador ni biblioteca cartográfica alguna. El mapa vacío
es la decisión expresa del usuario para esta extracción; no simula geografía ni
promete arrastre hasta vincular un proveedor.

## Taller y verificación

```sh
node tooling/bones/prepare-location-directory.mjs
node tooling/bones/serve-location-directory.mjs
```

Abrir `http://127.0.0.1:8779/bones/location-directory/`. El servidor sólo escucha
localmente. El taller enlaza la copia privada en el servidor existente de 8780.
No hace falta recuperar activos de referencia para construir el taller neutro.

```sh
node --experimental-strip-types --test tests/location-directory.test.ts tests/arabica-reference.test.ts
H4_BROWSER_PATH=/ruta/a/chromium node --experimental-strip-types scripts/audit-location-directory.ts
```

La auditoría completa requiere además la referencia privada actual en 8780 y el
archivo privado anterior en `.tools/arabica-locations-reference/before-bone-0.1.1`.
No activa Google. Las rutas `/multi/` y `/stress/` sólo son casos sintéticos del
build de taller. La comparación anterior se sirve bajo `/arabica/` en 8779, sin
endpoint de reserva de Google. Capturas y datos originales permanecen en `.tools/`.

Resultado: seis pruebas de contrato, dos builds Astro acotados, 94 comprobaciones
del hueso y 42 comprobaciones adicionales de la referencia sin activación.
Se inspeccionaron capturas nativas de escritorio/móvil y textos largos, ambos
lados de los breakpoints, historial, teclado, tacto, instancias múltiples,
ausencia de JavaScript, movimiento reducido y colores forzados. La geometría de
la referencia antes/después coincide en móvil/escritorio para tres niveles.
Cero solicitudes externas y cero cargas nuevas de Google; los dos contadores
persistentes permanecieron iguales. No se volvió a verificar cartografía viva.
Recibo publicable: [verificación resumida](location-directory-verification.json).
