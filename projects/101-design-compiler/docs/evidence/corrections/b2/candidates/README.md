# Candidatos de trabajo, no paquetes aprobados

Estos JSON conservan estados previos de construcción del sidecar. No son autoridades ni bibliotecas aceptadas por el consumidor actual.

- `library-01.json`: primer candidato, antes de explicitar en el historial la transferencia por software y la inspección visual por asistente.
- `library-02.json`: añadió ese historial, pero conservaba el recibo técnico ligado al SHA de la evaluación legal anterior.
- `technical-inspection-01.json`: recibo técnico de esa primera evaluación. Su hash de revisión no corresponde a la revisión vigente; no se presenta como evidencia legal actual. Los hashes de los archivos de imagen coinciden con los de la corrida final.
- `library-03.json`: candidato anterior a separar el evento único de adquisición y los eventos de derivación/inspección heredados por uso.
- `library-04-before-feature-binding-correction.json`: candidato con esos eventos, anterior a corregir referencias aspiracionales de capacidades sin ficha `offer_detail` compatible. La biblioteca final conserva `feature_id=null` donde todavía no hay vínculo explícito.

El consumidor detecta discrepancias de revisión y sólo acepta el sello explícito de `data/media/library-v1/usda-pilot.json`, los documentos y archivos finales. No se sustituye historia para fingir que estos candidatos eran la entrega.
