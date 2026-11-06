# Ver el hueso localmente

Requiere dependencias del compiler y checkout privado fijado en la ruta de la ficha.
El preparador falla si faltan archivos o sus hashes difieren; no descarga ni publica
ese código. No modifica el checkout original.

```powershell
$env:PATH = "$PWD\.tools\node-v24.21.0-win-x64;$env:PATH"
node tooling/bones/prepare-location-map.mjs
node --experimental-strip-types scripts/audit-location-map.ts
node tooling/bones/serve-location-map.mjs
```

Abrir http://127.0.0.1:8777/ para comparación, variantes y estados. El servidor sólo
escucha loopback. La demo es sintética y no inicia Google. Configurar Google requiere
un archivo local de instancia excluido de Git y revisión viva del estilo/map ID;
las pruebas de Google offline no sustituyen esa revisión.
