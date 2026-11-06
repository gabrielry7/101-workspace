# Little Amps · footer sin piel

Hueso `footer.identity-menus-social-rail@0.1.0`. Reconstrucción para revisión;
aprobación humana pendiente. [Spec](../../specs/004-footer-little-amps/spec.md),
[plan](../../specs/004-footer-little-amps/plan.md) y
[tareas](../../specs/004-footer-little-amps/tasks.md).

La extracción conserva estructura y comportamiento y retira la identidad gráfica.
«Piel» designa fuentes, colores, logo y tratamientos; la estructura sin esa piel
es el **hueso**. Las fotografías son contenido, no parte de la tipografía.

Capturas propias de la vista neutral: [escritorio](footer-little-amps/desktop.png),
[tablet](footer-little-amps/tablet.png) y [móvil](footer-little-amps/mobile.png).
Sólo contienen etiquetas y guías; no redistribuyen imágenes de la referencia.

## Fuentes inspeccionadas

- [Galería Footr](https://www.footer.design/sites/little-amps-coffee), ficha añadida
  el 24 de marzo de 2026; capturas desktop de 2048 × 846 y móvil de 786 × 1618.
  Son dimensiones de imagen, no se asegura que coincidan con el viewport CSS.
- [Página oficial](https://littleampscoffee.com/), HTML recuperado el 2026-11-05.
  Se contrastaron `section-footer.css`, `custom.css`, `footer.js`, la configuración
  inline del carril y los once medios, inspeccionados individualmente.
- Capturas/HTML/CSS/medios de análisis permanecen en
  `.tools/footer-little-amps/reference`. No se incluyen en el commit ni se supone
  que su acceso público dé permiso de redistribución.

## Mapa de composición

```text
ESCRITORIO > 1200 px
┌───────────────────────────────────────────────────────────────────────┐
│ LOGO GRÁFICO        │ EMPRESA (3 enlaces) │ TIENDA (5) │ EMBED MUSICAL │
│                    │                     │            │ externo      │
│ título ubicaciones │                     │            │ 380 px alto  │
│ dirección 1  redes │                     │            │              │
│ dirección 2  correo│                     │            │              │
└───────────────────────────────────────────────────────────────────────┘
│ GRÁFICA SOCIAL FIJA │ CARRIL DE 11 MEDIOS CUADRADOS → (ventana)         │
│ copyright + marca enlazada                             créditos       │

MÓVIL < 1100 px
logo → ubicaciones → redes/correo → grupo empresa → grupo tienda
→ gráfica fija + ventana de carril → copyright/marca a izq., créditos a der.
```

Entre 1100 y 1200 px los menús son columnas abiertas y el reproductor está oculto.
Los textos pueden crecer; no se impone la altura de una captura. El bloque de
contacto envuelve cuando falta espacio y se apila hasta 768 px. No se parte una
palabra para forzar cabida; una futura marca debe volver a pasar la revisión.

## Inventario semántico

El inventario completo de **50 partes** se genera con `littleAmpsAnatomy()` y se
muestra en `/bones/footer-little-amps/`. Cada fila incluye ID, tipo, posición,
propósito, referencia y responsable. Los mismos IDs aparecen una vez en el DOM
como `data-footer-part`; las copias decorativas del bucle son inertes y no duplican IDs.

| Región | Qué va ahí | Función y sustitución |
| --- | --- | --- |
| Identidad superior izquierda | Logo SVG compuesto de wordmark + amplificador | Enlace al inicio. Se conserva caja con proporción 385:156.675; no se recrea como texto ni se cambia por foto |
| Ubicaciones inferior izquierda | Un título y dos direcciones | Texto informativo; la etiqueta de título no es botón |
| Canales junto a ubicaciones | Dos iconos de redes y un correo debajo | Enlaces Facebook/Instagram y mailto; nombres accesibles cuando se vinculen |
| Empresa al centro | Un título y 3 enlaces | Grupo de navegación; desplegable en móvil |
| Tienda al centro | Un título y 5 enlaces | Segundo grupo de navegación; no duplicar el contenido móvil y desktop |
| Extremo derecho | Un embed externo musical | El proveedor posee portada, metadatos, guardar, reproducción y lista de pistas. No es una foto ni un reproductor nuevo |
| Izquierda de banda social | Ilustración de cactus/taza con bocadillo de invitación | Un PNG compuesto dentro de un enlace a Instagram. Semánticamente es enlace gráfico, no botón ni foto documental |
| Derecha de banda social | Once piezas cuadradas | Fotos y un cartel; sin destinos en el HTML original. No son once enlaces ficticios |
| Cierre izquierdo | Copyright/año y marca | La marca es enlace al inicio, separado del texto de copyright |
| Cierre derecho | Créditos | Enlace a página de créditos |

### Cada medio del carril

El orden siguiente es el del HTML oficial; la fase visible del bucle de la captura
puede empezar por otra pieza. No es un feed conectado a Instagram.

| ID | Archivo de referencia | Tipo / contenido observado | Criterio de reemplazo |
| --- | --- | --- | --- |
| gallery-1 | Rectangle_27 | Foto de producto: mano sosteniendo lata/envase | Producto legible; conservar mano y envase |
| gallery-2 | Rectangle_29 | Foto documental: entrada con personas y jardineras | Mantener fachada y contexto del negocio |
| gallery-3 | Rectangle_30 | Cartel de concierto con tipografía y retratos | No cortar información. Preferir arte cuadrado o contain; acompañar con descripción accesible |
| gallery-4 | Rectangle_31 | Foto documental: persona con tostadora y recipientes | Mantener persona, equipo y contexto del proceso |
| gallery-5 | Rectangle_32 | Foto documental: edificio en esquina urbana | Local reconocible en su entorno |
| gallery-6 | Rectangle_33 | Foto documental: actividad manual con letrero | Mantener gesto, persona y letrero |
| gallery-7 | Rectangle_34 | Foto documental: dos personas frente al local/calle | Conservar contexto; no inferir relación laboral |
| gallery-8 | Rectangle_35 | Retrato de dos personas dentro de cafetería | Rostros y contexto; identidades por confirmar |
| gallery-9 | Rectangle_36 | Foto de producto en exhibidor comercial | Mantener bolsas y contexto de venta |
| gallery-10 | Rectangle_37 | Foto documental de grupo ante puerta | Grupo completo; no afirmar quiénes son |
| gallery-11 | Rectangle_38 | Foto de mercancía: personas con camisetas ante mural | Prendas y personas visibles; permisos por separado |

Son **briefs semánticos**, no autorización ni evidencia de otro negocio. Reemplazos
requieren procedencia, derechos, ámbito, inspección, recorte, texto alternativo y
créditos según `src/media/gate.ts` y el planner existentes. La versión neutra
acepta etiquetas de huecos, no URLs de fotos ni flags `approved`. No introduce
un segundo sistema de permisos. Logo e invitación son huecos de gráfica; el embed
es un hueco de integración que requiere una decisión explícita del proveedor.

## Piel retirada y registrada

| Rol | Observación del CSS oficial | Estado neutral |
| --- | --- | --- |
| Fondo de banda | Brick `#C03001` | Sin aplicar |
| Panel principal | Beige `#F6EDE3` | Sin aplicar |
| Texto/cierre | Brown `#522C25` | Sin aplicar |
| Texto sobre cierre | Beige | Valores nativos del navegador |
| Texto de cuerpo/enlaces de menú | Inclusive Sans | Fuente inicial del navegador, sin descargar archivos |
| Menús/etiquetas/legal | Necto Mono | Sin familia ni tracking de marca |
| Display de la marca | Little Amps; el logo visible es un SVG | No sustituir el SVG por esta fuente |
| Superficies | Radio de panel de 7 px; tratamientos de enlaces y colores | Sin radios/acabados de marca |
| Dibujo | Amplificador, cactus/taza y bocadillo | Huecos tipados, sin imitación |
| Fotos/cartel | Medios propietarios de referencia | Sólo etiquetas; no se cargan |

Las líneas punteadas y fondos grises pertenecen al **taller de anatomía**, no a
una piel para clientes. La fuente, el color o un radio futuros no pueden cambiar
la receta, el orden, los breakpoints, la semántica ni las interacciones.

## Comportamiento y alternativas

- Flujo vertical normal; no hay footer fijado, scroll secuestrado ni puntero nuevo.
- Acordeones inicialmente abiertos bajo 1100 px. Al abrir uno se cierra el otro;
  se pueden cerrar ambos. A 1100 px vuelven a mostrarse ambos y los encabezados
  dejan de ser controles de teclado. Sin JS se conservan details nativos independientes.
- Spotify sólo aparece desde 1201 px; su espacio queda en el contrato en todos
  los tamaños. En la vista neutra no hay iframe ni acciones de audio simuladas.
- Invitación fija a izquierda: 17vw desde 769 px y 45vw hasta 768 px. Cada medio
  ocupa `(100vw - 44px)/15` desde 750 px y `/5` por debajo; gap 1vw. Su caja sigue
  siendo cuadrada aunque la foto fuente tenga otro formato.
- El original usa Swiper, bucle lineal, speed 9900, autoplay con delay 0, inicio 1
  y sin arrastre táctil ni controles visibles. La reconstrucción propia conserva
  el bucle lineal; su ciclo acotado de 108.9 s no promete igual fase frame a frame.
  No se copia el script comercial ni se añade dependencia de Swiper.
- Se añaden pausa/reanudación visibles, pausa al hover y alternativa manual al
  recibir foco. Pausar o enfocar puede reiniciar la fase: no cambia orden ni piezas.
  Sin JS, con movimiento reducido o colores forzados hay carril estático desplazable,
  incluyendo acceso con teclado al último medio. Copias ocultas e inertes.
- Destinos ausentes producen texto/huecos. Logo, redes, correo, menús, gráfica social,
  marca de copyright y créditos pueden vincularse como enlaces nativos seguros.
  No hay envíos, suscripciones, formularios ni integración operativa implícita.

## Reutilizar y comprobar

Componente único: `src/components/bones/SocialRailFooter.astro`.
Contrato/fixture/anatomía: `src/bones/footer-little-amps.ts`.
Página de taller: `src/pages/bones/footer-little-amps.astro`.

```astro
---
import Footer from './src/components/bones/SocialRailFooter.astro';
import { neutralLittleAmps } from './src/bones/footer-little-amps.ts';
---
<Footer content={neutralLittleAmps} />
```

Con Node 24 y las dependencias del proyecto:

```sh
npm run dev
node --experimental-strip-types --test tests/footer-little-amps.test.ts
node --experimental-strip-types scripts/audit-footer-little-amps.ts
```

El taller abre en `/bones/footer-little-amps/`. La auditoría usa el helper existente
`scripts/lib/local-browser.ts`, compila el componente real y guarda informe/capturas
en `.tools/footer-little-amps/audit`. El helper histórico permanece sin cambios:
el auditor corrige MIME de JS/PNG en la respuesta CDP sin cambiar los bytes, y
espera el evento nativo de carga para las comprobaciones sin JavaScript.

Si las dos capturas fuente están localmente disponibles, el auditor crea además
`/comparison/`, sólo dentro del build local de auditoría. Muestra original y neutro;
en pantallas amplias aparecen en paralelo. Sin capturas omite esa comparación y
continúa las comprobaciones. No copiar ese build a un despliegue público.

El [recibo de verificación](footer-little-amps-verification.json) registra condiciones
y hashes sin redistribuir medios. Cambiar los datos, las fuentes o la versión exige
repetir las comprobaciones pertinentes. No hay piel de otro negocio, selector
integrado ni aprobación visual humana concedida por estas pruebas.
