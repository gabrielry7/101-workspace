# B3 — revisión visual de las referencias externas

Evaluación: **2026-10-15, America/Bogota**. Navegador integrado de la app; consulta directa de las 21 URLs aportadas por el usuario. **21 referencias y 42 vistas representativas registradas, con límites por sitio.** No es una auditoría de todas las páginas, una certificación de vídeo/accesibilidad ni aprobación estética de B3.

La conexión antes bloqueada se recuperó al trabajar desde la app y se comprobó abriendo OSIP y viendo su renderizado. No se atribuye una causa técnica retrospectiva al fallo anterior. Se conserva el recibo del intento fallido.

## Qué se conserva y qué se añade

El [corpus original](../../data/reference/design/corpus-v1.json) y el documento del usuario conservan sus bytes y alcances. Las notas nuevas son observaciones del asistente, **no votos del usuario ni una explicación supuesta de por qué gustaron OSIP o Central**. El [registro asociado](../../data/reference/design/visual-review-2026-10-15.json) contiene las fuentes, la opinión previa literal, observaciones por aspecto, límites, reglas propuestas y las capturas seleccionadas con SHA-256. No se regenera el contexto ni las cuatro propuestas B3: ese contexto sigue siendo una evidencia reproducible del trabajo anterior. La incorporación de estas reglas a una futura generación requiere un cambio explícito, verificable y revisión humana; no se anuncia como ya implementada.

Las capturas son evidencia interna de análisis. Una referencia no concede licencia sobre fotografías, vídeos, logos, fuentes ni código: no se descargaron originales ni se introdujeron recursos externos en el runtime. No se abrieron cuentas, enviaron formularios, reservaron mesas, compraron productos o ejecutaron herramientas comerciales WebMCP.

## Hallazgos que sí sirven al motor

| Decisión compartida propuesta | Evidencia | Condiciones antes de implementarla |
| --- | --- | --- |
| Portada de una imagen, díptico o imagen enmarcada deben ser decisiones distintas. | Etxebarri / Central / LUCA. | Datos, longitud del título y medios suficientes para cada relación; no elegir sólo por sector. |
| La secuencia debe admitir capítulos, pausas y densidades diferentes. | OSIP / Aponiente / Khufu’s. | Conservar acceso directo a acciones e información; una introducción debe poder omitirse. |
| Tipografía, paleta y fotografías se evalúan juntas. | Dinesen / The Modern House / KOL. | Fuentes con permiso, contraste y lectura; coherencia del conjunto, no una suma de notas independientes. |
| El móvil necesita su propia composición. | Central apila; ÄNG recoloca enlaces; Noma oculta vídeo de escritorio. | Comprobar punto focal, orden semántico, acciones y encabezados en ambas vistas. |
| Vídeo necesita papel, poster y alternativa explícitos. | Aira pausado; Noma usa foto móvil; Heckfield tiene iframe. | Reproducción real, resolución frente a tamaño, fotogramas, costo de carga y derechos; no aprobar por existir un video. |
| Las capas deben tener reglas geométricas. | Heckfield superpone fotografías; Singer superpone navegación. | Intersección decorativa permitida sólo entre elementos declarados; texto y controles deben conservar zonas seguras. |
| Fondo oscuro y asimetría pueden ser coherentes. | LUNE / Padella. | Media compatible y legibilidad; no imponer minimalismo claro como única salida válida. |
| Sede, campaña, catálogo e historia son papeles diferentes. | Kadeau / FRAMA / Padella. | Mantener alcance por sede y distinguir CTA operativa de una demostración; no inventar cobertura funcional. |
| Un componente aprobado no arrastra al sitio completo. | Aponiente / Khufu’s / Singer; matiz de Polène. | Preservar alcance y negativos originales en cualquier selector o evaluación futura. |

Estas son hipótesis de gramática compartida, no 21 plantillas copiadas ni 1.000 diseños ya disponibles. Los operadores actuales Split/Diptych/Stage/Rows/Mosaic son un punto de partida; esta revisión revela relaciones adicionales a evaluar, no certifica que las cuatro páginas actuales alcancen ya el nivel aspiracional. Tampoco se utiliza la ausencia de fotos por plato en algunas referencias para reducir los requisitos del catálogo B1.

## Método, fallos y evidencia

Se solicitaron **1440×1000** y **390×844** CSS px. Se inspeccionaron renderizados y DOM, incluyendo cambios de navegación/composición móvil. Se capturaron páginas largas cuando funcionó y tramos de viewport cuando falló. [Ledger de capturas](../evidence/corrections/b3/external-references-2026-10-15/capture-ledger.json). Hay 61 capturas con recibo y un suplemento; las 42 seleccionadas son una por referencia y vista.

La API produjo algunas capturas transitorias o con tamaño distinto al DOM solicitado; las tomas no válidas se conservaron como intentos, no se contabilizan como nuevas vistas. Se comprobaron URL, tamaño solicitado, dimensiones de los bytes y SHA; se permite hasta 2 px por redondeo/ancho de scrollbar, no una reducción arbitraria de escritorio a móvil. Una asignación errónea de dos tomas al identificador Dinesen contenía URL Khufu’s: ambas se excluyeron mediante la comparación de dominio. La vista completa horizontal de OSIP no se usa como prueba automática de desbordamiento accidental. Una verificación geométrica tampoco demuestra que una imagen diferida o un vídeo haya cargado con calidad suficiente.

Hubo fallos de captura larga en Dinesen, LUNE, NORM y The Modern House, y fallos intermitentes de captura/sincronización en Khufu’s, Heckfield y Polène. Se recurrió a las alternativas documentadas del mismo navegador, sin automatización externa ni cambio de protecciones. Se cerró la pestaña temporal anterior; se restauró el tamaño normal del navegador. Algunas ventanas de cookies/promoción/región permanecen en evidencia y se declaran en cada caso.

El suplemento de Dinesen conserva los bytes originales de una captura limpia de escritorio; no se había registrado su instante exacto y por eso captured_at es null, separado de recorded_at. No se inventa precisión temporal. Las dimensiones CSS descritas no son prueba de dispositivo físico ni de retina. No se midieron red lenta, INP, coste total de transferencias o todos los estados de interacción de los sitios externos.

## Referencias, una por una

### 01 · OSIP

[Fuente oficial](https://osiprestaurant.com/) · Alcance original: `GLOBAL_REPORTED`. Intensidad previa: Favorita / excepcional.

[Captura de escritorio](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-01-desktop-horizontal.jpg) · [Captura móvil](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-01-mobile-scroll.jpg). Fechas de captura UTC y hashes están en el registro asociado.

**Composición:** La entrada abre un díptico fotográfico y después una secuencia horizontal de texto e imagen con mucho espacio vacío.

**Tipografía:** Serif de trazo peculiar y espaciado amplio; BrutonMedium aparece en el DOM. La identidad no depende de un gran titular convencional.

**Paleta y medios:** Blanco cálido y fotografías de luz natural, jardines y arquitectura; las imágenes aportan el carácter del lugar.

**Móvil:** El recorrido pasa a una columna vertical. El texto y los enlaces conservan su carácter; varias fotografías diferidas no quedaron resueltas en la captura larga.

**Límite:** Se vio la entrada y parte del recorrido; no se inspeccionaron todos los ensayos fotográficos ni el funcionamiento de reservas. El ancho horizontal de escritorio es deliberado, no se clasifica automáticamente como desbordamiento accidental.

**Propuesta para el motor:** Explorar un recorrido editorial horizontal opcional con alternativa vertical explícita y acceso directo a información práctica; exigir suficientes fotografías coherentes.

### 02 · Central Restaurante

[Fuente oficial](https://centralrestaurante.com.pe/) · Alcance original: `GLOBAL_REPORTED`. Intensidad previa: Favorita / excepcional.

[Captura de escritorio](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-02-desktop-overview.jpg) · [Captura móvil](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-02-mobile-overview.jpg). Fechas de captura UTC y hashes están en el registro asociado.

**Composición:** Dos campos de vídeo contiguos abren la página; después aparecen imágenes pequeñas centradas y bloques de texto desplazados a ambos lados.

**Tipografía:** Contraste entre rótulos estrechos y texto editorial en serif, con una frase en cursiva que cambia el ritmo.

**Paleta y medios:** Rojo intenso y texturas oscuras en la entrada, seguidos de fondo claro y silencios amplios. El audiovisual se relaciona con el relato territorial.

**Móvil:** El díptico se convierte en dos campos apilados; texto, fotografías y acciones se ordenan verticalmente.

**Límite:** Se observaron vídeos avanzando, pero no se midieron bitrate, transferencia, audio, red lenta ni calidad de todo el montaje. La causa de tu preferencia global sigue sin desglosarse.

**Propuesta para el motor:** Representar parejas audiovisuales y pausas editoriales como relaciones de composición, con una regla móvil propia; no convertir el relato de territorio en un hecho de otro negocio.

### 03 · Asador Etxebarri

[Fuente oficial](https://www.asadoretxebarri.com/) · Alcance original: `GLOBAL_REPORTED`. Intensidad previa: Muy positiva.

[Captura de escritorio](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-03-desktop-overview.jpg) · [Captura móvil](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-03-mobile-overview.jpg). Fechas de captura UTC y hashes están en el registro asociado.

**Composición:** Una fotografía de arquitectura ocupa la entrada completa; navegación compacta a la izquierda. Después se separan título y explicación de reservas en dos columnas.

**Tipografía:** Titulares serif grandes frente a información práctica en sans; las etiquetas secundarias son discretas.

**Paleta y medios:** Piedra, madera y luz del paisaje se acompañan de un fondo crema; no hay una galería obligatoria de platos.

**Móvil:** La imagen cambia su encuadre y la información pasa a una columna, conservando categorías y preguntas frecuentes.

**Límite:** Algunos textos prácticos se ven tenues. No se enviaron formularios ni se reservaron mesas.

**Propuesta para el motor:** Permitir una portada sostenida por una sola foto auténtica y una sección práctica independiente; no adoptar su falta de fotos por plato como requisito para nuestro restaurante ficticio.

### 04 · KOL

[Fuente oficial](https://kolrestaurant.com/) · Alcance original: `GLOBAL_REPORTED`. Intensidad previa: Favorita de una ronda previa.

[Captura de escritorio](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-04-desktop-overview.jpg) · [Captura móvil](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-04-mobile-overview.jpg). Fechas de captura UTC y hashes están en el registro asociado.

**Composición:** Primer plano gastronómico a gran escala, acciones de reserva arriba y contenido editorial alternado sobre un fondo cálido.

**Tipografía:** Serif con personalidad, títulos sobrios y bordes de botones con apariencia irregular; el DOM identifica clearface.

**Paleta y medios:** Crema amarillento, terracota y rojos del plato forman un conjunto material; se aprecia una dirección cromática compartida.

**Móvil:** La comida conserva protagonismo con un recorte mucho más estrecho; las acciones principales permanecen arriba.

**Límite:** El aviso de cookies y los estados de carga/transición ocultan parte de la experiencia; algunas imágenes interiores quedaron borrosas o pendientes en esta pasada.

**Propuesta para el motor:** Coordinar textura de interfaz y fotografía mediante tokens compartidos; comprobar siempre el recorte móvil y ofrecer estados de carga que no parezcan una página vacía.

### 05 · Aira

[Fuente oficial](https://aira.se/) · Alcance original: `GLOBAL_REPORTED`. Intensidad previa: Muy positiva; video destacado.

[Captura de escritorio](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-05-desktop-overview.jpg) · [Captura móvil](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-05-mobile-overview.jpg). Fechas de captura UTC y hashes están en el registro asociado.

**Composición:** La entrada reserva un campo audiovisual grande; siguen una declaración tipográfica amplia y un bloque de foto e información práctica.

**Tipografía:** Sans ligera y abierta, identificada como TT Norms Pro; frases largas ocupan un ancho generoso.

**Paleta y medios:** Superficies blancas, interiores de madera y fotografía gastronómica clara; la imagen de entrada se observó como un campo azul desenfocado.

**Móvil:** El bloque de dos columnas se apila y las fotografías gastronómicas conservan su función de cierre visual.

**Límite:** Los dos vídeos del DOM estaban pausados con tiempo cero. No se confirma el montaje que te gustó ni se atribuye el desenfoque a una elección artística final.

**Propuesta para el motor:** La gramática debe separar papel del vídeo, poster, reproducción observada y fallback; no dar por buena una dirección audiovisual por la mera presencia de un elemento video.

### 06 · LUCA

[Fuente oficial](https://luca.restaurant/) · Alcance original: `GLOBAL_REPORTED`. Intensidad previa: Positiva («linda»).

[Captura de escritorio](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-06-desktop-overview.jpg) · [Captura móvil](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-06-mobile-overview.jpg). Fechas de captura UTC y hashes están en el registro asociado.

**Composición:** Portada verde con una foto vertical desplazada y un logotipo fino que se extiende fuera de ella; después, piezas editoriales separadas por grandes pausas.

**Tipografía:** Logotipo muy fino y amplio, serif editorial y etiquetas condensadas; el DOM identifica Magister en el cuerpo.

**Paleta y medios:** Verde profundo y fotografía de interiores cálidos y platos; la coherencia procede del conjunto, no de un color de acento aislado.

**Móvil:** El logotipo se superpone dentro de una imagen más alta y las piezas forman una secuencia vertical.

**Límite:** Varias imágenes seguían diferidas o borrosas y algunos intervalos quedaron vacíos. No se inspeccionó cada historia ni el diálogo de reservas.

**Propuesta para el motor:** Añadir relaciones entre logotipo, imagen enmarcada y ritmo de artículos; exigir densidad de contenido suficiente para sostener las pausas.

### 07 · Padella

[Fuente oficial](https://www.padella.co/) · Alcance original: `GLOBAL_REPORTED`. Intensidad previa: Favorita de una primera ronda.

[Captura de escritorio](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-07-desktop-overview.jpg) · [Captura móvil](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-07-mobile-overview.jpg). Fechas de captura UTC y hashes están en el registro asociado.

**Composición:** Vídeo de ambiente, selección de tres locales mediante fotos y una carta tipográfica con categorías y precios enmarcada sobre negro.

**Tipografía:** Sans condensada, titulares compactos y precios alineados; el DOM identifica Roboto Condensed.

**Paleta y medios:** Negro y blanco con interiores cálidos. La identidad observada hoy no es exclusivamente una estética clara o minimalista.

**Móvil:** Los locales pasan a una secuencia vertical y la carta separa comida y bebida mediante pestañas visibles.

**Límite:** Un anuncio de reservas de grupos cubría la entrada. No se probaron las pestañas ni el flujo de reservas; la carta observada no incluye foto por plato.

**Propuesta para el motor:** Conservar la distinción entre local, categoría y producto. La referencia aporta jerarquía de carta; no sustituye nuestros requisitos de fotos, ingredientes, alérgenos, búsqueda y filtros.

### 08 · Noma

[Fuente oficial](https://noma.dk/) · Alcance original: `GLOBAL_REPORTED`. Intensidad previa: Favorita de una primera ronda.

[Captura de escritorio](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-08-desktop-overview.jpg) · [Captura móvil](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-08-mobile-overview.jpg). Fechas de captura UTC y hashes están en el registro asociado.

**Composición:** Entrada audiovisual con acción directa; productos, carta editorial e imágenes de equipo alternan módulos amplios y columnas desiguales.

**Tipografía:** Serif de lectura suave y etiquetas sans discretas; Reckless figura en el cuerpo.

**Paleta y medios:** Marfil, verde muy oscuro y fotografía natural con fondos de producto cuidadosamente escogidos.

**Móvil:** La portada usa fotografía donde el vídeo de escritorio queda oculto; el relato largo y las imágenes se ordenan en una columna.

**Límite:** La primera toma de escritorio recoge un fotograma oscuro y el aviso de cookies sigue visible. No se auditaron tienda, reserva ni todas las páginas.

**Propuesta para el motor:** Permitir fotografía móvil como alternativa declarada al vídeo y combinar piezas comerciales y editoriales sin alterar su orden factual.

### 09 · ÄNG

[Fuente oficial](https://www.restaurangang.se/) · Alcance original: `GLOBAL_REPORTED`. Intensidad previa: Aceptación moderada («bien»).

[Captura de escritorio](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-09-desktop-overview.jpg) · [Captura móvil](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-09-mobile-overview.jpg). Fechas de captura UTC y hashes están en el registro asociado.

**Composición:** Una sola imagen de paisaje y arquitectura sostiene toda la entrada; la marca se sitúa en el centro y los enlaces en zonas periféricas.

**Tipografía:** Logotipo serif de gran escala frente a navegación sans, identificada como futura-pt.

**Paleta y medios:** Tonos de campo y luz cálida; parte del primer plano está desenfocada en la propia imagen.

**Móvil:** La navegación se concentra bajo la marca en vez de conservar las esquinas del escritorio.

**Límite:** Se inspeccionó la entrada. El iframe de reservas no se operó y no se evaluaron todas las páginas interiores.

**Propuesta para el motor:** Usar una portada de navegación espacial sólo cuando la imagen soporte las superposiciones y existan accesos claros en móvil; mantener el menor entusiasmo de tu valoración original.

### 10 · Kadeau

[Fuente oficial](https://www.kadeau.dk/) · Alcance original: `GLOBAL_REPORTED`. Intensidad previa: Aceptación moderada («bien»).

[Captura de escritorio](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-10-desktop-overview.jpg) · [Captura móvil](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-10-mobile-overview.jpg). Fechas de captura UTC y hashes están en el registro asociado.

**Composición:** La home funciona como un selector de dos destinos: Copenhagen y Bornholm, distribuidos en dos zonas.

**Tipografía:** Serif ligera con nombres de sede en dos líneas; el DOM identifica Tobias-Light.

**Paleta y medios:** El fondo se observó difuso en tonos violetas y grises; los vídeos expuestos tenían resolución de 384 por 216.

**Móvil:** Los dos destinos pasan de una relación lateral a una relación superior e inferior.

**Límite:** No se recorrieron los interiores de cada sede. La captura no permite afirmar que el fondo difuso sea su calidad definitiva ni que se hayan revisado todas las funciones.

**Propuesta para el motor:** Hacer explícito el selector de sede como operador antes de mostrar ofertas, horario y acciones; nunca mezclar datos de dos sedes para lograr una composición.

### 11 · MIL Centro

[Fuente oficial](https://milcentro.pe/) · Alcance original: `GLOBAL_REPORTED`. Intensidad previa: Aceptación moderada.

[Captura de escritorio](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-11-desktop-overview.jpg) · [Captura móvil](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-11-mobile-overview.jpg). Fechas de captura UTC y hashes están en el registro asociado.

**Composición:** Paisaje a pantalla completa, titular grande arriba a la izquierda y dos acciones sencillas; el pie reúne información práctica.

**Tipografía:** Serif estrecha de gran escala sobre imagen, con información inferior en sans.

**Paleta y medios:** Verdes y azules de un paisaje concreto; la fotografía comunica lugar, no un decorado intercambiable.

**Móvil:** La imagen se reencuadra en vertical y las dos acciones bajan, manteniendo visibles las terrazas del paisaje.

**Límite:** No se verificaron los datos comerciales del sitio como fuente para nuestros fixtures ni se abrieron los flujos de reservas.

**Propuesta para el motor:** Relacionar título y espacio libre de la imagen mediante un punto focal verificable; sólo utilizar una escena territorial como documental cuando corresponda al negocio y tenga permiso.

### 12 · Aponiente — Menú 2026

[Fuente oficial](https://www.aponiente.com/menu-aponiente-2026/) · Alcance original: `SPECIFIC_PAGE_ONLY`. Intensidad previa: Scroll / composición de esa página.

[Captura de escritorio](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-12-desktop-overview.jpg) · [Captura móvil](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-12-mobile-overview.jpg). Fechas de captura UTC y hashes están en el registro asociado.

**Composición:** En la URL exacta del menú: vídeo de entrada, bloque de enlace al menú junto a una foto y galería irregular de platos sobre blanco.

**Tipografía:** Serif de alto contraste en mensajes y acciones; la información visual se apoya en pocos elementos grandes.

**Paleta y medios:** Blanco y negro con platos de fondos claros; las proporciones distintas introducen ritmo sin cambiar de paleta en cada bloque.

**Móvil:** El enlace al menú y la imagen principal se apilan; la galería mantiene varias columnas pequeñas con alturas diferentes.

**Límite:** Alcance exclusivo de esa página. Se vio el vídeo avanzando, pero no se midió su coste ni se descargó el PDF o los originales.

**Propuesta para el motor:** Añadir una galería editorial con proporciones declaradas y un recorrido móvil distinto; no tratar este gusto parcial como aprobación global de Aponiente.

### 13 · Khufu's

[Fuente oficial](https://khufus.com/) · Alcance original: `STORYTELLING_ONLY`. Intensidad previa: Storytelling visual; no aprobación total.

[Captura de escritorio](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-13-desktop-settled.jpg) · [Captura móvil](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-13-mobile-narrative.jpg). Fechas de captura UTC y hashes están en el registro asociado.

**Composición:** Introducción de frases que aparecen por etapas, seguida de una escena del lugar, titular y acción; el DOM organiza después capítulos de contexto, intención y atmósfera.

**Tipografía:** Titular serif con cambio de cursiva y de saltos de línea; rótulos y acciones más discretos.

**Paleta y medios:** Arena y marrones claros unidos al paisaje; el vídeo observado avanzaba en silencio.

**Móvil:** La frase de entrada cambia de extensión y saltos; el paisaje se reencuadra en vertical.

**Límite:** La introducción dominó la primera pasada y hubo una captura transitoria sin titular. Se comprobó la entrada posterior, no el montaje completo de todos los capítulos ni una secuencia completa de scroll animado.

**Propuesta para el motor:** Modelar el relato en capítulos con una alternativa inmediata para omitir la introducción; conservar únicamente el alcance de storytelling que aprobaste.

### 14 · Heckfield Place

[Fuente oficial](https://www.heckfieldplace.com/) · Alcance original: `GLOBAL_REPORTED`. Intensidad previa: Excepcional; móvil especialmente logrado.

[Captura de escritorio](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-14-desktop-overview.jpg) · [Captura móvil](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-14-mobile-overview.jpg). Fechas de captura UTC y hashes están en el registro asociado.

**Composición:** Secuencias de fotos de tamaños distintos, a veces superpuestas, acompañan bloques de texto espaciado; la navegación de estancia permanece separada.

**Tipografía:** Sans con mayúsculas y espaciado amplio; johnston-medium figura en el cuerpo.

**Paleta y medios:** Fondo gris azulado, imágenes de campo e interiores y pequeños acentos rojos sostienen una misma atmósfera.

**Móvil:** Las parejas y superposiciones se reorganizan en una columna con tamaños todavía diferenciados.

**Límite:** El vídeo de portada está dentro de un iframe de Cloudflare Stream. No se verificó su resolución de reproducción ni se reprodujo la observación histórica de peor calidad en PC; esa crítica se conserva como tu antecedente, sin confirmarla ni revocarla.

**Propuesta para el motor:** Permitir capas fotográficas declaradas con separación segura para texto y controles. Revisar calidad audiovisual por viewport antes de aprobarla, sin inferirla de la buena fotografía.

### 15 · FRAMA

[Fuente oficial](https://framacph.com/) · Alcance original: `GLOBAL_REPORTED`. Intensidad previa: Referencia ejemplar de retail.

[Captura de escritorio](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-15-desktop-overview.jpg) · [Captura móvil](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-15-mobile-overview.jpg). Fechas de captura UTC y hashes están en el registro asociado.

**Composición:** Campañas grandes en díptico, seguidas de producto, guías y configuración; la navegación comercial es una capa clara e independiente.

**Tipografía:** Sans uniforme y etiquetas limpias; el DOM identifica Univers.

**Paleta y medios:** Blanco, madera y fotografía de producto en tonos cálidos; el marco comercial acompaña la materialidad.

**Móvil:** Las dos campañas se apilan; los listados de producto se sugieren como carriles horizontales y las secciones editoriales siguen abajo.

**Límite:** Persistieron avisos de cookies y un teaser de newsletter. Algunos productos y guías no terminaron de cargar sus fotos en la toma larga; no se probó compra, configuración o búsqueda.

**Propuesta para el motor:** Separar campaña, ficha de producto y guía editorial como módulos distintos; una portada fotográfica no reemplaza la cobertura del catálogo ni autoriza usar estos activos.

### 16 · Dinesen

[Fuente oficial](https://www.dinesen.com/en) · Alcance original: `GLOBAL_REPORTED`. Intensidad previa: Excepcional; audiovisual y color.

[Captura de escritorio](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-16-desktop-final.jpg) · [Captura móvil](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-16-mobile-final.jpg). Fechas de captura UTC y hashes están en el registro asociado.

**Composición:** Imagen de material y arquitectura a gran escala, texto superpuesto en un área de menor ruido y navegación comercial clara arriba.

**Tipografía:** Sans ligera, titular de líneas amplias y jerarquía simple; AtlasGrotesk figura en el DOM.

**Paleta y medios:** Madera dorada y marrón, fondos claros y acento cálido de marca; la propia foto proporciona la mayor parte de la paleta.

**Móvil:** El espacio arquitectónico se conserva mediante un recorte estrecho y el titular se distribuye en más líneas.

**Límite:** La primera pasada estuvo tapada por consentimiento; se cerró y se revisó la entrada limpia. La captura larga falló y el vídeo expuesto seguía pausado: no se certifica el montaje ni la calidad de todos los vídeos.

**Propuesta para el motor:** Seleccionar media y paleta en conjunto, reservando espacio real para el texto. No basta con que todas las fotos tengan alta resolución de manera aislada.

### 17 · LUNE Croissanterie

[Fuente oficial](https://lunecroissanterie.com/) · Alcance original: `GLOBAL_REPORTED`. Intensidad previa: Excepcional; personalidad y armonía.

[Captura de escritorio](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-17-desktop-viewport.jpg) · [Captura móvil](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-17-mobile-scroll.jpg). Fechas de captura UTC y hashes están en el registro asociado.

**Composición:** Fondo negro, croissant de gran tamaño y una acción tipográfica desplazada; la fotografía se convierte en una pieza de identidad.

**Tipografía:** Sans de gran peso para la acción frente a controles muy pequeños; el DOM identifica Untitled Sans.

**Paleta y medios:** Negro profundo, reflejo del producto y tonos dorados de la masa; el contraste organiza la portada.

**Móvil:** El croissant se recorta de forma mucho más vertical y la acción mantiene su escala relativa.

**Límite:** La introducción cambió automáticamente antes de poder pulsar Play video. No se confirmó su reproducción; falló la captura larga y se inspeccionaron tramos de entrada. Algunas tomas inmediatas de resize se descartaron para conclusiones finas.

**Propuesta para el motor:** Admitir identidades oscuras y asimetría controlada; exigir una foto con fondo y encuadre compatibles. No convertir negro más foto en una receta universal.

### 18 · NORM Architects

[Fuente oficial](https://normcph.com/) · Alcance original: `GLOBAL_REPORTED`. Intensidad previa: Muy buena; limpieza y organización.

[Captura de escritorio](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-18-desktop-viewport.jpg) · [Captura móvil](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-18-mobile-scroll.jpg). Fechas de captura UTC y hashes están en el registro asociado.

**Composición:** Portada de proyecto a gran escala con navegación y descripción superpuestas; debajo se anuncia una selección de trabajos.

**Tipografía:** Sans y rótulos espaciados; el DOM identifica Euclid. Los textos sobre la foto son pequeños en la vista observada.

**Paleta y medios:** Fotografía de arquitectura y vegetación con tonos naturales; el fondo claro de la siguiente sección continúa la gama.

**Móvil:** La portada se vuelve más baja y la descripción ocupa varias líneas; la sección de trabajos comienza dentro del primer recorrido.

**Límite:** Falló la captura larga y algunas imágenes inferiores seguían diferidas. No se midió contraste suficiente para certificar el texto sobre cada fotograma ni se recorrió todo el portfolio.

**Propuesta para el motor:** Evaluar limpieza, color y organización como decisiones coordinadas; mantener un tamaño mínimo legible aunque la referencia utilice tipografía muy discreta.

### 19 · The Modern House

[Fuente oficial](https://themodernhouse.com/) · Alcance original: `GLOBAL_REPORTED`. Intensidad previa: Excelente; tipografía e identidad.

[Captura de escritorio](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-19-desktop-viewport.jpg) · [Captura móvil](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-19-mobile-viewport.jpg). Fechas de captura UTC y hashes están en el registro asociado.

**Composición:** Medio de gran tamaño a la izquierda y ficha editorial clara a la derecha; después aparece una cuadrícula de inmuebles con etiquetas y precios.

**Tipografía:** Titular serif de tono editorial, marca y metadatos sans; la tipografía acompaña la temática de arquitectura y vivienda.

**Paleta y medios:** Blanco cálido, negro y fotografía de espacios; se evita que todos los elementos tengan el mismo peso.

**Móvil:** El medio pasa encima de la ficha y la acción queda debajo del titular, antes del listado.

**Límite:** El consentimiento cubría parte del listado; no se enviaron alertas ni se operaron inmuebles. El vídeo observado era de 640 por 360, por lo que no se presenta como prueba de máxima calidad técnica.

**Propuesta para el motor:** Vincular tono tipográfico y dominio del contenido; permitir una ficha editorial junto al medio, diferenciada de la tarjeta repetida de catálogo.

### 20 · Polène

[Fuente oficial](https://www.polene-paris.com/) · Alcance original: `GLOBAL_REPORTED`. Intensidad previa: Buena; fundamentalmente por foto y video.

[Captura de escritorio](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-20-desktop-recovery.jpg) · [Captura móvil](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-20-mobile-viewport.jpg). Fechas de captura UTC y hashes están en el registro asociado.

**Composición:** Campaña audiovisual a toda pantalla con una ficha de producto pequeña superpuesta y navegación discreta.

**Tipografía:** Marca y nombres en serif, controles y precio secundarios; el producto no compite con un gran bloque de texto.

**Paleta y medios:** Paisaje y vestuario en gama fría/terrosa, enlazados cromáticamente con el bolso de la campaña.

**Móvil:** La campaña emplea un vídeo vertical distinto y una tarjeta de producto más baja. Se observó un prompt de cambio de región.

**Límite:** Las primeras tomas de escritorio no correspondían al tamaño; se recuperó una captura de escritorio verificable. El prompt regional siguió presente. No se inspeccionó toda la tienda ni se ejecutó ningún WebMCP comercial.

**Propuesta para el motor:** Separar dirección audiovisual de arquitectura de tienda; no ampliar tu aprobación centrada en foto/vídeo al resto del diseño. Comprobar fotogramas y resolución de cada variante antes de elegirlos.

### 21 · Singer Vehicle Design

[Fuente oficial](https://singervehicledesign.com/) · Alcance original: `DROPDOWN_ONLY`. Intensidad previa: Menú desplegable únicamente.

[Captura de escritorio](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-21-desktop-menu.jpg) · [Captura móvil](../../docs/evidence/corrections/b3/external-references-2026-10-15/reference-21-mobile-menu.jpg). Fechas de captura UTC y hashes están en el registro asociado.

**Composición:** El desplegable observado es un panel lateral estrecho sobre un fondo atenuado y difuso; las categorías forman una lista vertical sencilla.

**Tipografía:** Rótulos en mayúsculas y peso marcado; el cuerpo figura como Roboto en el DOM.

**Paleta y medios:** Panel oscuro y translúcido que conserva parte del contexto fotográfico de la página.

**Móvil:** El mismo panel ocupa una fracción mucho mayor del ancho; el control de cierre permanece arriba.

**Límite:** Se abrió el desplegable en ambas vistas. No se verificó toda la navegación con teclado, lector de pantalla o submenús. El sitio completo sigue fuera de tu aprobación.

**Propuesta para el motor:** Guardar sólo el patrón de navegación contextual y cierre explícito; imponer contraste, foco, Escape y tamaño de control como condiciones propias antes de implementarlo.

## Reproducción y estado de entrega

Verificación local, sin visitar otra vez los sitios ni generar votos:

```powershell
& ./.tools/node-v24.21.0-win-x64/node.exe --experimental-strip-types scripts/b3-reference-verify.ts
```

PASS: 21 referencias, 42 vínculos de captura, bytes y dimensiones, alcances y negativos conservados, cero votos nuevos. No convierte los textos de este informe en preferencias ni una captura en permiso. El corpus y el documento fuente se comprueban por SHA.

Se repitió la receta B3: [external-ref-post-01](../evidence/corrections/b3/external-ref-post-01/journal.json). Exportación, check, validación, build y replays de escenario, diseño, medios y bindings PASS. Tests: **382/383**; el único fallo conserva el bloqueo histórico H8 por LOCK_BROWSER_MISMATCH. No se presenta la suite como totalmente verde ni se reseallan locks. Se protegieron 2.815 archivos anteriores. El script de evidencia, incorporado después de esa receta, pasó check y validación de evidencia adicionales en el [recibo de seguimiento](../evidence/corrections/b3/external-ref-followup-01/journal.json).

La entrega de investigación se conserva en el commit **`7072725`**, sin cierre global de B3. El [recibo de bytes comprometidos](../evidence/corrections/b3/external-ref-followup-01/git-commit-proof.json) lee los objetos inmutables de ese commit y confirma las 61 capturas con recibo, el suplemento y los dos documentos fuente contra sus hashes. No es una nueva visita al sitio ni reproducción del estado de un proveedor; se verifica la evidencia archivada. La tarea revisora autorizada recibió el commit, la ruta del informe y los resultados para revisión independiente y propuesta del siguiente prompt.

La revisora respondió **PASS de evidencia representativa con límites**: repitió replay y check, confirmó 61/61 hashes locales y en Git e inspeccionó los alcances parciales y una muestra audiovisual. No declaró aprobación estética ni certificación de los vídeos. [Feedback conservado](b3-external-independent-review.md) y [prompt propuesto para aprobación humana](b3-external-proposed-prompt.md); la propuesta no se ejecuta en este seguimiento.

Este seguimiento atiende la revisión de referencias solicitada. **B3 en conjunto sigue pendiente** de la elección o rechazo estético explícito del usuario y del refuerzo oferta→medio señalado por la revisión independiente. No hay B4 ni aprobación humana supuesta.
