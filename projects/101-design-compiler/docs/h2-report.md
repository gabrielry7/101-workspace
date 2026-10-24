# H2 — Capability & Semantic Site Planner

## Resultado y cierre previo de H1

**H2: PASSED, listo para revisión.** Un mismo planner determinista produce CapabilityProfileV1 y SitePlanV1 desde datos aprobados, o devuelve bloqueo explícito sin SitePlan. No se avanzó a H3.

Antes de implementar H2 se leyeron `pipeline.md`, su especificación V0.2 (§4–9 y §24/H2), los informes H0/H1 y los contratos existentes. Baseline: **95/95 tests**, check sin diagnósticos, validación y build correctos. Evidencia: [tests](evidence/h2-baseline-tests.txt), [check](evidence/h2-baseline-check.txt), [build](evidence/h2-baseline-build.txt). Se repitió la auditoría H1 y se verificó el diff y los hashes antes de cerrar H1.

H1 quedó cerrado en **`7ad0c2ddab91824fbfee6d235460d8e16f07b578`**, `feat: close H1 taxonomy audit and versioned upstream protocol`. Solo se incluyeron fuentes, contratos, datos y evidencia intencional; herramientas, dependencias y salidas Astro permanecen ignoradas. Se añadieron atributos Git para conservar el inventario byte por byte y LF en registry/derivados; logs convertidos a UTF-8 con espacios finales normalizados. Un clon temporal con `core.autocrlf=true` conservó exactamente los bytes y hashes del inventario, mappings y coverage. El clon propio se eliminó después de verificarlo.

H2 queda en el worktree para revisión; no se solicitó commit H2. Los cuatro contratos H0, seis esquemas H1, fixtures H0, inventario, 67 reglas, derivados de taxonomía y lockfile **siguen sin diff contra el cierre H1**. La especificación original permanece intacta. No se añadieron dependencias.

## Arquitectura y contratos reutilizados

| Pieza | Responsabilidad |
|---|---|
| `src/validation/input.ts` | Frontera factual extraída del validador H1, compartida con protocolo, H0 y planner: esquema, referencias, scopes, IDs, identidad y evidencia |
| `src/taxonomy/resolve.ts` | Clasificación H1 intacta; exporta su vocabulario de relevancia para reutilizar la matriz candidata |
| `src/planner/contracts.ts` | CapabilitySpecV1, CapabilityRegistryV1 y SiteRequirementsV1, versiones 1.0.0 separadas |
| `src/planner/registry.ts` | 47 especificaciones tipadas, módulos semánticos compartidos, datos mínimos, prioridades, rutas y dependencias |
| `src/planner/content.ts` | Publicación, vigencia, referencias de objetos, tipos de hechos, clases y seguridad de destinos |
| `src/planner/plan.ts` | Genera capacidades, requisitos, bindings, rutas con contenido y exclusiones; sin I/O ni reloj implícito |
| `src/planner/validate.ts` | Reutiliza validateBundle H0 y añade invariantes de módulos obligatorios, integridad, dependencias y ledger |
| `scripts/{load,check}-planner-fixtures.ts`, `scripts/plan-fixtures.ts` | Harness único para nueve inputs; exportación determinista de evidencia |

**No se ampliaron silenciosamente CapabilityProfileV1 ni SitePlanV1.** Como SitePlanV1 no tiene campos para prioridades/dependencias/diagnósticos detallados, SiteRequirementsV1 los transporta en un artefacto asociado. El consumidor futuro debe recibir ambos. `required` permanece también en cada módulo del SitePlan.

Los JSON Schema de los tres nuevos contratos están en `contracts/planner/v1/`; `npm run contracts:export` exporta 13 schemas y sus pruebas detectan divergencias. SiteRequirements contiene IDs de artefactos, evaluación temporal, hashes, política/prioridad/disposición por capacidad y scope, dependencias por ID de requisito, bindings y omisiones con origen de solicitud. No contiene CSS, layout, componentes visuales ni texto de negocio generado.

## Registro compartido y elegibilidad

Las **47 capacidades V1** tienen especificaciones: **46 con semántica disponible** y `gallery` diferida a H3. Disponible significa contrato de planificación, **no UI implementada**. Todas las salidas conservan `frontend_status=NOT_SUPPORTED_YET` y `backend_status=BACKEND_NOT_CONNECTED`.

Módulos comunes: identidad, colecciones de ofertas, calendario, colecciones de hechos, información de localización, intención de enlace externo y medios diferidos. Menú, productos, servicios, membresías, habitaciones, programas, eventos y profesionales usan las mismas colecciones parametrizadas por objetos aprobados. No hay un planner ni una plantilla por categoría.

| Contexto representado | Datos/capacidades verificadas | Semántica compartida |
|---|---|---|
| Restaurante | menu + menu_item | Colección de ofertas |
| Retail / ferretería / industria | product_catalog + product/product_category | Colección de ofertas; variantes solo con datos y catálogo |
| Gimnasio | membership, class_schedule; trainer_profiles con rol aprobado | Colección de planes, calendario y profesionales |
| Clínica | service_catalog, professional_profiles; appointment con destino aprobado | Servicios/equipo y enlace externo |
| Servicios profesionales / hogar / vehículo / logística | service_catalog, contact_channels, service_area | Colección y hechos de contacto/cobertura |
| Hotel | rooms, amenities; room_booking con habitaciones y destino | Colección, hechos y enlace externo |
| Educación / eventos | programs, events; inscripción/entradas con objetos y destino | Colecciones y enlaces sujetos a dependencias |
| Espacios / otras actividades | portfolio, visit_policy, documents, faqs, etc. | Hechos aprobados, sin inventar inventario ni funcionalidades |

Reglas de decisión:

1. La categoría aporta clasificación y candidatas mediante H1. **No confirma ninguna capacidad**, ni limita una capacidad real por whitelist sectorial. Un gimnasio puede mostrar retail verificado sin añadir una regla taxonómica.
2. Cada entrada del CapabilityProfile conserva exactamente ID, scope, estado y evidencia upstream. Una candidata no declarada queda UNKNOWN solo en requisitos, con `source=CANDIDATE_ONLY`; no se fabrica una entrada factual en CapabilityProfile ni una exclusión respaldada artificialmente.
3. CONFIRMED_PRESENT/CONFIRMED_ABSENT necesitan evidencia aprobada vigente al corte y una afirmación específica de igual scope/valor. Afirmaciones aprobadas opuestas del mismo scope bloquean la entrada y solicitan corrección upstream. UNKNOWN/CONFLICTED/WITHHELD nunca producen módulos.
4. PRESENT no equivale a elegible. Sin objetos, hechos, destino o dependencia suficientes, conserva PRESENT y se bloquea por MISSING_INPUT. Ausencia conserva CONFIRMED_ABSENT; medios sin gate H3 conservan NOT_SUPPORTED_YET.
5. Solo se vinculan hechos aprobados y vigentes, de tipo esperado; las afirmaciones `capability:*` son evidencia, nunca contenido. No se convierten booleanos en precios ni números en nombres. Los campos tipados de ofertas requieren `offering_name`, `price`, `sku`, `membership_terms`, `class_starts_at` y `timezone`, según referencia existente. No se inventa moneda ni se realiza formato monetario.
6. Un Offering se vincula completo por ID. Si una referencia opcional, como precio, está withheld o vencida, se omite ese objeto con diagnóstico: no se crea una copia alterada para eludir la guarda H0. Otros objetos publicables sobreviven. Si no queda ninguno para una capacidad central PRESENT, se bloquea el sitio.
7. Horarios requieren horario aprobado y todas las excepciones conocidas publicables. Las fechas de clases y zonas horarias se validan; no se adivinan. Profesionales no se convierten en entrenadores: trainer_profiles requiere un hecho `professional_role=trainer` vinculado al objeto.
8. Las acciones requieren un destino exacto de capacidad/scope con `action_url` aprobado, HTTPS y sin credenciales. Purchase depende de catálogo; order de menú/catálogo; appointment de servicios/equipo; signup de membresía; enrollment de clases/programas; ticketing de eventos; room_booking de habitaciones. No se ejecutan enlaces, compras ni reservas. Si hay varios destinos aprobados, se escoge por ID estable y se conservan los demás en perfil y omisiones.

Las dependencias se resuelven hasta un punto fijo, sin heredar entre sucursales. El registro rechaza duplicados, dependencias desconocidas y ciclos. Nuevas especificaciones se revisan como cambios de plataforma; los nombres de capacidad siguen limitados al enum V1. Las prioridades numéricas son política editorial determinista, no scores aprendidos ni decisiones visuales.

## Alcance, rutas y estados de salida

Capacidades y objetos se seleccionan por **scope exacto**. Los hechos globales no autorizan capacidades operativas de una sucursal. Un objeto puede referenciar explícitamente un hecho global aprobado, conforme al contrato H0; se conserva el scope original en el ledger. Esto no replica objetos ni capacidades a otras sedes. La identidad global es una dependencia compartida, no prueba de otras operaciones.

Las rutas nacen de capacidades elegibles. Para scopes de sucursal se usa `/sedes/s-<hash-del-scope>/<ruta-semantica>`; IDs arbitrarios upstream no se interpolan como URL. Rutas y módulos tienen orden estable. `menu`, `catalogo`, `clases`, etc. son rutas de capacidades comunes, no plantillas sectoriales. Una ruta sin módulos sustantivos no se emite.

- **READY:** CapabilityProfileV1, SitePlanV1 y SiteRequirementsV1 validados, con bindings/exclusiones completos.
- **CONTENT_BLOCKED:** no hay SitePlan. Conserva perfiles y requisitos diagnósticos si el input era válido: clasificación ambigua/desconocida/no comercial, identidad sin capacidad verificada, negocio no ACTIVE, capacidad central PRESENT sin datos, evidencia esencial vencida o identidad como único contenido.
- **INPUT_INVALID:** error de esquema, IDs/referencias/scope, confirmación incompatible, contexto/registro inválido, datos no JSON o evaluación temporal inválida. Sin SitePlan y sin perfiles que aparenten una transformación aprobada.

`REQUIRED_IF_PRESENT` se aplica a identidad y oferta/calendario/equipo centrales confirmados. Las acciones y datos complementarios son condicionales; su omisión no inventa un botón. Un estado UNKNOWN de una oferta candidata no impone por sí solo una obligación ficticia.

En CONTENT_BLOCKED, los requisitos pueden conservar bindings semánticos elegibles para explicar qué datos existen; `BOUND` significa referencia propuesta a un módulo semántico, **no una página emitida ni DOM publicado**. No se entrega un plan parcial. En READY, el validador verifica que las referencias sobreviven exactamente en SitePlan. La futura auditoría de DOM pertenece a fases posteriores.

## Generalización: evidencia controlada

Tres inputs H0 reutilizados sin modificar sus fixtures y seis escenarios nuevos, todos **SYNTHETIC_FIXTURE**. Los planes manuales H0 no se usan como respuestas del planner. Destinos `example.invalid`, direcciones y nombres de H2 son ficticios; no son integración ni negocios reales.

| Fixture | Resultado | Rutas / módulos | Semántica emitida además de identidad |
|---|---|---|---|
| restaurante | READY | 2 / 2 | menú; reserva sin destino omitida |
| gimnasio | READY | 3 / 3 | membresías y clases; retail ausente |
| ferretería | READY | 2 / 2 | catálogo; cotización sin destino omitida; delivery UNKNOWN |
| clínica | READY | 4 / 4 | servicios, profesionales, solicitud externa sintética de consulta |
| híbrido gimnasio + tienda | READY | 4 / 4 | planes, clases y catálogo; coexistencia aprobada |
| híbrido sin evidencia de coexistencia | CONTENT_BLOCKED | 0 / 0 | clasificación AMBIGUOUS; sin plan |
| hotel + restaurante, dos sucursales | READY | 6 / 6 | habitaciones y dirección por sede; menú solo en la primera |
| información incompleta | CONTENT_BLOCKED | 0 / 0 | catálogo PRESENT sin objetos; sin plan |
| servicios profesionales | READY | 3 / 3 | servicios y contacto; citas UNKNOWN |

Artefactos íntegros: `data/derived/planner-v1/*.json`. [Log de generación](evidence/h2-planner-fixtures.txt). **Los nueve resultados se regeneraron idénticos byte por byte**, incluyendo los bloqueos: [log de replay](evidence/h2-planner-replay.txt) y [manifest SHA-256 por archivo](evidence/h2-planner-replay.json).

El hash canónico del registro semántico evaluado es `9755d7f5af749f2d11e1702d0d589da934fa7862244833d8105e712d289e4af7`. Los IDs de CapabilityProfile/SitePlan incluyen un fingerprint de versión del planner, input, registro semántico, reglas taxonómicas, sidecars de clasificación y fecha de evaluación. Cambiar reglas o coexistencia cambia el linaje. Los hashes de input/registro/reglas/contexto son del JSON canónico H1, no hashes del texto de los archivos.

## Comandos y API

```sh
npm test
npm run check
npm run validate
npm run build
npm run contracts:export
npm run planner:fixtures
```

`npm run validate` conserva la validación H0 y añade los nueve resultados H2, incluidos bloqueos esperados. El build ejecuta esa validación antes de Astro. `planner:fixtures` solo exporta datos de prueba; la API del motor es `planBusiness(input, options)` en `src/planner/plan.ts`.

```ts
const result = planBusiness(input, {
  rules: taxonomyRegistry.rules,
  activity_relationships: approvedRelationships,
  category_context: preservedCategoryContext,
  evaluation_time: explicitCutoff,
});
if (result.status === 'READY') {
  const { input, profile, capabilities, plan, requirements } = result;
  const audit = validateSemanticPlan({ input, profile, capabilities, plan }, requirements);
}
```

El futuro consumidor real debe validar primero el protocolo H1; aquí no existe transporte ni adapter upstream. Si no se indica evaluation_time, se evalúa al `input.as_of`, sin leer el reloj. Para publicación futura debe pasarse una fecha de evaluación pertinente y una política de frescura acordada.

## Pruebas y comprobaciones finales

| Verificación | Resultado | Evidencia |
|---|---|---|
| `npm test` | **161/161**, 0 fallos/omitidos/cancelados | [log](evidence/h2-tests.txt) |
| `npm run check` | 0 errores, warnings e hints | [log](evidence/h2-check.txt) |
| `npm run validate` | 3 paquetes H0 y 9 escenarios H2 correctos | [log](evidence/h2-validate.txt) |
| `npm run build` | Validación previa y una ruta del inspector Astro | [log](evidence/h2-build.txt) |
| `npm run contracts:export` | 13 schemas, H0/H1 intactos | [log](evidence/h2-contracts-export.txt) |
| `npm run planner:fixtures`, replay | 7 READY y 2 bloqueos correctos; nueve hashes idénticos | Logs y manifest anteriores |
| Auditoría H1 repetida | Sin cambios en 4.582 filas, 67 reglas ni métricas | [log](evidence/h2-taxonomy-audit.txt) |

95 pruebas previas siguen pasando; 66 adicionales verifican esquemas H2, escenarios, no-inferencia, PUBLICATION/expiry, tipos de precio/identidad, UNKNOWN/ABSENT/CONFLICTED/WITHHELD, híbridos, abstención, falta de datos, ofertas parciales, scopes, URLs, dependencias, rol de entrenador, rutas vacías, identidad imprescindible, integridad del ledger y conservación de módulos obligatorios. Mutaciones que eliminan o degradan un módulo obligatorio, su requisito, bindings o dependencias fallan. Generalización adicional: educación, eventos, industria, plomería y logística usan el mismo selector de colecciones. No se midió cobertura porcentual de líneas ni precisión del clasificador.

Errores encontrados durante implementación y resueltos:

- La extracción inicial de guardas perdió dos códigos de diagnóstico esperados por H0; se conservaron `MISSING_EVIDENCE` y `EVIDENCE_KIND_MISMATCH`, junto al diagnóstico H1. No se relajaron pruebas.
- TypeScript detectó literales de estado ensanchados a string; se tipó el mapeo de CapabilityProfile.
- El primer script auxiliar de fixtures tenía un error de indentación y no creó archivos; se corrigió. Las ejecuciones posteriores validaron todos los JSON.
- El harness pasaba el envelope del resultado a validateBundle, que correctamente rechazaba campos ajenos; ahora pasa únicamente input/profile/capabilities/plan y conserva los errores reales de validación.
- La revisión detectó linaje incompleto si cambiaban reglas o sidecars; se incorporaron al fingerprint y se añadió regresión. Ninguno de esos fallos persiste en la ejecución final.

## Límites y riesgos pendientes

- La clasificación H1 conserva su cobertura parcial y abstención; no se intentó mejorar métricas. Un negocio factual con categoría aún no resuelta sigue bloqueado para SitePlan y requiere revisión upstream/crosswalk.
- Semántica disponible no demuestra UI, accesibilidad, calidad visual, costos ni rendimiento comercial. El inspector Astro sigue mostrando paquetes manuales H0 y explicita el comando H2.
- `gallery` permanece diferida. No se adquieren ni autorizan medios por una URI o estado DOCUMENTED. Portfolio/documents son hechos descriptivos aprobados; no un motor multimedia o de descarga.
- Las convenciones de fact kinds/roles son candidatas y requieren acuerdo con 101-world-model. OfferingV1 no modela todavía paquetes/variantes/propiedades como objetos completos; sus capacidades usan hechos descriptivos, sin inventar relaciones de inventario. No hay moneda, stock, credenciales ni disponibilidad fabricados.
- No hay autenticación de PublicationDecision ni comprobación de existencia/funcionamiento de URLs. HTTPS y aprobación factual no demuestran una integración conectada. En fixtures, REAL_APPROVED_EXTERNAL_LINK es una modalidad contractual simulada, limitada por FIXTURE_PREVIEW y dominios invalid.
- Se conserva el estado factual del snapshot incluso si una evaluación posterior bloquea elegibilidad por vencimiento; no se reescribe la verdad upstream. Sin expires_at ni política de TTL acordada no se presume una fecha de vencimiento.
- Prioridades, centralidad y mínimos de contenido son política V1 explícita que requiere revisión editorial. Dependencias regulatorias adicionales por sector no se inventan desde el nombre de una categoría; no se certifica readiness de un sitio clínico/legal real.
- Las referencias propuestas no prueban preservación en DOM. El renderer, auditorías de contenido/rendering y selección de representación visual siguen pendientes.

**Implementado:** registro, planner, validadores, contratos asociados, evidencia determinista y harness. **Simulado:** nueve escenarios y sus afirmaciones/destinos. **Pendiente:** representación visual, LLM, multimedia H3, runtime comercial, pagos/reservas reales y conexión upstream. H2 termina aquí para revisión.
