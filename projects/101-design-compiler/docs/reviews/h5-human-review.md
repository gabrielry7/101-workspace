# H5 — revisión humana en curso

Fecha: 2026-10-12. Base técnica: `3f2d2f36e1617ae600237b6b289473e8209554bc`. Entrega H5 auditada históricamente: `58af61e34f15e38342acab5ea477da1fd5c2c667`.

El usuario solicita revisar H5 tras aportar su corpus de preferencias. Se explica implementación actual y se acumulan notas para el prompt final; no se regeneran diseños, consumen APIs, adquieren medios o implementan correcciones.

## Explicación para la revisión

H4 representa componentes en composiciones base. H5 introduce dirección artística declarativa y búsqueda contextual acotada: propone una idea global de diseño, explora composiciones/tokens compatibles, descarta inválidos/duplicados y presenta finalistas. No inventa hechos, edita permisos, genera código libre o decide por sí solo que un diseño es bello.

Propuestas actuales: typographic-pause (tipografía dominante/pausas), balanced-dialogue (texto/medio adyacentes), indexed-field (navegación/campo compacto). Fueron redactadas por el modelo activo en la sesión de implementación, no una llamada a un proveedor API configurado. Prompt/context/output/procedencia se guardan y cotejan. Build/replay consumen ese registro, no producen dirección artística nueva para cada negocio.

## Lo demostrado

- 3 propuestas, 24 intentos baratos, 6 planes únicos y 4 finalistas.
- Gramática pequeña: Flow/Rail y Sequence/Split, con tokens acotados de paleta, tipografía, ritmo, escala y medios. No 1.000 layouts ni prueba de 100.000 sitios diferentes.
- Prioridades de muestreo condicionadas por datos/medios, heurísticas sin calibración empírica de preferencias; la aleatoriedad no prueba calidad.
- Finalistas conservan las dos rutas, contenido escaso y foto atmosférica autorizada del mismo fixture. No muestran todavía la demo completa solicitada durante H4.
- Capturas históricas: 16 vistas, más 28 comprobaciones responsive/texto. Menor diversidad móvil declarada. PASS independiente técnico de laboratorio, no aprobación estética humana.
- Los finalistas se escogen por diversidad estructural, no por ranking humano de belleza; no se declara vencedor visual.

## Corpus recibido y límites

La fuente histórica de H5 registra referencias MISSING y preferencias NOT_COLLECTED. El documento con 21 preferencias aportado ahora está disponible como texto, pero no se ha inspeccionado visualmente ni incorporado al contexto/motor H5. No modificar la procedencia histórica para afirmar que esos diseños usaron referencias que llegaron después. Incorporar referencias en ejecuciones nuevas versionadas cuando se corrija.

La información de costos/tokens de la sesión original continúa null; cero gasto/API nuevos no implica costo histórico total cero. Runtime comercial ausente. El original H3 pesado es excepción de laboratorio y su permiso interno no autoriza derivados.

## Implicaciones del feedback H3/H4 para el prompt final

Estas notas aplican requisitos ya expresados por el usuario. Tras esta explicación, el usuario ratifica que estas correcciones y complementos son vitales y deben aplicarse correctamente al motor final. Se convierten en criterios obligatorios del prompt consolidado, manteniendo el acuerdo de tomar notas durante la revisión y aplicar las correcciones después:

1. Dirección artística contextual orientada por referencias/preferencias trazables y material audiovisual pertinente. Separar preferencias del usuario de observaciones nuevas y de autorización de activos.
2. Generación sobre una gramática ampliada y probada, con opciones estructurales y móviles reales; no contar cosmética, seeds o combinatoria teórica como personalización demostrada.
3. Evaluar finalistas con el mismo contenido suficientemente rico y medios autorizados, en muestras con aspecto final aunque las operaciones sean demo.
4. Precisar cómo se obtienen propuestas nuevas: productor LLM autorizado, contexto/contrato, procedencia y costo/tiempo cuando medibles. No describir recorder de sesión como API o servicio de generación autónoma ya conectado.
5. Selección por validez/diversidad/coherencia contextual y revisión estética humana, admitiendo que ninguno sea aceptable; usar feedback para ajustar criterio sin fabricar métricas.

## Criterios obligatorios para la corrección posterior

Prioridad: esencial para el motor final, no mejora cosmética opcional. No tratar el PASS técnico histórico como aceptación de estos requisitos nuevos.

- H5-C01 — Contexto artístico: una ejecución nueva debe identificar los datos y medios autorizados del caso, referencias/preferencias efectivamente consultadas y alcance de aprobación de cada referencia. La dirección propuesta debe explicar cómo sus decisiones responden a ese contexto. Incorporar corpus mediante artefactos nuevos; no reescribir provenance histórico.
- H5-C02 — Coherencia: dirección artística común gobierna jerarquía, tipografía, paleta, ritmo, navegación, medios y motion cuando corresponda. Verificar el resultado completo; mezclar piezas válidas de manera independiente no basta para demostrar armonía.
- H5-C03 — Variedad: ampliar y probar gramática sobre el runtime compartido, sin forks por cliente. Demostrar cambios estructurales con contenido suficientemente rico y medios apropiados, también en móvil. Cambios de colores, seeds, número de intentos o combinatoria no acreditan por sí solos diversidad. Umbrales y tamaño de muestra deben acordarse/calibrarse, no inventarse.
- H5-C04 — Generación nueva: documentar y probar el productor de propuestas autorizado que se usará en el flujo objetivo. Separar producción creativa, búsqueda y replay. Una ejecución con JSON grabado acredita reproducción, no una nueva llamada/generación automática. Conservar versiones, contexto, output, fallos y costo/tiempo cuando disponibles; desconocidos explícitos.
- H5-C05 — Audiovisual y demo final: conectar con la corrección prioritaria H3 y demostrar una página visualmente completa, con archivos inspeccionados/autorizados y tratamiento permitido. La misma base de contenido/medios en cada comparación. Acciones pueden ser de demostración, sin afirmar backend ni autenticidad documental del stock.
- H5-C06 — Selección y revisión: bloquear pérdida de hechos, módulos, sucursal, permisos, navegación o legibilidad; comparar propuestas válidas por diversidad y criterio contextual. Mantener evaluación humana independiente de checks técnicos y registrar preferencias con contexto exacto. Admitir ninguna aceptable, reparar/reintentar dentro de presupuesto y no aprobar por falta de alternativas.
- H5-C07 — Evidencia de cierre: exportar contratos cuando cambien, ejecutar tests/check/validación/build/replays pertinentes y auditar bindings/medios. Inspeccionar candidatos nuevos en navegador, conservar capturas/observaciones desktop/móvil y comprobar preservación histórica. Presupuestar intentos y medir costo/tiempo reales cuando medibles. No declarar escala de 100.000 páginas, belleza o aceptación humana a partir de ejemplos insuficientes.

Estos criterios requieren ejecución posterior y evidencia propia. Durante la revisión se documentan; no se conectan proveedores, implementan funciones o contratan servicios. No hay autorización de gastos nuevos inferida del reconocimiento de prioridad.

## Verificación dirigida durante esta revisión

12/12 pruebas `tests/design.test.ts` PASS con Node portable 24.21.0. Incluyen generación/selección acotada, procedencia/replay, contexto/derechos/bindings, presupuesto, diversidad no cosmética y DOM archivado. No es nueva recaptura ni build completo; se preservan artefactos históricos.

Estado: feedback H5 ratificado por el usuario como esencial; correcciones obligatorias registradas para el prompt final. Implementación y verificación de esas correcciones pendientes. Sólo notas y corpus recibido, sin cambios funcionales ni commit.
