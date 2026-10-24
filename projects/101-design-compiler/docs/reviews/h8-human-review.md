# H8 — revisión humana en curso

Fecha: 2026-10-12. Base técnica: `3f2d2f36e1617ae600237b6b289473e8209554bc`; corrección técnica auditada `ca1a86b048a5c92da9b5a44cb1de423b7c0e3cfd`.

El usuario solicita revisar H8. Se explica congelación, reconstrucción y vuelta a versión previa. Las correcciones H0–H7 se acumulan para el prompt final; no se modifica renderer, contratos, locks, activos ni evidencia histórica.

## Responsabilidad

Guardar una receta resuelta de una versión concreta: datos/plan, dirección artística y composición, medios/bytes/autorizaciones, componentes, herramientas/entorno y reportes que la comprobaron. Reconstruir consume esa versión; no vuelve a pedir creatividad al modelo, muestrear layouts o buscar medios. Una nueva propuesta/modificación es una nueva versión, no una sustitución silenciosa.

Rollback reconstruye un snapshot anterior en otra salida, sin sobrescribir workspace u originales. El permiso del archivo no se amplía al guardarlo; reproducción histórica no equivale a autorización vigente para cualquier nueva publicación.

## Qué existe y qué se demostró

Tres locks técnicos: dos composiciones H5 distintas del piloto restaurante y un híbrido H7 sin medios. Capturas históricas H8: 56 vistas; originales, dos reconstrucciones, rollback y regresiones deliberadas. Comparaciones válidas tienen HTML/DOM/geometría iguales y cero píxeles diferentes en el entorno controlado fijado.

Se comprobaron incompatibilidades de fuentes/herramientas, corrupción de copia de medio, import deliberado del sampler y cambio CSS que reduce texto a 8px. No son fallos de páginas reales en producción; controles prueban rechazo y regresión.

La primera revisión FAIL detectó auditoría técnica insuficientemente preservada dentro de los locks. La corrección guarda y valida reportes, contexto/policy/cobertura/evidencia y fuentes recuperables; reauditoría independiente PASS. Guardar literal approval sin evidencia ya no basta.

## Límites para la revisión humana

Reproducir exactamente un diseño no lo hace bueno. Los locks congelan los candidatos mínimos H5/H7; no satisfacen por sí solos la petición de páginas finales completas y casos reales. Contrato actual permite sólo lock técnico LAB, preferencias NOT_COLLECTED y production_ready=false. Las nuevas preferencias/ratings H6 requerirán representación versionada posterior sin falsificar aprobación de locks históricos.

Equivalencia demostrada en Windows/Node/Edge/fuentes locales fijados, no en cualquier computador o versión nueva. No hay dashboard `/h8/` en el sitio normal; es infraestructura de reconstrucción y evidencia. No se confunde fijación de artefactos con actualización factual, vigilancia de permisos o sistema operativo conectado.

## Implicaciones de las correcciones anteriores

Puntos derivados del feedback H0–H7, no decisiones específicas H8 ratificadas aún:

1. Congelar páginas completas una vez evaluadas técnicamente y con aprobación estética explícita, conservando qué se aprobó por página/viewport/aspecto y qué sigue pendiente.
2. Incluir nuevas composiciones/medios/versiones y demostrar reconstrucción fiel del resultado real; preservar los locks históricos como pruebas de laboratorio.
3. Distinguir recuperar versión, modificar datos, actualizar diseño y publicar. Reevaluar datos/derechos/condiciones aplicables en operaciones nuevas sin presentar un permiso antiguo como perpetuo o multicliente.
4. Conservar cada versión y permitir retorno verificable a la anterior; no relanzar generación probabilística durante reconstrucción.
5. Precisar entorno reproducible del producto final y probar portabilidad requerida. No prometer equivalencia universal desde las capturas de este laboratorio.

## Hallazgo de reproducción durante esta revisión

Pruebas dirigidas ejecutadas: `tests/lock.test.ts` y `tests/lock-files.test.ts`, Node portable 24.21.0: 14 tests, 13 PASS y 1 FAIL. El test de corrupción de evidencia esperaba LOCK_AUDIT_FILE_MISMATCH, pero la verificación se detuvo antes por LOCK_BROWSER_MISMATCH. No es un PASS actual de la suite dirigida.

El lock fija Edg/154.0.4258.62; `browserFingerprint()` detecta ahora Edg/155.0.4283.45, con exe/DLL/resources distintos. SHA exe esperado `d366716ba3cd2cc67d92d9b712b129fea4c8df769961d1e04b037ce034780ad0`, observado `4bb4545b4ab80a3cf463a588ce570ca42de38fe6db16e3baeb0798ac75b4648b`. Se contrastó usando la función del verificador y su raíz de instalación de Edge, no rutas relativas al repo. La incompatibilidad demuestra el bloqueo de entorno, no una nueva corrupción demostrada del paquete o pérdida de permisos.

La revisión independiente histórica PASS correspondía al entorno entonces fijado. No se degradó navegador, cambiaron pins, relajaron asserts o reescribió evidencia para ocultar la diferencia. No se ejecutó reconstrucción/captura nueva ni se afirma equivalencia bajo la versión actual.

Corrección técnica propuesta para el prompt final: preservar/materializar el entorno de render y auditoría de forma aislada/reproducible en vez de depender sólo del navegador local que se actualiza; distinguir reconstrucción exacta histórica de una migración intencional, versionada y reauditable al entorno nuevo. Adaptar pruebas para ejercitar el fallo de evidencia en su entorno de referencia y probar el cambio de navegador como caso separado, sin aflojar gates. El mecanismo y plataformas objetivo deben acordarse; no se promete portabilidad universal.

## Feedback humano y correcciones obligatorias

El usuario exige que los resultados finales guardados sean los que él escoge porque le gustan. Si no le gustan, debe iniciarse un proceso de iteración para identificar el motivo y corregirlo en el motor. Se registra como condición obligatoria para el prompt consolidado, sin ejecución de correcciones durante esta revisión.

- H8-C01: distinguir snapshots de intentos/pruebas del Design Lock final elegido. El lock de entrega debe vincular aceptación humana explícita del resultado exacto, además de evidencia técnica y permisos aplicables. No elevar una elección relativa, nota aislada, preferencia de componente o ausencia de feedback a aprobación global.
- H8-C02: si ninguno gusta o requiere cambios, no emitir un cierre estético final. Usar comparación por aspectos/notas/razones H6 para identificar tipografía, paleta, composición, audiovisual u otros motivos y convertirlos en objetivos concretos de la siguiente iteración.
- H8-C03: ajustar parámetros/reglas de la dirección y generación compartidas; ampliar componentes/gramática cuando el defecto revele una limitación del motor. No crear código específico de un cliente para aparentar que la plataforma lo resolvió. Renderizar propuestas completas nuevas y comprobar regresiones de otros casos.
- H8-C04: conservar trazabilidad de la iteración: versión propuesta, feedback exacto y alcance, cambios aplicados, nuevas vistas/checks y decisión humana posterior. Los intentos pueden conservarse como historial de prueba/aprendizaje sin etiquetarlos como diseño aprobado o entregable; evitar pérdida de la versión previamente aceptada.
- H8-C05: después de la elección, congelar esa composición/medios/contenido, aprobación y evidencia. Modificar el resultado aprobado produce una nueva versión; cambios relevantes de estética/contenido/medios requieren reevaluación y no heredan automáticamente la aprobación anterior.
- H8-C06: extender contratos de aceptación de forma versionada preservando lectores/evidencia históricos. Los locks actuales están explícitamente marcados LAB_TECHNICAL_LOCK_NOT_HUMAN_APPROVED; no cambiar su procedencia ni añadirles aprobación humana retroactiva. Una aprobación estética tampoco anula bloqueos técnicos, factuales o de permisos.

Flujo requerido: propuestas completas → comprobación técnica → evaluación humana por aspecto/global → si no gusta, corrección del motor y nuevas propuestas → elección/aprobación explícita → lock final recuperable. Preservar el último resultado aprobado durante iteración. Registrar costes/tiempos cuando medibles y los límites de la corrida; no asumir gasto ilimitado.

Estado: feedback H8 esencial ratificado y registrado; lock final con aprobación humana y ciclo iterativo pendientes de implementación. Bloqueo actual de entorno sigue documentado. Sólo notas, sin cambios funcionales ni commit.
