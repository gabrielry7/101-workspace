# Inventario de referencia

El **archivo original** del inventario entregado por el usuario está en `message (4).txt`. Se conserva intacto; el informe H1 documenta su SHA256 y auditoría. El archivo no estaba presente al iniciar H1; este README no sustituye sus datos. No inventar filas ni extraer cifras de la especificación como si fueran el archivo.

`npm run taxonomy:audit` procesa los archivos `.tsv`, `.csv` o `.txt` de esta carpeta. También admite una ruta explícita: `npm run taxonomy:audit -- data/reference/archivo.txt`. El parser exige las siete columnas de V0.2: `source`, `category_field`, `category_value`, `provider_category_id`, `source_observations`, `business_candidates`, `other_observations`. Admite UTF-8/BOM, delimitador tab/coma/punto y coma, quoting, comillas escapadas y líneas dentro de una celda. Otros formatos requieren adapter explícito.

Cada fila es una combinación de proveedor/campo/categoría y conteos, **no un negocio único**. No unir filas originales con normalizadas para fabricar una relación de un negocio. No sumar los conteos de distintos proveedores o categorías como locales únicos. Conservar el archivo intacto y su SHA256; los derivados intencionales se escriben en `data/derived/taxonomy-v1/`.
