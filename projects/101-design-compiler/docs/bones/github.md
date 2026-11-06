# Entregas del esquema en GitHub

Dirección del usuario del 2026-11-05: guardar las entregas mediante commit y push.
Repositorio de destino: [gabrielry7/101-workspace](https://github.com/gabrielry7/101-workspace),
carpeta `projects/101-design-compiler`. Es un repositorio público.

## Esta entrega

- Rama: `codex/section-bones-20261105`.
- Base remota: `codex/restaurant-preapproved-20261026`, commit
  `d47576481ee60c0711e8d656e3c8824c66028a24`.
- Contenido: reglas actualizadas, spec 002, mapa del modelo y de integración,
  índice/resumen del archivo y herramientas oficiales de Spec Kit ya adoptadas.
- Referencia de Tomás: repositorio privado fijado en
  `6c0ed29940985bfb1789280c1972e47386775193`; no es el destino de esta entrega.

El checkout local principal tiene historial propio y cambios pendientes de otros
trabajos. No se añadió un remoto de monorepo a ese historial para empujarlo como
si tuviera la misma raíz. Se preparó un clon aislado en
`.tools/github-bones-20261105`, se creó la rama de entrega desde la base remota y
se transfirieron únicamente los archivos revisados a la subcarpeta del compiler.

En un checkout nuevo, abrir `projects/101-design-compiler` como raíz del proyecto.
Spec Kit guarda su puntero de feature por máquina; para seleccionar la spec vigente:

```powershell
Set-Content -LiteralPath .specify/feature.json -Value '{"feature_directory":"specs/003-footer-caretta-bones"}' -Encoding UTF8
```

Ese archivo está ignorado por diseño. Las plantillas, la constitución y la spec sí
se versionan. Los comandos del proyecto se ejecutan desde esta subcarpeta.

La feature activa posterior es el [Footer 001](footer-001.md), en la rama
`codex/footer-caretta-bones-20261105`, derivada del esquema publicado en
`46d375927fcc17d7812b04d415a524e6200c1500`. Spec 002 conserva el marco general.

## Regla para las próximas entregas

1. Confirmar la rama de destino y el estado del checkout; preservar cambios ajenos.
2. Trabajar con el ciclo SDD proporcional al cambio y revisar las diferencias finales.
3. Preparar explícitamente sólo los archivos del alcance, comprobar el diff y
   excluir credenciales, datos/referencias privadas y medios restringidos.
4. Hacer commit con el alcance y push de la rama; verificar que GitHub contiene
   el mismo SHA. Guardar el enlace al commit en la entrega al usuario.
5. Mantener merge, despliegue y comunicación a clientes como acciones distintas;
   esta instrucción de versionado no las ejecuta automáticamente.

Si se continúa desde este checkout independiente, usar el clon de destino o una
transferencia revisada equivalente. No copiar toda la carpeta ni usar `git add .`
sobre el trabajo acumulado. No hacer force push ni publicar el paquete privado de
Tomás: su manifiesto declara `publication_allowed: false`.

El archivo completo de trabajo anterior permanece local bajo `old/snapshots`.
GitHub conserva el nuevo esquema y el índice del respaldo, no una redistribución
de las capturas privadas. Si falla un push, informar el motivo concreto y conservar
el commit local; no dar por realizada la sincronización.
