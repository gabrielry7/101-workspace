# Comprobación
Desde projects/101-design-compiler con Node 24, dependencias y dueño privado fijado:
```sh
node --experimental-strip-types --test tests/location-map.test.ts
node tooling/bones/prepare-location-map.mjs
H4_BROWSER_PATH=/home/tom/.local/bin/chromium node --experimental-strip-types scripts/audit-location-map.ts
node tooling/bones/serve-location-map.mjs
```
Abrir http://127.0.0.1:8777/. Inspeccionar tres recetas neutras, logo/pin, guías, pan/zoom y alternativas.
Google real sigue el procedimiento de docs/bones/location-map.md y requiere configuración propia y revisión viva autorizada.
