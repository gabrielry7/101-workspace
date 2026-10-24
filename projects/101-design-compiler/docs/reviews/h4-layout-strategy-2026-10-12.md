# H4 — estrategia de diversidad y demostración estética

Consulta: 2026-10-12. Investigación para revisión humana; no implementación, compra, captura de corpus, adquisición de medios, entrenamiento o nuevo hito.

## Pregunta y recomendación

El usuario solicita una muestra que permita evaluar la apariencia final y cuestiona escalabilidad de sólo tres variantes. Compara biblioteca de 1.000 layouts por feeling con generación probabilística bajo restricciones.

Recomendación de ingeniería para 101: segundo camino orientado por biblioteca curada de referencias/patrones y componentes compartidos. La parte curada aporta criterio visual y ejemplos; la generación explora organización contextual; los validadores controlan hechos/derechos, geometría, responsive, navegación y peso; aceptación estética requiere comparación humana. Esta recomendación es una inferencia, no ganador probado por cifras de mercado ni decisión humana ya aceptada.

## Comparación razonada

| Enfoque | Ventajas | Límites |
|---|---|---|
| Layouts completos prediseñados | Calidad curada y previsualizable; reproducción sencilla; fallos conocidos y testables | Mantener muchos layouts y variaciones de contenido/móvil cuesta; catálogo finito puede repetir estructura; etiquetas de feeling no prueban adaptación al contenido |
| Generación probabilística sin gramática suficiente | Gran espacio potencial de propuestas | Variación no garantiza belleza, coherencia, validez ni rendimiento; reintentos pueden ser caros; riesgo de converger siempre en lo mismo o producir ruido |
| Generación contextual acotada + corpus/gramática curados | Reutiliza componentes/criterio, adapta estructura a datos/medios, filtra y congela resultado | Requiere ampliar/probar gramática, calibrar preferencias, comprobar diversidad efectiva y costo. No promete unicidad de 100.000 páginas |

Simetría, blanco y proporciones son objetivos artísticos/contextuales, no máximos universales. No colisión debe distinguir colisión accidental de superposición deliberada y permitida. Diseño elegido se guarda resuelto: probabilístico al explorar, determinista al reproducir.

## Ejemplos documentados en productos

- [Wix templates](https://www.wix.com/website/templates): anuncia más de 2.000 plantillas. Confirma catálogo comercial, no diversidad estructural de todas las plantillas ni causalidad de éxito.
- [Wix AI](https://www.wix.com/ai-website-builder): ofrece generación y edición con AI. Ambos caminos conviven en el producto; no se atribuye algoritmo interno de restricciones que la documentación no demuestra.
- [Framer AI](https://www.framer.com/ai/): describe generación de páginas/secciones editables y refinamiento de layouts, tipografía, componentes y breakpoints. Es documentación del proveedor, no benchmark independiente de calidad frente a plantillas.
- [Webflow AI](https://help.webflow.com/hc/en-us/articles/38840145286035-Build-a-site-with-Webflow-s-AI-site-builder): genera estructura/páginas y reutiliza Flowkit, patrones de componentes y tokens. Ejemplo de generación sobre base estructurada; no prueba equivalencia con el motor propuesto 101 ni mayor éxito comercial.

## Investigación primaria pertinente

- [GRIDS, CHI 2020](https://arxiv.org/abs/2001.02921): optimización MILP para layouts de grilla diversos, alineación/agrupación/posicionamiento; estudios de ratings N=13 y diseño N=16 aportan evidencia en etapas tempranas. No estudia desplegar 100.000 sitios completos ni gana una comparación contra 1.000 plantillas comerciales.
- [DesignScape, CHI 2015](https://www.dgp.toronto.edu/~donovan/design/designscape.pdf): sugerencias y refinamientos usando ejemplos y muestreo de estilos; estudios A/B comparan diseños asistidos con una interfaz baseline. Apoya estudiar ejemplos + exploración; alcance de diseño gráfico/estudios acotados, no éxito comercial de website builders.
- [LayoutDM, CVPR 2023, Inoue et al.](https://openaccess.thecvf.com/content/CVPR2023/html/Inoue_LayoutDM_Discrete_Diffusion_Model_for_Controllable_Layout_Generation_CVPR_2023_paper.html): generación de bounding boxes con restricciones opcionales de posición/tipo/tamaño. No equivale a un renderer HTML/CSS accesible, responsive y licenciado. No se propone incorporar modelo entrenado ni dataset sin evidencia de necesidad/derechos.

No se encontró en esta revisión un benchmark comparable que permita declarar un ganador global por ventas, aceptación humana, unicidad y costos sobre sitios completos. Las fuentes muestran uso comercial e investigación de ambos caminos; no resultados medidos de 101.

## Cómo decidir para 101

Primero producir una demo visual completa con el mismo contenido/medios permitidos por cada comparación. Comparar familias estructurales y estilos, desktop/móvil y contenido variable. Evaluación humana puede elegir ninguno. Medir candidatos aceptados, parecidos/repetición real, errores, intentos, tiempo y costo observado. No convertir combinatoria teórica, raster o cambios de color en evidencia de calidad/escala.

El tamaño del catálogo o gramática inicial y los umbrales de diversidad/calidad requieren acordarse; no se fijan 1.000 layouts o un nuevo número arbitrario como condición validada. La demo estética no habilita operaciones comerciales ni convierte stock en evidencia del negocio. El audiovisual debe tener función, pertinencia, permiso de uso y de transformación y un presupuesto de carga.
