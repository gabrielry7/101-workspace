# H7 — revisión humana en curso

Fecha: 2026-10-12. Base técnica: `3f2d2f36e1617ae600237b6b289473e8209554bc`. Corrección técnica H7 auditada: `5f3ff3844ab9ec9b83da40c8eaf142147f83e593`.

El usuario solicita revisar H7. Se explica prueba multiarquetipo y límites. Se conservan requisitos previos H0–H6 para el prompt final; no se crean negocios/medios, cambian inputs, regeneran propuestas o implementan correcciones.

## Qué comprueba

Usar el mismo planner, gramática y componentes compartidos con seis casos sintéticos preparados antes de la prueba: hotel, dentista, servicio a domicilio, híbrido gimnasio/tienda, medio UNKNOWN y clasificación Unknown. Cinco emiten planes, el sexto conserva bloqueo. Diez propuestas finales de los cinco casos montan 15 rutas semánticas por conjunto de casos (duplicadas por dos variantes).

Hotel ejercita habitaciones/comodidades; dentista servicios/equipo/acerca; servicio a domicilio servicios/cobertura; híbrido membresías/clases/catálogo; medio UNKNOWN servicios sin renderizar el activo no autorizado. No son negocios ni servicios conectados reales.

La primera prueba planificó cinco casos, pero sólo uno pudo proyectarse con los componentes entonces disponibles. Cuatro fallos motivaron añadir colecciones de hechos y calendarios compartidos; después los cinco casos se renderizan. No se alteraron los inputs ni se crearon archivos de código por cliente. La cohorte ya se usó para ajustar la plataforma; comprobar generalización inédita después requiere casos nuevos independientes.

## Evidencia y alcance

60 vistas técnicas de candidatos (dos variantes, todas las rutas, desktop/móvil), tres negativos deliberados y dos vistas de índice. Negativos bloquean imagen no autorizada, texto cambiado y contraste insuficiente. La revisión inicial detectó main duplicado en el índice; corrección y reauditoría PASS preservan el fallo inicial.

Los cinco casos no tienen fotos elegibles; se muestran composiciones tipográficas con huecos conservados. En desktop difieren Flow/Rail; en móvil ambas apilan y no demuestran diversidad estructural móvil. No existe todavía la prueba estética multivertical con medios completos/preferencias humanas solicitada en H3–H6, ni evidencia de 100.000 sitios personalizados.

## Implicaciones del feedback previo para el prompt final

Son consecuencias de las correcciones H0–H6, no feedback nuevo H7 ratificado aún:

1. Probar el catálogo común de requisitos y diagnóstico de datos faltantes con tipos, funciones y sucursales distintos, incluidos híbridos y casos incompletos.
2. Añadir casos reservados que permitan comprobar comprensión contextual H1: categoría desconocida con ofertas/descripción suficientes frente a datos realmente insuficientes o contradictorios. No forzar clasificación de todo Unknown.
3. Probar una gramática ampliada y dirección contextual con muestras visuales completas y medios reales/autorizados adecuados, manteniendo controles sin medios/no autorizados.
4. Evaluar cada tipo y viewport con preferencias por aspecto y nota global según H6; no aplicar una estética gastronómica a todos los sectores ni un único promedio ocultando casos fallidos.
5. Conservar primera evaluación/fallos y corregir plataforma compartida; usar un grupo nuevo no utilizado para ajustes al volver a afirmar generalización inédita. No confundir reserva inicial con holdout aún intacto después de ajustar.

## Comprobación actual

8/8 pruebas dirigidas `tests/cohort.test.ts` y `tests/index-audit.test.ts` PASS con Node portable 24.21.0. `/h7/` responde 200. No nueva recaptura ni build; estas comprobaciones usan contratos/observaciones archivadas y controles negativos y no sustituyen QA integral nueva.

## Feedback humano y correcciones obligatorias

El usuario rechaza los ejemplos actuales como validación suficiente: exige páginas reales/completas para comprobar el motor, no mockups de baja calidad. Este juicio se registra sobre la suficiencia y calidad de la demostración presentada; no elimina los resultados técnicos históricos ni convierte fixtures en casos reales.

- H7-C01: validar el recorrido con páginas completas y representativas del resultado final, contenido suficiente, audiovisual real/autorizado y composición cuidada, desktop/móvil. Los fixtures mínimos permanecen como controles técnicos, no como demostración de calidad o cierre de producto.
- H7-C02: incorporar casos de negocios reales autorizados para demostrar comportamiento sobre datos reales y dejar explícito su origen, permisos y alcance. Si no están disponibles, conservar esa condición pendiente; una demo ficticia completa puede probar estética pero no sustituye un caso real. No inferir negocio/permiso de una URL ni inventar hechos para completar el caso.
- H7-C03: evaluar el conjunto de H0–H6 ya corregido en varios tipos de negocio, con referencias contextuales y preferencias/nota estética por aspectos H6. Una página que conserve bindings pero sea visualmente insuficiente no cumple la aceptación humana/producto solicitada.
- H7-C04: conservar primera evaluación y fallos, mejorar componentes/gramática comunes y repetir con nuevos casos no usados en ajustes. No corregir exclusivamente un fixture ni imponer el mismo estilo a todos los sectores.
- H7-C05: presentar evidencia verificable por página y viewport: render completo/capturas, contenido y medios, checks, problemas observados y evaluación humana. Separar aceptación visual, funcionamiento operativo y preparación de producción. Las operaciones pueden seguir en demo para la revisión estética acordada; no atribuir reservas/pagos/integraciones reales sin prueba.

El rechazo de suficiencia se aplica también a las demostraciones mínimas anteriores según lo señalado por el usuario; debe constar en el prompt consolidado. No se declara H7 aprobado humanamente por haber pasado tests. Tampoco se reclasifica todo PASS técnico histórico como falso: su alcance de laboratorio permanece documentado.

Estado: H7 actual no aceptado como validación visual/producto suficiente por el usuario. Corrección esencial registrada; casos reales autorizados, páginas completas y evaluación nueva pendientes. Sólo notas, sin cambios funcionales ni commit.
