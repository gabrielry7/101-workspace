# Superdesign sobre B3 — piloto ejecutado para revisión humana

Fecha: **2026-10-22**, America/Bogota (la receta final registra timestamps UTC del 2026-10-23). Base limpia al comenzar: `b97f76f9bc632f57bba9e21ceefd9a060700cf08`.

**CONNECTED / PILOT_READY_FOR_HUMAN_REVIEW.** La cuenta está autenticada, existe un proyecto real y se generaron una reproducción y dos alternativas de **La mesa abierta**. Se inspeccionaron seis vistas con el paquete audiovisual real en localhost. **No se eligió ganadora, no se registra aprobación estética y no se sustituyó el diseño del motor.** Es continuación de B3; no B4 ni un hito posterior.

Revisión: [comparación local](http://127.0.0.1:4332/) y [canvas real de Superdesign](https://superdesign.dev/teams/0d4d1ed8-c7b0-4018-80a5-860612ee5ef9/projects/919d462f-3d02-4b56-a5d8-9f7953126f37). El servidor local debe estar iniciado para abrir la comparación.

## Conexión, versiones y consumo real

La skill oficial se instaló fuera del repositorio, en `%USERPROFILE%/.codex/skills/superdesign`, fijada en `f9f05cd988c247dce6c072eaf9ac6b162f2ffc4b`. El CLI oficial **0.14.0** se reprodujo con `npm ci --prefix tooling/superdesign --ignore-scripts --no-fund --no-audit`: 61 paquetes, lock propio y lifecycle scripts desactivados. El runtime raíz conserva sus manifests, lockfile y dependencias. La receta desactiva telemetría CLI con `DO_NOT_TRACK=1` y `SUPERDESIGN_TELEMETRY_DISABLED=1`; la generación sigue siendo remota.

La primera autorización caducó. Se renovó y el usuario pulsó «Authorize CLI» para el equipo **Personal**. El proceso de login devolvió éxito y el preflight confirmó `authenticated as team Personal`. No se leyeron ni copiaron tokens, claves privadas o `.env` a evidencia. La configuración de sesión del CLI permanece fuera del repositorio, en `%USERPROFILE%/.superdesign/config.json`.

Se usó **Gemini 3 Flash**, modelo estándar del catálogo real `ddd33b7ef0a92d0e`, para explorar estructura con una cuota acotada. La página de facturación mostraba plan **Free** y 100 créditos; explica que la generación se detiene al agotarse la cuota, que el plan gratuito renueva 100 créditos diarios y que unos 6 créditos por diseño Flash es solo un promedio variable. La ejecución concreta fue:

| Operación | Resultado / consumo |
|---|---|
| Proyecto y dos componentes de contexto | Creados; sin generación de imágenes o vídeo |
| Primera solicitud de reproducción | Rechazo de validación: más de 50.000 caracteres en un archivo de contexto |
| Reproducción con contexto completo separado | Un borrador, **8 créditos** |
| Corrección determinista de contenido del borrador | Versión 2 mediante importación, sin nueva generación |
| Exploración `branch` con dos prompts explícitos | Dos borradores, **30 créditos** en total |
| Corrección determinista de selector/paleta en Editorial | Versión 2, sin nueva generación |
| Total y saldo observado en el canvas | **38 créditos de la cuota gratuita; 62 restantes** |

No hubo compras, recargas, cambios de plan, publicación ni una promesa de costo a escala. No se midieron los tokens/costo de esta sesión de Codex ni el tiempo humano. Los recibos `creditsConsumed` se conservan; no se presenta el promedio comercial como una cotización exacta.

IDs reales: proyecto `919d462f-3d02-4b56-a5d8-9f7953126f37`; base `437beb18-e438-43da-a1b8-7f81b1def321` v2; Editorial `cbfcc8b2-d86d-4256-8ba3-4d1ec417b6c4` v2; Chapter `d076add9-3aaf-4db4-8cc8-1f53217c4b19` v1. La base sigue activa en el estado local: ninguna rama se seleccionó en nombre del usuario.

## Contexto proporcionado y límites de medios

Se inicializaron los seis archivos de descubrimiento de la skill a partir de la rama real de B3, con 56 imports locales trazados. El inventario completo quedó local e ignorado. El payload real fue el sistema de diseño, el HTML literal de la home y sus cuatro hojas de estilo completas. Al rechazar el límite de 50.000 caracteres por archivo se separaron HTML y CSS; no se redujo la página a adjetivos o a un ejemplo genérico. Las rutas, datos y UI se obtuvieron del build real.

Se extrajeron `ExperienceNavigation` y el footer compartido como componentes de contexto remotos. El frontend 101 mantiene los componentes Astro existentes. No hay SDK Superdesign en el cliente, nueva biblioteca visual, código específico de un negocio real, integración upstream o runtime comercial simulado. Astro sigue siendo el laboratorio compartido.

**No se subieron a Superdesign fotos, vídeo, originales ni capturas que los contienen.** Los grants B3 permiten vision, pero deniegan entrenamiento, edición IA y redistribución; no se ampliaron para autorizar el tratamiento de un proveedor nuevo. El contexto remoto conserva los once elementos de medios con su geometría y usa rectángulos SVG neutros de autoría local. El canvas remoto sirve para explorar estructura: no representa una reproducción audiovisual completa ni se declara igualdad de píxeles con B3.

Las propuestas se evalúan localmente con las imágenes y el vídeo reales ya autorizados. El builder extrae solo el bloque CSS de cada propuesta y lo aplica al **HTML real intacto**, añadiendo una clase de operador y un bloque de estilos. Un round trip byte a byte verifica que al retirarlos se obtiene exactamente el original. No usa el HTML reescrito por el modelo para sustituir hechos, enlaces o avisos. Los scripts y assets ejecutados son los del build existente; no se ejecutan scripts del proveedor.

Se conservan nueve archivos servidos y **3.462.266 bytes del paquete completo** de rendiciones, con sus hashes comprobados contra `data/media/demo-v1/b3-rich-experience-review.json`, revisión `5f114b66dab6e87092e87e5b942135e2a17922330f845f0393d2afcaefed567a`. Esta suma incluye rendiciones alternativas y **no es una medición de transferencia de una carga fría**. Las selecciones efectivas se registran en el navegador. Las capturas locales son composiciones de revisión del mismo proyecto ficticio, con los créditos y el aviso de no respaldo preservados.

La ruta semántica local sigue siendo `/b3/candidate-01/`, con un parámetro de comparación; los destinos restantes se sirven desde el mismo build. Los medios no se convierten en stock documental: no prueban platos, instalaciones o clientes reales. No hay nuevas adquisiciones, derivaciones binarias, permisos inventados ni uso de `101-world-model`.

La pantalla OAuth enlazó documentos de **Treg**, cuyo alcance explícito es `treg.to`. No se extrapolaron al canvas Superdesign. Su política de tratamiento de fotos/capturas y sus modelos sigue pendiente antes de plantear subir el paquete. La licencia MIT de la skill/CLI tampoco sustituye ese análisis. Este piloto pudo avanzar con código y geometría sin ese upload.

## Hallazgos y correcciones supervisadas

La reproducción inicial acortó **13 segmentos**: los ocho párrafos extensos de relatos, avisos de ficción y otros textos, además del control de vídeo. Se rechazó su fidelidad. Se importó el HTML literal completo al mismo borrador, conservando historial. La refetch de v2 verificó **147 segmentos de texto**, hechos, once claves de medios y enlaces completos. Esa corrección se atribuye a 101 y al proceso supervisado, no a una regeneración exitosa del modelo. La refetch v2 archivada como `current.geometry.html` tiene SHA-256 `92d7da82edf45ec6f069b1420298382007241c4996af8fb64fe6552bc1f231bd`, idéntico al payload literal corregido: la fidelidad se demuestra con esos bytes y el audit, no solo con el número de versión.

En Editorial, tres selectores escribían `.pilot-EditorialSpread .experience-Immersive` cuando ambas clases están en el mismo elemento. No podían aplicar el cambio del hero. Se corrigió la relación de clase y se sustituyó el color nuevo `#fbfbf9` por el token aprobado `var(--paper)`. Se guardó la corrección como v2 y se volvió a obtener el HTML. No se gastaron créditos adicionales para estos arreglos exactos.

Cuatro negativos reales del builder bloquearon CSS con URL externa, selector global, filtro de medios no revisado y ocultación del contenido. Tras cada prueba se restauró la respuesta original y el replay archivado. Esto comprueba esas barreras concretas; no es una certificación general de seguridad o calidad artística de cualquier CSS generado.

## Diferencias que se pueden revisar

| Variante | Cambio estructural observado | Límite para valorar |
|---|---|---|
| Actual | Hero centrado, introducción/directorio equilibrados, diario de cuatro columnas en escritorio y dos en móvil | Punto de comparación apreciado por el usuario |
| Editorial Spread | Título del hero alineado a la izquierda y más abajo; primer relato dominante, tres continuaciones de distinta escala; citas mayores en cursiva | Más largo: unos 7.881px en móvil frente a 5.685px del actual; valorar si el aire y la longitud ayudan |
| Chapter Rhythm | Hero más corto; rail de rutas junto a introducción; relatos en filas alternadas y cierre de contacto centrado | El cambio es mayor en escritorio; en móvil conserva bastante de la cuadrícula original |

No se afirma que las dos propuestas sean mejores. Son opciones reales del proveedor sobre el molde existente, con correcciones supervisadas y el mismo paquete final. Una decisión humana debe preceder su incorporación como operadores reutilizables del motor.

## Navegador y cobertura comprobada

CUA, navegador de la aplicación, vistas solicitadas de **1440×1000** y **390×844**. Se recorrieron y capturaron las tres composiciones completas: **seis capturas JPEG**. Se restauró el viewport al acabar. Los recibos registran también el ancho útil con scrollbar, geometría por sección, tipografía, URI efectiva de imágenes y estado de vídeo.

En las seis observaciones: cinco imágenes decodificadas, cuatro relatos, 34 enlaces, dos referencias factuales de la home y avisos preservados; sin overflow horizontal ni texto con caja fuera de los bordes. El vídeo estuvo reproduciéndose, silenciado y con `readyState=4`. Los fotogramas varían: no se promete igualdad entre capturas.

Cuatro recorridos adicionales —dos propuestas por dos tamaños— comprobaron salto de teclado con foco fuera del header, apertura de navegación con nueve destinos, expansión del primer relato con sus dos párrafos completos y acceso a la página separada de créditos con cinco autorizaciones/orígenes. No se enviaron reservas, pedidos, consultas ni reseñas.

Alturas medidas antes de capturar, desktop: actual 4.541px, Editorial 5.615px y Chapter 6.682px; móvil: 5.685px, 7.881px y 5.687px. Se conservan Georgia/Arial y la paleta WhiteInk. Las medidas son evidencia de estructura, no un score de belleza.

La revisión independiente detectó que los ocho archivos nombrados inicialmente `.png` contienen JPEG/JFIF. Se corrigieron sus extensiones a `.jpg` y se verificaron formato/MIME y dimensiones leyendo los bytes; no se convirtieron los píxeles para cambiar el formato. También detectó una medida móvil inconsistente: se había medido después de `screenshot({fullPage:true})`. Se repitió la secuencia y el adaptador informó para Editorial móvil 375px/7.881px antes de la captura y 390px/7.895px después. Las medidas finales se toman **antes de la captura**, con ancho útil consistente de 1.425px en escritorio y 375px en móvil para las tres propuestas. Los JPEG de página completa miden 1.424px/374px de ancho por exclusión del scrollbar y redondeo de límites fraccionales; sus alturas difieren como máximo un píxel del scrollHeight previo. Los tamaños solicitados siguen siendo 1440×1000 y 390×844; no se confunden con el ancho de píxeles del archivo. Se conserva el recibo original en `browser-measurements-original.json`, la secuencia antes/después en `capture-reconciliation.json` y formato/dimensiones en `capture-metadata.json`. Las seis capturas y medidas se readquirieron sin nuevas generaciones ni cambios de código.

No se midieron LCP/CLS/INP o red fría; no se afirma certificación WCAG, prueba exhaustiva de lectores de pantalla o compatibilidad de todos los navegadores. El vídeo sigue siendo 1280×720 y puede ampliarse en escritorio, límite histórico del paquete. La limitación de salto sin JavaScript documentada en B3 sigue fuera de esta pasada; se probó la mejora con JS existente.

## Verificación y reproducción

[Journal final](../evidence/design-evaluation/superdesign-20261022/verification-journal.json), [medidas](../evidence/design-evaluation/superdesign-20261022/browser-measurements.json), [interacciones](../evidence/design-evaluation/superdesign-20261022/interactions.json), [negativos](../evidence/design-evaluation/superdesign-20261022/negative-gates.json), [manifest local](../evidence/design-evaluation/superdesign-20261022/local-review-manifest.json).

| Comprobación final | Resultado |
|---|---|
| `npm test` | **423/424**; único fallo histórico H8 `LOCK_BROWSER_MISMATCH` en `tests/lock-files.test.ts` |
| `npm run check` | PASS, 306 archivos; cero errores, warnings o hints |
| `npm run contracts:export` y `npm run validate` | PASS; sin cambios de contratos |
| `npm run build` | PASS, 168 páginas |
| `npm run media:verify` | PASS; H3 autorizado con hueco documental bloqueado |
| Replay exacto B3 | PASS; verifica la evidencia previa de 44 rutas/88 vistas/68 operaciones, no nuevas llamadas Superdesign |
| Preservación | PASS, **2.815 archivos protegidos** sin cambios |
| Replay local de las propuestas archivadas | PASS, nueve hashes de medios y HTML original preservados |
| Negativos de CSS | **4/4 bloqueados** |

El material reproducible incluye versiones, prompts completos, rechazo inicial, recibos reales, respuestas HTML sin medios licenciados, correcciones, hashes y capturas locales. `.gitattributes` preserva sus bytes; no se normalizan los recibos brutos para hacerlos pasar por otros resultados. `.env`, credenciales, originales privados, dependencias instaladas y archivos de trabajo de `.tools`/`.superdesign` quedan fuera de Git.

Replay **sin autenticación, compras ni llamadas a modelos**, con Node 24, dependencias raíz y paquete B3 autorizado disponible:

```powershell
npm run build
node tooling/superdesign/prepare-pilot.mjs
node tooling/superdesign/build-local-review.mjs
node tooling/superdesign/serve-local-review.mjs
```

Abrir `http://127.0.0.1:4332/`. Las herramientas Superdesign son optativas para obtener nuevos borradores; no hacen falta para servir el sitio ni para este replay. La reproducción de futuras llamadas al modelo no promete resultados probabilísticos idénticos: se reproduce esta salida archivada.

## Decisión pendiente

Revisar actual, Editorial y Chapter con los mismos medios y señalar qué conservar de entrada, ritmo del diario, proporciones, citas y cierre. No hay nueva preferencia guardada ni aprobación automática. Incorporar una dirección al motor requerirá la elección del usuario y una adaptación revisada a la gramática compartida; no se inicia ese paso en este piloto.

Fuentes oficiales consultadas el 2026-10-22: [skill fijada](https://github.com/superdesigndev/superdesign-skill/tree/f9f05cd988c247dce6c072eaf9ac6b162f2ffc4b), [flujo de UI existente](https://github.com/superdesigndev/superdesign-skill/blob/f9f05cd988c247dce6c072eaf9ac6b162f2ffc4b/skills/superdesign/references/SUPERDESIGN.md), [CLI 0.14.0](https://www.npmjs.com/package/@superdesign/cli/v/0.14.0) y ayuda/tabla del plan observada en la cuenta. Documentos OAuth con alcance Treg, no canvas: [privacidad](https://treg.to/privacy), [términos](https://treg.to/terms). El permiso de los medios remite a la evidencia H3/B3 existente, no a estas URLs de software.
