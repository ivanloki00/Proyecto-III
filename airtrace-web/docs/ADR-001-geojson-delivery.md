# ADR-001 — Estrategia de entrega de GeoJSONs mensuales

**Estado:** Aceptado  
**Fecha:** 2026-04-20  
**Contexto:** Feature 2 del PRD de AirTrace (`PRD_webapp_v1.1.md`)

---

## Contexto

Los 12 GeoJSONs mensuales de contaminación de Liverpool pesan ~6–8 MB cada uno sin comprimir. Un fetch+parse naive contra Supabase Storage tarda 2–3 s por mes en banda estándar. El criterio de aceptación del PRD exige < 1.000 ms en primera carga y < 150 ms en caché.

---

## Decisión

Implementar las siguientes 6 optimizaciones **en conjunto** como requisito para el sprint de Feature 2. Son acumulativas: cada una elimina un cuello de botella diferente.

| # | Optimización | Impacto estimado |
|---|--------------|------------------|
| 1 | **Compresión Brotli/Gzip** en Supabase Storage bucket con `Content-Encoding: br` y `Cache-Control: public, max-age=31536000, immutable`. El GeoJSON comprime ×10–×20 por repetición de claves y coordenadas. | 8 MB → ~500–800 KB. Descarga: de ~1.300 ms a ~150 ms en 50 Mbps. |
| 2 | **Prefetch en background** de los 12 meses tras el primer paint del mapa anual, explotando la multiplexación HTTP/2. Disparado con `requestIdleCallback` para no competir con la interacción inicial. | Tras ~3 s invisibles, todos los meses están en caché del navegador. Las transiciones son locales. |
| 3 | **Caché en memoria tipada** (`Map<MonthKey, FeatureCollection>`) en el cliente. Una vez parseado un mes, el swap es `source.setData(cache.get(month))` — instantáneo. | Elimina el re-parse de JSON, que es el cuello de botella real en dispositivos medios. |
| 4 | **Parse en Web Worker** con `postMessage` + `Transferable` (`ArrayBuffer`). `JSON.parse` de 8 MB bloquea el hilo principal 300–500 ms en un móvil medio. Moverlo al worker mantiene la UI responsive durante la transición. | Jank eliminado. Tiempo percibido = tiempo de red. |
| 5 | **`map.getSource(id).setData(...)` en lugar de `removeLayer`/`addLayer`**. Mapbox GL reutiliza el tile cache interno y aplica un diff de features; recrear el layer fuerza un re-tiling completo (~200–300 ms). | Transición más fluida; reduce trabajo en GPU. |
| 6 | **Cross-fade controlado**: mantener la capa previa visible con `line-opacity-transition` de 400 ms hasta que la nueva emita el evento `sourcedata` con `isSourceLoaded === true`. | Cero frames en blanco — requerimiento explícito del PRD (F2-AC6). |

---

## Alternativa considerada y descartada

**PMTiles / FlatGeobuf** (range-requests para eliminar descarga completa) — descartada para v1.0 por complejidad de setup. Documentada en backlog como mejora para cobertura multi-ciudad.

---

## Consecuencias

- El bucket de Supabase Storage debe configurarse con Brotli habilitado antes del deploy.
- La lógica de caché y el Web Worker son piezas de infraestructura del frontend que el equipo debe construir antes de Feature 2.
- Si se omite cualquiera de las 6 optimizaciones, el criterio F2-AC1 (< 1.000 ms) probablemente no se cumplirá en dispositivos de gama media.

---

## Referencia

PRD: `docs/PRD_webapp_v1.1.md` → Feature 2, criterios de aceptación F2-AC1 y F2-AC2.
