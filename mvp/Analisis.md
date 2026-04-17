Informe MVP — Liverpool Air Quality Intelligence Platform

Fecha: 15 de Abril de 2026
Basado en: Milestone 1, pipeline LUR completado (Milestone 2 en curso)
Propósito: Definir enfoque, alcance y stack tecnológico de un producto mínimo viable comercializable

---

1. El Activo Real: Lo Que Ya Tienes

Antes de hablar de producto, hay que entender qué material existe hoy:

┌────────────────────────────────────┬──────────────────────┬──────────────────────────────────────────────────────────────────────────┐  
 │ Activo │ Estado │ Valor comercial │  
 ├────────────────────────────────────┼──────────────────────┼──────────────────────────────────────────────────────────────────────────┤  
 │ liverpool_pollution_map.geojson │ Producido │ 8.450 tramos de calle con PM2.5 y PM10 predichos — cobertura 100% de la │  
 │ │ │ red viaria │  
 ├────────────────────────────────────┼──────────────────────┼──────────────────────────────────────────────────────────────────────────┤  
 │ lur_model_PM25.pkl / PM10.pkl │ Serializado │ Modelos reentrenables, integrables en cualquier API Python │  
 ├────────────────────────────────────┼──────────────────────┼──────────────────────────────────────────────────────────────────────────┤  
 │ Pipeline reproducible │ 9 scripts │ Permite actualizar predicciones con nuevos datos de sensores │  
 │ │ encadenados │ │  
 ├────────────────────────────────────┼──────────────────────┼──────────────────────────────────────────────────────────────────────────┤  
 │ 24 sensores con historial │ CSV │ Activo de monitorización real, no datos sintéticos │  
 │ 2021–2025 │ │ │  
 ├────────────────────────────────────┼──────────────────────┼──────────────────────────────────────────────────────────────────────────┤  
 │ Features urbanas enriquecidas │ OSM + AADF + │ Base para ampliar a cualquier ciudad con red viaria en OSM │  
 │ │ Elevación │ │  
 └────────────────────────────────────┴──────────────────────┴──────────────────────────────────────────────────────────────────────────┘

El GeoJSON es el producto. Los modelos son el motor. El pipeline es la ventaja defensiva.

---

2. Definición del MVP

Propuesta de valor central

▎ "Cualquier dirección de Liverpool. Su nivel de contaminación PM2.5/PM10. En menos de 3 segundos."

No es un mapa académico. Es la capa de inteligencia ambiental que faltaba en las herramientas de decisión urbana.

Nombre propuesto: AirTrace

---

3. Casos de Uso por Segmento — Visión Empresarial

Segmento A — B2G (Business to Government) ⭐ Prioritario MVP

Cliente: Liverpool City Council, Transport for Liverpool, NHS Cheshire & Merseyside

Problema que resuelven con AirTrace:

- Cumplimiento del UK Clean Air Strategy (objetivo PM2.5 < 10 µg/m³ para 2040)
- Planificación de zonas de baja emisión (Clean Air Zones) basada en datos, no en intuición
- Localización óptima de nuevas zonas verdes para maximizar reducción de exposición
- Justificación de inversión en infraestructura ciclista con datos de calidad del aire

Modelo de monetización: Licencia SaaS anual + consultoría de datos (£25k–£80k/año)

---

Segmento B — B2B Real Estate & Construcción

Cliente: Agencias inmobiliarias, promotores, tasadoras (Rightmove, Savills, CBRE)

Problema: El comprador moderno exige transparencia ambiental. El EPC (Energy Performance Certificate) es obligatorio. Un "APC" (Air
Performance Certificate) no existe todavía — ventana de mercado abierta.

Propuesta: API que devuelve un score de calidad del aire (A–F) para cualquier coordenada de Liverpool, embebible en cualquier ficha de  
 propiedad.

Modelo de monetización: API pay-per-call (£0.002–£0.01 por consulta). 1M de consultas/mes = £2.000–£10.000/mes.

---

Segmento C — B2B Logística y Flotas

Cliente: DHL, Amazon Logistics, empresas de reparto urbano con flotas eléctricas

Problema: Las empresas de logística buscan cumplir objetivos ESG y reducir exposición de conductores a contaminantes. Los repositorios de  
 rutas actuales (Google Maps, HERE) no incluyen la dimensión ambiental.

Propuesta: Integración del GeoJSON en algoritmos de optimización de rutas que penalicen tramos con PM2.5 > umbral regulatorio. Ruta más  
 limpia, no solo más rápida.

Modelo de monetización: Plugin para plataformas de gestión de flotas (£500–£2.000/mes por empresa)

---

Segmento D — B2C Salud y Bienestar (Monetización diferida)

Cliente final: Ciudadanos de Liverpool, especialmente grupos vulnerables (asmáticos, padres con niños pequeños, ciclistas urbanos)

Propuesta: App móvil / widget que muestra el nivel de contaminación de la ruta que el usuario está a punto de recorrer. Integrable con Apple
Health, Garmin, Strava.

Modelo de monetización: Freemium → suscripción premium £2.99/mes. No prioritario en MVP — requiere escala de usuarios. Pero construye la  
 base de datos de comportamiento más valiosa a largo plazo.

---

4. Arquitectura Técnica del MVP

[Fuentes de datos] [Backend / Motor] [Interfaces]

24 sensores IoT ────────→ pipeline Python Dashboard web (Streamlit/Dash)
OSM Liverpool ────────→ lur_model.pkl ─────────→ REST API (FastAPI)
AADF DfT ────────→ geojson 8.450 ─────────→ GeoJSON endpoint
MIDAS Meteo ────────→ tramos Embed widget (iframe)

[Actualización] [Distribución B2B]
Cron semanal/mensual API key management
cuando llegan nuevos Rate limiting
datos de sensores SLA 99.5%

Stack mínimo viable

┌─────────────────┬──────────────────────────┬─────────────────────────────────────────────────┐
│ Capa │ Tecnología │ Justificación │
├─────────────────┼──────────────────────────┼─────────────────────────────────────────────────┤
│ Backend API │ FastAPI + Uvicorn │ Python nativo, comparte entorno con los modelos │
├─────────────────┼──────────────────────────┼─────────────────────────────────────────────────┤
│ Modelos │ Existentes .pkl │ 0 trabajo de ML adicional para MVP │
├─────────────────┼──────────────────────────┼─────────────────────────────────────────────────┤
│ Geodatos │ GeoPandas + GeoJSON │ Pipeline ya produce el output │
├─────────────────┼──────────────────────────┼─────────────────────────────────────────────────┤
│ Visualización │ Kepler.gl / Mapbox GL JS │ El GeoJSON se renderiza directamente │
├─────────────────┼──────────────────────────┼─────────────────────────────────────────────────┤
│ Base de datos │ PostGIS (PostgreSQL) │ Consultas espaciales por coordenada/bbox │
├─────────────────┼──────────────────────────┼─────────────────────────────────────────────────┤
│ Hosting │ Railway / Render │ Despliegue desde GitHub, sin DevOps │
├─────────────────┼──────────────────────────┼─────────────────────────────────────────────────┤
│ Auth / API keys │ Supabase │ Gratuito hasta ~50k req/mes │
└─────────────────┴──────────────────────────┴─────────────────────────────────────────────────┘

Estimación de tiempo de construcción del MVP funcional: 3–4 semanas con el pipeline actual como base.

---

5. Ventaja Competitiva Defensible

La pregunta clave para cualquier inversor o cliente institucional: ¿por qué no lo hace Google?

1. Hiperlocal y validado estadísticamente. Los servicios generales de calidad del aire (IQAir, Breezometer) usan interpolación gruesa.  
   AirTrace tiene validación LOOCV a nivel de tramo de calle.
2. Pipeline reproducible. No es un snapshot. Se puede reentrenar con nuevos sensores o nuevas ciudades en horas.
3. Infraestructura de datos abiertos. OSM + DfT + ONS = coste de datos cercano a cero. La IP está en el pipeline, no en los datos.
4. Extensible a cualquier ciudad UK con datos OSM + AADF. Manchester, Birmingham, Leeds son el siguiente paso natural.

---

6. Hoja de Ruta Post-MVP

┌───────────────┬──────────────────────────────────────────┬───────────────────────────┐
│ Fase │ Entregable │ Habilitador técnico │
├───────────────┼──────────────────────────────────────────┼───────────────────────────┤
│ MVP (mes 1–4) │ API + dashboard Liverpool │ Pipeline actual + FastAPI │
├───────────────┼──────────────────────────────────────────┼───────────────────────────┤
│ v1.1 │ Score A–F por dirección postal (LSOA) │ Issue #21 (LUR barrios) │
├───────────────┼──────────────────────────────────────────┼───────────────────────────┤
│ v1.2 │ Validación vs estaciones DEFRA AURN │ Issue #26 │
├───────────────┼──────────────────────────────────────────┼───────────────────────────┤
│ v1.3 │ Health Impact Assessment integrado │ Issue #24 │
├───────────────┼──────────────────────────────────────────┼───────────────────────────┤
│ v2.0 │ Segunda ciudad (Manchester / Birmingham) │ Pipeline reproducible │
├───────────────┼──────────────────────────────────────────┼───────────────────────────┤
│ v2.1 │ Datos en tiempo real (ingesta streaming) │ Apache Kafka o Pub/Sub │
└───────────────┴──────────────────────────────────────────┴───────────────────────────┘

---

7. Claude Code — Plugins, Skills y Conectores Recomendados

Para construir y operar AirTrace eficientemente desde Claude Code:

Skills a desarrollar (custom)

┌─────────────────────────┬───────────────────────────────────────────────────────────────────────────────────────────┐
│ Skill │ Qué haría │
├─────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────┤
│ airtraceapi:deploy │ Despliega la FastAPI con el GeoJSON al servidor de staging, verifica el endpoint /predict │
├─────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────┤
│ airtraceapi:refresh-map │ Ejecuta el pipeline completo (scripts 1–9) y sube el nuevo GeoJSON a la BD PostGIS │
├─────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────┤
│ airtraceapi:validate │ Corre LOOCV sobre los datos más recientes y compara R² vs baseline almacenado │
├─────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────┤
│ lur:pruebad │ Ejecuta el experimento PruebaD (efectos fijos año) y genera el informe comparativo │
└─────────────────────────┴───────────────────────────────────────────────────────────────────────────────────────────┘

Conectores MCP útiles

┌──────────────────────────────────┬──────────────────────────────────────────────────────────────────────────┐
│ Conector │ Propósito en AirTrace │
├──────────────────────────────────┼──────────────────────────────────────────────────────────────────────────┤
│ Google Maps / Mapbox MCP │ Validar coordenadas de entrada, geocodificar direcciones postales UK │
├──────────────────────────────────┼──────────────────────────────────────────────────────────────────────────┤
│ GitHub MCP │ Automatizar PRs cuando el pipeline produce un nuevo GeoJSON validado │
├──────────────────────────────────┼──────────────────────────────────────────────────────────────────────────┤
│ PostgreSQL/PostGIS MCP │ Consultar y actualizar la tabla de tramos directamente desde Claude Code │
├──────────────────────────────────┼──────────────────────────────────────────────────────────────────────────┤
│ Slack/Teams MCP │ Notificar al equipo cuando el reentrenamiento detecta degradación de R² │
├──────────────────────────────────┼──────────────────────────────────────────────────────────────────────────┤
│ Google Drive MCP (ya disponible) │ Compartir reportes PDF con stakeholders institucionales (City Council) │
├──────────────────────────────────┼──────────────────────────────────────────────────────────────────────────┤
│ Gmail MCP (ya disponible) │ Envío automatizado de alertas de calidad del aire a suscriptores B2G │
└──────────────────────────────────┴──────────────────────────────────────────────────────────────────────────┘

Hooks de automatización (settings.json)

// Tras ejecutar cualquier script del pipeline, verificar que los outputs existen
// hook: post_tool_use → Bash → python src/utils/verify_outputs.py

// Antes de cualquier commit en rama LUR, correr el LOOCV rápido
// hook: pre_commit → python src/models/quick_loocv_check.py

Agentes especializados (ya existentes, reutilizables)

┌───────────────────────────┬──────────────────────────────────────────────────────┐
│ Agente │ Rol en AirTrace │
├───────────────────────────┼──────────────────────────────────────────────────────┤
│ lur-01-data-extraction │ Reingesta de sensores + OSM cuando hay nuevos datos │
├───────────────────────────┼──────────────────────────────────────────────────────┤
│ lur-03-model-deliverables │ Reentrenamiento + validación automática mensual │
├───────────────────────────┼──────────────────────────────────────────────────────┤
│ model-deliverables │ Generación de informes para clientes institucionales │
└───────────────────────────┴──────────────────────────────────────────────────────┘
└───────────────────────────┴──────────────────────────────────────────────────────┘

---

8. Métricas de Éxito del MVP

┌────────────────────────────┬────────────────────────────────────┬──────────────────────────┐
│ KPI │ Target a 6 meses │ Cómo medirlo │
├────────────────────────────┼────────────────────────────────────┼──────────────────────────┤
│ Latencia API /predict │ < 200 ms │ Monitorización endpoint │
├────────────────────────────┼────────────────────────────────────┼──────────────────────────┤
│ Cobertura geográfica │ 100% red viaria Liverpool │ Verificar NaN en GeoJSON │
├────────────────────────────┼────────────────────────────────────┼──────────────────────────┤
│ Precisión del modelo │ R² PM2.5 ≥ 0.58 en reentrenamiento │ LOOCV automatizado │
├────────────────────────────┼────────────────────────────────────┼──────────────────────────┤
│ Primer cliente B2G │ 1 piloto pagado │ CRM / contrato │
├────────────────────────────┼────────────────────────────────────┼──────────────────────────┤
│ Número de API keys activas │ ≥ 5 empresas │ Supabase dashboard │
└────────────────────────────┴────────────────────────────────────┴──────────────────────────┘

---

Conclusión

El trabajo científico de Milestone 1 ya produjo el activo central del producto: 8.450 tramos de calle con predicciones validadas  
 estadísticamente. El MVP no requiere más ciencia — requiere envolver ese activo en una interfaz comercializable.

El vector más directo al mercado es B2G: un piloto con Liverpool City Council o NHS que pague por acceso al dashboard y a la API. Es el
cliente con mayor disposición a pagar, menor fricción regulatoria para datos urbanos, y que además da credibilidad para escalar a otras
ciudades UK.

La ventana de oportunidad es ahora: la legislación UK de Clean Air Zones está en implementación activa y los gobiernos locales buscan
herramientas de datos. AirTrace resuelve exactamente ese problema, con datos ya producidos.
