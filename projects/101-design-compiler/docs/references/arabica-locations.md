# % Arabica · reproducción privada de ubicaciones

Versión 0.1.1. Referencia: https://arabica.com/en/locations/.
[Spec](../../specs/009-arabica-locations-reference/spec.md),
[plan](../../specs/009-arabica-locations-reference/plan.md),
[tareas](../../specs/009-arabica-locations-reference/tasks.md).

Vista local: http://127.0.0.1:8780/arabica/. Esta entrega reproduce la sección
para revisión; convertirla en huesos es el paso posterior solicitado por el usuario.
No se incorpora al catálogo de huesos aprobados.

## Alcance implementado

Composición y tipografías de referencia, mapa Google con los 35 ajustes de estilo
observados, panel regional con recuentos, estados de futuras aperturas, pines
numerados, navegación mundo → país → ciudad, regreso, historial y tarjetas de
locales. El catálogo retenido contiene 102 vistas. En móvil el mapa precede a la
lista; se conservan los umbrales de composición y encuadre medidos.

La navegación interna reutiliza una sola instancia de Google. Los detalles de un
local y los enlaces ajenos a la sección abren el sitio oficial. La animación de
entrada utiliza el DROP nativo de Google y respeta movimiento reducido. No se
redistribuye ni ejecuta el JavaScript original de la web ni su clave de Maps.

El original no define `createPoint('Macau')`: se conserva su ausencia de pin
global y el centro de la vista local de Macau usa la coordenada de su propio pin
de ciudad, retenida de la misma página. Esta corrección está registrada en el
catálogo privado; no se inventa una coordenada.

## Preparación local

Ejecutar desde la raíz del compiler, con las dependencias existentes de Astro y
Node instaladas. `H4_BROWSER_PATH` debe señalar el Chromium local.

```sh
node tooling/references/capture-arabica-reference.mjs
node tooling/references/prepare-arabica-reference.mjs
node tooling/bones/serve-honorato-google.mjs
```

`capture` conserva un máximo acotado de páginas oficiales y fuentes bajo
`.tools/arabica-locations-reference/`; `--offline` reprocesa sólo las copias
retenidas. No refresca el catálogo en cada visita. El build utiliza el componente
Astro existente y genera únicamente una entrada privada, sin construir las demos
históricas. Los medios visibles de las comprobaciones se conservan localmente;
las demás tarjetas usan sus URLs oficiales en esta vista privada.

El servidor requiere la configuración propia y restringida de Google que ya está
fuera de Git en `.tools/honorato-google-live/`. El 19 de noviembre el usuario
autorizó diez cargas adicionales para esta copia, manteniendo US$1 como máximo
total y diez cargas diarias. El permiso se conserva en
`.tools/arabica-locations-reference/google-permission.json`; el contador adicional
en `trial-budget.json`. El contador de Honorato no se reinicia ni se amplía.
Abrir la página no consume Google: se activa con su botón y la navegación interna
conserva la instancia. No se deben borrar los contadores para obtener más cargas.

## Verificación

```sh
node --experimental-strip-types --test tests/arabica-reference.test.ts tests/location-map-controls.test.ts
node --experimental-strip-types scripts/audit-arabica-reference.ts
```

El audit por defecto comprueba layout sin activar Google. `--live` realiza una
reserva real del contador autorizado: usarlo sólo cuando corresponda verificar
cambios del mapa. La ejecución final pasó 57 comprobaciones nativas con Google
real y una inicialización para todos sus recorridos. Incluyó pines clicados,
coordenadas, país/ciudad, historial, doce anchos de 360 a 1440 px, ambos lados de
los umbrales, teclado, fuente de respaldo, movimiento reducido y un fallo de
proveedor identificado mediante inyección de servicio. Las ocho pruebas de datos
y regresión del editor pasaron. Solicitudes de reserva con método/origen inválido
se rechazaron sin alterar el contador.

Capturas, mediciones originales y recibo detallado están bajo el directorio
privado `verification/`. El resumen versionado no contiene imágenes, fuentes,
credenciales ni código privado de Thomas. El acceso público a los recursos de la
referencia no se presenta como una licencia de redistribución. La revisión visual
del usuario y la extracción del hueso siguen siendo pasos separados.

## Corrección de movimiento · 0.1.1

El mapa conserva la posición al terminar un arrastre, usar controles o cambiar
el tamaño de la vista. El manejador general de clics ahora admite únicamente
enlaces de navegación: antes confundía el atributo de estado del contenedor con
un enlace y volvía a seleccionar la región tras interacciones del mapa.
Los gestos se configuran explícitamente para arrastre con ratón/dedo y zoom con
rueda; el observador de tamaño no vuelve a aplicar el encuadre inicial.

La comprobación anterior no cubría el arrastre real. La regresión específica
pasó diez comprobaciones con entrada nativa en un iframe: ratón, rueda, retención
de cámara al redimensionar, un dedo, scroll exterior y selección posterior de
país. Reutilizó una inicialización de Google. Ejecutar sólo dentro del cupo:

```sh
node --experimental-strip-types scripts/audit-arabica-pan.ts --live
```

Recibo resumido: [arabica-pan-verification.json](arabica-pan-verification.json).
