# Pipeline 101 — versión 2.1.1

Parche de consistencia sobre el documento 2.1 y los contratos del paquete 2.0. Conserva las siete fases, las cuatro capas, la dirección de diseño y el piloto N0. No modifica ni certifica el repositorio de 101.

## Qué abrir

**`Pipeline_101_restaurantes_v2.1.1.md`** es el documento principal completo. Sustituye al 2.1 como especificación vigente dentro de esta entrega.

**`REGISTRO_DE_CAMBIOS.md`** explica las correcciones y sus pruebas. **`MIGRACION_2_1_1.md`** describe qué adaptar al integrar los contratos y por qué un `PASS` antiguo no migra mediante un cambio de nombre.

**`PRUEBAS_DE_ACEPTACION.md`** es el índice generado de los 84 casos del producto. Bajo los supuestos propuestos del piloto, 61 están dentro del alcance y 23 fuera. Hay 59 casos con obligaciones previas y 10 con obligaciones posteriores; estos grupos se solapan. No son resultados de ejecución.

## Qué cambia

G04a y G04b existen ahora tanto en el documento como en los esquemas, catálogos, ejemplos y comprobadores documentales. La clasificación del piloto se deriva de condiciones y momentos explícitos. La recuperación conserva datos/derechos actuales, también en un sitio estático. La seguridad no desaparece por no tener servidor de pedidos. La alternancia entre secciones y las dos líneas de descripción son guías, no garantías universales. La revisión humana se invalida por sus entradas visuales y su ámbito, no únicamente por composición.

## Contenido

```text
Pipeline_101_restaurantes_v2.1.1.md   Documento principal
REGISTRO_DE_CAMBIOS.md              Correcciones y trazabilidad
MIGRACION_2_1_1.md                   Adaptación e incompatibilidades
PRUEBAS_DE_ACEPTACION.md             Índice generado por caso y compuerta
APLICABILIDAD_PILOTO.json            Selección condicional y sus huellas
VALIDACION_ENTREGA.json             Resultado de los controles documentales
VALIDACION_REGRESIONES.json         Resultado de 17 regresiones documentales
DIFF_2.1_A_2.1.1.patch               Diferencia exacta del documento
SHA256SUMS                          Integridad de los archivos entregados
requirements.txt                   Dependencia del validador
especificacion/
  compuertas.json                   18 compuertas, controles y reparación
  pruebas_aceptacion.json           84 casos, todos NOT_RUN
  contratos.schema.json            Siete tipos de contratos y auxiliares
  catalogos.schema.json            Forma estricta de catálogos y políticas
  perfil_piloto.json                Supuestos propuestos, todavía NOT_RUN
  politica_diseno.json              Aserciones y dependencias de revisión
  procedencia.json                  Huellas de las fuentes conservadas
herramientas/
  politicas.py                      Selección y controles de referencia
  generar_indices.py               Generación y comprobación de tablas
  validar_especificacion.py         Validador de ESTA entrega, no del producto
  comprobar_regresiones.py          Ejecuta las regresiones documentales
pruebas_documentales/
  test_regresiones.py               Copia intacta y 16 mutaciones aisladas
ejemplos/                         Datos sintéticos; no usar en producción
referencia/
  Pipeline_101_original.md          Original preservado
  Pipeline_101_restaurantes_v2.1.md  Documento 2.1 preservado
  v2/                              Contratos/documentación históricos usados
```

`referencia/` es archivo histórico: sus cifras, identificadores y reportes no son los de la versión activa. Los nombres con «v2» dentro de esa carpeta se mantienen para preservar las fuentes sin modificar.

## Reproducir los controles

Desde esta carpeta, con Python 3.10 o posterior y la dependencia indicada:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 herramientas/generar_indices.py --check
python3 herramientas/validar_especificacion.py --report VALIDACION_ENTREGA.json
python3 herramientas/comprobar_regresiones.py --report VALIDACION_REGRESIONES.json
```

En Windows, activar `.venv\Scripts\activate` en lugar de `source`. Los comprobadores no hacen solicitudes de red; la instalación de la dependencia puede necesitar acceso a su distribuidor. La entrega se ejecutó con `jsonschema==4.26.0`.

Para editar una regla o un caso, modificar el catálogo/política correspondiente y después:

```bash
python3 herramientas/generar_indices.py
python3 herramientas/validar_especificacion.py --report VALIDACION_ENTREGA.json
python3 herramientas/comprobar_regresiones.py --report VALIDACION_REGRESIONES.json
```

No editar a mano `APLICABILIDAD_PILOTO.json`, el índice de pruebas ni los tres bloques marcados `GENERATED` del documento. El validador falla si no coinciden con sus fuentes. Un cambio intencional que afecte las garantías requiere actualizar la versión y sus regresiones; no basta regenerar una tabla para hacerlo admisible.

Las regresiones trabajan en carpetas temporales y verifican que el paquete intacto pase y que ciertas modificaciones incorrectas sean rechazadas. No alteran los originales. El reporte es distinto del catálogo de casos del producto.

## Límites de lo entregado

Los 155 controles del paquete y las 17 regresiones documentales pasaron en esta entrega. Eso comprueba estructura, selección, referencias, derivación de tablas y ciertos rechazos previstos. **No ejecuta los 84 casos del producto.** Cada uno conserva `NOT_RUN`, sin implementación ni evidencia inventadas.

El perfil de piloto es una propuesta con supuestos sin verificar. La selección calculada no emite `NOT_APPLICABLE` operativo ni habilita las capacidades. La integración necesita evidencia de que las condiciones se cumplen, especialmente la ausencia de superficies privadas compartidas. Esas verificaciones se guardan aparte, ligadas al hash del perfil; no se convierten los campos `NOT_RUN` de esta entrega en resultados inventados.

Las huellas no prueban derechos, autoridad ni que una persona haya revisado un diseño. El ejemplo de aprobación está rechazado y las revisiones/compuertas almacenadas están `NOT_RUN`. Los `PASS` sintéticos creados en memoria solo ensayan reglas estructurales y se descartan; no constituyen reportes del producto.

No se modificaron repositorios, cuentas, dominios, sitios, datos de restaurantes ni servicios externos. Las fuentes externas se conservaron de los documentos de entrada y no se volvieron a verificar; esta entrega no certifica cumplimiento legal, seguridad, accesibilidad, rendimiento ni calidad de una página real.
