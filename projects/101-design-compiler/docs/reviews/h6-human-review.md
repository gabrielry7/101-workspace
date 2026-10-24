# H6 — revisión humana en curso

Fecha: 2026-10-12. Base técnica: `3f2d2f36e1617ae600237b6b289473e8209554bc`. Entrega histórica H6: `94e948b1939e0a5df9ed8b4a22ba714471b6b6db`, PASS independiente de infraestructura/experimento de laboratorio.

El usuario solicita revisar H6. Se presentan detección, crítica, reparación limitada, rollback y comparación humana. Se mantienen las correcciones esenciales H3/H4/H5 registradas; la navegación entre partes no equivale a aprobación visual de los candidatos actuales. Sólo notas para el prompt final.

## Explicación y evidencia actual

H5 propone composiciones; H6 comprueba resultados renderizados, localiza problemas, ensaya una reparación permitida, compara con la versión anterior y conserva/restaura. Nueve familias de evaluación no significan nueve evaluadores independientes calibrados. Hechos/capacidades/bindings/medios/geometría/accesibilidad/performance tienen checks locales; visual y diversidad por vista no se presentan como calidad humana medida.

Caso probado: ancho fijo causa overflow en móvil/escritorio; reparación cambia exclusivamente medida a fluid; nuevo render recupera lectura. Otra modificación vuelve a empeorar y se restaura el artefacto reparado previo, comprobando hash y render. Hay negativos de texto factual alterado, crédito eliminado y contraste insuficiente.

Mutator actual tiene una sola clase de reparación de anchura, no arreglador general ni crítico artístico LLM conectado. No cambia hechos/licencias para hacer desaparecer fallos. Comparación requiere las mismas rutas/viewports/política/contexto y rechaza errores nuevos en otra ubicación aunque el conteo total baje.

La fotografía original pesada se admite exclusivamente por política LAB. El perfil COMMERCIAL control rechaza ese home y devuelve NO_ACCEPTABLE_DESIGN; el umbral experimental de bytes no demuestra performance de campo ni estándar universal. LCP/INP/CLS/p75 no medidos. No se probaron videos o audio nuevos, ni calidad semántica del audiovisual mediante estas métricas raster.

27 vistas históricas comprueban baseline y defectos/reparación/restauración. Se decodifican PNG y recomputan estadísticas auxiliares; contar tinta/bordes no equivale a saber si el sitio es bello o armonioso. El medio original está excluido de esas estadísticas.

## Panel humano

24 comparaciones: parejas con misma ruta/contenido/viewport, A/B/empate/ninguna y razón opcional. Decisions se descargan localmente mediante acción explícita; no persistencia ni backend. Orden registrado; no prueba ciega perfecta, porque existen etiquetas internas.

Ocho decisiones históricas fueron TEST_SIMULATION para probar UI, no elecciones humanas. Preferencias siguen NOT_COLLECTED y selección NEEDS_HUMAN_REVIEW. El corpus recibido de 21 sitios de terceros no cuenta como votos sobre candidatos generados por H6 ni aceptación de sitios reales para H9.

## Implicaciones del feedback previo para las correcciones

No son nuevos requisitos H6 ratificados todavía; aplican las peticiones H3/H4/H5:

1. Aplicar checks técnicos y evaluación artística a muestras completas con audiovisual pertinente/autorizado; mantener resultados separados y no tratar un PASS técnico como belleza demostrada.
2. Evaluar calidad audiovisual, framing/adaptación y carga por viewport en las nuevas demos; el experimento sin video no cubre el uso audiovisual final.
3. Ampliar reparaciones mediante parámetros compartidos explícitos y pruebas before/after, sin código por cliente, pérdida de hechos o permiso inventado. No afirmar capacidad de reparación más amplia antes de probarla.
4. Conservar preferencias literales y alcance exacto; admitir ninguna y evitar convertir referencias parciales en aprobación de todo el diseño.
5. Definir cómo se usarán las revisiones para afinar criterio/selección y cómo se validará el flujo a escala. No inferir que 100.000 sitios puedan aprobarse automáticamente ni que deba haber revisión manual de cada sitio sin política acordada.

## Verificación durante esta revisión

12/12 pruebas dirigidas `tests/audit.test.ts` PASS con Node portable 24.21.0. La página local `/h6/` respondió 200. Tests consumen evidencias históricas y comprueban negativos; no hubo nueva recaptura, build completo, votos humanos, llamadas a proveedores o implementación de correcciones.

## Feedback humano: preferencias por aspecto y notas

El usuario propone segregar qué gusta más entre dos diseños por fuente, paleta y otros aspectos, calificar del 1 al 10 para expresar intensidad y señalar qué no gustó, por ejemplo distribución o audiovisual. Se registra para el prompt consolidado; no se cambia el panel ahora.

- H6-C01: añadir comparación por criterio además de A/B/empate/ninguna global. Criterios solicitados expresamente: tipografía, paleta, distribución/composición y contenido audiovisual. Otros candidatos a concretar: ritmo/espacio, identidad, navegación y movimiento cuando exista.
- H6-C02: permitir nota estética global de 1 a 10 por candidato para distinguir favorito relativo de diseño realmente aprobado. Ofrecer nota por criterio como detalle opcional y conservarla separada de la nota global. No transformar A/B en puntuaciones inventadas ni asignar nota por defecto.
- H6-C03: permitir aspectos que no gustaron, razón literal y observación por sección/elemento cuando pueda identificarse. Un rechazo de audiovisual puede referirse a calidad, pertinencia, encuadre, tamaño o integración; pedir precisión sin inventar la causa.
- H6-C04: permitir A/B/empate/ninguna y no evaluado/no aplicable por criterio. No puntuar audio/video que no está presente ni asumir que falta de voto equivale a rechazo. Una selección relativa no implica que alguna alternativa sea suficientemente buena.
- H6-C05: conservar contexto exacto de la evaluación: negocio/datos, candidato y versión, pareja, página/sección, viewport, capturas y material evaluado, fecha/autor y preferencias/notas explícitas. La misma persona puede valorar distinto mobile/desktop o el mismo patrón con medios diferentes.
- H6-C06: aprender preferencias condicionadas por contexto y criterio, manteniendo juicio global de coherencia. Preferir tipografía A y paleta B permite proponer una combinación nueva, pero exige render/evaluación propia; no declarar esa mezcla aprobada automáticamente ni reducir calidad a promedio de notas.

Propuesta de experiencia: nota global y decisión de pareja, luego motivos y detalle por aspecto si el usuario desea explicarlos. Los campos son opcionales/sin respuesta preseleccionada, salvo elección explícita. La escala debe mostrar anclas claras: bajo = no gusta, medio = aceptable/necesita cambios, alto = gusta mucho; el umbral de aceptación final todavía debe acordarse, no deducirse de una cifra sola.

La ficha por aspectos complementa checks técnicos y permisos; una nota estética alta no elimina un fallo factual o de derechos. Este feedback estético no cambia la decisión H0 de priorizar listado funcional/datos faltantes frente al score funcional.

Estado: feedback H6 específico recibido y registrado. Panel, persistencia/import de notas y aprendizaje por criterios pendientes de implementación posterior; no votos numéricos reales recogidos ni cambios funcionales/commit en esta revisión.
