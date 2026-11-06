# Verificar Footer 001

Desde `projects/101-design-compiler` en la rama de entrega, con Node 24:

1. `npm ci`
2. Opcional, con acceso al checkout privado fijado de Tomás:
   definir `BONES_REFERENCE_ROOT` como su ruta y ejecutar
   `node tooling/bones/prepare-inspector.mjs`.
3. `npm run check` y `npm test`.
4. `node tooling/bones/build-preview.mjs` para compilar las rutas de esta entrega.
   El build global `npm run build` sigue sujeto a los paquetes históricos de medios.
5. `node --experimental-strip-types scripts/audit-footer-bones.ts`.
6. `python -m http.server 4337 --bind 127.0.0.1 --directory dist-footer-bones`.

Abrir `http://127.0.0.1:4337/bones/footers/caretta/`.
Comparar la captura histórica con el hueso; cambiar tamaño, medir, activar
anatomía y descargar JSON. El consumidor sin inspector vive en
`/bones/footers/caretta/instance/`.

Esperado: cuatro grupos, cinco Soon sin navegación, ausencia de fuentes/colores
de Caretta, métricas complementarias con método visible y ningún chatbot llamado.
Sin preparar la dependencia, las medidas de texto siguen disponibles y la
medición compartida informa que falta, sin romper el componente.

El build de revisión usa copias verificadas byte a byte de los mismos fuentes
Astro y una carpeta estática temporal. No cambia el renderer ni reseña como
superados los gates del legado. Los módulos privados viven en
`.tools/footer-inspector`; sólo se incluyen en ese artefacto local de revisión.
