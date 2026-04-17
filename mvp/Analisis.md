# Informe MVP — Liverpool Air Quality Intelligence Platform

**Fecha:** 15 de Abril de 2026  
**Base técnica:** Milestone 1 completado · Pipeline LUR completado (Milestone 2 en curso)  
**Propósito:** Definir enfoque, alcance, stack tecnológico y estrategia go-to-market de un producto mínimo viable comercializable

---

## 1. El Activo Real: Lo Que Ya Tienes

Antes de hablar de producto, hay que entender con precisión qué material científico existe hoy y qué valor comercial representa cada pieza.

| Activo | Estado | Descripción | Valor comercial |
|---|---|---|---|
| `liverpool_pollution_map.geojson` | Producido | 8.450 tramos de calle con PM2.5 y PM10 predichos | Cobertura 100% de la red viaria de Liverpool — ningún competidor tiene esto a nivel de tramo |
| `lur_model_PM25.pkl` / `lur_model_PM10.pkl` | Serializados | Modelos SVR entrenados, R² = 0.602 (PM2.5) y 0.581 (PM10) LOOCV | Reentrenables e integrables en cualquier API Python sin trabajo de ML adicional |
| Pipeline reproducible | 9 scripts encadenados | Desde ingesta de sensores hasta GeoJSON final | Permite actualizar predicciones con nuevos datos de sensores; **la ventaja defensiva clave** |
| Datos de 24 sensores | CSV histórico 2021–2025 | Historial real de monitorización, no datos sintéticos | Credibilidad científica frente a modelos puramente satelitales o de interpolación gruesa |
| Features urbanas enriquecidas | OSM + AADF + Elevación + Vegetación | Variables proxy validadas estadísticamente | Replicable a cualquier ciudad con red OSM y datos DfT AADF disponibles públicamente |

**Conclusión de inventario:** El GeoJSON es el producto entregable. Los modelos son el motor. El pipeline es la ventaja defensiva. Los sensores son la credibilidad.

Lo que aún falta para tener un MVP funcional no es ciencia — es ingeniería de producto: una API, un dashboard, y un proceso de venta.

---

## 2. Contexto Regulatorio y de Mercado

Entender por qué existe una ventana de oportunidad ahora es tan importante como el producto mismo.

### Marco normativo UK

| Norma | Contenido relevante | Implicación para AirTrace |
|---|---|---|
| **UK Clean Air Strategy 2019** | Objetivo: reducir PM2.5 a < 10 µg/m³ para 2040; todos los ayuntamientos deben presentar planes locales | Los gobiernos locales *necesitan* datos hiperlocales para justificar inversiones y medir progreso |
| **Environment Act 2021** | Obliga a autoridades locales a establecer Local Air Quality Management Areas (AQMAs) con evidencia cuantitativa | Las decisiones sobre zonas de baja emisión requieren el nivel de granularidad que AirTrace ofrece |
| **Clean Air Zones (CAZ) Framework** | Bath, Birmingham, Bristol ya operativas; Liverpool en etapa de evaluación según JAQU (Joint Air Quality Unit) | Liverpool City Council tiene una obligación legal activa de tomar decisiones basadas en datos de calidad del aire |
| **WHO Guidelines 2021** | Nuevo límite PM2.5: 5 µg/m³ anual (más estricto que el objetivo UK) | Presión creciente; los datos de AirTrace muestran qué tramos ya superan incluso los límites UK actuales de 20 µg/m³ |

### Tamaño del mercado (UK urbano)

- **317** autoridades locales en UK con obligaciones de LAQM
- **~£4.2bn** presupuesto combinado de gestión ambiental en gobiernos locales UK (2024, DLUHC)
- **£1.2bn** en fondos UKSPF y Levelling Up con componentes de sostenibilidad urbana activos hasta 2026
- El mercado de "environmental intelligence" SaaS en UK y Europa creció un **23% CAGR** entre 2021–2025 (Verdantix, 2025)

**Ventana temporal:** La CAZ de Liverpool está en evaluación activa. El momento de venta es ahora, no cuando la zona esté aprobada.

---

## 3. Definición del MVP

### Propuesta de valor central

> **"Cualquier dirección de Liverpool. Su nivel de contaminación PM2.5/PM10 validado. En menos de 3 segundos."**

No es un mapa académico. Es la capa de inteligencia ambiental que falta en las herramientas de decisión urbana, inmobiliaria, logística y de salud pública.

### Nombre propuesto: AirTrace

### Qué ES el MVP

1. Una **API REST** con autenticación por API key que acepta coordenadas (o postcodes UK) y devuelve predicciones de PM2.5/PM10 con nivel de confianza
2. Un **dashboard web interactivo** con el mapa de calor de Liverpool por tramo de calle, filtrable por contaminante y umbral regulatorio
3. Un **endpoint de descarga** del GeoJSON completo (acceso solo para clientes institucionales con licencia)
4. Un **sistema de API keys** con rate limiting, dashboar de uso, y facturación básica

### Qué NO ES el MVP (scope boundaries explícitos)

- No incluye datos en tiempo real (eso es v2.1)
- No incluye otras ciudades (eso es v2.0)
- No incluye una app móvil (eso es Segmento D, monetización diferida)
- No incluye health impact assessment calculado automáticamente (eso es v1.3)
- No incluye reentrenamiento automático en producción (cron mensual manual es suficiente para MVP)

### Definición de "lanzado"

El MVP está lanzado cuando:
- [ ] El endpoint `/predict` responde con < 200 ms en el 95° percentil
- [ ] El dashboard está accesible en una URL pública con autenticación básica
- [ ] Existe al menos 1 API key activa de un cliente piloto
- [ ] El GeoJSON está en PostGIS y se puede consultar por bounding box

---

## 4. Casos de Uso por Segmento — Visión Empresarial

### Segmento A — B2G (Business to Government) ⭐ Prioritario MVP

**Clientes objetivo:** Liverpool City Council · Transport for Liverpool · NHS Cheshire & Merseyside · Merseytravel

**Problema que tienen hoy:**

Los departamentos de planificación urbana y salud pública de Liverpool toman decisiones sobre Clean Air Zones basándose en:
- Mediciones de las **4–6 estaciones DEFRA AURN** de Liverpool (una cada ~5 km²)
- Modelos de dispersión del Departamento de Transporte con granularidad de 100×100 m
- Estudios de consultoras contratadas ad-hoc (precio: £50k–£200k por encargo)

Ninguna de estas fuentes ofrece resolución a nivel de tramo de calle con cobertura total.

**Cómo AirTrace resuelve cada problema:**

| Problema del cliente | Solución AirTrace | Dato de soporte |
|---|---|---|
| Seleccionar qué calles priorizar para CAZ | Ranking de tramos por PM2.5/PM10, exportable a GIS | 8.450 tramos ordenados por contaminación predicha |
| Justificar inversión en carril bici (Green Routes) | Mostrar reducción de exposición en rutas alternativas | Diferencias de PM2.5 entre calles paralelas a la misma distancia |
| Cumplir KPIs de UK Clean Air Strategy | Baseline cuantitativo con historicidad 2021–2025 | Permite medir mejora año a año cuando se implementen medidas |
| Responder al NHS sobre zonas de alta exposición | Mapa de exposición superpuesto con datos de densidad poblacional | Integrable con datos LSOA del ONS |
| Presupuestar intervenciones ambientales | Priorización objetiva vs. política | Reduce coste de consultoría externa recurrente |

**Buyer journey:**

1. Primer contacto → demostración del dashboard con datos reales de Liverpool (no un demo genérico)
2. Piloto de 3 meses gratuito o £5k → acceso completo a la API y al GeoJSON
3. Evaluación interna por parte del equipo de datos del Council
4. Contrato anual de licencia SaaS

**Modelo de monetización:**

| Tier | Precio anual | Incluye |
|---|---|---|
| Starter (NHS, ONGs) | £15.000/año | Dashboard + 50k llamadas API/mes + soporte email |
| Professional (City Council) | £35.000/año | Dashboard + 500k llamadas API/mes + GeoJSON descargable + 4 sesiones de consultoría |
| Enterprise (Transport for Liverpool, consorcio) | £75.000+/año | Todo lo anterior + SLA 99.9% + reentrenamiento personalizado + integración GIS a medida |

**Potencial de ingresos a 12 meses:** 1 cliente Professional + 1 Starter = £50.000 ARR. Ese número es alcanzable con 0 empleados de ventas — solo con el PI del proyecto más un contacto en el Council.

---

### Segmento B — B2B Real Estate & Construcción

**Clientes objetivo:** Rightmove · Savills · CBRE · Barratt Developments · agencias locales independientes

**El problema estructural:**

El EPC (Energy Performance Certificate) es obligatorio en toda venta e alquiler en UK. La calidad del aire interior (MEES) empieza a aparecer en diligencias de due diligence. El paso siguiente — un certificado de calidad del aire exterior por dirección — **no existe todavía como producto estándar de mercado**.

El comprador de vivienda de 2026 ya busca datos de calidad del aire en Zoopla y Rightmove. Rightmove ofrece ruido (noise maps), transporte y colegios. La calidad del aire no está. Es una gap de datos real, no especulativa.

**Propuesta:**

Una API que devuelve un **Air Quality Score A–F** para cualquier coordenada de Liverpool, embebible en cualquier ficha de propiedad con una línea de JavaScript. El score se calcula como combinación ponderada de PM2.5 y PM10 respecto a los límites WHO/UK.

```
GET /api/v1/score?lat=53.4048&lon=-2.9814
→ { "score": "C", "pm25": 14.2, "pm10": 22.1, "label": "Moderate", "who_limit_pm25": 5 }
```

**Modelo de monetización:** API pay-per-call

| Volumen mensual | Precio por llamada | Ingreso mensual estimado |
|---|---|---|
| < 10.000 | £0.012 | < £120 |
| 10.000 – 100.000 | £0.008 | £80 – £800 |
| > 100.000 | £0.004 | > £400 |
| Plan fijo (agencias) | £299/mes ilimitado en Liverpool | Predecible |

**Un solo cliente agregador** (p. ej. Rightmove con ~50M listings en UK, aunque solo Liverpool inicialmente) puede representar > 1M llamadas/mes.

**Barrera de adopción principal:** Integración técnica (1–2 días de desarrollo del cliente). Mitigación: SDK JavaScript de 3 líneas + documentación en Postman.

---

### Segmento C — B2B Logística y Flotas

**Clientes objetivo:** DHL Supply Chain (Liverpool hub) · Amazon Logistics · Yodel · empresas de reparto last-mile con flotas eléctricas o mixtas

**El problema:**

Las empresas de logística con compromisos ESG (Science Based Targets, CDP reporting) necesitan cuantificar la **exposición de conductores a contaminantes** en sus rutas operativas. Los sistemas de optimización de rutas actuales — Google OR-Tools, HERE Routing, Routific — optimizan por tiempo y distancia. **Ninguno incorpora calidad del aire como dimensión de coste.**

Además, el UK Taskforce on Nature-related Financial Disclosures (TNFD) y el Corporate Sustainability Reporting Directive (CSRD, aplicable a filiales UK de empresas europeas) están empezando a requerir métricas de impacto en calidad del aire.

**Propuesta:**

Integración del GeoJSON de AirTrace en algoritmos de optimización de rutas como capa de penalización. Un parámetro `air_quality_weight` en la llamada API permite a cada empresa decidir cuánto peso dar a la ruta limpia vs. la ruta rápida.

También: un **informe mensual automático** de exposición agregada de la flota (kg·h de PM2.5 acumulados por conductor), listo para incluir en reporting ESG.

**Modelo de monetización:**

| Producto | Precio | Target |
|---|---|---|
| Plugin API (routing overlay) | £800/mes por empresa | Empresas con > 20 vehículos en Liverpool |
| Informe ESG mensual automatizado | £500/mes add-on | Empresas con obligaciones CSRD/CDP |
| Integración custom (SDK para su TMS) | £5.000–£15.000 one-time + £500/mes | Operadores logísticos grandes |

**Riesgo:** Ciclo de venta largo (6–12 meses para decisiones de TMS en empresas grandes). Mitigación: empezar con PYMEs de reparto local donde la decisión la toma una persona.

---

### Segmento D — B2C Salud y Bienestar (Monetización diferida, valor estratégico ahora)

**Usuarios objetivo:** Ciudadanos de Liverpool con condiciones respiratorias · padres con niños pequeños · ciclistas y corredores urbanos · turistas

**Por qué no es prioritario en MVP:**

- Requiere escala de usuarios (> 10.000 DAU) para monetizar con publicidad o freemium significativo
- El CAC en B2C supera el LTV en los primeros 18 meses si no hay red effect
- No hay revenue hasta masa crítica

**Por qué sí hay que construir la capa técnica ahora:**

- La base de datos de comportamiento de rutas de ciudadanos es el **activo más valioso a largo plazo** para vender a seguros de salud, farmacias y NHS a nivel agregado y anonimizado
- Un widget embebible en la web del Council (Segmento A) puede generar awareness B2C sin coste adicional
- Las métricas de engagement B2C son el argumento para una ronda de inversión en v2.0

**Propuesta diferida:**

App web progresiva (PWA) con integración en Apple Health / Google Fit que muestra el score de calidad del aire de la ruta planificada antes de salir. Freemium: ruta básica gratuita → rutas optimizadas por calidad del aire £2.99/mes.

---

## 5. Arquitectura Técnica del MVP

### Diagrama de flujo de datos

```
[Fuentes de datos]              [Backend / Motor]              [Interfaces]
───────────────────             ─────────────────              ─────────────
24 sensores IoT ──────────────→ Pipeline Python ────────────→ Dashboard web
OSM Liverpool   ──────────────→ lur_model.pkl  ────────────→ REST API (FastAPI)
AADF DfT        ──────────────→ GeoJSON 8.450  ────────────→ GeoJSON endpoint
MIDAS Meteo     ──────────────→ tramos PostGIS ────────────→ Embed widget (iframe)

[Actualización]                                [Distribución B2B]
───────────────                                ──────────────────
Cron mensual cuando llegan                     API key management (Supabase)
nuevos datos de sensores                       Rate limiting por tier
                                               SLA 99.5% uptime
```

### Stack mínimo viable

| Capa | Tecnología elegida | Alternativa descartada | Justificación de elección |
|---|---|---|---|
| **Backend API** | FastAPI + Uvicorn | Flask, Django | Python nativo, async, autodoc con OpenAPI, comparte entorno con los modelos `.pkl` |
| **Modelos ML** | Existentes `.pkl` (Ridge) | Reentrenar XGBoost | 0 trabajo de ML adicional para el MVP; rendimiento ya validado |
| **Geodatos** | GeoPandas + GeoJSON | Shapefile, FlatGeobuf | El pipeline ya produce GeoJSON; sin conversión |
| **Base de datos** | PostGIS (PostgreSQL) | SQLite + Spatialite | Consultas espaciales por coordenada/bounding box; necesario para escala |
| **Visualización** | Mapbox GL JS | Kepler.gl, Leaflet | Kepler.gl es mejor para exploración; Mapbox es mejor para producto embebible en otros webs |
| **Hosting** | Railway.app o Render | AWS, GCP, Azure | Despliegue desde GitHub en < 30 min, sin DevOps; gratis hasta cierta escala |
| **Auth / API keys** | Supabase | Auth0, Clerk | Gratuito hasta ~50k req/mes; tiene dashboard de uso integrado |
| **Frontend dashboard** | React + Mapbox GL JS | Streamlit | Streamlit es adecuado para prototipo interno; no para producto comercial que se muestra a un cliente institucional |

### Especificación mínima de endpoints (MVP)

```
GET  /api/v1/predict?lat={lat}&lon={lon}
     → { pm25: float, pm10: float, confidence: "high"|"medium"|"low", nearest_segment_id: str }

GET  /api/v1/score?lat={lat}&lon={lon}
     → { score: "A"|"B"|"C"|"D"|"E"|"F", pm25: float, pm10: float, who_limit_pm25: 5, uk_limit_pm25: 20 }

GET  /api/v1/bbox?minlat=&minlon=&maxlat=&maxlon=
     → GeoJSON FeatureCollection de tramos en el bounding box (máx. 500 features)

GET  /api/v1/geojson/full
     → GeoJSON completo (requiere licencia Enterprise)

GET  /api/v1/health
     → { status: "ok", model_version: str, last_trained: date, coverage_segments: 8450 }
```

### Consideraciones GDPR / seguridad

- Las coordenadas enviadas a la API **no son datos personales** per se, pero en contexto pueden serlo (localización de un usuario)
- Para el MVP B2G/B2B: las consultas son de tipo "¿cuánta contaminación hay en esta calle?", no tracking de personas → sin obligaciones especiales de GDPR
- Para MVP B2C futuro: anonimización obligatoria, no almacenar coordenadas en logs
- API keys rotables, sin hardcoding en dashboards públicos
- Rate limiting obligatorio para evitar scraping del GeoJSON completo por competidores

### Estimación de costes de infraestructura (MVP)

| Servicio | Tier | Coste mensual |
|---|---|---|
| Railway (API + PostGIS) | Starter | £0–£20 |
| Mapbox GL JS | Free (50k map loads/mes) | £0 |
| Supabase (auth + logs) | Free | £0 |
| Dominio .co.uk | Anual | ~£12/año |
| **Total MVP operativo** | | **< £25/mes** |

El coste de infraestructura es irrelevante hasta 100k llamadas/mes. El coste real del MVP es tiempo de desarrollo.

---

## 6. Análisis Competitivo

### Competitors directos e indirectos

| Competidor | Qué hace | Granularidad | Datos Liverpool | Ventaja AirTrace |
|---|---|---|---|---|
| **Breezometer** | API global de calidad del aire | ~1 km² (interpolación) | Sí, genérico | AirTrace tiene resolución de tramo de calle; Breezometer usa modelos satelitales sin validación local |
| **IQAir** | Plataforma consumer + B2B | Red de sensores fijos | Cobertura limitada UK | AirTrace cubre 100% red viaria Liverpool, no solo ubicaciones con sensor |
| **DEFRA AURN** | Red oficial de monitorización | 4–6 estaciones en Liverpool | Sí, oficial | Resolución espacial incomparablemente menor; datos abiertos (lo cual es una amenaza, ver riesgos) |
| **Plume Labs** (adquirida por Samsara) | Sensores portátiles + API | Resolución alta pero puntual | No | AirTrace da cobertura de ciudad sin necesidad de hardware adicional |
| **Aclima** (US) | Mapping de calidad del aire a nivel de calle | Alta (datos de flota de coches) | No (solo US) | Modelo similar pero sin presencia UK; oportunidad de primera entrada |
| **Consultoras (AECOM, WSP)** | Estudios ad-hoc para councils | Alta cuando los hacen | Sí, bajo contrato | AirTrace es autoservicio, actualizable, y 10–20x más barato por encargo |

### ¿Por qué no lo hace Google?

1. **Hiperlocal con validación estadística.** Google Environmental Insights Explorer usa datos satelitales agregados. AirTrace tiene validación LOOCV a nivel de tramo de calle con sensores reales de Liverpool.
2. **Pipeline reproducible y reentrenable.** No es un snapshot de 2024. Se puede reentrenar con nuevos sensores o nuevos años en horas. Google no tiene incentivo en mantener un modelo de una ciudad específica actualizado mensualmente.
3. **Coste de datos cercano a cero.** OSM + DfT AADF + MIDAS son datos abiertos. La IP está en el pipeline y los modelos, no en los datos. Google podría replicarlo, pero no lo hará para el mercado de gobiernos locales UK.
4. **Relación con el cliente institucional.** Los councils UK no compran SaaS directamente de Google para datos sensibles de política urbana. Compran a proveedores locales especializados con conocimiento del marco regulatorio UK.

---

## 7. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| **R² del modelo degradado con datos nuevos** | Media | Alto | LOOCV automatizado antes de cada despliegue; alerta si R² cae > 5% respecto a baseline |
| **Competidor replica el pipeline con OSM + AADF** | Baja (barrera técnica real) | Alto | Publicar paper académico que cite el proyecto; primeras ventas antes de que llegue un competidor |
| **Liverpool City Council tiene proveedor existente** | Media | Medio | Investigar contratos actuales vía FOI; proponer como complemento, no como reemplazo |
| **DEFRA publica datos a granularidad fina (el argumento de venta colapsa)** | Baja | Alto | Diversificar a otras ciudades UK; la ventaja pasa a ser la actualización frecuente y la integración en APIs |
| **La CAZ de Liverpool se cancela políticamente** | Baja | Medio | El mercado B2B Real Estate y Logística no depende de la CAZ |
| **Costes de hosting se disparan con escala** | Baja (MVP) | Bajo | PostGIS escala verticalmente; Railway admite migración a AWS RDS sin cambiar el código |
| **Privacidad / GDPR en uso B2C futuro** | Alta si no se planifica | Alto | No almacenar coordenadas en logs desde el día 1; política de privacidad antes del lanzamiento B2C |
| **El modelo no generaliza a otras ciudades** | Media | Medio | Validar en Manchester con datos AADF disponibles antes de vender v2.0 |

---

## 8. Economía Unitaria y Modelo Financiero

### Escenario conservador (12 meses post-lanzamiento)

| Fuente de ingresos | Clientes | Precio | ARR |
|---|---|---|---|
| B2G — Professional (Council) | 1 | £35.000/año | £35.000 |
| B2G — Starter (NHS/ONG) | 1 | £15.000/año | £15.000 |
| B2B Real Estate — Plan fijo | 3 agencias | £299/mes × 3 | £10.764 |
| B2B Logística — Plugin API | 2 empresas | £800/mes × 2 | £19.200 |
| **Total ARR conservador** | | | **£79.964** |

### Escenario optimista (18 meses)

| Fuente de ingresos | Clientes | Precio | ARR |
|---|---|---|---|
| B2G — Enterprise (consorcio TfL) | 1 | £75.000/año | £75.000 |
| B2G — Professional | 2 | £35.000/año | £70.000 |
| B2B Real Estate API | 500k calls/mes | £0.006 avg | £36.000 |
| B2B Logística | 5 empresas | £800/mes | £48.000 |
| **Total ARR optimista** | | | **£229.000** |

### Coste de adquisición (CAC) estimado

- Canal principal MVP: contacto directo + demo en person con el Council (CAC ≈ £0, solo tiempo)
- Canal B2B Real Estate: outreach LinkedIn + integración técnica asistida (CAC estimado ≈ £500–£2.000 por cliente)
- Canal B2B Logística: conferencias ESG + referrals del cliente B2G (CAC estimado ≈ £1.000–£5.000)

**LTV/CAC estimado para B2G:** LTV (3 años × £35k) / CAC (≈ £2k) = **52x**. Ratio excelente para SaaS.

---

## 9. Hoja de Ruta Post-MVP

| Fase | Timeline | Entregable | Habilitador técnico | Ingreso incremental |
|---|---|---|---|---|
| **MVP** | Mes 1–4 | API + dashboard Liverpool + 1 cliente B2G piloto | Pipeline actual + FastAPI + PostGIS | £0 (piloto) |
| **v1.0** | Mes 5 | Primer contrato de pago firmado | Proceso comercial + SLA documentado | +£35k ARR |
| **v1.1** | Mes 5–6 | Score A–F por código postal (LSOA) | Issue #21 (LUR barrios) | Nuevo argumento de venta B2B Real Estate |
| **v1.2** | Mes 6–7 | Validación vs estaciones DEFRA AURN | Issue #26 | Credibilidad para licitaciones B2G formales |
| **v1.3** | Mes 7–8 | Health Impact Assessment (DALYs por tramo) | Issue #24 | Argumento NHS irrefutable |
| **v2.0** | Mes 9–12 | Segunda ciudad (Manchester) | Pipeline reproducible; validación AADF Manchester | Duplica TAM accesible |
| **v2.1** | Mes 12–18 | Datos en tiempo real (sensores IoT streaming) | Apache Kafka o Google Pub/Sub | Nuevo tier Enterprise + contratos de monitorización continua |

---

## 10. Go-to-Market: Los Primeros 90 Días

La secuencia importa. No lanzar sin un cliente piloto identificado.

### Días 1–30: Construir y preparar

- Desplegar la API en Railway con los datos actuales
- Crear el dashboard con Mapbox GL JS mostrando Liverpool completo
- Preparar un deck de 10 slides para el Council (problema → solución → demo → precio)
- Identificar el contacto correcto en Liverpool City Council: Directora de Sostenibilidad o Jefa de Estrategia de Transporte

### Días 31–60: Primera venta

- Solicitar demo con Liverpool City Council vía LinkedIn o contacto frío por email institucional
- Mostrar el mapa real de Liverpool con los datos reales — no mockups
- Proponer piloto de 3 meses a £5.000 (acceso completo al dashboard + 3 sesiones de revisión de datos)
- Paralelamente: contactar a 5 agencias inmobiliarias locales para piloto de API key gratuita

### Días 61–90: Iteración y expansión

- Incorporar feedback del piloto B2G en el dashboard
- Presentar resultados del piloto en una sesión interna del Council para obtener endorsement de más departamentos
- Convertir el piloto en contrato anual
- Publicar 1 post técnico en LinkedIn sobre el proyecto (tráfico inbound orgánico para B2B)

---

## 11. Infraestructura Claude Code para Operar AirTrace

### Skills custom a desarrollar

| Skill | Descripción | Cuándo se usa |
|---|---|---|
| `airtraceapi:deploy` | Despliega la FastAPI con el GeoJSON al servidor de staging; verifica el endpoint `/predict` y `/health` | Antes de cada release |
| `airtraceapi:refresh-map` | Ejecuta el pipeline completo (scripts 01–09) y sube el nuevo GeoJSON a la BD PostGIS | Mensualmente cuando llegan nuevos datos de sensores |
| `airtraceapi:validate` | Corre LOOCV sobre los datos más recientes y compara R² vs baseline almacenado; bloquea el despliegue si degradación > 5% | Antes de cada `refresh-map` |
| `lur:pruebad` | Ejecuta el experimento PruebaD (efectos fijos año) y genera el informe comparativo automáticamente | Al iniciar cada nueva iteración de modelado |

### Conectores MCP relevantes

| Conector | Propósito en AirTrace | Disponible hoy |
|---|---|---|
| **Google Maps / Mapbox MCP** | Geocodificar postcodes UK a coordenadas para normalizar inputs de la API | No (pendiente configurar) |
| **GitHub MCP** | Automatizar PRs cuando el pipeline produce un nuevo GeoJSON validado + actualizar issues de Milestone 2 | No |
| **PostgreSQL/PostGIS MCP** | Consultar y actualizar la tabla de tramos directamente desde Claude Code sin salir del contexto | No |
| **Slack/Teams MCP** | Notificar al equipo cuando el reentrenamiento detecta degradación de R² o cuando un nuevo cliente solicita API key | No |
| **Google Drive MCP** | Compartir reportes PDF con stakeholders institucionales (City Council, NHS) tras cada ciclo de análisis | Sí (ya disponible) |
| **Gmail MCP** | Envío automatizado de alertas de calidad del aire a suscriptores B2G y resúmenes mensuales de uso de API | Sí (ya disponible) |

### Hooks de automatización recomendados (`settings.json`)

```jsonc
// Tras ejecutar cualquier script del pipeline, verificar que los outputs existen
// hook: post_tool_use → Bash → python src/utils/verify_outputs.py

// Antes de cualquier commit en rama LUR, correr el LOOCV rápido (< 2 min)
// hook: pre_commit → python src/models/quick_loocv_check.py

// Al hacer deploy a Railway, verificar que /health devuelve 200 y R² > 0.55
// hook: post_deploy → python scripts/smoke_test_api.py
```

### Agentes especializados existentes (reutilizables)

| Agente | Rol en AirTrace |
|---|---|
| `lur-01-data-extraction` | Reingesta de sensores + OSM cuando hay nuevos datos disponibles |
| `lur-03-model-deliverables` | Reentrenamiento + validación automática mensual; genera el nuevo `.pkl` |
| `model-deliverables` | Generación de informes técnicos para clientes institucionales tras cada ciclo |

---

## 12. Features Diferenciadores del Dashboard — Brainstorm

Las cuatro ideas del brainstorm no son solo mejoras estéticas: cada una resuelve una necesidad diferente del cliente institucional y genera argumentos de venta que un mapa estático no puede ofrecer.

### Feature 1 — Evolución Temporal del Mapa

**Idea:** Un slider de tiempo que permita ver cómo han cambiado los niveles de PM2.5/PM10 por tramo de calle entre 2021 y 2025.

**Por qué importa comercialmente:**
- El cliente B2G necesita demostrar que sus intervenciones (p. ej. cambio de gestión de tráfico, nuevas rutas de autobús) han reducido la contaminación. Sin un mapa histórico, no hay antes/después.
- Para una licitación formal, el Consejo necesita mostrar tendencia temporal, no solo un snapshot.

**Implementación técnica:**
- Añadir columna `year` (2021–2025) a la tabla `streets` en Supabase.
- Cada tramo tiene una fila por año, con sus predicciones correspondientes.
- El slider en el frontend filtra por `year` vía parámetro en `/api/streets?year=2023`.
- El pipeline ya produce un GeoJSON por ejecución anual — solo hay que etiquetar y cargar los históricos.

**Prioridad:** v1.1 (no MVP, pero preparar el esquema de BD desde el inicio para evitar migración)

---

### Feature 2 — Panel EDA Evolutivo

**Idea:** Gráficos de tendencia temporal en el sidebar del dashboard, no solo el mapa estático.

**Por qué importa comercialmente:**
- Convierte el producto de "mapa bonito" a "herramienta de análisis". Un analista del Council puede exportar el gráfico directamente a su presentación de comité.
- Las series temporales de PM2.5 medio mensual por zona (barrio, LSOA, tipo de vía) responden a preguntas que el mapa no puede: ¿la contaminación en el centro mejora en verano? ¿Las calles residenciales empeoran los lunes?

**Visualizaciones mínimas:**
- Serie temporal de PM2.5 y PM10 medio de Liverpool (línea)
- Distribución mensual por tipo de vía (`highway`: primary / secondary / residential)
- Comparativa entre LSOAs seleccionados (multi-línea)

**Implementación técnica:**
- Endpoint `GET /api/timeseries?lsoa={code}&metric=pm25` — agrega datos históricos por LSOA y mes.
- Frontend: componente `TimeseriesChart.tsx` usando Chart.js o Recharts (< 50 kB de bundle).

**Prioridad:** v1.1 — junto con el slider temporal

---

### Feature 3 — Eventos Canónicos (Popups Explicativos)

**Idea:** Superponer en la línea de tiempo hitos que explican cambios en la contaminación: confinamientos COVID, cambios de política de transporte, obras importantes, eventos climáticos extremos.

**Por qué importa comercialmente:**
- Transforma el producto de "datos crudos" a "inteligencia contextualizada". Un directivo del Council no quiere solo ver que PM2.5 bajó en abril de 2020 — quiere saber por qué y qué aprendizaje se puede replicar.
- Los popups de eventos son argumentos de causa-efecto que justifican inversiones: "cuando cerramos esta calle al tráfico, PM2.5 bajó X%".

**Eventos base a incluir:**
| Fecha | Evento | Tipo |
|---|---|---|
| Mar 2020 – Jun 2021 | Confinamiento COVID-19 | Societal |
| Ene 2023 | Anuncio de evaluación CAZ Liverpool | Policy |
| Ago 2024 | Ola de calor UK (efecto en PM10) | Climate |
| Ene 2022 | Nuevas rutas de bus eléctrico Merseytravel | Transport |

**Implementación técnica:**
- Tabla `events` en Supabase con campos: `date`, `label`, `description`, `type` (policy/climate/health/transport).
- Endpoint `GET /api/events?from=&to=` — devuelve eventos en rango de fechas.
- Frontend: marcadores en el eje de tiempo del slider con tooltip al hover.

**Prioridad:** v1.1 — bajo coste técnico, alto impacto demo

---

### Feature 4 — Interactividad Profunda

**Idea:** El mapa no es solo un fondo — responde a interacciones del usuario.

**Interacciones prioritarias:**
1. **Click en tramo** → popup con `name`, `highway`, `pm25_pred` (score A–F), `pm10_pred`, `aadf_imputed` (tráfico estimado), distancia al centro
2. **Buscar dirección** → geocodificación (Nominatim/Mapbox) → centrar mapa + resaltar tramos en radio 200m + mostrar `PollutionScore` card
3. **Filtros de capa** → mostrar solo tramos con score D/E/F (los peores) para identificar zonas de intervención prioritaria
4. **Comparar LSOAs** → seleccionar dos LSOAs y ver diferencia de PM2.5 con contexto de desigualdad social

**Implementación técnica:**
- Todo en el frontend (`AirMap.tsx`) con eventos Mapbox GL JS estándar (`map.on('click', ...)`)
- Filtro de capas: expresión Mapbox `['>', ['get', 'pm25_pred'], 15]` — sin llamada adicional a la API
- Búsqueda por dirección: Nominatim (gratuito, GDPR-compliant) o Mapbox Geocoding API (token ya disponible)

**Prioridad:** MVP — las features 1 y 2 son las que diferencian en demo; el click básico debe estar en v0.1

---

### Integración en roadmap actualizado

| Feature | Roadmap | Coste técnico estimado |
|---|---|---|
| Click en tramo → popup | MVP | 0.5 días |
| Búsqueda por dirección | MVP | 1 día |
| Filtros de capa (score D/E/F) | MVP | 0.5 días |
| Slider temporal (2021–2025) | v1.1 | 3 días (incluyendo carga de históricos) |
| Panel EDA evolutivo | v1.1 | 2 días |
| Eventos canónicos (popups timeline) | v1.1 | 1 día |
| Comparativa LSOAs | v1.2 | 2 días |

---

## 13. Métricas de Éxito del MVP

### KPIs técnicos

| KPI | Target a 6 meses | Cómo medirlo | Estado actual |
|---|---|---|---|
| Latencia API `/predict` (p95) | < 200 ms | Monitorización endpoint (UptimeRobot o similar) | No desplegada |
| Cobertura geográfica | 100% red viaria Liverpool | Verificar NaN en GeoJSON | ✅ 8.450 tramos |
| R² PM2.5 en reentrenamiento | ≥ 0.60 | LOOCV automatizado | ✅ 0.602 (SVR, sesión Abril 2026) |
| R² PM10 en reentrenamiento | ≥ 0.58 | LOOCV automatizado | ✅ 0.581 (SVR, sesión Abril 2026) |
| Uptime API | ≥ 99.5% | UptimeRobot monthly report | No desplegada |
| Tiempo de actualización del mapa | < 2 horas desde nuevos datos de sensores | Log del pipeline | No medido |

### KPIs de negocio

| KPI | Target a 6 meses | Target a 12 meses | Cómo medirlo |
|---|---|---|---|
| ARR | £5.000 (piloto) | £50.000 | CRM / contrato firmado |
| Clientes activos con API key | ≥ 1 piloto | ≥ 5 empresas | Supabase dashboard |
| Primer contrato B2G | Piloto firmado | Contrato anual | Proceso comercial |
| NPS clientes piloto | N/A | ≥ 40 | Encuesta post-piloto |
| Tasa de retención (renewal) | N/A | ≥ 80% | Renovaciones año 1 |

---

## 14. Conclusión: Próximos Pasos Concretos

El trabajo científico de Milestone 1 ya produjo el activo central del producto: 8.450 tramos de calle con predicciones validadas estadísticamente. El MVP no requiere más ciencia — requiere envolver ese activo en una interfaz comercializable.

**La prioridad absoluta es conseguir el primer piloto pagado antes de construir más features.** Un cliente real de Liverpool City Council o NHS dará más información sobre qué mejorar que cualquier análisis adicional.

El vector más directo al mercado es B2G: un piloto con Liverpool City Council o NHS que pague por acceso al dashboard y a la API. Es el cliente con mayor disposición a pagar, el que más legitimidad aporta para escalar a otras ciudades UK, y el que tiene una obligación legal activa de buscar exactamente este tipo de herramienta.

**La ventana de oportunidad es ahora:** la legislación UK de Clean Air Zones está en implementación activa, los fondos UKSPF con componentes ambientales tienen deadline en 2026, y AirTrace resuelve exactamente ese problema con datos ya producidos y validados.

**Orden de acciones:**

1. Desplegar la API (FastAPI + PostGIS) en Railway — estimación: 3–5 días de trabajo
2. Construir el dashboard mínimo con Mapbox GL JS — estimación: 1 semana
3. Identificar el contacto correcto en Liverpool City Council vía LinkedIn
4. Solicitar demo y proponer piloto de £5.000
5. Firmar el primer contrato antes de invertir más tiempo en features
