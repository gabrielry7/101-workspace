**Assessment A — juicio visual independiente del detector**

Las cuatro condiciones son variaciones de una misma página editorial. Conservan contenido, módulos, medios y composición; cambian jerarquía tipográfica, legibilidad y espaciado. B/D mejoran la lectura, pero ninguna condición demuestra todavía páginas finales ricas, identidades ampliamente distintas o buen audiovisual.

Hay coherencia visual: serif expresiva, fondo cálido, reglas finas y enlaces convencionales. La especificidad pertenece al **laboratorio**. Restaurante y hotel siguen siendo intercambiables como plantillas informativas: el primero aporta una foto atmosférica; el segundo, principalmente texto y avisos. Esto puede servir para comparar refinamientos acotados del motor, pero no valida su capacidad de producir sitios finales completos.

El juicio se formó sin resultados del detector ni informes anteriores. La comparación `/quality/` reveló automáticamente los proveedores correspondientes a A–D en su introducción; por ello no hubo cegamiento por herramienta.

**Heurísticas Nielsen**

Puntuación de la familia informativa, contrastando A–D y recorriendo D en vivo. No es una media de puntuaciones técnicas. El formulario opcional de preferencia no se envió ni forma parte de esta puntuación.

| # | Heurística | Nota | Razón |
|---|---|---:|---|
| 1 | Visibilidad del estado | 3/4 | La navegación marca la página actual y el destino cambia correctamente. No hay procesos asincrónicos relevantes que evaluar. |
| 2 | Correspondencia con el mundo real | 2/4 | `amenities`, `rooms`, `fixture`, `Alcance` e identificadores internos exigen interpretar el modelo del laboratorio. Habitaciones termina bajo el título genérico `Oferta`. |
| 3 | Control y libertad | 3/4 | Se puede volver a Identidad y a Comparar finalistas mediante enlaces claros. No se observan estados que atrapen al visitante. |
| 4 | Consistencia y estándares | 3/4 | Lenguaje visual y comportamiento estables. La jerarquía título/descriptor cambia entre home y páginas interiores; las etiquetas mezclan inglés y español. |
| 5 | Prevención de errores | 3/4 | Se distingue lo ficticio, lo atmosférico y lo no operativo. El crédito y la falta de respaldo USDA/ARS permanecen visibles. |
| 6 | Reconocimiento frente a recuerdo | 3/4 | Dos o tres destinos visibles y estado activo reducen memoria. La equivalencia `rooms` → `Oferta` añade una traducción mental innecesaria. |
| 7 | Flexibilidad y eficiencia | n/a | Demo Persuade/Read sin tarea repetitiva que necesite aceleradores o personalización. |
| 8 | Estética y minimalismo | 2/4 | Hay orden y poco ruido, pero títulos y vacíos ocupan más atención que la información útil. La escasez de contenido limita la evaluación de jerarquía real. |
| 9 | Recuperación de errores | n/a | Las páginas evaluadas no producen errores de entrada ni contienen un flujo operativo. No se penaliza la ausencia deliberada de compra o reserva. |
| 10 | Ayuda y documentación | 3/4 | Los límites documentales y la trazabilidad están presentes y próximos. Parte de su vocabulario sigue orientado al constructor. |
| **Total** | | **22/32 — 68,75 %, Aceptable** | Base funcional para una demo; no certifica un sitio final. |

**Carga cognitiva**

| Ítem | Resultado | Motivo |
|---|---|---|
| Foco único | Pass | El visitante puede leer y elegir una página sin interrupciones. |
| Fragmentación | Pass | Los grupos principales contienen de uno a tres elementos; habitaciones tiene dos objetos. |
| Agrupación | Pass | Proximidad, reglas y bloques separan navegación, contenido y restricciones. |
| Jerarquía visual | **Fail** | El título del fixture domina la pantalla; en hotel la información que ayudaría a comprender el caso queda subordinada al estado experimental. |
| Una cosa a la vez | Pass | No hay decisiones simultáneas obligatorias en los fixtures. |
| Opciones mínimas | Pass en fixtures | Restaurante muestra dos destinos; hotel, tres. |
| Memoria de trabajo | Pass | La navegación permanece visible y señala la ubicación. No hace falta recordar datos para completar el recorrido informativo. |
| Revelación progresiva | Pass | La trazabilidad extensa está en un desplegable. |

**1 fallo de 8: carga cognitiva baja.** Esto se debe en parte a la poca información; no equivale a utilidad alta.

En la comparación, el grupo **Qué influyó** sí presenta **seis casillas visibles**. El selector de preferencia ofrece seis resultados posibles —A, B, C, D, Empate y Ninguna— y el de nota diez, pero estas opciones se revelan al abrir los controles nativos. Los grupos de comparación visual tienen cuatro variantes por caso y se mantienen dentro del umbral.

**Recorrido emocional**

La entrada transmite calma y control. En restaurante, el pimiento crea el único pico sensorial evidente; las advertencias posteriores delimitan correctamente su significado. Al entrar en la oferta, el recorrido pierde interés porque solo aparece un ítem de prueba sin desarrollo. El final aporta tranquilidad sobre restricciones y permite volver a comparar, aunque no entrega una conclusión memorable sobre el restaurante.

Hotel carece de ese pico visual. El título experimental y los avisos establecen honestidad, pero las habitaciones sintéticas y la frase del patio no construyen una experiencia que se pueda imaginar. Es un tono apropiado para revisar contratos de un laboratorio; queda lejos del objetivo de un sitio final atractivo.

**Fortalezas**

- La separación entre fotografía atmosférica y evidencia del negocio es explícita. Se conservan contexto, autoría Steve Ausmus, USDA Agricultural Research Service y ausencia de respaldo.
- La navegación es visible, convencional y funcional. Verifiqué enlaces de ida, páginas secundarias y retorno a la comparación.
- La familia mantiene un sistema visual reconocible. B/D aumentan claramente la comodidad de lectura de créditos y restricciones sin introducir ornamentación gratuita.

**Problemas prioritarios**

1. **P1 — Etiquetas del modelo interno dificultan comprender el destino.**  
   Evidencia: `/quality/hotel-d/`, navegación `amenities` y `rooms`; `/quality/hotel-d/habitaciones/`, H1 `Oferta`, `Alcance: h7-synthetic-hotel`. También aparece un identificador de sucursal en el menú del restaurante. Se ve en desktop y mobile de todas las condiciones correspondientes.  
   Fuentes: `src/components/composition/DesignComposition.astro`, `FactCollection.astro` y `OfferingCollection.astro`.  
   **Propuesta acotada:** usar etiquetas de presentación `Comodidades` y `Habitaciones`, y un título de página que coincida con el destino. Mantener identificadores técnicos dentro de Trazabilidad. Conservar todos los hechos sintéticos y las restricciones.  
   **Comando sugerido:** `$impeccable clarify`.

2. **P2 — C/D consumen más altura móvil para la misma navegación.**  
   Evidencia: `restaurante-{c,d}-mobile-home.png` apila los dos destinos que A/B presentan en una fila; `hotel-{c,d}-mobile-home.png` reparte tres destinos en dos filas. En restaurante D, el contenido y la imagen comienzan aproximadamente una fila de navegación más abajo que en B. En las secundarias D ocurre lo mismo.  
   Fuente visual: `docs/evidence/design-evaluation/iteration-1/`; componente `.site-nav` y reglas compartidas en `src/design/styles.css` / `src/composition/styles.css`.  
   **Propuesta acotada:** ajustar separación y relleno horizontal para conservar una fila cuando los rótulos quepan, manteniendo objetivos táctiles de al menos 44 px. Permitir salto cuando el ancho o el texto realmente lo exijan.  
   **Comando sugerido:** `$impeccable adapt`.

3. **P2 — La escala tipográfica favorece el rótulo experimental más que la lectura útil.**  
   Evidencia: `hotel-*-desktop-home.png` dedica tres líneas monumentales al nombre del fixture; `restaurante-a-mobile-home.png` deja créditos y restricciones sensiblemente menores que B/D. En hotel, la entrada tiene poco contenido más allá del gran título y los avisos.  
   Fuentes: `.identity`, `.eyebrow`, `figcaption` y `.audit`; `src/components/composition/Identity.astro` y estilos compartidos.  
   **Propuesta acotada:** conservar serif, paleta y copy; reducir la escala del título largo del laboratorio y su separación, y adoptar la lectura más cómoda de B/D para créditos y restricciones. No agrandar todo indiscriminadamente: el objetivo es una proporción más útil entre título, contenido y límites.  
   **Comando sugerido:** `$impeccable typeset`, seguido de `$impeccable layout` si aún sobra altura.

No encontré P0 en el recorrido informativo observado.

**Personas y señales de riesgo**

- **Jordan, primera visita:** entiende que es ficticio, pero `rooms` → `Oferta` y los identificadores de alcance le obligan a descifrar términos antes de comprender qué página está leyendo. El siguiente paso físico es claro; el significado del contenido, menos.
- **Casey, móvil distraído:** tiene pocos destinos y enlaces legibles, pero C/D le hacen desplazar más para llegar al mismo contenido. Los créditos de B/D se leen mejor que A, con el coste razonable de más longitud.
- **Riley, evaluador deliberado:** puede verificar límites y navegar sin promesas operativas engañosas. Su principal señal de alerta sería interpretar estas muestras mínimas como prueba de riqueza, diversidad o capacidad audiovisual general del motor.

**Diferencias A–D y observaciones menores**

- **A:** la presentación más compacta; descriptor en mayúsculas antes del título y texto auxiliar más pequeño. Móvil utiliza mejor el ancho de navegación.
- **B:** título antes del descriptor en home y cuerpo auxiliar mayor. Es la combinación más equilibrada de legibilidad y altura móvil dentro de estas muestras.
- **C:** mantiene el descriptor superior de A, amplía texto auxiliar y aumenta el espacio ocupado por navegación móvil. El cambio no produce un carácter visual nuevo.
- **D:** se aproxima a B en jerarquía y lectura, y a C en navegación móvil. No se aprecia un beneficio estético adicional claro frente a B.
- En páginas interiores, B/D no trasladan de manera uniforme la inversión título/descriptor de home.
- El estado actual usa peso tipográfico y conserva el subrayado; no depende únicamente de color.
- No observé un problema visual de desbordamiento en las capturas revisadas.
- Los títulos de las pestañas repiten `candidate-01 · laboratorio QUALITY`; identificar caso y página ayudaría al comparar varias pestañas.
- Hotel no tiene medios elegibles. Ese hueco debe seguir visible: no recomiendo sustituirlo por stock, generar pruebas del establecimiento ni inventar disponibilidad.

**Suficiencia de la muestra**

Las muestras bastan para observar efectos de legibilidad, jerarquía local y navegación bajo contenido constante. No bastan para validar páginas finales ricas, diversidad de composición, personalidad por negocio o audiovisual: solo hay una foto atmosférica autorizada, ningún medio hotelero, un ítem de menú, dos objetos de habitación y una frase de comodidad. La igualdad estructural permite aislar refinamientos, pero precisamente impide demostrar una generación de mundos visuales distintos.

Preguntas útiles para la síntesis: ¿la aceptación inmediata se limita a mejorar lectura de este laboratorio, o pretende demostrar ya sitios finales? ¿Debe priorizarse la legibilidad de B conservando su navegación compacta? ¿Qué evidencia futura distinguirá variedad real de simples cambios tipográficos?

**Cobertura y límites**

- **28 capturas vistas:** las 16 home de restaurante/hotel × A–D × desktop/mobile; y 12 secundarias, A/D × desktop/mobile para menú del restaurante, habitaciones y comodidades del hotel.
- Capturas comprometidas: desktop 1280 × 900 y móvil 390 × 844; alturas completas variables. No cambié el viewport.
- **Browser 2, tab nuevo ID `1`**, creado exclusivamente para Assessment A y **cerrado al terminar**. No reutilicé ni cerré tabs ajenos.
- Navegación real: comparación → restaurante D → oferta → comparación → hotel D → habitaciones → comodidades. Destinos y estado actual confirmados mediante snapshots; comparación, restaurante home/oferta y hotel home inspeccionados también visualmente en vivo.
- Viewport live leído: **1280 × 720**. La cobertura móvil procede de las capturas comprometidas.
- Sin detector, auditorías previas, informes de B ni revisión independiente. Sin overlay, mutación DOM, cambios de código, archivos, assets o evaluaciones guardadas.
- No inicié servidor ni generé snapshot. El coordinador comunicó comprobación de frescura; no la presento como una verificación de hashes hecha por mí.
- No probé lector de pantalla, zoom, red lenta, envío del formulario de preferencia ni estados de error. La ausencia de compra/reserva es una restricción deliberada y no se contabiliza como fallo.
