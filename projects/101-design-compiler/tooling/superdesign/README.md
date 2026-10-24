# Superdesign — piloto optativo sobre B3

Destino inicial: `/b3/candidate-01/` (**La mesa abierta**). Base: `b97f76f9bc632f57bba9e21ceefd9a060700cf08`. Es continuación de B3; no B4 ni reemplazo del runtime Astro compartido.

La skill oficial está instalada fuera del repositorio en `%USERPROFILE%/.codex/skills/superdesign`, desde `superdesigndev/superdesign-skill`, revisión `f9f05cd988c247dce6c072eaf9ac6b162f2ffc4b`. El CLI se fija en **0.14.0**. Su código tiene licencia MIT; esto no concede derechos sobre medios ni define las condiciones del servicio alojado.

## Instalar y comprobar

Desde la raíz, con Node 24 y npm disponibles:

```powershell
npm ci --prefix tooling/superdesign --ignore-scripts --no-fund --no-audit
$env:DO_NOT_TRACK='1'
$env:SUPERDESIGN_TELEMETRY_DISABLED='1'
node tooling/superdesign/node_modules/@superdesign/cli/bin/superdesign.js
```

El preflight informa si existe una sesión; no crear proyectos para probar autenticación. Para vincular una cuenta existente:

```powershell
node tooling/superdesign/node_modules/@superdesign/cli/bin/superdesign.js login --no-browser --json
```

Abrir únicamente el `authUrl` devuelto, comparar código y equipo, y completar la autorización en el navegador. Los códigos caducan; no guardarlos en este documento. La configuración privada predeterminada vive en `%USERPROFILE%/.superdesign/config.json`, fuera del repositorio. No copiar su contenido ni tokens a informes. La telemetría CLI está desactivada en esta receta; esto no significa que la generación remota sea local o que no envíe contexto.

Preparar el contexto local, sin red ni uploads:

```powershell
node tooling/superdesign/prepare-context.mjs
```

Se generan los seis archivos de descubrimiento, el sistema de diseño y las huellas SHA-256 en `.superdesign/`, ignorados por Git. La receta traza imports del renderer real y no lee `.env`. Estos archivos son inventario local: antes de una llamada remota se selecciona y revisa el payload concreto. Capturas y estado remoto también quedan locales. No existe una ejecución automática de generaciones.

## Replay local del piloto completado

La conexión se autorizó y se ejecutaron una reproducción y dos variantes con Gemini 3 Flash: **38 créditos de la cuota gratuita**, sin compras. El resultado espera evaluación humana; no se eligió una ganadora ni se modificó el renderer del proyecto. [Informe y límites](../../docs/reviews/superdesign-b3-20261022-report.md).

Con las dependencias raíz, el build y el paquete privado B3 autorizado disponibles, se puede reproducir la comparación sin credenciales de Superdesign ni llamadas a modelos:

```powershell
npm run build
node tooling/superdesign/prepare-pilot.mjs
node tooling/superdesign/build-local-review.mjs
node tooling/superdesign/serve-local-review.mjs
```

Abrir `http://127.0.0.1:4332/`. La receta usa los HTML devueltos y archivados en `docs/evidence/design-evaluation/superdesign-20261022/`; extrae únicamente el bloque CSS del operador y lo aplica al HTML real intacto. Comprueba el hash del build, nueve archivos de medios y el round trip del contenido/bindings. Los scripts originales de B3 manejan vídeo y navegación. No ejecuta scripts del proveedor ni carga fotos de la nube. `--live` en el builder selecciona explícitamente las últimas respuestas locales para otra corrida revisada.

El parser CSS es PostCSS 8.5.29, ya fijado en las dependencias transitivas de Astro del lock raíz. No se añadió una dependencia al runtime ni al navegador. El servidor es una vista estática de solo lectura en localhost; no es el runtime comercial 101, una publicación o un backend de reservas.

## Alcance del experimento

- Capturar la home actual en escritorio y móvil y leer su rama real de renderizado.
- Inicializar los seis archivos locales de descubrimiento de la skill y describir la identidad actual en `.superdesign/design-system.md`; no inventar IDs remotos ni un `resume.json` antes de un resultado real.
- Seleccionar contexto de esa home, no el repositorio completo. Excluir `.env`, claves, originales privados y datos de otros proyectos.
- Consultar modelos, saldo y costo aplicable una vez autenticado. No comprar planes o recargas. No ejecutar generaciones con un costo sin presupuesto autorizado.
- Verificar las condiciones aplicables a Superdesign canvas y sus proveedores antes de subir medios: los grants B3 permiten vision, pero deniegan edición, entrenamiento y redistribución. La política de **Treg** que aparece en OAuth es de otro servicio y no demuestra las condiciones de tratamiento de los borradores de diseño. No ampliar los grants existentes por instalar esta herramienta.
- Reproducir el estado actual y comparar propuestas acotadas. Conservar fuentes, paleta, contenido, destinos separados, avisos de ficción, créditos y no respaldo. No sustituir fotos ni añadir claims o funciones comerciales.
- Revisar propuestas antes de adaptar cualquier mejora a los operadores/componentes compartidos de 101. No añadir SDK al cliente, bifurcaciones por cliente o una implementación visual paralela.

Una sesión autenticada, un proyecto creado y una propuesta revisada son tres resultados distintos. Ninguno se declara por haber instalado el CLI. La aprobación estética sigue siendo humana.

Fuentes oficiales consultadas el **2026-10-22**: [skill](https://github.com/superdesigndev/superdesign-skill/tree/f9f05cd988c247dce6c072eaf9ac6b162f2ffc4b), [CLI 0.14.0](https://www.npmjs.com/package/@superdesign/cli/v/0.14.0), [flujo existente](https://github.com/superdesigndev/superdesign-skill/blob/f9f05cd988c247dce6c072eaf9ac6b162f2ffc4b/skills/superdesign/references/SUPERDESIGN.md).
