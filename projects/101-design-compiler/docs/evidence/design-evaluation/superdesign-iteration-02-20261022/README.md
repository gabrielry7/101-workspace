# Superdesign B3 — iteración 02

Propuestas no aprobadas. Dos reemplazos creativos con Gemini 3 Flash, 16 créditos gratuitos; correcciones literales posteriores sin generación. Motor y paquete audiovisual conservados.

## Replay local

Desde la raíz, con Node 24, dependencias y el paquete autorizado B3 existente:

```powershell
npm run build
node tooling/superdesign/prepare-pilot.mjs
Copy-Item -LiteralPath 'docs/evidence/design-evaluation/superdesign-iteration-02-20261022/editorial.provider.html' -Destination '.superdesign/tmp/editorial.provider.html'
Copy-Item -LiteralPath 'docs/evidence/design-evaluation/superdesign-iteration-02-20261022/chapters.provider.html' -Destination '.superdesign/tmp/chapters.provider.html'
node tooling/superdesign/build-local-review.mjs --live
node docs/evidence/design-evaluation/superdesign-iteration-02-20261022/review-server.mjs
```

Abrir http://127.0.0.1:4333/. No requiere acceso al proveedor ni nuevas generaciones. Los HTML remotos contienen SVG neutros; las fotos/vídeo autorizados se recuperan del build local. La comparación original archivada sigue disponible con el builder sin --live. Los datos de navegador registran secciones y estados concretos, no una auditoría visual completa de todas las páginas.
