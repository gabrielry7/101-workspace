# H4 — revisión humana en curso

Fecha: 2026-10-09. Base técnica `3f2d2f36e1617ae600237b6b289473e8209554bc`; entrega histórica H4 `65877747aa526d7e6711142a3df6c6e8e5deca0b`.

Tras la revisión H3 el usuario solicita continuar con la siguiente pregunta. Se presenta H4 como siguiente parte secuencial: composición visual. No se interpreta como aprobación global H3 ni ejecución del prompt de correcciones. El audiovisual prioritario y los conectores pendientes siguen registrados en H3.

## Qué se presenta

H4 distribuye contenido y medio en tres composiciones usando el mismo SitePlan, mismos hechos y componentes compartidos: Editorial (secuencia vertical y pausas amplias), Split (texto/imagen en dos campos desktop), Rail (navegación lateral y jerarquía compacta). En móvil se reorganizan sin forzar columnas. No hay código o template específico por cliente/sector.

Las rutas de laboratorio `/h4/editorial/`, `/h4/split/`, `/h4/rail/` conservan identidad en `/` lógico y la oferta de sucursal en su ruta semántica. Dos hechos: nombre ficticio e ítem de menú de prueba. Medio único atmosférico H3; no se inventan platos, precios, horarios, sede o acciones para llenar el diseño. El paquete de datos escaso limita la revisión a estructura, no una página completa de restaurante.

## Evidencia y límites

H4 archivó 12 vistas de navegador (tres variantes, dos rutas, escritorio/móvil), con checks de bindings, medios, navegación, foco, contraste y geometría. La fuente fotográfica pesada es excepción de laboratorio; no acredita rendimiento comercial. Runtime comercial ausente: renderer Astro local compartido.

En esta revisión pasan 7/7 tests dirigidos `tests/composition.test.ts`, incluyendo auditoría de DOM archivado e invariantes negativos. No es nueva recaptura de las 12 vistas ni nuevo build; se mantienen HTML/capturas/evidencia históricos.

## Pregunta humana de esta parte

Comparar organización visual, lectura, navegación y espacio reservado a medios, manteniendo los datos iguales. Registrar preferencias y problemas concretos sin afirmar aprobación global o convertir este fixture escaso en prueba de calidad de un sitio completo. No realizar adquisiciones ni ajustes visuales durante la toma de notas.

## Feedback humano del 2026-10-12 y correcciones para el prompt final

El usuario indica que esperaba una muestra visual completa, con contenido y audiovisual suficientes para mostrar el aspecto de una página final, aunque las operaciones no funcionen. Las vistas escasas actuales no satisfacen ese propósito. Cuestiona tres diseños como fundamento de personalización a escala de 100.000 páginas. Plantea biblioteca de aproximadamente 1.000 layouts realmente distintos etiquetados por feeling o generación probabilística con límites rigurosos y solicita recomendación y evidencia externa.

- H4-C01: preparar una demostración estética completa y representativa, con contenido suficiente y archivos audiovisuales reales/autorizados adecuados al concepto. Puede ser un prototipo sin backend, con acciones claramente de demostración. No presentar datos sintéticos como negocio real ni stock como prueba documental. Necesidad de materiales auténticos conserva bloqueos; evidencia histórica H3/H4 no se reescribe para aparentar cobertura.
- H4-C02: separar prueba técnica mínima de composición de aceptación estética de una página final. El PASS histórico del laboratorio no sustituye esta revisión humana. Estado estético de la muestra actual: insuficiente para el objetivo de revisión; no aprobación humana.
- H4-C03: ampliar diversidad estructural real: jerarquía, organización/secuencia, navegación, proporciones, relación texto/medios, ritmo, densidad y responsive. No contar cambios cosméticos o seeds como nuevos diseños. Comprobar parecidos entre sitios y diversidad móvil; tres variantes H4 y cuatro topologías H5 no demuestran escala de 100.000 diseños personalizados.
- H4-C04: catalogar carácter/feeling mediante criterios de diseño concretos y referencias con procedencia: elegante/editorial/cálido/expresivo/etc., sin reducir cada sector a un estilo fijo. La propuesta de moods y gramática debe ratificarse; no se ha construido una biblioteca de 1.000 layouts.
- H4-C05: el usuario respalda construir un vocabulario de diseño rico y ofrece aportar numerosas páginas que considera buenas, junto con las referencias ya mapeadas. Recibir URLs y, cuando sea posible, observaciones literales de qué le gusta; inventariar las referencias existentes distinguiendo enlaces conocidos de recursos efectivamente disponibles/inspeccionados. Conservar origen, fecha de observación, rasgos compositivos y preferencia humana explícita. Usar referencias para orientar familias y evaluar demos completas; no inferir permisos de reutilización de fotos, código, logos o datasets por recibir un enlace.
- H4-C06: corpus recibido del usuario el 2026-10-12, [21 referencias y preferencias](../../data/reference/design/101_referencias_aprobadas_completas_v01.md). Integrar al futuro registro visual con 18 valoraciones globales y 3 parciales, intensidad cualitativa, observaciones positivas/negativas y alcance exacto. Mantener referencias negativas fuera de la lista positiva. No convertir razones no especificadas en atributos inventados ni equivaler aprobación estética a rendimiento/a11y/derechos. Registrar inspección futura por fecha y viewport; la aportación del documento no es inspección actual de cada sitio.

Recomendación de esta revisión, todavía NO RATIFICADA: generación contextual probabilística sobre una gramática compartida y componentes probados, orientada por corpus/familias artísticas curadas, con restricciones verificables y revisión humana. Las referencias no son una lista cerrada de páginas para clonar. La simetría es una elección estética; no una restricción universal. Evitar colisiones no intencionales, texto ilegible y pérdida de contenido/permisos sí es obligatorio; overlays deliberados necesitan condiciones de legibilidad y permisos.

Investigar ambos enfoques no prueba cuál tiene más éxito comercial global. La comparación y fuentes oficiales/primarias se conservan en [estrategia de layouts](h4-layout-strategy-2026-10-12.md). H5 tiene sampler y dirección registrada, pero gramática finita pequeña y pesos heurísticos sin calibración humana. La propuesta ya coincide con la intención de V0.2; falta demostrar calidad y amplitud suficientes.

Respuesta posterior: el usuario expresa «Exacto» sobre construir vocabulario rico con referencias/componentes/reglas y comprobar calidad/variedad en muestras completas; aporta el documento de referencias el 2026-10-12. Se registra respaldo de ese criterio y recepción del corpus textual. No equivale a aprobación de la muestra actual, todos los detalles del motor o permiso para comenzar la implementación durante la revisión.

Estado: feedback H4 registrado; prototipo actual no aceptado como demostración estética suficiente. Criterio de vocabulario y referencias respaldado; corpus textual recibido, inspección visual actual/detalles/demos pendientes. Sólo documentación para prompt final, sin cambios funcionales ni commit.
