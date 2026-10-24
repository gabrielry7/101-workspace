# 101 / UnoCeroUno — Business Website Compiler

## Especificación integrada del pipeline multivertical, V0.2

**Fecha:** 7 de octubre de 2026  
**Estado:** diseño de arquitectura y plan de implementación; **no** constituye prueba de integración, aprobación legal de proveedores ni sitio publicado.  
**Evolución:** sustituye el alcance exclusivo de restaurantes de `101_restaurant_design_pipeline_v0_1.md`, conservando sus decisiones técnicas, de diseño, medios, permisos y evaluación.  
**Alcance inmediato:** **frontend y dirección de arte** de sitios para distintos tipos de negocios. Se definen contratos de futuras funcionalidades, pero **no** se implementan todavía sus backends, pagos, disponibilidad, logística, CRM o reservas reales.  
**Sistema upstream:** ya existe un proceso separado que extrae y estructura información de los negocios, incluso fotografías y otros medios. **No se integra en esta fase**. Este proyecto especifica qué debe recibir; más adelante se construye un adaptador sobre el `SiteSpec`/Truth existente.

> **Objetivo:** lograr que un negocio nuevo produzca un sitio específico para su actividad, bello, coherente, ligero, verificable, autorizado en su uso de medios y reproducible, con trabajo de programación específico por cliente cercano a cero. Para lograr variedad real, la **dirección artística y la composición** se exploran probabilísticamente; la **verdad, los permisos, las interfaces, la implementación, las restricciones técnicas y la compilación final** se controlan determinísticamente.

---

## 0. Lectura ejecutiva y decisiones cerradas

### 0.1. Qué estamos construyendo

Una **máquina para diseñar y compilar sitios web de negocios**. No es un conjunto de templates por sector, no es un prompt que escribe una aplicación distinta para cada cliente, y no es otro proyecto paralelo que reemplaza `101-world-model`. Aprovecha el productor de información ya existente, los componentes y el runtime de 101, las investigaciones anteriores de gramática espacial, el corpus de componentes externos, las capturas de navegador, la crítica visual y las mutaciones.

La arquitectura debe atender simultáneamente cinco preguntas distintas:

1. **¿Qué negocio tenemos delante?** Clasificación multietiqueta, modelo comercial, sedes, situación de datos y necesidades reales.
2. **¿Qué debe comunicar y representar su sitio?** Capacidades verificadas, objetos comerciales, módulos semánticos, rutas y obligaciones de contenido.
3. **¿Con qué material visual podemos representarlo honestamente?** Medios upstream, necesidades adicionales, búsqueda externa, licencias, calidad, coherencia y coste.
4. **¿Cómo puede verse extraordinariamente bien y diferente de otros sitios?** Investigación de referencias, LLM como director artístico, gramática espacial, operadores, composición probabilística y búsqueda diversa.
5. **¿Podemos construirlo sin código específico ni comprometer seguridad, verdad, permisos, usabilidad o velocidad?** Registry y runtime compartidos, compilador, pruebas, auditoría, reparación, bloqueo del diseño y trazabilidad.

### 0.2. Decisiones acordadas que esta versión preserva

| Asunto | Decisión |
|---|---|
| Investigación del negocio | La hace **otro sistema ya existente**; no construir aquí un nuevo crawler ni duplicar Truth. |
| Fotos originales del negocio | El upstream ya puede entregarlas. Se **inspeccionan y aprovechan** antes de buscar más. No se presupone que sean suficientes ni que sus derechos estén aclarados. |
| Medios externos | Crear un subsistema capaz de buscar y obtener **fotografía y video excepcionales** de catálogos grandes, gratis o pagando, con derechos comprobables por cliente y uso. |
| Tipo de negocio | No se limita a restaurantes: el inventario actual abarca retail, salud, servicios, gastronomía, gimnasios, automotriz, hoteles, educación, industria y muchos más. |
| Funciones | Se definen por **capacidades confirmadas del negocio**, condicionadas por su arquetipo. La categoría nunca autoriza inventar funciones. |
| Fase inmediata | Se construyen **contratos y presentaciones de frontend**. Integraciones operativas en fase posterior. |
| Diversidad visual | No convertir sectores en templates estereotipados. Un mismo componente puede participar en composiciones muy diferentes. |
| Parte probabilística | LLM y búsqueda exploran dirección de arte, topología, jerarquía, medios, escalas, ritmo, asimetría y movimiento dentro de restricciones estrictas. |
| Base tecnológica | **Una sola**: Astro/TypeScript, HTML/CSS primero, React islands únicamente si se necesitan, sistemas compartidos de diseño, accesibilidad, responsive y medios. |
| Dependencias de UI | Usar bibliotecas externas como **corpus de patrones**, adaptar al registry propio y conservar procedencia/licencia del código. No instalar librerías arbitrarias por cliente. |
| Rendimiento | Se trata como restricción y auditoría transversal, no como reparación al final. Video atractivo no puede justificar cualquier peso. |
| Evaluación | Compilar, renderizar, inspeccionar, auditar, criticar, mutar y volver a renderizar; aprobación humana inicialmente. |
| Reproducibilidad | Una vez aprobado, guardar un **Design Lock** y compilar sin volver a solicitar creatividad al LLM. |
| Economía | Aproximar a cero el **código específico**, sin fingir que licencias, cómputo, selección de medios y revisión cuestan cero. |

### 0.3. Principios invariantes

- **La verdad no es un parámetro artístico.** Un modelo puede elegir cómo presentar una capacidad, nunca decidir que existe porque la categoría la hace plausible.
- **Categoría, modelo de negocio, capacidad, objeto comercial, módulo, componente y operador espacial son entidades diferentes.** Se definen formalmente más adelante.
- **Licencia y veracidad visual son pruebas separadas.** Poder usar una foto no significa poder presentarla como el local o producto del cliente.
- **Componentes estables, páginas distintas.** La diversidad nace de relaciones, composición, medios, proporciones y dirección de arte, no de un fork nuevo del runtime.
- **La IA propone; el motor valida y ejecuta.** Un LLM no puede añadir dependencias, código arbitrario, datos inventados o medios no autorizados.
- **No hacer pasar un prototipo bonito por una web operativa.** Preview frontend, diseño aprobado, sitio listo para publicar y sitio productivo son estados distintos.
- **Mejorar la máquina es más valioso que parchear un ejemplo.** Resolver un caso aislado no prueba generalización.

---

## 1. Fuentes disponibles, alcance del inventario y límites de certeza

### 1.1. Antecedentes técnicos documentados

El handoff `chat_handoff_101_website_design_compiler.md` documenta **dos trabajos complementarios**, todavía necesitados de verificación en el repositorio y de integración controlada:

**A. Sistema productivo `101-world-model`:** adquisición de evidencia, distinción entre observación y hecho publicable (Truth), Business Genome/Market Context, `SiteSpec`, `DesignProfile`, `ConstrainedCompositionEngine`, `CompilerBindingPlanner`, `WebsiteCompiler`, `@101/site-runtime`, Astro, navegador y `CustomerSiteAdequacyEvaluator`.

**B. Design Compiler experimental:** de v0.1 a v0.12; búsqueda semántica, geometría en Chromium, análisis raster, operadores de composición, gramática tipográfica, gramática de movimiento, crítica de capturas, mutación, análisis de focalidad/crop, ingesta OSS con procedencia y experimentos topológicos/geométricos.

El mismo handoff diferencia capacidades **documentadas y probadas en prototipos** de capacidades **integradas en producción**. En particular, señalaba como no demostrados a esa fecha la integración entre sistemas, resolución topológica responsive en producción, grandes volúmenes de componentes OSS efectivamente renderizables y calidad visual de cliente a escala. **No inferir el estado actual del repositorio desde ese documento histórico.**

La lista anterior es un **mapa para localizar y verificar**, no autorización para anunciar funcionalidades completadas. El Hito 0 debe buscar rutas, commits y tests reales.

### 1.2. Archivo adjunto de categorías

`message (4).txt` tiene **4.582 registros de datos** con columnas:

```text
source
category_field
category_value
provider_category_id
source_observations
business_candidates
other_observations
```

Las fuentes en este extracto son **Foursquare (890 filas), OSM (1.195) y Overture (2.497)**. Filas = combinaciones de fuente/campo/valor; **no** equivalen a 4.582 negocios o 4.582 categorías únicas. Las cuentas de `business_candidates` **no deben sumarse entre proveedores** para afirmar cuántos negocios únicos existen; fuentes pueden referirse al mismo establecimiento. El archivo también incluye observaciones que el pipeline clasificó como **no-negocio**, y categorías `Unknown`.

Existe una categorización normalizada `101.normalized_category`, pero también campos originales de granularidad muy distinta (`foursquare.category`, `osm.shop`, `osm.amenity`, `overture.taxonomy.*`). Hay que conservar ambos niveles: uno para el arquetipo común y otro para detalles operativos del subtipo.

Cobertura visible de alto nivel: restaurantes/comida, bar/café/panadería/mercados, retail (ferretería, ropa, medicamentos, electrónica, muebles, mascotas), belleza, fitness, odontología y otras clínicas, veterinaria, talleres/autopartes/concesionarios, hotelería, entretenimiento y eventos, educación, servicios profesionales/legales/contables, construcción/hogar, manufactura/B2B, transporte y finanzas.

**Ejemplos del archivo, no censo deduplicado:**

| Fuente/campo | Valor | `business_candidates` en esa fuente/categoría |
|---|---|---:|
| Foursquare / normalized | `Food/Restaurant` | 20.122 |
| Foursquare / normalized | `Professional Services/Other Professional` | 18.725 |
| Foursquare / normalized | `Retail/Other Retail` | 16.266 |
| Overture / normalized | `Retail/Other Retail` | 20.883 |
| Overture / normalized | `Food/Restaurant` | 18.264 |
| Overture / normalized | `Beauty and Wellness/Fitness and Wellness` | 4.766 |
| OSM / normalized | `Automotive/Repair` | 1.131 |
| Overture / `taxonomy.hierarchy_level_4` | `hardware_store` | 1.193 |
| Foursquare / `foursquare.category` | `Sports and Recreation > Gym and Studio > Gym` | 480 |

Esas frecuencias ayudan a decidir qué arquetipos estudiar primero, **no** confirman capacidades concretas ni tamaño de mercado deduplicado. La aplicación futura del resolvedor debe aceptar taxonomías nuevas y categorías desconocidas sin romper el build.

### 1.3. Qué sabemos y qué no

**Sabemos por el usuario:** la extracción del negocio ya existe por separado, incluye imágenes y quizá otros medios, pero la integración queda pendiente; se quiere una fábrica multivertical, diseño de alto nivel, variedad real, calidad audiovisual, base común y bajo coste marginal.

**Sabemos por documentación histórica:** existen rutas de Truth→SiteSpec→compilación y prototipos de gramática/búsqueda/auditoría, con niveles dispares de madurez.

**Todavía debemos verificar:** HEAD y worktree activos, código reutilizable, cobertura de tests, contratos concretos actuales, disponibilidad de DB, compatibilidad entre las dos ramas de trabajo, permisos de adquisición de proveedores y calidad real de la salida visual.

---

## 2. Dos circuitos distintos: desarrollo del motor y ejecución por negocio

### 2.1. Circuito de plataforma (se construye y mejora una vez)

```text
Verificar sistemas existentes
  → contratos y taxonomía
  → ontología y registry de capacidades
  → políticas de medios y acceso a proveedores
  → corpus de referencias y design grammar
  → componentes certificados
  → runtime común, compilador y auditorías
  → fixtures y benchmarks multiverticales
  → experimentación y aprendizaje
  → versionado y publicación de nuevas capacidades
```

Este circuito absorbe trabajo duro: programar un catálogo, especificar una reserva visual, escribir adaptadores, añadir un operador, negociar un proveedor, mejorar el solver, probar el runtime. **No se repite para cada negocio.**

### 2.2. Circuito de producción de una página (costo marginal bajo)

```text
BusinessInput validado
  → resolver actividad/arquetipos
  → derivar y comprobar capacidades
  → producir SitePlan semántico
  → examinar fotos/video existentes
  ↔ definir necesidades de medios y dirección preliminar
  → buscar/adquirir medios autorizados faltantes
  → proponer varias direcciones artísticas
  → componer variantes dentro del registry
  → compilar a Astro / HTML / CSS
  → auditar verdad, permisos, contenido, frontend, rendimiento y estética
  → reparar dentro de un presupuesto
  → escoger finalistas diversos
  → elección humana y registro de preferencias
  → design.lock.json y rebuild determinista
```

La generación debe tener límites explícitos de renders, tokens, búsqueda, horas humanas y costos. Si no hay un candidato válido y bueno, retorna un bloqueo documentado: **no maquillar un fracaso como éxito.**

---

## 3. Modelo conceptual: siete objetos que NO deben mezclarse

| Concepto | Definición | Ejemplo ferretería | Ejemplo gimnasio |
|---|---|---|---|
| **Categoría** | Etiqueta de una taxonomía de fuente o 101. | `hardware_store` | `gym` |
| **Arquetipo** | Modelo operativo/comercial general, **combinable**. | `product_retail` y quizá `local_service` | `membership_business` y `scheduled_classes` |
| **Capacidad** | Algo que el negocio realmente ofrece o puede hacer, con evidencia y estado. | `catalog`, `delivery`, `quote_request` | `membership`, `class_schedule` |
| **Objeto comercial** | Información estructurada que soporta una capacidad. | `Product`, `ProductCategory` | `MembershipPlan`, `ClassSession` |
| **Módulo semántico** | Bloque de contenido/acción que el sitio necesita representar. | `CatalogModule` | `MembershipModule` |
| **Operador visual** | Regla de composición sin semántica comercial propia. | `Rail`, `Editorial`, `Split` | `Stage`, `Sequence`, `Monument` |
| **Componente runtime** | Código compartido que renderiza estados y accesibilidad. | `ProductGrid`, `ActionLink` | `ScheduleView`, `PlanTable` |

No se puede implementar `if gym: use black page`, ni `if hardware: enable_delivery`. Categoría y arquetipo dan **hipótesis de relevancia**; solamente datos aprobados habilitan la capacidad concreta.

Un negocio puede pertenecer a varios arquetipos: una panadería con café, pedidos y catering; un veterinario con clínica y tienda; un gimnasio que vende suplementos; un hotel con restaurante; una ferretería con instalación y reparto. El sistema debe admitir combinaciones sin multiplicar implementaciones.

---

## 4. Contrato de entrada V1: frontera con upstream

### 4.1. Responsabilidades

**Upstream** conserva autoridad sobre: identidad de negocio y sucursal, origen de datos, relación entre fuentes, verificación/publicabilidad, clasificación observada, oferta real, precios/horarios/contactos, asociaciones y medios propios recolectados. **No decide layout ni instala componentes.**

**Website Compiler** define el esquema que necesita; valida; construye arquetipos y `CapabilityProfile`; propone el `SitePlan`; encuentra multimedia adicional si hace falta; desarrolla dirección de arte y páginas; conserva bindings de contenido; audita. **No convierte hipótesis en hechos publicables.**

Se prioriza construir un **adaptador versionado desde el `SiteSpec` existente**, no reemplazar Truth o crear una segunda base de hechos incompatible.

### 4.2. Esquemas y separación de autoridad

Contratos versionados sugeridos:

```text
BusinessInputV1          entrada factual de upstream
BusinessProfileV1        interpretación de actividad/arquetipos
CapabilityProfileV1      capacidades y estado de evidencia
SiteRequirementsV1       obligaciones de contenido/acción
SitePlanV1               rutas + módulos, SIN estética
MediaManifestV1          archivos existentes y adquiridos + derechos
ArtDirectionV1           hipótesis de diseño
DesignPlanV1             árbol de operadores + tokens + bindings
AuditReportV1            fallos, observaciones, pruebas y métricas
DesignLockV1             composición final reproducible
```

Versionar y validar con esquemas legibles por máquina (por ejemplo JSON Schema o Zod), pruebas de consumidor/productor, migraciones explícitas e identificadores estables. Usar SemVer o revisiones con reglas documentadas: cambios incompatibles no se introducen silenciosamente.

### 4.3. Campos mínimos de `BusinessInputV1`

**Identidad y clasificación:** `business_id`, nombre publicable, alias aprobados, organización/marca y sucursales, estado, lenguaje(s), categorías originales con sus códigos y fuente, categoría normalizada, evidencia, grado de confianza de clasificación, atributos verificados de posicionamiento cuando existan.

**Localización/contacto:** sedes, coordenadas y direcciones aprobadas, zona atendida (puede ser negocio sin local), horarios y excepciones, teléfono, email, WhatsApp, perfiles oficiales, links, política de visitas.

**Oferta:** lista de `Offering` tipada: productos, servicios, menú, citas, profesionales, clases, horarios de clases, membresías, habitaciones, amenidades, eventos, tarifas, paquetes, cotizaciones. Solo los campos que apliquen; precios, moneda, vigencia y variantes cuando estén documentados.

**Operación comercial:** capacidades verificadas (reserva, cita, catálogo, compra, entrega, retiro, inscripción, cotización, contacto, visita, etc.), estado y alcance por sucursal; destinos de acción aprobados y requisitos si existen. La ausencia de integración técnica no equivale a ausencia de capacidad comercial.

**Confianza/publicación:** identificadores de afirmaciones, `PublicationDecision`/estado de aprobación de upstream, fuente, fecha de corte, conflictos, expiración o necesidad de actualización, restricciones legales o editoriales.

**Medios disponibles:** `asset_id`, origen, URI/archivo, resolución, tipo, entidad/sucursal vinculada, derechos documentados o desconocidos, restricciones y metadatos conocidos. Que el extractor entregue una URL **no transfiere automáticamente derechos de uso**.

**Preferencias/restricciones:** identidad de marca existente cuando esté aprobada, logotipos y sus usos, idiomas, accesibilidad relevante, requisitos regulatorios por actividad y cualquier prohibición visual/documental constatada.

### 4.4. Estados de campo y capacidad

No usar únicamente booleanos. Para afirmaciones operativas:

```text
CONFIRMED_PRESENT       aprobado y vigente
CONFIRMED_ABSENT        ausencia respaldada explícitamente
UNKNOWN                 sin evidencia suficiente
CONFLICTED              evidencia contradictoria
WITHHELD                conocido, pero no autorizado para publicación
```

Separadamente, el frontend tiene su propio estado de implementación:

```text
FRONTEND_SUPPORTED      representación de UI disponible
BACKEND_NOT_CONNECTED   flujo operativo aún no integrado
BACKEND_CONNECTED       adaptador real conectado y probado (fase futura)
NOT_SUPPORTED_YET       aún no existe el módulo en el registry
```

**Dos ejes independientes.** Un negocio puede tener reservas confirmadas pero nuestro backend todavía no conectado. En preview podemos diseñar el espacio; **no publicamos un botón que simule confirmar una reserva**.

### 4.5. Insuficiencia de datos

El compilador debe retornar un reporte accionable, no fabricar contenido:

```yaml
need: service_or_product_list
scope: branch-123
reason: required_for_supported_capability
status: missing_publishable_evidence
requested_from: upstream
blocks: [service_catalog_page]
```

Los módulos opcionales pueden omitirse. Los módulos imprescindibles para el caso y respaldados por datos deben conservarse. Si no hay suficientes datos esenciales para una web honesta, el estado es `CONTENT_BLOCKED`, aunque una composición vacía pueda verse bonita.

### 4.6. Ejemplo ilustrativo de contrato (datos ficticios)

```json
{
  "schema_version": "1.0.0",
  "business_id": "fixture-ferreteria-001",
  "identity": {
    "name": { "value": "Ferretería Ejemplo", "publishable": true, "fact_id": "f-name" }
  },
  "category_observations": [
    { "source": "overture", "field": "taxonomy.primary", "value": "hardware_store" },
    { "source": "osm", "field": "shop", "value": "hardware" }
  ],
  "locations": [{ "id": "branch-1", "address_fact_id": "f-address" }],
  "offerings": [
    { "id": "category-herramientas", "kind": "product_category", "publishable": true }
  ],
  "business_capabilities": {
    "catalog": { "status": "CONFIRMED_PRESENT", "evidence_ids": ["f-catalog"] },
    "delivery": { "status": "UNKNOWN" },
    "quote_request": { "status": "CONFIRMED_PRESENT", "evidence_ids": ["f-quote"] },
    "checkout": { "status": "CONFIRMED_ABSENT", "evidence_ids": ["f-no-checkout"] }
  },
  "existing_media": [
    { "id": "m-1", "kind": "image", "business_relation": "branch-1", "rights_status": "UNKNOWN" }
  ]
}
```

Esto **no** es el esquema final del upstream; es una interfaz candidata para acordar campos y validar restricciones. Los ejemplos ficticios no prueban nada sobre negocios reales.

---

## 5. Clasificación, taxonomía y arquetipos

### 5.1. Procesamiento de taxonomías heterogéneas

La secuencia propuesta:

```text
categorías observadas (OSM/Foursquare/Overture/otras)
  → conservar literal y código del proveedor
  → normalización a taxonomía 101
  → recuperar subtipos y atributos relevantes
  → construir hipótesis de uno o varios arquetipos
  → contrastar contra evidencia real de oferta y operación
  → producir BusinessProfile con trazabilidad y confianza
```

No perder categoría original en la normalización: `Retail` puede ocultar ferretería, floristería, tienda de ropa, artículos para mascotas o farmacia. No inferir que `Office`, `Non Business`, `Unknown`, edificios, carreteras o parques sean automáticamente clientes comerciales elegibles. La actividad puede quedar `UNRESOLVED`: el pipeline debe degradar honestamente y solicitar aclaración.

### 5.2. Arquetipos iniciales **combinables**, no plantillas visuales

| Arquetipo | Modelo que describe | Capacidades que amerita investigar, no asumir |
|---|---|---|
| `food_hospitality` | restaurante, cafetería, bar, panadería | menú, reservas, pedido, entrega, horarios |
| `product_retail` | ferretería, boutique, autopartes, mercado | catálogo, categorías, variantes, compra, delivery/retiro, cotización |
| `appointment_service` | odontología, salón, óptica, consultorio | servicios, profesionales, cita, preparación, políticas |
| `membership_and_classes` | gimnasio, yoga, club, academia | membresías, clases, calendarios, instructores |
| `lodging` | hotel, hostel, alojamiento | habitaciones, amenidades, reglas de estancia, disponibilidad |
| `field_service_and_quote` | construcción, reparación, limpieza a domicilio | servicios, zona atendida, cotización, portafolio, urgencias cuando proceda |
| `vehicle_service` | taller, lavado, mantenimiento | servicios por tipo de vehículo, cita, cotización |
| `professional_advisory` | abogados, contadores, consultores | especialidades, profesionales, consulta, credenciales verificadas |
| `education_programs` | institutos y educación privada | cursos, programas, horarios, inscripción |
| `events_and_entertainment` | venue, teatro, nightclub, eventos | agenda, entradas, reservas, normas de acceso |
| `industrial_b2b` | fabricantes, proveedores, distribuidores | líneas de producto, especificaciones, capacidad, cotización |
| `property_and_spaces` | inmobiliaria, coworking, alquiler de espacios | inventario de unidades/espacios, atributos, visita, disponibilidad |
| `transport_and_logistics` | operadores de transporte y reparto | rutas/servicios, coberturas, consulta/cotización |
| `regulated_services` | atención sanitaria, finanzas, otros regulados | avisos, profesionales/licencias pertinentes, limitaciones publicitarias |

El último arquetipo **no sustituye** a los demás: funciona como modificador de riesgo, contenido, aprobación y publicidad. Los modelos pueden convivir. La ontología evoluciona cuando aparecen necesidades reales, sin crear una rama de código por cada subcategoría.

### 5.3. Resolución multietiqueta

La salida puede ser:

```yaml
archetypes:
  - id: product_retail
    relevance: primary
  - id: field_service_and_quote
    relevance: secondary
regulated_domains: []
classification:
  status: resolved
  evidence: [category_observations, approved_offerings]
```

El puntaje de clasificación puede ordenar hipótesis o solicitar revisión; **no reemplaza** pruebas de que vende un producto específico, hace domicilios o presta un servicio. El router puede tener reglas deterministas basadas en taxonomía y un clasificador asistido por LLM para casos ambiguos, siempre sin publicar resultados no sustentados.

### 5.4. Responsabilidades del `BusinessProfile`

Debe resumir, sin añadir hechos: rama o local involucrado, arquetipos y sus justificaciones, objetos de oferta existentes, necesidades de contacto y visita, capacidades candidatas/verificadas, datos presentes/faltantes y restricciones. Es el contexto que necesita el planner, no una nueva fuente de autoridad factual.

---

## 6. Capability Ontology: qué puede hacer el negocio

### 6.1. Separar **candidata**, **publicable** y **conectada**

Ejemplo correcto para ferretería:

```text
Categoría hardware_store → catalog es razonable de INVESTIGAR
Datos upstream → catalog CONFIRMED_PRESENT
Datos upstream → delivery UNKNOWN
Datos upstream → quote_request CONFIRMED_PRESENT
Frontend → CatalogModule SUPPORTED
Frontend → QuoteRequestShell SUPPORTED
Backend → NOT_CONNECTED
```

Un gimnasio podría tener una tienda y ofrecer entregas; entonces tendrá ambas capacidades si están probadas. La frase coloquial “los gimnasios no tienen domicilios” sirve para explicar el error típico, **no** es una regla universal.

### 6.2. Inventario inicial de capacidades semánticas

**Información universal:** `identity`, `about`, `locations`, `opening_hours`, `contact_channels`, `social_profiles`, `reputation`, `gallery` (solo si existen datos/medios aptos). 

**Oferta:** `service_catalog`, `product_catalog`, `menu`, `product_variants`, `price_list`, `packages`, `rooms`, `programs`, `professional_profiles`, `trainer_profiles`, `portfolio`, `case_studies` verificables.

**Acciones:** `reservation`, `appointment`, `quote_request`, `contact_request`, `purchase`, `order`, `delivery`, `pickup`, `membership_signup`, `class_enrollment`, `ticketing`, `room_booking`, `visit_booking`, `service_request`.

**Información operativa:** `class_schedule`, `events`, `availability_display`, `service_area`, `delivery_policy`, `visit_policy`, `payment_methods`, `amenities`, `accessibility_info`, `branches`, `faqs`, `documents`.

Esta es una **biblioteca de nombres y contratos previstos**, no una declaración de que cada uno está implementado hoy.

### 6.3. Diferencias que no debemos colapsar

- `catalog` **≠** `checkout`: mostrar productos no demuestra que exista e-commerce.
- `menu` **≠** `online_ordering`: un restaurante puede publicar menú y no aceptar pedidos online.
- `reservation` **≠** `appointment`: reservar mesa no es agendar una consulta de odontología; compartirán piezas de UI, no necesariamente reglas de negocio.
- `delivery` **≠** `service_area`: un electricista puede visitar casas, pero eso no equivale a entregar productos.
- `membership` **≠** `class_schedule`: vender planes no implica tener clases programadas.
- `price_list` **≠** `fixed_quote`: mostrar rangos no equivale a cerrar presupuestos.
- `location` **≠** `storefront`: un servicio remoto puede no tener atención física al público.
- `front_end_capability` **≠** `back_end_integration`: el diseño puede existir antes de conectar un proveedor real.

### 6.4. Contrato de cada capability

Cada `CapabilitySpec` define:

```yaml
id: product_catalog
version: 1.0.0
commercial_objects: [Product, ProductCategory]
required_fact_kinds: [product_or_category_identity]
optional_fact_kinds: [price, variant, image, sku, brand]
applicable_archetypes: [product_retail, industrial_b2b]
preview_variants: [editorial_list, rail, structured_grid]
frontend_interactions: [category_navigation]
backend_adapter: null  # futuro
routes: [/catalogo]
qa:
  - category_and_product_bindings_valid
  - no_fake_availability
  - catalog_items_approved
  - accessible_product_navigation
```

Para una capacidad que exija campos faltantes se produce `MISSING_INPUT`, no se rellena con ejemplos inventados. Los contratos tienen versiones y tests; incorporar una capacidad nueva en el registry es una inversión de plataforma, no una excepción por cliente.

---

## 7. Matriz multivertical de necesidades (borrador del planner)

**Interpretación:** la tabla registra módulos usualmente pertinentes para estudiar. Nada aparece en un sitio real sin ser relevante y estar respaldado. Algunas obligaciones son condicionales a que exista una oferta publicable, acción real, sede o modalidad informada.

| Tipo/arquetipo de negocio | Objeto/oferta a representar | Módulos semánticos prioritarios | Acciones candidatas, sujetas a evidencia |
|---|---|---|---|
| Restaurante / café / panadería | Menú, platos, categorías, sedes | Presentación, menú, visita/horarios, fotos auténticas si hay | Mesa, pedir, retirar, entregar, contacto |
| Bar / nightclub / venue | Programación, espacios, consumo cuando aplique | Identidad, fechas, acceso, localización, galería | Entradas, mesas, reserva, consulta |
| Ferretería / suministros | Productos, familias, referencias, marcas aprobadas | Catálogo, búsqueda/navegación, sedes, modalidades | Compra, cotización, retiro, reparto |
| Boutique / ropa | Categorías, prendas, variantes | Colección, catálogo, ficha, tamaños si existen | Compra, consulta, retiro |
| Supermercado / farmacia | Catálogo, productos, sedes | Categorías, productos, horarios, políticas | Compra/reparto/retiro solo aprobados; cuidado regulatorio |
| Gimnasio / yoga / pilates | Planes, clases, entrenadores, instalación | Membresías, clases, instalaciones, horarios | Inscripción, clase de prueba, agenda |
| Odontología / consultorio | Servicios clínicos, equipo autorizado, sedes | Tratamientos, profesionales, contacto, ubicación, información responsable | Solicitar cita, consulta |
| Veterinaria | Servicios veterinarios, equipo, horarios | Servicios, sede, profesionales, atención | Cita, urgencias solo si confirmado, posible tienda |
| Salón / barbería / spa | Servicios, profesionales, precios si constan | Portafolio, servicios, equipo, sedes | Cita, consulta, compra si vende productos |
| Taller / lavado de vehículos | Reparaciones/mantenimiento, tipos de vehículos | Servicios, especialidades, localización | Cita, presupuesto, asistencia si confirmada |
| Hotel / hostal | Tipos de habitaciones, amenidades, reglas | Habitaciones, espacios, servicios, políticas, ubicación | Reservar estancia, consulta disponibilidad |
| Abogado / contador / consultor | Especialidades, profesionales, credenciales autorizadas | Servicios, equipo, experiencia comprobable, consulta | Solicitud de consulta/cotización |
| Construcción / servicios del hogar | Servicios, zonas atendidas, obras demostrables | Portafolio, oferta, cobertura, procesos | Cotización, visita, contacto |
| Fabricante / B2B industrial | Líneas de producto, especificaciones | Catálogo técnico, capacidades industriales verificadas, documentos | Cotización, contacto comercial |
| Institución educativa | Programas, calendarios, sedes | Cursos, descripción, fechas, instructores cuando existan | Inscripción, consulta |
| Inmobiliaria / coworking | Propiedades o espacios, atributos | Inventario, fichas, ubicación, reglas | Agendar visita, consulta disponibilidad |
| Agencia / entretenimiento / eventos | Servicios o agenda, espacios, obras autorizadas | Eventos/portafolio, equipo/servicios, acceso | Consulta, entradas, reserva de espacio |
| Logística / transporte | Rutas o servicios disponibles, cobertura | Modalidades, cobertura, condiciones | Consulta de envío, cotización |
| Lavandería / reparación de objetos | Servicios, condiciones, sedes | Lista de servicios, operación, tiempos solo comprobados | Recogida, cotización, contacto |

**Multiuso:** hotel con restaurante puede necesitar `rooms` + `menu`; farmacia con e-commerce requiere `product_catalog` + `purchase` sujeto a permisos; gimnasio con tienda necesita `membership` + `catalog` pero no adquiere `delivery` automáticamente.

**Densidad editorial:** un laboratorio B2B puede requerir especificaciones y descargas; una tienda con cientos de referencias necesita navegación densa; un restaurante de autor puede necesitar silencio visual. La estética no debe sacrificar contenido indispensable para reproducir el estilo de otra categoría.

---

## 8. `SiteRequirementsV1` y `SitePlanV1`: decidir **qué** existe antes de decidir **cómo se ve**

### 8.1. Requisitos y prioridades

El `SiteRequirementsPlanner` cruza arquetipos, capacidades verificadas, objetos publicados, sede y destino de acción. Emite requisitos de contenido explícitos:

- `REQUIRED_IF_PRESENT`: debe estar representado si un hecho/capacidad está aprobado y es central para ese tipo de negocio.
- `CONDITIONAL`: incluir solamente si hay datos suficientes y cumple una condición.
- `OPTIONAL`: aporta valor, pero no es imprescindible.
- `BLOCKED`: no hay autorización, datos o soporte técnico mínimo para presentarlo.

`required` se aplica a la experiencia semántica, no implica una ruta o sección propia. Por ejemplo, horarios y ubicación pueden convivir en el mismo bloque; dos sucursales pueden requerir navegación por sedes.

### 8.2. Capas de página

El plan tiene tres escalas:

1. **Sitio:** sitemap, sedes, idiomas, identidad, navegación, rutas y relaciones entre páginas.
2. **Página:** intención comunicativa, obligaciones semánticas, prioridad de información, lista de módulos y estados.
3. **Módulo:** datos vinculados, variantes de frontend admitidas, requisitos de interacción y accesibilidad.

Separar `SitePlan` de `DesignPlan` permite rediseñar un sitio sin perder el contenido, y cambiar de backend posteriormente sin redibujar toda la presentación.

### 8.3. Ejemplo de `SitePlan` sin decisiones estéticas

```json
{
  "schema_version": "1.0.0",
  "business_id": "fixture-ferreteria-001",
  "archetypes": ["product_retail", "field_service_and_quote"],
  "capabilities": ["product_catalog", "quote_request", "locations"],
  "pages": [
    {
      "path": "/",
      "modules": [
        { "id": "identity", "required": true },
        { "id": "product_categories", "required": true },
        { "id": "quote_action", "required": true },
        { "id": "location_and_contact", "required": true }
      ]
    },
    {
      "path": "/catalogo",
      "modules": [{ "id": "product_catalog", "required": true }]
    }
  ],
  "excluded_capabilities": {
    "delivery": "UNKNOWN",
    "checkout": "CONFIRMED_ABSENT"
  }
}
```

Las rutas se emiten únicamente cuando disponen de contenido sustantivo publicable. Conservar la corrección histórica de 101: un candidato de ruta bloqueado permanece en los diagnósticos, **no** se convierte en una página vacía para clientes.

### 8.4. Restricción de esta fase: frontend sin backend inventado

Para cada módulo marcar:

```text
VISUAL_PREVIEW_ONLY
STATIC_PUBLIC_INFORMATION
REAL_APPROVED_EXTERNAL_LINK
LIVE_CONNECTED_INTEGRATION   (posterior)
```

El preview puede utilizar datos de prueba claramente identificados y mostrar cómo se vería un flujo. En una web entregable no incluir controles engañosos que aparenten efectuar una compra, reservar una mesa o confirmar una cita sin backend; utilizar información estática honesta, enlaces reales aprobados o retener la acción hasta integrarla.

Menú desplegable, tabs locales, galería, controles de video o navegación sí pueden funcionar en el frontend, con comportamiento y accesibilidad reales.

---

## 9. Preservación de verdad y trazabilidad del contenido

El renderer debe consumir referencias a hechos aprobados, no texto libre generado como supuesto de realidad. Por cada elemento sustantivo:

```text
Observation → Truth/PublicationDecision → BusinessInput/SiteSpec
→ Requirement → SitePlan → DesignPlan binding → rendered DOM
```

Mantener una `binding-report` comparable a la del sistema productivo: ID de afirmación, ubicación prevista, ruta emitida, selector/snapshot final, estado de publicación y motivo si se retuvo. La presencia en el plan **no prueba** que sobrevivió al HTML: auditar la salida compilada.

Reglas:

- No inventar precios, descuentos, tiempos de envío, cobertura, disponibilidad, menús, tratamientos, credenciales, biografías ni testimonios.
- No publicar afirmaciones regulatorias, médicas, financieras o de resultados sin fuente aprobada, contexto y revisión que corresponda.
- No confundir evidencia de una sucursal con la de toda la marca.
- No tomar `UNKNOWN` como `FALSE` ni como `TRUE`.
- No aumentar customer-readiness repitiendo el mismo dato de identidad varias veces.
- No fabricar fotos documentales o “antes/después” de procedimientos mediante stock o generación.
- No copiar fragmentos de web ajena para llenar secciones sin derecho o atribución.
- Ante conflictos o vencimiento: bloquear el hecho, degradar el módulo o solicitar nueva evidencia.

Un buen diseño debe poder trabajar con información escasa **sin exagerar**: menor cantidad de módulos, tipografía y composición más fuertes, o estado `CONTENT_BLOCKED` cuando el contenido es insuficiente.

---

## 10. Media Engine: amplitud de catálogo, calidad, coherencia y derechos

### 10.1. Prioridad de medios

El upstream **sí entrega fotografías y otros recursos cuando los tiene**. Primera acción: auditar calidad y derechos de ese material. Segunda: encontrar huecos de cobertura. Tercera: adquirir externamente recursos de alta calidad y uso legalmente permitido. No se depende de que el cliente mande material directamente al comienzo; podría ser alternativa futura voluntaria, junto con fotografía encargada.

```text
media upstream → inspección factual/visual/derechos
                     ↕
necesidades de dirección artística / coverage gap
                     ↓
búsqueda amplia de catálogos elegibles
                     ↓
shortlist, coherencia, permisos, costo
                     ↓
licencia aplicable al cliente y uso concreto
                     ↓
descarga y transformación autorizada
                     ↓
MediaManifest con linaje completo
```

### 10.2. Tres entidades obligatorias

**`MediaAsset` (objeto digital):** fuente, ID externo, hash original, URI, modalidad (foto/video/audio), dimensiones, duración, bitrate/codec, miniaturas, sujeto, luz, composición, focalidad, espacio negativo, recortabilidad, tratamiento, papel documental/ilustrativo, sucursal asociada cuando corresponda, versiones, coste, clasificación y provenance.

**`LicenseGrant` (permiso):** tipo/titular de licencia, documento y versión, proveedor, comprador, cliente, proyecto, activo, extensión territorial/temporal, uso web comercial, permiso de múltiples clientes y reutilización, redistribución/sublicencia, exclusividad cuando exista, atribución, modificaciones, derechos de imagen/model/property releases, automatización de acceso/descarga, procesamiento con IA y límites de almacenamiento/retención. **No asumir que licencia comercial equivale a uso irrestricto.**

**`MediaUsage` (instancia):** sitio, sucursal, página, módulo, asset, crop, variante, finalidad semántica, rol `DOCUMENTARY|ILLUSTRATIVE|ATMOSPHERIC|TEXTURE|ABSTRACT`, licencia concreta que ampara ese uso, vínculo a cliente y estado.

Se almacena cada derivado como descendiente del original: el hecho de convertir a AVIF/MP4 no elimina restricciones de licencia.

### 10.3. Truthfulness visual, independiente de la licencia

**Documental:** la imagen demuestra algo sobre el negocio real (fachada, interior, plato, profesional, producto, instalación). Requiere origen vinculado y autorización suficiente.

**Ilustrativo/ambiental:** comunica materialidad, contexto genérico o atmósfera, pero **no afirma** que ese espacio, persona, plato o máquina pertenece al cliente. Nunca presentarlo bajo textos que creen tal implicación.

Una imagen de stock de un restaurante vacío **no** puede titularse “Nuestro salón”. Una imagen genérica de pesas **no** puede sustituir honestamente la instalación de un gimnasio. Una fotografía de un procedimiento no verificado **no** puede representar el trabajo de una clínica. Si no hay medios documentales aptos, diseñar una presentación distinta o bloquear esa sección; no simular evidencia.

### 10.4. Catálogo grande **≠** descarga masiva

El objetivo es tener acceso a una **oferta enorme y de primera calidad**, no almacenar millones de archivos sin necesidad. Conectar APIs, búsquedas autorizadas o acuerdos comerciales; recorrer metadatos y previews; licenciar y descargar únicamente finalistas pertinentes. Cachear conforme a términos. No extraer contenidos de Google Maps, redes sociales, sitios de clientes o plataformas de video como si su presencia pública concediera derechos generales de redistribución.

### 10.5. Criterios para evaluar proveedores

La matriz de negociación/legal debe registrar de forma independiente:

| Dimensión | Pregunta verificable |
|---|---|
| Calidad | ¿Tiene fotografía/video con dirección visual excelente y material continuo de una misma sesión? |
| Cobertura | ¿Tiene suficiente material útil para restaurantes, retail, fitness, salud, servicios, manufactura, etc.? |
| Licencia comercial | ¿Cubre páginas de clientes con las condiciones exactas pretendidas? |
| Multi-cliente | ¿Exige licenciar cada activo por cliente, proyecto o uso? |
| Acceso automatizado | ¿API/documentación/acuerdo permiten consulta, descarga y procesamiento automatizado? |
| IA | ¿Qué permite respecto a clasificación, embedding, vision, edición y entrenamiento? Son actos distintos. |
| Derechos terceros | ¿Model/property releases? ¿Marcas, diseños, personas o lugares reconocibles? |
| Modificaciones | ¿Se permiten crop, color grading, recorte y transcodificación? |
| Restricciones | ¿Contenido editorial-only, atribución, territorio, transferibilidad, volumen, revocación? |
| Economía | ¿Costo por asset/licencia, cuotas, tarifas enterprise, almacenamiento y auditoría? |
| Retirada | ¿Podemos encontrar y reemplazar todos los usos afectados? |

**Proveedores a investigar con sus términos vigentes:** Adobe Stock, Pexels, Envato Elements, Artlist, Filmsupply y otros que superen el benchmark. **No están aprobados para nuestro uso automatizado ni para licenciamiento multi-cliente por aparecer aquí.** El documento de restaurante V0.1 conserva referencias a políticas y APIs oficiales para realizar la due diligence; confirmar cada condición vigente antes de construir un conector, especialmente automatización y derechos por cliente.

Para audio, aplicar auditoría separada de composición/grabación/master, territorios, sincronización, reproducción en web y claims. Por defecto, los videos hero se sirven **silenciados**; no introducir autoplay audible.

### 10.6. Detección de huecos visuales: `MediaBrief`

La búsqueda se guía por roles compositivos, no por una query genérica “fotos de gym”:

```yaml
site: fixture-gym-001
visual_needs:
  - role: atmospheric_hero
    media_type: video
    subject: generic_human_movement
    aspect_preference: landscape
    negative_space: left
    legal_representation: illustrative_only
  - role: detail_sequence
    media_type: image
    count: 3
    mood: tactile_contemporary
    crop_support: [portrait, square]
constraints:
  no_implication_of_actual_facilities: true
  mobile_alternative_required: true
  target_cost_class: budgeted
```

La dirección preliminar puede modificarse si no hay medios aptos. **Relación bidireccional:** disponibilidad de imágenes informa al diseño, y necesidades visuales informan la búsqueda.

### 10.7. Calidad y coherencia de conjuntos

Evaluar:

- resolución **útil tras crop**, compresión y foco, no solo pixeles de origen;
- composición, orientación, focalidad, espacio negativo, legibilidad del sujeto;
- color/luz, contraste, temperatura, grano y continuidad de textura;
- coherencia entre tomas, personas y escenas; evitar mosaicos de campañas incompatibles;
- narrativa audiovisual (apertura/ritmo/detalle/cierre) cuando hay video;
- aptitud para móvil y variantes horizontales/verticales;
- ausencia de marcas o elementos que creen afirmaciones engañosas;
- costo, licencia, procesamiento IA autorizado y procedencia;
- preferencias visuales del proyecto: excelente video puede justificar una composición cinematográfica, pero no necesariamente un video en cada vertical.

### 10.8. Pipeline técnico de medios

```text
catalog preview / fuente upstream
→ archivo original autorizado
→ hash + manifiesto + licencia
→ análisis imagen/video/metadatos + comprobación manual donde haga falta
→ composición con focal points y crop-safe regions
→ derivados responsive + formatos apropiados
→ poster y fallback para video
→ referencias inmutables en DesignPlan/DesignLock
→ load strategy por viewport y prioridad
→ medición de transferencias reales
```

Imágenes: `srcset`/`sizes`, AVIF/WebP con fallback cuando corresponda, dimensiones explícitas, lazy fuera del fold y carga prioritaria **solo** del principal recurso LCP. Audio/video: posters, rendiciones, carga diferida/controlada, reducción de movimiento y opción de pausa; compresión y formatos probados en navegadores objetivo. **Poster no implica que autoplay no descargue el video.** No enviar originales 4K por defecto al móvil.

### 10.9. Política de insuficiencia

Si no encontramos material documental o ilustrativo defendible, el sistema puede: priorizar tipografía y diseño gráfico, usar iconografía/ilustración propia con derechos, reducir medios o devolver `MEDIA_BLOCKED`. Nunca representar productos, personal, resultados médicos, espacios, infraestructura o procedimientos inexistentes como auténticos. Una sesión fotográfica comisionada puede ser ruta comercial futura para casos donde stock jamás será honesto o suficiente.

---
## 11. Reference Dataset y aprendizaje de dirección de arte

### 11.1. La investigación inicial pertenece a restaurantes, no a todos los sectores

En el trabajo de referencias de restaurantes, el usuario expresó preferencias reales. Conservarlas **literalmente** sin sustituirlas por una nota numérica inventada:

| Referencia | Juicio registrado | Implicación legítima para el corpus |
|---|---|---|
| **Osip** | Una de las favoritas más claras. | Prioridad de análisis visual completo. |
| **Central Restaurante** | Una de las favoritas más claras. | Prioridad de análisis visual completo. |
| **KOL** | Fue la favorita declarada en una ronda. | Prioridad de análisis; estudiar diseño gráfico y página entera. |
| **Asador Etxebarri** | Gustó mucho. | Referencia visual positiva fuerte. |
| **Aira** | Gustó sobre todo por el **video**. | Etiquetar aceptación del tratamiento audiovisual, no extrapolar al resto del sitio. |
| **Padella** | Gustó mucho al comienzo. | Referencia de lenguaje visual real de restaurante. |
| **Noma** | Gustó mucho al comienzo. | Referencia de lenguaje visual real de restaurante. |
| **LUCA** | “Linda”. | Referencia positiva. |
| **MIL Centro** | Gustó algo; fue la única aceptada parcialmente en un lote. | Referencia moderada, con contexto. |
| **ÄNG** | “Bien”. | Referencia moderada. |
| **Kadeau** | “Bien”. | Referencia moderada. |
| **Aponiente, menú 2026** | “Tiene cosas interesantes”. | **Ideas/secciones** aprobadas para disección, no aprobación integral. |
| **Khufu's** | “Tiene cosas interesantes”. | **Ideas/secciones** aprobadas para disección, no aprobación integral. |
| **The Clove Club** | “Suave”. | No etiquetar como rechazo absoluto ni como favorita. |
| **Frantzén** | Rechazo explícito: “horrible”. | Registrar rechazo a esta realización específica; **no** atribuir causa sin preguntar/probar. |
| **Mugaritz, The Jane, Tigermilk** | Ninguna gustó. | Rechazo de esos sitios concretos; no inferir regla universal. |

No inferir que el usuario odia todos los fondos oscuros, todas las serif o toda la animación porque rechazó determinados sitios. Distinguir **observación visual independiente** (“gran imagen horizontal”) de **preferencia humana registrada** y de **hipótesis del investigador** (“quizá gusta por la relación entre imagen y texto”).

### 11.2. Corpus como estructura, no carpeta de screenshots sin significado

Esquema de referencia:

```yaml
reference_id: restaurant-osip-home-2026-10
source_url: https://osiprestaurant.com/
observed_at: 2026-10-07
source_type: live_business_site
vertical: food_hospitality
page: homepage
artifacts:
  - desktop_fullpage_screenshot
  - mobile_fullpage_screenshot
  - viewport_crops
  - motion_notes_or_recording_if_authorized
human_feedback:
  verdict: strongly_positive
  literal_evidence: "Osip entre las favoritas"
  reason: not_explicitly_given
analyst_observations:
  - media_dominance
  - spatial_relationships
  - typography
hypotheses_to_test: []
reuse_policy:
  use_as_reference_only: true
  do_not_reuse_photos_or_layout_copy: true
```

Registrar capturas en tamaños comparables, fecha/versiones y, cuando sea necesario, video/estado de scroll; no confundir comportamiento observado con una suposición desde una imagen fija. Revisar derechos al almacenar screenshots, videos o activos de sitios ajenos, especialmente si se pretende reutilizarlos para entrenamiento. **El corpus sirve para estudiar principios, no para copiar código, composición exacta, marcas ni fotografías de referencias.**

### 11.3. Expandir por vertical sin perder una gramática general

Dos capas:

**Patrones globales:** jerarquía, alineación, espacios negativos, masas visuales, proporción, simetría/asimetría, tipografía, ritmo, relación texto-media, contraste, continuidad y movimiento.

**Patrones contextualizados:** densidad de catálogo en retail, estructura clínica y credibilidad verificable en salud, secuencias visuales de hospitalidad, necesidad de legibilidad técnica en industria, agenda en eventos, planes/clases en fitness, etc.

El corpus de restaurantes inicia el entrenamiento de *taste*; **no** se aplica indistintamente el gusto “tipo Osip” a bancos, ferreterías y dentistas. Crear nuevos sets de referencia por arquetipo a medida que haya casos y feedback humanos. Evitar homologar estética por etiquetas sociales (“odontólogo = azul”, “gimnasio = negro y rojo”).

### 11.4. Etiquetas útiles para el análisis

**Geometría:** número de columnas, amplitud, límites de contenedor, simetrías local/global, offset, densidad, proporción entre bloques, alineación aparente y ritmo entre secciones.

**Tipografía:** voz (no solamente familia), escalas relativas, leading, tracking, longitud de línea, proporción título-cuerpo, roman/italic, breaks intencionales y densidad del texto.

**Medios:** imagen/video/mixto, prominencia, secuencia, dirección de luz, crops, focalidad, continuidad, relación con fondos y texto.

**Movimiento:** función del movimiento, duraciones, easing, triggers, interacción con scroll, carga percibida y versión reduced-motion.

**Experiencia visual completa:** primera impresión, consistencia entre páginas, transiciones, cierre y adaptación móvil. No confundir sitio vistoso en un screenshot con experiencia visual completa.

---

## 12. Design Grammar común: semántica, operadores, tokens y movimiento

### 12.1. Mantener las capas separadas

```text
                 SitePlan (qué debemos mostrar)
                            │
              ArtDirection (criterio/planteamiento)
                            │
          Composition Grammar (relaciones espaciales)
                            │
            Component Registry (implementación)
                            │
          Design Tokens + Media + Motion Language
                            │
                   Runtime / Astro
```

**Una capacidad** produce obligaciones semánticas; **un operador** ubica elementos; **un componente** los representa; **tokens** gobiernan el lenguaje común; **el LLM** coordina estos elementos.

### 12.2. Operadores ya documentados

Reutilizar/adaptar operadores de los prototipos anteriores:

`Monument`, `Editorial`, `Split`, `Stage`, `Bleed`, `Metric Field`, `Rail`, `Sequence`, `Diptych`, `Triptych`, `Overlap`.

No presumir que todos estén certificados ni integrados a Astro. El Hito 0 identifica cuáles existen efectivamente, qué firma aceptan y qué tests tienen. El `Metric Field` es natural para métricas documentadas, pero no debe rellenarse con números inventados; `Overlap` necesita gates responsive estrictos.

Parámetros por operador: proporción, orientación, número de elementos, alineación, profundidad, separaciones, ancho de texto, escala, offset, presencia de bleed, dimensiones del medio, posición focal, crop, orden visual y orden semántico en móvil.

### 12.3. Tipografía como gramática, no lista cerrada de fuentes

El trabajo experimental previo contemplaba voces como `neo-grotesk`, `contrast-serif`, `editorial-serif`, `humanist-sans`, `mono-display`; además escala, peso, tracking, leading, casing, itálicas, cuerpo, measure y estilo de metadatos.

Esas voces son **vocabulario adaptable**, no selección automática por sector. Conservar licencias y permisos de las familias tipográficas. Restringir número de familias/archivos y cargar solo los pesos/subsets útiles, sin forzar todas las páginas a una tipografía genérica.

### 12.4. Color, materialidad y ritmo

Los tokens estructurados definen fondo, primer plano, acentos, contraste, superficies, tipografía, curvas de escala, spacing y densidad. El LLM puede proponerlos, pero el motor normaliza contraste, tolerancias y consistencia por página y sitio.

No maximizar simetría o blanco vacío: optimizar relaciones **intencionales**. El espacio negativo puede ser el componente principal de una dirección artística y un error en otra. El evaluador debe distinguir vacío deliberado de ausencia injustificada de contenido.

### 12.5. Lenguaje de movimiento

El prototipo ya documenta `clip-reveal`, `fade-rise`, `cascade`, `media-scale`, `drift-left` y `quiet`. El motion se selecciona **después de aprobar la composición estática** y según papel semántico, nunca porque exista una animación disponible.

Niveles de complejidad:

```text
Nivel 0: sin animación
Nivel 1: CSS básico — transform/opacity y transiciones medidas
Nivel 2: CSS avanzado — transiciones/secuencias soportadas
Nivel 3: pequeña isla o librería aprobada para interacción no expresable limpiamente en CSS
Nivel 4: efectos especiales excepcionales, con justificación y presupuesto explícito
```

WebGL/Three.js, smooth-scroll global, pesadas secuencias de GPU y runtimes nuevos **no** se habilitan por defecto. `prefers-reduced-motion`, pausas y legibilidad sin animación forman parte del contrato.

---

## 13. Art Direction Planner: papel concreto del LLM

### 13.1. Ni creatividad aleatoria pura ni instrucciones rígidas

El enfoque no es:

```text
random.choice([hero1, hero2])
```

ni:

```text
if vertical == 'fitness': use GymTemplate
```

El LLM recibe información factual aprobada, el SitePlan, módulos obligatorios, inventario audiovisual elegible, referencias analizadas, operadores certificados, presupuesto y restricciones. Propone **hipótesis compositivas coordinadas**, dejando explícita su justificación, papel de cada medio y reglas de coherencia.

### 13.2. Entrada de un plan artístico

```text
BusinessProfile
+ CapabilityProfile
+ SiteRequirements / SitePlan
+ MediaManifest / MediaBrief
+ Reference Dataset global y por vertical
+ Registry de operadores/componentes certificados
+ constraints (truth, rights, accessibility, performance)
+ diversidad frente a candidatos anteriores
```

### 13.3. Salida estructurada del LLM

Cada hipótesis define:

- principio narrativo visual y nivel de materialidad;
- qué elemento domina y por qué (no inventar un atributo del negocio);
- secuencia editorial por página, sin eliminar módulos obligatorios;
- geometrías y relaciones de operadores;
- tratamiento tipográfico y paleta;
- assignment de medios **autorizados para su rol**;
- ritmo vertical y variaciones entre secciones;
- motion justificado y su versión sin movimiento;
- riesgos de legibilidad, cobertura y calidad;
- grado de cercanía o distancia respecto a otras alternativas.

Ejemplo parcial:

```yaml
art_direction_id: industrial-editorial-02
site_intent: clear_product_culture
brand_positioning_source: approved_business_profile
visual_principles:
  - strong_typographic_navigation
  - tactile_material_details
  - asymmetric_but_legible_composition
module_priorities: [identity, categories, catalog, quote, location]
media_bindings:
  hero: licensed_illustrative_asset_38
  product_details: approved_first_party_product_images
motion:
  approach: restrained
  respects_reduced_motion: true
constraints_acknowledged:
  no_false_documentary_claims: true
  no_unverified_delivery: true
```

**Prohibido:** insertar código JS/CSS arbitrario, inventar logos/fotos/documentos, usar assets `rights=UNKNOWN`, declarar capacidad por probabilidad o modificar reglas de render. El artefacto debe pasar un validador de esquema y de bindings.

### 13.4. Probabilidades condicionadas, sin tratar ejemplos numéricos como ciencia

Podemos conceptualizar la generación como:

\[
P(\text{DesignPlan}\mid\text{Business},\text{Capabilities},\text{SitePlan},\text{Media},\text{References},\text{Constraints})
\]

El motor no tiene necesariamente una distribución estadística calibrada: al principio son **priors heurísticos y decisiones generadas bajo restricciones**. Cuando existan comparaciones suficientes podremos ajustar sus preferencias. No debemos presentar los pesos iniciales como probabilidades estimadas empíricamente.

Jerarquía de generación:

```text
proponer art directions distintos
   ↓
proponer topologías de sitio/página
   ↓
seleccionar secuencia de operadores
   ↓
ajustar relaciones y proporciones
   ↓
asignar y recortar medios elegibles
   ↓
normalizar tokens tipográficos/color/espacio
   ↓
resolver layouts responsive
   ↓
proponer motion solamente si beneficia
```

No elegir operadores de forma independiente y acabar con una colección incoherente. Las propuestas locales deben servir al carácter de la página completa.

### 13.5. Variación significativa

La diversidad puede operar sobre: macroestructura y rutas, secuencia de módulos permitida, topología, medias dominantes, jerarquía de títulos, proporciones, densidad, distribución de vacío, composición tipográfica, sistema cromático, orden de imágenes y cantidad/finalidad de movimiento.

**No basta** cambiar el color de fondo, fuente y borde de tarjetas. El evaluador de diversidad debe comparar estructura y composición; a la vez debe **no penalizar** relaciones que todas las páginas de un tipo necesitan por legibilidad o función.

---

## 14. Dos fases de resolución espacial: topología y geometría

### 14.1. Qué significan

**Topología:** relaciones y orden: qué elemento está arriba, abajo, a izquierda, superpuesto o agrupado con otro.  
**Geometría:** medidas concretas: tamaños, offsets, gaps, medidas de texto y proporciones en un viewport.

La investigación previa (v0.12) exploró `layout = topology + geometry` con reglas de no colisión, dimensiones mínimas y objetivos suaves, pero quedó **experimental y sin integración productiva demostrada**. Debe evaluarse frente a CSS Grid, flex y reglas responsive comunes; **no** convertir un solver de optimización pesado en dependencia obligatoria sin mejora demostrada.

### 14.2. Flujo propuesto

```text
DesignPlan candidato
  → checker de topología semántica permitida
  → constraints: orden, gaps, mínimos, proporciones, crop
  → solver/restricciones de geometría o reglas CSS certificadas
  → contratos responsive por operador
  → CSS variables/estructura Astro
  → medición de navegador de verdad
```

Cada operador debe tener una especificación desktop/tablet/mobile. No confiar en que una composición desktop “se apila” de cualquier manera y sigue siendo buena. El orden visual no debe quebrar navegación por teclado o lectura por lectores de pantalla.

### 14.3. Restricciones duras

- sin superposición ilegible o elementos fuera del lienzo;
- sin contenido cortado o controles ocultos;
- tamaño mínimo legible y ancho de párrafo razonable;
- dimensiones y gaps mínimos con targets táctiles apropiados;
- medios dentro de recortes legales y significativos, sin pérdida del sujeto principal;
- navegación, encabezados y orden de lectura lógico;
- contenido vinculado intacto;
- contraste, movimiento reducido y accesibilidad previstos;
- comportamiento aceptable desde móviles pequeños a desktop ancho.

### 14.4. Objetivos blandos

Equilibrio, tensión visual, asimetría intencional, ritmo, continuidad, escasez selectiva, escala, distribución de saliencia, carácter de marca y diversidad. No utilizar un score único tan agresivo que elimine soluciones editoriales poco ortodoxas.

### 14.5. Responsive solver y puntos de prueba

Desarrollo inicial con capturas en **360/390, 768, 1024, 1440 y 1920 px** (propuesta, no dispositivo único). Añadir pruebas entre puntos para descubrir rupturas no presentes en breakpoints. También probar longitud de texto, idiomas, escalado de fuentes, ausencia de media y red lenta.

Los componentes certificados declaran reflow alternativo. Ejemplo `Split`: proporción adaptable, inversión opcional de lado visual **sin cambiar orden semántico**, recorte alternativo, capacidad de no usar video en móvil.

### 14.6. No optimizar una sección aislada y arruinar el conjunto

Medir tanto módulos individuales como ritmos de página (transiciones entre secciones, variedad, densidad acumulada, repetición de fórmulas y cierre). Los cambios locales no pueden romper decisiones globales de dirección artística.

---

## 15. Component Registry y bibliotecas externas: preservar el trabajo anterior

### 15.1. Capas de código

```text
Business capabilities (semántica / contrato)
       ↓
Accessible UI behavior (headless cuando sea necesario)
       ↓
101 Component Registry (código certificado y versionado)
       ↓
Composition operators (estructura visual flexible)
       ↓
Astro site-runtime (carga, fuentes, medios, rutas, assets)
```

Los componentes semánticos (`Menu`, `Catalog`, `Schedule`, `ProfessionalProfile`) no determinan por sí mismos un look. Los operadores (`Rail`, `Editorial`, `Bleed`, etc.) tampoco conocen las reglas operativas del negocio.

### 15.2. Reutilización del corpus OSS histórico

El handoff documenta ingesta de fuentes Origin, Cult, Kibo, Dice y Animate; además discusiones sobre shadcn/Base UI, HeroUI, Radix Themes, Aceternity y 21st.dev. Los usos propuestos:

- **Base UI/shadcn y piezas headless:** foco, teclado, menú, diálogo, tabs, controles accesibles; evitar que las cards genéricas dicten la estética de toda web.
- **Origin, Cult, Kibo, Dice, Animate:** biblioteca de patrones visuales, composiciones y comportamientos para seleccionar, adaptar y certificar.
- **Motion references:** inspiración estructural de transiciones; no instalar todas las dependencias de animación en cada página.

No asumir que ingestar archivos equivale a que ya sean renderizables. El ingester anterior diferenciaba:

```text
SOURCE_BACKED_RENDERABLE
SOURCE_BACKED_NEEDS_ADAPTER
INDEXED_ONLY
COMPILER_NATIVE
```

Conservar esa distinción. Una pieza marcada `SOURCE_BACKED_RENDERABLE` debe tener código fuente, licencia, ruta, hash, adapter probado y dependencias identificadas. Una entrada `INDEXED_ONLY` sirve para investigación, **no** para producción. Nunca atribuir origen de una pieza propia a una librería OSS por conveniencia.

### 15.3. Filtro para incorporar una primitiva

Una idea ingresa a `@101/components` solamente si:

1. Su código y permiso de uso son conocidos, su procedencia es demostrable.
2. Se adapta al runtime común; no requiere una nueva infraestructura por sitio.
3. Tiene estados semánticos, responsive, accesibilidad y fallbacks definidos.
4. Supera tests de funcionalidad frontend, visual regression y bundle budget.
5. Aporta diversidad o comportamiento real frente a las familias ya certificadas.
6. Expone parámetros compositivos razonables en vez de una estética rígida.

### 15.4. Regla anti-bloat

**Un sitio individual no puede instalar una dependencia de UI nueva** ni clonar un componente de internet. Si aparece una necesidad no soportada, proponerla al registry, justificar su utilidad general, adaptar y probar. Excepciones se registran, revisan y cuentan como deuda —no se normalizan automáticamente.

### 15.5. Versionado y compatibilidad

Una actualización de `EditorialSplit` o `ScheduleView` no altera silenciosamente 500 sitios ya aprobados. Versiones semánticas, builds reproducibles, snapshots, migración explícita y rollback. Mantener inventario de **qué sitios usan cada componente, fuente y asset licenciado**.

---

## 16. Base técnica común, rendimiento y accesibilidad

### 16.1. Runtime propuesto

```text
Astro + TypeScript
HTML/CSS estático por defecto
React islands solo para interacciones justificadas
Tailwind + variables CSS o equivalentes ya integrados en el repo
Design tokens tipados y versionados
Base UI/headless para controles complejos cuando aplique
CSS motion primero; Motion solo si lo exige una interacción aprobada
Imagen optimizada / video responsable / tipografía con licencia
Browser QA + performance QA
```

**No introducir un nuevo framework sin inventario de la base que ya existe.** `@101/site-runtime` y los componentes productivos actuales son el punto de integración a confirmar.

### 16.2. Presupuestos iniciales propuestos (hipótesis, no resultados)

| Dimensión | Política inicial de diseño | Cómo se comprueba |
|---|---|---|
| JS inicial propio | Idealmente ~0 para páginas informativas; permitir islas solo cuando necesarias | Bundle report + red real |
| JS total | Presupuesto por capability; sin scripts globales pesados injustificados | Build analyzer y Lighthouse/DevTools |
| Fuentes | Preferir 1–2 familias optimizadas, subsets y WOFF2, no decenas de variantes | Network waterfall |
| Imágenes | Tamaños responsivos, tamaño útil correcto, prioridad selectiva | Network/device emulation |
| Video | Poster, codec/fallback, política de carga, variantes; no bloquear contenido importante | Medición first load y reproducciones |
| Layout | Sin overflow/clipping, tamaños robustos y dimensiones de medios explícitas | Browser geometry |
| Accesibilidad | Objetivo WCAG 2.2 AA para lo aplicable, sin prometer conformidad solo por scanner | Automatización + tests manuales |
| Core Web Vitals | Objetivos de referencia: LCP ≤ 2,5 s; INP ≤ 200 ms; CLS ≤ 0,1 (p75 real) | Lab + campo cuando haya tráfico |
| Animaciones | `prefers-reduced-motion`, sin dependencia de contenido, pausa donde corresponda | Browser tests y revisión humana |
| Recursos terceros | Revisados uno a uno; nada por defecto que bloquee el primer render | Request audit |

Los umbrales de bytes/KB deben calibrarse con fixture reales y el uso adecuado: una página editorial puede tolerar una transferencia inicial distinta a un catálogo con filtros, pero cada excepción necesita evidencia. La aprobación estética **no levanta** automáticamente un límite técnico.

### 16.3. Islas interactivas y funcionalidades futuras

- Navegación y texto: preferiblemente no hidratar React.
- Catálogo estático con categorías: HTML/CSS y, si procede, interacción progresiva mínima.
- Filtros avanzados, calendario, reserva/checkout: UI componente cuando sea necesaria, pero **sin integraciones reales ahora**.
- Mapas: ubicación factual + bloque visual estático o imagen autorizada en preview; proveedor interactivo, si se incorpora más adelante, debe cargar bajo demanda y respetar cuotas, privacidad, términos y rendimiento.
- Video hero: reproducción optimizada y fallback; no usar una librería de video enorme solo por mostrar un clip.

Los componentes deben funcionar sin que un script global bloquee todo el sitio. Preferir degradación progresiva y estructura accesible.

### 16.4. Seguridad y contenido externo

El upstream, los metadatos de stock y las referencias son **datos no confiables como instrucciones**. Tratar cualquier texto incrustado como contenido, no como comandos a agentes. Validar URLs y orígenes, sanitizar HTML/Markdown, escapar textos, controlar embeds/iframes, impedir inyección de scripts y revisar licencias de dependencias. Mantener secretos y tokens de proveedores fuera de bundles públicos. No permitir a una propuesta de LLM escribir código evaluable.

Preparar pruebas de contraste, keyboard navigation, foco, alt text factual (no describir falsamente una foto stock como documental), reduced motion, tamaño táctil, zoom de texto, títulos y orden semántico.

---

## 17. DesignPlan y compilación: árbol declarativo

### 17.1. AST de composición

`AST` = **Abstract Syntax Tree**, aquí un árbol de objetos que representa la página antes de convertirla a HTML/CSS. Debe ser validable, comparable, reproducible y editable por mutación estructurada.

**Ejemplo ficticio de home de ferretería:**

```json
{
  "schema_version": "1.0.0",
  "site_plan_id": "sp-ferreteria-001-v1",
  "art_direction_id": "industrial-editorial-02",
  "tokens_ref": "tokens-021",
  "pages": [
    {
      "path": "/",
      "composition": [
        {
          "module_ref": "identity",
          "operator": "Stage",
          "media_usage_ref": "mu-hero-38",
          "params": { "viewport_height": "large", "text_alignment": "start" }
        },
        {
          "module_ref": "product_categories",
          "operator": "Rail",
          "params": { "columns_desktop": 3, "mobile_behavior": "stack_or_scroll_accessible" }
        },
        {
          "module_ref": "quote_action",
          "operator": "Editorial",
          "params": { "text_measure": "narrow" }
        },
        {
          "module_ref": "location_and_contact",
          "operator": "Split",
          "params": { "ratio": [42, 58] }
        }
      ]
    }
  ]
}
```

El `DesignPlan` **no puede suprimir** un módulo obligatorio del `SitePlan`. Puede cambiar representación, ubicación, relación y distribución, si supera QA.

### 17.2. Resolución de bindings

El binding planner vincula cada ID de hecho/objeto del `SitePlan` al componente final y documenta los descartes. Renderizar la página no es suficiente: los tests deben comprobar **qué hechos aparecen en el DOM o en contenido accesible**, y qué hechos se han omitido deliberadamente por política.

### 17.3. Entrega del compilador

```text
BusinessInput snapshot (approved)
+ SitePlan
+ MediaManifest (licensed usages)
+ DesignPlan (validated)
+ Component Registry (pinned version)
+ site-runtime (pinned version)
  → deterministic Astro project/build
  → static HTML/CSS + optimized assets + minimal JS
  → build manifest + binding report + audit report
```

El runtime no debe ejecutar LLM en cada visita ni recalcular el diseño en cada deploy. Los identificadores de recursos son estables; resoluciones y licencias quedan trazadas.

---

## 18. Búsqueda de candidatos y ciclo de crítica/mutación

### 18.1. Pipeline acotado de búsqueda

```text
SitePlan + media apta + constraints
          ↓
LLM: varios conceptos de art direction
          ↓
Compositor: varias topologías por concepto
          ↓
cheap legality/content/rights checks
          ↓
cheap geometry/complexity estimates
          ↓
preselección por calidad esperada + diversidad
          ↓
compile + browser render de finalistas
          ↓
checks objetivos + evaluación visual contextual
          ↓
crítica específica y mutación controlada
          ↓
rerender y reevaluación
          ↓
frontera de finalistas válidos y realmente distintos
          ↓
selección humana (incluye «ninguna»)
```

Generar 100 composiciones no es un objetivo en sí mismo. Un presupuesto de ejemplo para arrancar —**a calibrar**, no promesa— podría generar 24–40 propuestas estructurales baratas, compilar 6–12 variantes y presentar 3–4 finalistas. Si encontramos candidatos sólidos con menos cómputo, mejor.

### 18.2. Filtro Pareto, no un número mágico

Hay varios objetivos en conflicto:

```text
contenido completo y factual
+ permisos íntegros
+ calidad estética
+ diversidad
+ accesibilidad
+ rendimiento
+ bajo costo de medios y cómputo
```

Los errores de verdad, permisos, UI rota y accesibilidad crítica son **restricciones duras**, no penalizaciones que puedan compensarse con mayor belleza. Entre candidatos válidos utilizamos selección multiobjetivo, diversidad y preferencia humana. No inventar un `visual_score=9.4` como si fuera una medición objetiva sin protocolo y calibración.

### 18.3. Mutaciones autorizadas

- **Local:** gap, ancho de texto, escala tipográfica, cropped position, lado de imagen, proporción de columnas, número de elementos visibles, color/contraste dentro de límites.
- **Estructural:** cambiar operador, topología, orden de módulos donde sea legal, secuencia de medios, ritmo y secciones de apoyo.
- **Dirección artística:** replanear una alternativa completa cuando cambios locales no pueden corregir incoherencia sistémica.
- **Media:** reemplazar asset si existe alternativa autorizada o redefinir MediaBrief para cubrir una brecha real.

Cada mutación debe registrar **qué cambió, por qué, cuál era el fallo y si mejoró**. Si no mejora, rollback al estado anterior. No permitir que una reparación cambie el significado o suprima contenido esencial.

### 18.4. Ejemplo de crítica útil

```yaml
issue_id: visual-031
scope: /, viewport_390
kind: media_crop
observation: "el recorte excluye el sujeto principal"
evidence: screenshot_390_before.png
severity: high
suggested_mutations:
  - use_approved_mobile_crop_variant
  - change_operator_from_bleed_to_split
constraints:
  same_factual_role: true
  same_licensed_usage: true
```

Esto sí habilita automatización. «Se siente feo» sin localizar causa, componente o evidencia sirve menos como insumo de ingeniería.

### 18.5. Evitar optimización circular

El mismo LLM que genera no debe ser la **única** autoridad de calidad. Combinar tests objetivos, comparaciones visuales ciegas, auditoría humana, un evaluador separado si aporta independencia y conjuntos de evaluación no usados para ajustar el generador. Guardar fallos honestamente; un evaluator que siempre da 9/10 no prueba excelencia.

---

## 19. Sistema de auditorías: nueve familias independientes

| Auditoría | Qué debe demostrar | Condición de fallo típica |
|---|---|---|
| **A. Entrada y evidencia** | Esquema, identidad, sucursal, vigencia y datos publicables consistentes | `site_plan` usa dato desconocido o conflictivo |
| **B. Negocio/capacidades** | Módulos adecuados al negocio y **solo** operaciones verificadas | Entrega en gym sin confirmación; menú falso de ferretería |
| **C. Cobertura semántica** | Hechos obligatorios y módulos esenciales sobreviven al HTML | Menú declarado pero no visible; horas aprobadas omitidas |
| **D. Derechos/representación** | Licencias por uso y verdad de la imagen | Stock aparece como foto de una clínica real; licencia desconocida |
| **E. UI/geometry/responsive** | No hay clipping, overflow, mal orden, colisiones, crops destruidos | Título cortado en 390 px; elemento fuera de pantalla |
| **F. Accesibilidad** | Lectura, teclado, contraste, foco, alt apropiado, movimiento reducido | Control inaccesible o información solo dentro de animación |
| **G. Rendimiento** | Bytes, requests, ejecución, LCP/INP/CLS cuando aplica | Video bloquea el contenido; excesivo JS |
| **H. Calidad y coherencia visual** | Jerarquía, ritmo, media treatment, identidad, consistencia entre rutas y móviles | Diseños genéricos, secciones incoherentes, pobre fotografía |
| **I. Variedad y costo** | Variaciones estructurales reales con costo presupuestado | Todos los finalistas son la misma página recoloreada |

### 19.1. Orden y ahorro de costes

Orden recomendado: **schema/truth/rights → capability coverage → geometría barata → build/browser → performance/accessibility → crítica visual → diversidad finalista**. Si la licencia está bloqueada, no gastar en renders y crítica. Si una ruta es semánticamente falsa, no intentar mejorarla con video.

### 19.2. Browser QA que debemos conservar/adaptar

El prototipo histórico midió: overflow, clipping, tamaño mínimo de texto, occupancy/fill, títulos y wrap, líneas finales, coverage de medios, geometría de secciones. También rasgos raster: ink/whitespace ratios, contraste, edge density, entropía, centros y balances visuales, concentración de saliencia y complejidad. Son **instrumentos auxiliares**, no una fórmula universal de belleza.

Añadir: distintos tamaños, zoom 200%, contenido largo/corto, idiomas, campos faltantes, imágenes ausentes, reduced motion, teclado, estados de UI, enlaces/acciones y pruebas por módulo/sector.

### 19.3. Evaluación audiovisual real

Screenshots estáticos **no** evalúan un video como el que gustó de Aira. Para media hero y motion necesitamos comprobar al menos inicio, reproducción, pausas, cuadro clave, transición/scroll, versión móvil, poster, fallback y rendimiento. Evaluación humana y, donde sea posible, registro corto de la secuencia con autorización para usarlo en el entorno de QA.

### 19.4. Validación de rendimiento: laboratorio vs campo

Playwright/Lighthouse sirven para pruebas reproducibles; al existir usuarios reales, medir Core Web Vitals y errores de cliente con sus distribuciones. Una sola captura de Lighthouse no demuestra que el p75 de usuarios tenga buena experiencia. Etiquetar `MEASURED`, `NOT_MEASURED` y `NOT_APPLICABLE`; no convertir mediciones ausentes en aprobaciones.

### 19.5. Gates y estados

```text
INPUT_VALID
BUSINESS_RESOLVED
CAPABILITIES_RESOLVED
SITE_PLAN_VALID
MEDIA_ELIGIBLE
DESIGN_PLAN_VALID
BUILD_PASS
SEMANTIC_PASS
TECHNICAL_PASS
PERFORMANCE_PASS
VISUAL_REVIEWED
DESIGN_ACCEPTED
DESIGN_LOCKED
```

Estados **no equivalentes**: `DESIGN_ACCEPTED` no implica `LIVE_FUNCTIONAL`, `CUSTOMER_READY` ni `PUBLISHED`. Es perfectamente válido emitir `BLOCKED_UPSTREAM`, `BLOCKED_LICENSE`, `BLOCKED_CAPABILITY`, `NO_ACCEPTABLE_DESIGN`, `NEEDS_HUMAN_REVIEW` o `NOT_MEASURED`.

---

## 20. Selección humana, Taste Dataset y aprendizaje

### 20.1. Feedback correcto

La interfaz de revisión debe permitir comparar páginas equivalentes en el mismo viewport y contenido, aleatorizando izquierda/derecha:

```text
A es mejor
B es mejor
Empate
Ninguna es aceptable
```

Razones opcionales estructuradas y comentario libre: tipografía, ritmo, composición, media, movimiento, coherencia, claridad del negocio. **No inventar razones a posteriori** por la elección humana. Si se pregunta explícitamente por un segmento o video, registrar preferencia **local**, no transformar en aprobación global del sitio.

### 20.2. Datos que deben acompañar una preferencia

```text
vertical + archetypes + category detail
BusinessInput fixture/version
SitePlan y capabilities
MediaManifest y calidad/role de medios
ArtDirection/DesignPlan/AST/hash
viewport y versión de screenshot/video
pares comparados y orden de presentación
resultado humano literal y razón si se dio
costo estimado y gates técnicos
```

Esto permite distinguir «me gustó más porque tenía mejor video» de «me gustó más por composición». No aprender una preferencia universal del usuario sin condicionar por vertical y contexto.

### 20.3. Etapas de aprendizaje

1. **Inicial:** hipótesis y pesos manuales, transparencias de incertidumbre.
2. **Después de suficiente evaluación repetida:** estadísticas simples de preferencia por familia de decisiones.
3. **Luego:** modelos de ranking por pares (p. ej. Bradley–Terry o un ranker apropiado), con train/validation separados y controles de sesgo.
4. **Solo si hay permiso y evidencia de mejora:** modelos más ambiciosos, nunca entrenamiento indiscriminado con imágenes no autorizadas.

No confundir preferencias de una persona con calidad general de usuarios, clientes o sectores. Idealmente incorporar revisión visual experta e información de aceptación real de clientes, sin que esa señal introduzca incentivos para sacrificar legibilidad o veracidad.

### 20.4. Diseño final inmutable

Una vez elegido, congelar el AST aprobado y las referencias exactas, no solamente el `seed`. Versionar modelo/prompt/output. Una API LLM puede cambiar resultados aunque use misma seed; para reproducibilidad se conserva el **resultado estructurado final** y el ambiente de compilación.

---
## 21. Artefactos, storage, linaje y reproducibilidad

### 21.1. Directorios lógicos (no orden de reorganización inmediata del repo)

```text
101-world-model / existing worktree(s)
├── contracts/
│   ├── business-input.schema.json
│   ├── business-profile.schema.json
│   ├── capability-profile.schema.json
│   ├── site-plan.schema.json
│   ├── media-manifest.schema.json
│   ├── art-direction.schema.json
│   ├── design-plan.schema.json
│   ├── design-lock.schema.json
│   └── audit-report.schema.json
├── taxonomy/
│   ├── source-mappings/
│   ├── archetypes/
│   └── coverage-audit/
├── capabilities/
│   ├── registry/
│   ├── frontend-contracts/
│   └── qa/
├── media/
│   ├── provider-adapters/
│   ├── rights/
│   ├── analysis/
│   ├── art-direction-briefs/
│   └── derivatives/
├── design/
│   ├── reference-dataset/
│   ├── grammar/
│   ├── operators/
│   ├── tokens/
│   ├── typography/
│   └── motion/
├── compiler/
│   ├── planners/
│   ├── composition-search/
│   ├── geometry-responsive/
│   └── adapters-to-existing-runtime/
├── audits/
│   ├── truth-bindings/
│   ├── media-rights/
│   ├── capability/
│   ├── geometry/
│   ├── accessibility/
│   ├── performance/
│   └── visual/
├── evaluation/
│   ├── fixtures/
│   ├── benchmarks/
│   ├── preference-data/
│   └── regression/
└── generated/
    └── <site-id>/<run-id>/
        ├── snapshots/
        ├── media-manifest.json
        ├── site-plan.json
        ├── design-plan.json
        ├── build/
        ├── binding-report.json
        ├── audit-report.json
        ├── screenshots/
        ├── preference-record.json
        └── design.lock.json
```

**Advertencia:** es una organización de responsabilidades. H0 debe localizar carpetas reales y definir el cambio mínimo; no copiar todo a una codebase paralela. Respetar registros de contexto y worktrees existentes de 101, verificando su estado antes de operar.

### 21.2. Identidades/hashes y replays

Por generación conservar:

```yaml
run_id: run-20261007-0001
business_snapshot_hash: sha256:...
upstream_schema_version: 1.0.0
site_plan_hash: sha256:...
capability_registry_version: ...
component_registry_commit: ...
site_runtime_commit: ...
media_manifest_hash: sha256:...
design_plan_hash: sha256:...
model_record:
  provider: ...
  model: ...
  prompt_revision: ...
  output_hash: ...
random_seed_for_local_sampler: ...
render_environment: ...
qa_environment: ...
```

Los hashes anteriores son **campos de esquema**, no hashes reales. El principio es: poder reconstruir **sin volver a decidir**. Los archivos físicos pueden almacenarse en un objeto versionado; los links de acceso pueden caducar, por lo que el hash de contenido y derecho licenciado deben sobrevivir.

### 21.3. Diseño bloqueado

`design.lock.json` debe incluir snapshot/fuente de datos autorizados, plan semántico final, media/rights usage, AST final, tokens, fonts y sus licencias, recortes responsive, motion, componentes y versiones, salida de LLM **ya resuelta**, aprobaciones y estado de auditorías. El rebuild usa esa información, no busca nuevos medios ni recomputa probabilidades.

Actualizar un sitio implica revisión de facts/assets y un nuevo lock explícito. Cambios al registry o a licencias pueden activar auditorías para sitios dependientes, pero no migraciones silenciosas.

### 21.4. Índice de impacto

Mantener relaciones:

```text
Asset → LicenseGrant → MediaUsage → Site/Route
Component@version → Site/Route
FactID → Module → Route → RenderedElement
Capability@version → Site/Route
Font/license → Site/Route
```

Permite retirar material, rotar fuentes, actualizar datos y determinar qué sitios hay que revalidar.

---

## 22. Estrategia de pruebas multivertical y diseño experimental

### 22.1. Dos clases de fixtures

**Ficticios controlados:** datos creados y marcados como pruebas, usados para explorar diseños y reproducciones sin publicar hechos de terceros. **Reales con evidencia:** datos aprobados por el upstream o extraídos de snapshots legales, usados para probar preservación factual y preparación de despliegue. No confundir los resultados.

Conservar fixtures *congelados* por versión. Un fixture puede ser rico en media y otro pobre; los medios ilustrativos elegidos también deben tener derechos aptos para tests si salen del entorno privado.

### 22.2. Cohorte inicial propuesta

No arrancar con todas las categorías, pero tampoco cerrar arquitectónicamente en restaurantes. Probar una selección que ponga a prueba capacidades diferentes:

| Fixture | Lo que estresa | Medio |
|---|---|---|
| Restaurante con menú y reserva real aprobada | Oferta alimentaria, identidad, visita; referencia Osip/KOL como criterio de gusto, no copia | media muy fuerte |
| Ferretería con catálogo + cotización, delivery desconocido | Alta densidad de producto, navegación y prohibición de inferir reparto | mixta |
| Gimnasio con membresías + clases, sin venta de productos confirmada | Planes, calendario visual, instalaciones | video potencial |
| Dentista con tratamientos/profesionales aprobados | Contenido regulado, credenciales, fotos auténticas | media escasa/mixta |
| Hotel con habitaciones y amenidades | Inventario de espacios, media documental, distintas rutas | media rica |
| Taller o servicio de construcción | Servicios, cobertura, presupuestos, fotografías documentales | media pobre |
| Negocio híbrido (café+tienda o gimnasio+retail) | Varias capacidades y arquetipos en el mismo sitio | mixta |
| Categoría desconocida o inconsistente | Que el router sepa abstenerse sin inventar | irrelevante hasta resolver |

Las categorías aquí son **casos de prueba propuestos**, no negocios concretos identificados en el archivo de observaciones.

### 22.3. Experimentos ortogonales

**E1 — Composición:** mismo business fixture, mismos datos, mismos assets y licencias; variar `ArtDirection` y `DesignPlan`. Mide calidad compositiva y variedad.

**E2 — Medios:** mismo fixture, `SitePlan` y macrocomposición; variar conjuntos de media igualmente autorizados y comparables. Mide curaduría y costo audiovisual.

**E3 — Capacidades:** misma estética base y medios adecuados; variar `CapabilityProfile` con verdad controlada. Deben aparecer/desaparecer módulos correctos sin reescribir código.

**E4 — Generalización:** fixtures retenidos de verticales nunca usados en tuning. Medir si la máquina puede resolverlos sin hacks.

**E5 — Robustez:** datos insuficientes, ambigüedad de categoría, falta de fotos auténticas, licencia bloqueada, título largo, muchas sedes, texto de otro idioma, ausencia de precio, 1.000 referencias de catálogo, 360 px, reduced-motion y red limitada.

**E6 — Regresión:** modificar una primitiva y comprobar los sitios dorados aprobados, incluidos screenshots en ambiente controlado, semántica, bundle y validadores.

### 22.4. Qué significa una prueba exitosa

Para el primer motor multivertical:

- Todas las páginas candidatas presentadas como válidas pasan gates duros.
- El sistema produce composiciones genuinamente diferentes con la misma base.
- Ningún candidato añade código, componentes o dependencias específicas de ese negocio.
- Las capacidades mostradas corresponden a la información confirmada.
- Las fotos externas no representan hechos locales inexistentes.
- Los fallos muestran razones verificables.
- Los candidatos aceptados pueden reconstruirse exactamente desde su lock.

No usar métricas vagas como «se ve profesional» sin rubric humana o comparación ciega. Definir aceptación estética mediante revisiones efectivas, no puntuaciones autoasignadas.

---

## 23. Métricas y economía del sistema

### 23.1. Métricas agrupadas

**Cobertura:** número de negocios y arquetipos procesados, proporción resuelta/no resuelta, módulos pertinentes completos, pérdida de bindings, tipos de capabilities certificados, porcentaje de rutas sustantivas.

**Media:** fracción con licencia completa, costo por activo y por cliente, tiempo/calls hasta un conjunto aceptable, porcentaje de recursos documentales vs ilustrativos, cobertura de roles de la composición, tasas de rechazo legal, calidad audiovisual humana, ratios de reutilización **solo cuando autorizada**.

**Diseño:** porcentaje de propuestas que pasan gates duros, variedad estructural de finalistas, aceptación humana sin corrección de código, número de rondas y mutaciones por aceptación, frecuencia de «ninguna» por vertical, diferencias desktop/mobile.

**Tecnología:** bundle JS/CSS, requests, MB transferidos, LCP/INP/CLS disponibles, errores, accesibilidad, comportamiento responsive, incidencias por componente y regresiones.

**Producción:** tiempo por sitio, costo de tokens/renders/media, revisiones humanas, excepciones por cliente, nuevas dependencias, cambios al registry, porcentaje reproducible y tasa de rollback.

### 23.2. Qué significa costo cercano a cero

El KPI estratégico es:

```text
new_site_specific_code_files ≈ 0
new_site_specific_dependencies = 0
new_site_specific_backend = 0 (en fase frontend)
new_site_specific_responsive_hacks ≈ 0
```

Se reconoce la inversión inicial del motor y el costo marginal real:

\[
C_{\text{sitio aceptado}} =
\frac{C_{\text{medios}} + C_{\text{búsqueda}} + C_{\text{LLM}} +
C_{\text{render}} + C_{\text{QA}} + C_{\text{revisión}} + C_{\text{transferencia}}}
{\text{sitios aceptados del lote}}
\]

Para costos compartidos definir regla explícita de asignación; incluir mantenimiento, hosting y soporte en un modelo de costo completo cuando corresponda. Una licencia que exige compra por cliente **no** se amortiza ilegalmente entre varios clientes. El presupuesto de video no puede desaparecer por considerar la descarga “gratis”.

### 23.3. Priorizar arquetipos por demanda y no por capricho

Usar conteos **por fuente** del inventario como señal imperfecta de frecuencia, complejidad funcional, facilidad de encontrar material y oportunidad comercial. Evitar sumar Foursquare/OSM/Overture como si fueran locales únicos o proyectar categorías `Unknown` sin revisión. El roadmap puede iniciar en 3–5 arquetipos representativos, y expandirse según cobertura y evidencia real.

### 23.4. Primeros criterios de rendimiento del proyecto (a validar)

- **H3:** tres páginas distintas sobre un mismo fixture y una base común, todas con QA semántico/técnico básico, sin código por cliente.
- **H4:** entre tres finalistas válidos, al menos uno aceptado visualmente en una prueba controlada; no confundir este umbral de demostración con tasa de éxito a escala.
- **H6/H7:** ejecutar al menos cuatro arquetipos con capabilities diferentes, incluyendo un híbrido y uno pobre en medios, sin arreglos particulares al renderer.
- **Fase de escala:** medir percentiles de tiempo/costo y tasas de intervención humana, no solo los casos exitosos elegidos para demo.

Estos son **gates propuestos**; no indicar «pasó» sin actas de prueba y artefactos reales.

---

## 24. Roadmap formal de implementación con condiciones de cierre

La regla de ejecución es **un milestone pequeño, prueba real, informe, decisión y siguiente cambio**. Prohibido declarar completado algo por existir como idea, documento o índice de corpus.

### H0 — Reconciliación del trabajo existente (primero, obligatorio)

**Entrada:** repositorios/worktrees de `101-world-model`, Design Compiler y documentación histórica.  
**Acciones:** leer instrucciones locales del repo; identificar ramas, HEAD, árbol sucio y restricciones; localizar esquemas, `SiteSpec`, Truth/publication, binding planner, compiler, Astro runtime, QA, operadores, tipografía, motion, media analysis, screenshot critic, mutant/re-render, OSS ingester y topology solver. Ejecutar tests controlados.  
**Entrega:** `reuse-map.md`, `gap-map.md`, `integration-boundaries.md`, lista de rutas/commits/tests, y estado **EXISTS / TESTED / INTEGRATED / EXPERIMENTAL / STALE / MISSING** con evidencia.  
**Cierre:** ninguna pieza crítica queda declarada usable sin ruta y prueba; no se crea generador paralelo.

### H1 — Taxonomía y `BusinessInputV1`

**Acciones:** analizar íntegro `message (4).txt`; preservar campos originales; construir crosswalk y conjunto explícito de `UNRESOLVED`; definir arquetipos combinables y adaptador planeado hacia `SiteSpec`.  
**Entrega:** esquema validable, mapping registry, fixtures de clasificación con ambiguos, matriz de errores y protocolo con upstream.  
**Cierre:** categorías representativas resueltas o abstención justificada, sin inventar capacidades; tests en cada proveedor de origen; contrato exportable al sistema extractor.

### H2 — Capability Registry y planner semántico

**Acciones:** elegir 3–5 arquetipos diferentes; escribir especificaciones y contratos frontend de capabilities básicas, más reglas de `SiteRequirementsV1`, `SitePlanV1` y binding.  
**Entrega:** capability registry tipado, matriz real `category/archetype ↔ capability` (candidata, no hecho), generator de `SitePlan`, tests de no-inferencia y omisión de rutas vacías.  
**Cierre:** restaurante, ferretería y gimnasio (al menos) producen planes distintos desde datos distintos, sin condicionar diseños ni crear hechos.

### H3 — Medios: manifiesto, huecos y permisos

**Acciones:** inventariar medios upstream, analizar calidad y relación con negocio; implementar `MediaAsset/LicenseGrant/MediaUsage`; evaluar proveedores con muestras y documentos legales; seleccionar/adquirir un paquete de prueba permitido.  
**Entrega:** media manifest tipado, rights gate, MediaBrief, evaluación de proveedores y paquete audiovisual coherente y trazable.  
**Cierre:** los recursos de los fixtures pueden renderizarse con usos concretos amparados por permisos; un recurso con licencia desconocida se bloquea; no afirmar automatización aprobada sin términos/acuerdo.

### H4 — Composiciones base sobre el runtime 101

**Acciones:** certificar los operadores existentes más útiles y el vínculo módulo-operador; definir tokens/motion/media responsive, usar Astro que ya exista.  
**Entrega:** **tres** composiciones sustancialmente distintas del mismo caso y medios, desktop/móvil, sin dependencias o código específico de cliente.  
**Cierre:** build, bindings, media usage, geometría, responsive, contenido y accesibilidad principal pasan. Si las tres son malas, mejorar gramática antes de automatizar búsqueda.

### H5 — LLM director artístico + búsqueda probabilística

**Acciones:** salida estructurada, validación por contrato, proponer varios art directions y topologías, sampling guiado por contexto, prefiltrado barato, selección diversa.  
**Entrega:** `ArtDirectionV1`, `DesignPlanV1`, generador con presupuesto y resultados comparables en un fixture congelado.  
**Cierre:** variedad no cosmética, cero dependencias arbitrarias, ninguna supresión de módulos y sin fallos de verdad/medios entre candidatos válidos.

### H6 — Auditorías, visión, mutación y torneo humano

**Acciones:** unir browser geometry/raster con critic y mutator existentes; incorporar gates de capabilities, licencias, contenido, performance y a11y; revisión A/B/empate/ninguna.  
**Entrega:** reportes de ejecución, capturas reproducibles, historial de mutaciones, finalistas válidos y panel de comparación.  
**Cierre:** el sistema detecta fallos sembrados, repara problemas acotados cuando puede, hace rollback de mutaciones peores y admite `NO_ACCEPTABLE_DESIGN`.

### H7 — Generalización entre verticales

**Acciones:** validar sin cambiar código específico sobre hotel, dentista, taller/servicio a domicilio, negocio híbrido y caso `Unknown`/media pobre.  
**Entrega:** cohorte retenida y reporte de cobertura, costos, diversidad, fallos, código específico y ajustes al registry necesarios.  
**Cierre:** funciona en arquetipos nuevos sin forks; si surge una capacidad faltante, se agrega al registry con contrato/test en vez de escribir el sitio individualmente.

### H8 — Design Lock y reconstrucción

**Acciones:** congelar planes, fuentes, assets/licencias, fingerprints y runtime. Implementar reconstrucción determinista, rollback y regresión de componentes.  
**Entrega:** `DesignLockV1`, función rebuild, manifest de dependencias y reportes de reproducibilidad.  
**Cierre:** misma entrada bloqueada + mismo toolchain producen salida funcionalmente y visualmente equivalente bajo entorno controlado **sin llamar al LLM ni buscar nuevos medios**.

### H9 — Economía y escalamiento de medios/proveedores

**Acciones:** benchmark de proveedores por vertical, acuerdos/API cuando proceda, caching permitido, métricas de costo, automatización de selección autorizada, pruebas de volumen.  
**Entrega:** costos p50/p90 por sitio aprobado, costes legales/documentales y cobertura del catálogo para varios sectores.  
**Cierre:** casos piloto con gastos y tiempos humanos transparentes, sin licencias incompatibles ni descargas prohibidas.

### H10 — Preparación para integraciones funcionales (fase posterior, fuera de alcance actual)

**Acciones futuras posibles:** conectar adapters de reservas, citas, pedidos, inventario, disponibilidad, pagos, membresías, mapas o entregas; seguridad, privacidad, auditoría y pruebas de flujos de negocio.  
**Entrega de esta fase:** **solo especificaciones e interfaces** que permitan conectarlos sin rediseñar componentes.  
**No adelantarse** implementando backends como supuesto prerrequisito para probar la máquina de diseño.

### 24.1. Dependencias entre hitos

```text
H0 → H1 → H2 → H4 → H5 → H6 → H7 → H8
                  ↑     ↑
             H3 medios ┘
                         H9 tras pruebas reales
                         H10 posteriormente
```

H3 puede avanzar parcialmente en paralelo con H1/H2 si se trabaja con fixtures y derechos. La selección final de medios depende del brief y del diseño; por tanto, el ciclo de media/art direction continúa iterando incluso cuando el conector esté listo.

### 24.2. Cada PR/milestone debe terminar con

```text
Objetivo / scope
Archivos tocados
Qué se reutilizó y qué se añadió
Evidencia de ejecución y resultados
Tests y cobertura
Riesgos o límites conocidos
Comparación contra baseline
Condición de cierre PASSED/FAILED/NOT_TESTED
Siguiente cambio acotado
```

No avanzar en dependencias críticas cuando un Hito previo falla: primero entender si el problema es upstream, componentes, medios, entorno o criterio visual.

---

## 25. Riesgos, tensiones y mitigaciones

| Riesgo o tensión | Consecuencia | Diseño de mitigación |
|---|---|---|
| Categoría tomada como permiso | Capacidad falsa, página impropia | Tri-state factual + arquetipos como priors + capability QA |
| Pérdida de información en el renderer | Web bonita pero vacía o incorrecta | Binding report + cobertura semántica DOM |
| Stock comercial engañoso | Publicidad que atribuye instalaciones/personas falsas | Roles documentales/ilustrativos y truthfulness visual |
| Licencias multi-cliente incompatibles | Riesgo contractual/copyright | LicenseGrant por activo-uso-cliente; rights gate; asesoría contractual |
| Búsqueda automatizada prohibida | Incumplimiento de plataforma | Conectores solo tras verificar APIs/acuerdos y condiciones |
| Ingesta OSS confundida con integración | Dependencias o componentes rotos | Estados SOURCE_BACKED/INDEXED_ONLY y pruebas reales |
| Plantillización | Centenares de sitios casi iguales | Composición probabilística + diversidad estructural + comparación humana |
| Caos probabilístico | Sitios incoherentes e imposibles de mantener | AST declarativo + constraints + runtime fijo + DesignLock |
| Sobreoptimización de screenshots | Fallos móviles/video/interacciones reales | Navegador dinámico, móvil, motion, auditoría humana |
| Evaluador visual complaciente | Falso progreso | Pruebas ciegas, fixtures retenidos, opción «ninguna», métricas verificables |
| Video de alto peso | Sitios bonitos pero lentos | Media budgets, posters, cargas controladas, fallback móvil |
| Overengineering del solver | Complejidad sin mejora visual | Comparar solver topológico con CSS Grid/flex certificados |
| Mucho código cliente-específico | Escala económica no alcanzada | KPI de archivos/hacks/dependencias por sitio; propuesta al registry |
| Cambios silenciosos del upstream | Contenido y sedes inconsistentes | Snapshots, contrato versionado, fact IDs y QA de bindings |
| Uso de LLM como ejecutor de código | Inyección, dependencias y build incontrolados | Solo planes declarativos validados y sandbox/escape de datos |
| Sesgo hacia restaurante premium | Diseño inapropiado para otros negocios | Corpus de referencia por sector + fixtures multiverticales |
| Mezcla de sucursales | Horarios/servicios/fotos erróneos | Bindings y capacidades scope por branch |
| Acciones visuales inoperantes | Confusión y falta de credibilidad | Preview etiquetado; solo enlaces reales o UI estática en entregas |
| Datos de salud/finanzas/personas | Errores sensibles y exposición de información | Restricción de contenido, minimización, revisión regulatoria y permisos |

---

## 26. Decisiones aún abiertas y protocolo para cerrarlas

No presentarlas como decisiones ya tomadas. Para cada una registrar responsable, experimento, fecha, evidencia y conclusión:

| Pregunta abierta | Experimento o verificación para resolverla |
|---|---|
| ¿Qué archivos reales del compiler experimental siguen vigentes? | H0: inventario de worktrees/commits + tests actuales |
| ¿Conviene extender `SiteSpec` o adaptar una representación intermedia? | Prueba de compatibilidad con binding planner y menor migración |
| ¿Cuáles de los operadores históricos tienen calidad certificable? | Reconstruir 3 páginas con esos operadores y benchmarks visuales |
| ¿Qué proveedor de media cubre automación legal multi-cliente? | Matriz de términos actuales, licencias efectivas y acuerdos comerciales |
| ¿Qué proporción de media upstream tiene derechos de publicación? | Muestreo por fuentes, negocio y sucursal; revisión de provenance |
| ¿Qué copyright/uso de datasets de referencias está permitido? | Política de almacenamiento/capturas/entrenamiento y revisión documental |
| ¿Cuándo conviene video frente a fotografía? | A/B contenido fijo + perf + preferencia humana |
| ¿Es útil un solver topológico costoso? | Comparación ciega de resultados vs reglas CSS con igual presupuesto |
| ¿Qué pesos/prior de diseño iniciales tienen validez? | Fixture fijo, comparaciones repetidas y análisis de preferencias |
| ¿Cuál es el techo real de rendimiento por capability? | Lab tests y campo, no bytes fijados solo por intuición |
| ¿Qué capabilities requieren backend mínimo para mostrar algo honesto? | Matriz de estados y revisión de UX por tipo de acción |
| ¿Qué verticales cubrir primero? | Cruce de inventario no deduplicado, oportunidad comercial, dificultad y casos reales |
| ¿Cómo elegiremos entre calidad y costo por sitio? | Frontera Pareto con revisión humana y presupuesto explícito |

---

## 27. Primer encargo ejecutable para Codex/agente del repositorio

> **Objetivo:** preparar integración y primer experimento multivertical **sin construir otro sitio generador ni duplicar el upstream**.
>
> 1. Trabaja sobre los repositorios y worktrees existentes de 101. Lee sus archivos de instrucciones de contexto; identifica branch, HEAD, cambios locales y restricciones antes de editar.
> 2. Localiza y prueba `Truth`/publication, `SiteSpec`, `Business Genome`, `CompilerBindingPlanner`, `ConstrainedCompositionEngine`, `WebsiteCompiler`, `@101/site-runtime`, Astro, browser QA, el Design Compiler experimental, operadores espaciales, raster critique, media analyzer, mutator, el solucionador topológico y el corpus OSS.
> 3. Entrega `reuse-map` con ruta exacta, commit, estado **INTEGRATED/TESTED/EXPERIMENTAL/INDEXED_ONLY/MISSING** y comando de prueba; entrega `gap-map` con el adaptador mínimo. No declares integrado lo que solo se mencionó en un handoff.
> 4. Analiza `message (4).txt` como **inventario de observaciones de categorías**, no como negocios únicos. Conserva datos por Foursquare/OSM/Overture y campos originales. Propón `BusinessInputV1`, `BusinessProfileV1`, `CapabilityProfileV1` y `SitePlanV1` con ejemplos **restaurante, ferretería y gimnasio**. `delivery=UNKNOWN` no se convierte en un módulo de reparto.
> 5. Diseña la matriz de capabilities con frontend contracts y estados. El backend permanece pospuesto; un preview de compra/reserva no debe fingir operaciones reales.
> 6. Diseña `MediaAsset`, `LicenseGrant` y `MediaUsage`; audita derechos de fotos upstream y lista necesidades adicionales. **No descargues** catálogos ni automatices proveedores sin permisos verificados. Incluye roles `DOCUMENTARY/ILLUSTRATIVE/ATMOSPHERIC`.
> 7. El primer slice de código, si H0 demuestra una ruta reutilizable, debe producir **SitePlans distintos** y una salida declarativa auditable con tests de verdad/capacidad. No instales dependencias de UI y no reescribas el runtime.
> 8. Reporta PASSED/FAILED/NOT_TESTED, las rutas tocadas y el siguiente milestone mínimo. Reserva los cambios estéticos probabilísticos para cuando se haya demostrado que el vocabulario visual puede renderizar tres variantes buenas dentro del runtime existente.
>
> **Condición de cierre inicial:** trazabilidad total del inventario y del código actual, contratos propuestos alineados a 101 y una demostración de planificación semántica de tres arquetipos sin inventar hechos ni añadir un nuevo sistema paralelo.

---

## 28. Fuentes y trazabilidad de esta especificación

**Fuentes del usuario y antecedentes internos:**

1. **Conversación de octubre de 2026:** decisiones literales sobre referencias, adquisición de media, separación upstream/frontend, multiverticalidad, componente determinista + dirección de arte probabilística, reutilización de 101 y costo marginal.
2. **`message (4).txt`**, archivo adjunto (7 de octubre de 2026): 4.582 registros `source/category_field/category_value/...`, fuentes Foursquare, OSM y Overture; es inventario de observaciones/categorías y **no** una base de negocios deduplicados.
3. **`101_restaurant_design_pipeline_v0_1.md`** (6 de octubre de 2026): especificación anterior de media, derechos, referencias, operadores, QA, costos y responsabilidades; preservada y generalizada aquí.
4. **`chat_handoff_101_website_design_compiler.md`** (Library): evolución documentada del Design Compiler v0.1–v0.12, ingesta OSS, fact binding, Astro/runtime, QA, historia de replays y frontera integración.
5. **`101_chat_handoff_2026-09-28.md`** y **`101_chat_state_2026-09-28.md`** (Library): estado histórico de `101-world-model`, Truth/SiteSpec y reparación; **no sustituye** auditoría actual del repo.

**Documentación pública de referencia para la implementación, cuyos términos se deben reconfirmar:**

- Astro islands: https://docs.astro.build/en/concepts/islands/
- Astro images: https://docs.astro.build/en/guides/images/
- Playwright snapshot tests: https://playwright.dev/docs/test-snapshots
- Web Vitals: https://web.dev/articles/vitals
- Video performance: https://web.dev/learn/performance/video-performance
- Animation performance: https://web.dev/articles/animations-guide
- WCAG 2.2: https://www.w3.org/TR/WCAG22/
- Adobe Stock licenses: https://stock.adobe.com/license-terms
- Adobe Stock developer documentation: https://developer.adobe.com/stock/docs/getting-started/
- Pexels terms: https://www.pexels.com/terms-of-service/
- Artlist license: https://artlist.io/help-center/privacy-terms/artlist-license/
- Envato Elements license: https://help.elements.envato.com/hc/en-us/articles/360000628966-Envato-Elements-License
- Filmsupply: https://www.filmsupply.com/

**Límite de verificación:** esta especificación sintetiza materiales anteriores y el archivo de categorías. No demuestra que cada módulo exista implementado, que el upstream ya cumpla el contrato, que se haya firmado un acuerdo multimedia, que el proveedor permita el volumen de automatización esperado ni que los sitios finales hayan alcanzado el nivel visual buscado. Todo se somete a hitos y pruebas con evidencia.

---

## 29. Glosario breve

- **Upstream:** sistema anterior que obtiene, clasifica y valida datos del negocio.
- **Truth/PublicationDecision:** controles existentes de 101 sobre qué hechos pueden publicarse.
- **BusinessInput:** paquete de datos factuales para el Website Compiler.
- **Arquetipo:** patrón del modelo de negocio, potencialmente combinado con otros.
- **Capability:** capacidad operativa del negocio con estado factual independiente de su representación técnica.
- **Offering:** objeto de oferta (producto, servicio, curso, habitación, plato, etc.).
- **Módulo semántico:** qué contenido/acción representa un fragmento o página.
- **SitePlan:** mapa de rutas y módulos, sin dirección visual.
- **ArtDirection:** planteamiento coherente de lenguaje visual.
- **Operador:** regla abstracta de composición espacial reutilizable.
- **DesignPlan/AST:** representación declarativa de composición apta para compilar, mutar y auditar.
- **Runtime:** infraestructura compartida y componentes que ejecutan todos los sitios.
- **MediaAsset:** archivo/original y derivados con provenance.
- **LicenseGrant:** autorización contractual delimitada para uso del recurso.
- **MediaUsage:** aplicación concreta de un asset en un cliente, sección y propósito.
- **QA gate:** prueba o regla cuya aprobación permite avanzar; no todos los gates son sustituibles por scores.
- **Fixture:** caso de prueba congelado que permite comparar experimentos.
- **Design Lock:** snapshot de decisiones, medios y versiones para reproducir el resultado final sin regeneración probabilística.
- **Pareto frontier:** conjunto de alternativas donde mejorar un objetivo exigiría empeorar otro, usado para elegir entre calidad, diversidad, performance y costo después de pasar restricciones duras.

---

## 30. Cierre: el criterio de éxito

La prueba de que construimos el sistema correcto no será presentar una home hermosa de un restaurante Michelin. Será demostrar, sin introducir código particular, que el **mismo motor** toma datos verificados de una **ferretería**, un **gimnasio**, un **restaurante**, una **clínica** o un **hotel**, determina los módulos pertinentes a cada uno, reúne los medios disponibles o legalmente adquiridos, propone varias direcciones visuales no triviales, produce sitios correctos y rápidos, y deja una versión aprobada que puede reconstruirse exactamente.

> **Base común y leyes estrictas; interpretación del negocio correcta; recursos visuales excepcionales y honestos; dirección artística probabilística; composición original; auditorías y aprendizaje.** Cada nuevo negocio debe consumir la máquina, no obligarnos a volver a construirla.
