# Research: extracción del footer Caretta

- **Decisión**: La captura suministrada es la referencia fija; el HTML público
  actual sólo completa destinos. **Razón**: el sitio hoy incluye DPA, que no aparece
  en el objetivo histórico; no se reemplaza Cookie settings por DPA.
  **Alternativa**: replicar la web actual completa, fuera del alcance pedido.
- **Decisión**: No se añade movimiento. **Razón**: `motion: null` y captura fija.
  La consulta HTML no demuestra comportamiento temporal en un navegador.
- **Decisión**: Astro en el renderer existente. **Razón**: el footer anterior
  contiene etiquetas y rutas ficticias; no puede asumirse como base de este caso real.
  **Alternativa**: otra app de preview, descartada por duplicación.
- **Decisión**: Mantener huecos geométricos y reemplazar la piel por valores neutros.
  **Razón**: el usuario pide extraer huesos, no rediseñar la composición.
- **Decisión**: Reutilizar `packages/component-preview/measure.js` y `guides.js`
  del checkout fijado de Tomás; incorporar una extensión propia para texto.
  **Razón**: su espacio 40×28 es un proxy de contenido, no porcentaje de tinta
  ni de sólo texto. No duplicar geometría/contraste/superficies.
- **Decisión**: El texto se calcula por unión exacta de cajas de línea recortadas,
  excluyendo logos y marca decorativa. **Razón**: evita doble conteo y distingue
  texto de control. **Alternativas**: contar caracteres o analizar píxeles;
  la primera no mide área y la segunda confunde decoración/antialias.
- **Decisión**: La dependencia privada se prepara sólo localmente y es opcional.
  **Razón**: el repo del usuario es público; la compilación no debe necesitarla.
- **Decisión**: Cookies usa contrato de evento explícito y estado no conectado
  por defecto. **Razón**: no existe un gestor de consentimiento de este consumidor.

Fuentes: JSON/captura suministrados, HTML público de https://caretta.so/ leído el
2026-11-05 y README/código de component-preview en
`101-world-model@6c0ed29940985bfb1789280c1972e47386775193`.
No se consultó una base de clientes ni se ejecutaron proveedores de IA.
No quedan incertidumbres materiales para el alcance acotado.
