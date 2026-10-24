# La mesa abierta — iteración visual 02 con Superdesign

Fecha de trabajo: **2026-10-22, America/Bogota**. Continuación de B3, sobre la base `24c4301c2a36fc5a023d3cd695030afc13a47f09`. **Pendiente de elección estética humana.** No se eligió ganadora, no se integraron estos estilos en el motor y no se inició otro hito. No se configuró, enlazó ni modificó el historial de Git; esta entrega no tiene commit nuevo.

Solicitud: continuar las iteraciones después de que el usuario indicara que los cambios del primer piloto eran poco abruptos. Se conservaron el molde La mesa abierta, Georgia/Arial, blanco/tinta, contenido, destinos separados y medios autorizados. La exploración cambia composición y jerarquía.

## Revisar el resultado

- [Comparador con escritorio/móvil y accesos por sección](http://127.0.0.1:4333/).
- [Editorial II, página completa con audiovisual local](http://127.0.0.1:4332/b3/candidate-01/?pilot=editorial).
- [Mesa abierta II, página completa con audiovisual local](http://127.0.0.1:4332/b3/candidate-01/?pilot=chapters).
- [Canvas existente](https://superdesign.dev/teams/0d4d1ed8-c7b0-4018-80a5-860612ee5ef9/projects/919d462f-3d02-4b56-a5d8-9f7953126f37).

Los servidores de localhost deben estar iniciados. El canvas remoto conserva geometría SVG neutra; **las fotos y el vídeo se ven en local**. La reproducción archivada de la primera ronda sigue disponible y el builder sin `--live` sigue usando aquella evidencia.

## Qué cambió

**Editorial II — cine y tinta.** Entrada lateral sobre película de ancho completo; título y lema agrupados en una columna. Introducción amplia y directorio en dos columnas. Diario con fondo tinta, una apertura dominante de imagen/texto y tres continuaciones de proporciones y posiciones distintas. Opiniones sobre blanco y contacto asimétrico. En móvil el primer relato ocupa todo el ancho, el segundo combina imagen/copia y los dos últimos comparten fila; se preserva su orden de lectura.

**Mesa abierta II — composición por pares.** Título y lema en una relación horizontal en escritorio, con una franja blanca de acceso al terminar la película. Introducción amplia y cuatro destinos en una secuencia horizontal. Diario claro con dos pares de imágenes de diferente proporción y desplazamiento vertical. Opiniones sobre tinta y cierre dividido. En móvil el diario conserva una apertura y una interrupción de ancho completo, con dos relatos intermedios en columnas.

Estas son dos interpretaciones más marcadas del mismo sistema. No se afirma que resulten mejores por ser distintas. La utilidad del contraste, el espacio vacío y la longitud siguen siendo decisiones de la persona revisora.

## Ejecución real y correcciones

Preflight autenticado en el equipo Personal. CLI oficial **0.14.0**; modelo **Gemini 3 Flash**. Se reutilizaron proyecto y borradores mediante dos operaciones `replace`, una por dirección, conservando historial. Cada una consumió **8 créditos gratuitos**: **16 esta ronda, 54 acumulados, saldo 46 observado en el canvas**. Sin compras ni generaciones adicionales.

Los seis archivos de init existían. Se verificaron los seis archivos de contexto y sus SHA-256 antes de enviarlos: sistema de diseño, HTML estructural neutral y las cuatro hojas de estilo existentes. El caché de resume mezclaba fingerprints del inventario completo con los del payload; se separó ese inventario local y se dejó el mapa exacto de los seis inputs. No se amplió el payload ni se enviaron claves, `.env`, originales o capturas licenciadas.

El modelo introdujo un gris ajeno a la paleta, un token `--gutter` sin definición en su contexto y reglas que no resolvían bien los tres hijos del título. Se corrigieron literalmente: token blanco existente, gutter del sistema, colocación explícita de título/lema, separación del control de vídeo y enlaces, contraste de avisos, tracking y escalas del cierre. La primera salida editorial móvil rondaba 7.789px; se compactaron directorio, diario y pausas hasta **5.911px**, sin quitar textos.

Las correcciones se importaron sin generación. Estado final remoto: Editorial **v5** (`cbfcc8b2-d86d-4256-8ba3-4d1ec417b6c4`) y Mesa abierta/Chapter **v4** (`d076add9-3aaf-4db4-8cc8-1f53217c4b19`). La refetch final fue byte idéntica al HTML corregido. La base permanece sin una selección estética nueva.

## Preservación y permisos

La comparación local extrae exclusivamente el CSS del operador y lo aplica al HTML real. Al retirar clase y bloque CSS se recupera el original byte a byte: textos, hechos, vínculos, scripts y bindings conservados. Continúan 34 enlaces, cuatro relatos, sus ocho párrafos desplegables, dos opiniones ficticias y las dos referencias factuales de la home. El contenido de las demás páginas no se rediseñó.

Los mismos nueve archivos servidos suman **3.462.266 bytes**, con hash contrastado contra la revisión autorizada existente. Esa cifra es el paquete de rendiciones, no una medición de transferencia de una visita. Se preservan crédito enlazado, avisos de ficción, uso ilustrativo y no respaldo de Pixabay. El hueco documental continúa bloqueado. No hubo adquisiciones, edición de píxeles, cambios de grants ni uploads de medios licenciados a Superdesign.

## Navegador y límites de evidencia

Se inspeccionaron entradas, diario, opiniones, contacto y controles mediante CUA. Las seis mediciones finales del comparador usan frames reales de **1440×1000** y **390×844 CSS px**; anchos útiles observados de **1425** y **375px**. Sus vistas se reducen visualmente al 55%/62% para caber en el panel. La escala del visor no cambia el viewport interior.

| Composición | Alto escritorio | Alto móvil | Overflow horizontal / texto fuera de ancho |
|---|---:|---:|---|
| Actual | 4.541px | 5.685px | 0 / 0 |
| Editorial II | 6.076px | 5.911px | 0 / 0 |
| Mesa abierta II | 6.246px | 6.171px | 0 / 0 |

Son medidas de estructura, no una puntuación estética. En la apertura el vídeo se observó reproduciéndose, silenciado y con `readyState=4`. Las capturas de diario documentan imágenes concretas visibles; las mediciones de apertura solo documentan una de cinco imágenes decodificada en cinco de los seis casos, por lazy loading. La revisión independiente señaló que faltaba el estado posterior al recorrido. Se añadió `media-after-scroll.json`: al situar en pantalla la última imagen ilustrativa mediante el locator del navegador, los cuatro casos —dos propuestas por dos tamaños— registran **5/5 imágenes con `complete=true` y dimensiones naturales positivas**, junto a sus URI. No se alteraron sus bytes, atributos ni carga mediante JavaScript de evaluación. El primer intento de scroll del visor no alcanzó ese estado y se conserva en `media-scroll-attempt.json`, sin contarlo como PASS. Fuera de la apertura el runtime puede pausar el vídeo intencionadamente.

Cuatro recorridos —dos propuestas por dos tamaños— probaron apertura de navegación, nueve enlaces, apertura inicial del relato, cierre por Enter, sus dos párrafos y acceso a cinco entradas de créditos. No se enviaron reservas, pedidos, mensajes o reseñas. El recibo no se presenta como un test exhaustivo de todos los estados.

**Limitación del adaptador:** esta sesión no pudo obtener capturas de página completa y el setter de viewport no cambió el tamaño observado del tab. No se usó ese setter como prueba de móvil. Se recurrió al frame del comparador, con sus dimensiones verificadas, y a capturas JPEG nativas de estados concretos. Las dos capturas de diario en escritorio son páginas directas a tamaño normal del panel. Las capturas no son páginas completas, montajes ni pruebas de un dispositivo físico. Se descartaron del conjunto aceptado los nombres iniciales que no correspondían al estado ya asentado; algunas capturas muestran solo una parte de una sección. Los PNG/JPEG del primer piloto no se modificaron.

No se midieron red fría, LCP/CLS/INP ni una certificación WCAG completa. No se declara cobertura de otros navegadores. El vídeo original sigue siendo 1280×720: sus límites de resolución no desaparecen con la composición.

## Verificación técnica

| Comando o comprobación | Resultado |
|---|---|
| `npm test` | **423/424**; único fallo histórico H8 `LOCK_BROWSER_MISMATCH` |
| `npm run check` | PASS; 306 archivos, cero errores, warnings o hints |
| `npm run contracts:export` | PASS; no contratos nuevos |
| `npm run validate` | PASS |
| `npm run build` | PASS; 168 páginas |
| `npm run media:verify` | PASS; hueco documental bloqueado |
| `node --experimental-strip-types scripts/b3-evaluate.ts verify` | PASS; replay exacto del B3 previo, 44 rutas/88 vistas/68 operaciones |
| `node --experimental-strip-types scripts/b3-preservation.ts --verify` | PASS; 2.815 archivos protegidos |
| `node tooling/superdesign/build-local-review.mjs --live` | PASS; dos propuestas, nueve hashes de medios y round trip de HTML |

El replay de 88 vistas verifica el B3 archivado, no convierte las nuevas capturas en 88 pruebas nuevas. Se ejecutó además por error el verificador antiguo `b3-reference-current-verify.ts`, que devolvió `B3_CURRENT_BUILD_STALE` al buscar el atributo de la rama histórica reference-application. No se alteró el build para forzarlo ni se contó como PASS; después se ejecutó el replay que corresponde al experimento actual. El fallo H8 queda abierto y no se cambió para obtener una suite verde.

Recibos, prompts, HTML neutral final, estilos originales generados, correcciones y receta de replay: [evidencia](../evidence/design-evaluation/superdesign-iteration-02-20261022/README.md). El índice incluye hashes y tamaños. No se añadieron dependencias al runtime, catálogos, backups `.tar` ni originales privados.

## Revisión pendiente

Comparar Actual, Editorial II y Mesa abierta II en entrada, diario y cierre. Indicar qué conservar de tipografía, paleta, distribución y audiovisual; separar preferencias de defectos. No se registra una puntuación ni una aprobación en nombre del usuario. La incorporación de una dirección al motor requiere esa elección y su adaptación revisada a la gramática compartida.

Revisión independiente recibida de la tarea autorizada: **apta para elección visual humana como experimento**, sin integración ni hito nuevo. Verificó el índice entonces vigente de 43 archivos y 15 JPEG, nueve hashes de medios y recuperación byte a byte del HTML; confirmó las diferencias más claras en escritorio y la menor diferencia de la entrada editorial en móvil. Su salvedad sobre la carga completa quedó resuelta después con los cuatro recibos de 5/5 imágenes descritos arriba. El índice posterior añade esos dos registros de carga, sin cambios de diseño, y se verifica localmente. [Dictamen y prompt humano](superdesign-b3-iteration-02-independent-review.md). No hay autorización implícita para otro hito.
