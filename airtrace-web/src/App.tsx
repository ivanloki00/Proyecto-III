import { useEffect, useMemo, useRef, useState } from "react";
import mapboxgl from "mapbox-gl";
import type { LoadedData } from "@/types/lsoa";
import { loadAll } from "@/lib/data";
import { GRADE_BINS, GRADE_BINS_PM10, WHO_PM25, WHO_PM10, UK_PM10, gradeOf, gradeOfPM10, binsForPollutant, gradeForPollutant } from "@/lib/scale";
import { windowedMeans, countAbove, windowedTemporalFactor } from "@/lib/exposure";
import type { Pollutant } from "@/types/lsoa";
import { useAppStore } from "@/store/useAppStore";
import { DateRangeSlider } from "@/components/Controls/DateRangeSlider";
import { SidePanel } from "@/components/SidePanel/SidePanel";
import { TimeSeriesChart } from "@/components/SidePanel/TimeSeriesChart";

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN as string | undefined;

type Status =
  | { kind: "loading" }
  | { kind: "ready"; data: LoadedData }
  | { kind: "error"; message: string };

export default function App() {
  const [status, setStatus] = useState<Status>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    loadAll()
      .then((data) => { if (!cancelled) setStatus({ kind: "ready", data }); })
      .catch((err: unknown) => {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : String(err);
          setStatus({ kind: "error", message });
        }
      });
    return () => { cancelled = true; };
  }, []);

  if (!MAPBOX_TOKEN) {
    return <FullScreenMessage title="Missing Mapbox token" body="Add VITE_MAPBOX_TOKEN to airtrace-web/.env then restart npm run dev." tone="error" />;
  }
  if (status.kind === "loading") {
    return <FullScreenMessage title="Loading AirTrace…" body="Fetching streets, LSOA polygons and 5 years of monthly predictions." />;
  }
  if (status.kind === "error") {
    return <FullScreenMessage title="Failed to load data" body={status.message} tone="error" />;
  }
  return <MainView data={status.data} />;
}

const PM25_STEP_LSOA_DYNAMIC = [
  "step", ["coalesce", ["feature-state", "meanPM25"], 0],
  "#475569", 0.001,
  "#00c864", 5,
  "#c8e632", 10,
  "#ffc800", 15,
  "#ff8200", 20,
  "#e63232", 25,
  "#960096",
] as const;

const PM10_STEP_LSOA_DYNAMIC = [
  "step", ["coalesce", ["feature-state", "meanPM10"], 0],
  "#475569", 0.001,
  "#00c864", 15,
  "#c8e632", 30,
  "#ffc800", 45,
  "#ff8200", 60,
  "#e63232", 75,
  "#960096",
] as const;

/** Updates sensor circle paint using property-based expressions — avoids setFeatureState/promoteId unreliability. */
function applySensorState(map: mapboxgl.Map, activeIds: Set<string>) {
  const ids = Array.from(activeIds);
  if (ids.length === 0) {
    map.setPaintProperty("sensors-circle", "circle-color", "#334155");
    map.setPaintProperty("sensors-circle", "circle-opacity", 0.35);
    map.setPaintProperty("sensors-circle", "circle-stroke-color", "#475569");
    map.setPaintProperty("sensors-circle", "circle-radius",
      ["interpolate", ["linear"], ["zoom"], 10, 4, 14, 6] as never);
    return;
  }
  const inList = ["in", ["get", "device_id"], ["literal", ids]];
  map.setPaintProperty("sensors-circle", "circle-color", [
    "case", inList,
    ["case", ["boolean", ["get", "is_final"], false], "#10b981", "#f97316"],
    "#334155",
  ] as never);
  map.setPaintProperty("sensors-circle", "circle-opacity",
    ["case", inList, 1, 0.35] as never);
  map.setPaintProperty("sensors-circle", "circle-stroke-color",
    ["case", inList, "#ffffff", "#475569"] as never);
  map.setPaintProperty("sensors-circle", "circle-radius", [
    "interpolate", ["linear"], ["zoom"],
    10, ["case", inList, 6, 4],
    14, ["case", inList, 10, 6],
  ] as never);
}

/** Computes the [west, south, east, north] bounding box of a Polygon or MultiPolygon feature. */
function lsoaBbox(feature: GeoJSON.Feature<GeoJSON.Polygon | GeoJSON.MultiPolygon>): [number, number, number, number] {
  let minLng = Infinity, minLat = Infinity, maxLng = -Infinity, maxLat = -Infinity;
  const rings = feature.geometry.type === "Polygon"
    ? feature.geometry.coordinates
    : feature.geometry.coordinates.flat(1);
  for (const ring of rings) {
    for (const [lng, lat] of ring) {
      if (lng < minLng) minLng = lng;
      if (lat < minLat) minLat = lat;
      if (lng > maxLng) maxLng = lng;
      if (lat > maxLat) maxLat = lat;
    }
  }
  return [minLng, minLat, maxLng, maxLat];
}

/** Streets paint expression scaled by a per-window seasonal factor. */
function streetPaintExpression(factor: number, pollutant: Pollutant = "PM2.5") {
  if (pollutant === "PM10") {
    return [
      "step",
      ["*", ["get", "pm10"], factor],
      "#00c864", 15,
      "#c8e632", 30,
      "#ffc800", 45,
      "#ff8200", 60,
      "#e63232", 75,
      "#960096",
    ];
  }
  return [
    "step",
    ["*", ["get", "pm25"], factor],
    "#00c864", 5,
    "#c8e632", 10,
    "#ffc800", 15,
    "#ff8200", 20,
    "#e63232", 25,
    "#960096",
  ];
}

function MainView({ data }: { data: LoadedData }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const popupRef = useRef<mapboxgl.Popup | null>(null);
  const rippleMarkersRef = useRef<mapboxgl.Marker[]>([]);
  const activeStreetRef = useRef<{ props: { name: string | null; highway: string; pm25: number; pm10?: number }; lngLat: mapboxgl.LngLat } | null>(null);
  const prevSelectedRef = useRef<string | null>(null);

  const viewMode = useAppStore((s) => s.viewMode);
  const setViewMode = useAppStore((s) => s.setViewMode);
  const pollutant = useAppStore((s) => s.pollutant);
  const setPollutant = useAppStore((s) => s.setPollutant);
  const fromYM = useAppStore((s) => s.fromYM);
  const toYM = useAppStore((s) => s.toYM);
  const selectedLsoa = useAppStore((s) => s.selectedLsoa);
  const setSelected = useAppStore((s) => s.setSelected);
  const showOverlay = useAppStore((s) => s.showOverlay);
  const toggleOverlay = useAppStore((s) => s.toggleOverlay);
  const showSidebar = useAppStore((s) => s.showSidebar);
  const toggleSidebar = useAppStore((s) => s.toggleSidebar);

  const means = useMemo(
    () => windowedMeans(data.series, fromYM, toYM, pollutant),
    [data.series, fromYM, toYM, pollutant],
  );
  const overlayThreshold = pollutant === "PM10" ? UK_PM10 : 10;
  const aboveUK = useMemo(() => countAbove(means, overlayThreshold), [means, overlayThreshold]);
  const factor = useMemo(() => windowedTemporalFactor(data.series, fromYM, toYM), [data.series, fromYM, toYM]);
  const totalLsoas = data.lsoaGeo.features.length;

  // Init map once
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    mapboxgl.accessToken = MAPBOX_TOKEN!;
    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: "mapbox://styles/mapbox/dark-v11",
      center: [-2.97, 53.41],
      zoom: 11,
      attributionControl: false,
    });
    mapRef.current = map;

    // ResizeObserver fires on every animation frame while the sidebar CSS transition runs,
    // so the canvas expands/contracts smoothly rather than jumping at the end.
    const ro = new ResizeObserver(() => { map.resize(); });
    ro.observe(containerRef.current!);

    map.addControl(new mapboxgl.AttributionControl({ compact: true }), "bottom-left");

    map.on("load", () => {
      map.resize();
      setTimeout(() => map.resize(), 100);

      map.addSource("lsoa", {
        type: "geojson",
        data: data.lsoaGeo as GeoJSON.FeatureCollection,
        promoteId: "LSOA21CD",
      });
      map.addLayer({
        id: "lsoa-fill", type: "fill", source: "lsoa",
        paint: { "fill-color": PM25_STEP_LSOA_DYNAMIC as never, "fill-opacity": 0.7 },
      });
      map.addLayer({
        id: "lsoa-outline", type: "line", source: "lsoa",
        paint: { "line-color": "#ffffff", "line-opacity": 0.25, "line-width": 0.6 },
      });
      map.addLayer({
        id: "lsoa-overlay", type: "line", source: "lsoa",
        paint: {
          "line-color": "#ffffff",
          "line-width": 1.6,
          "line-opacity": [
            "case",
            [">", ["coalesce", ["feature-state", "meanPM25"], 0], 10],
            1, 0,
          ],
        },
      });
      map.addLayer({
        id: "lsoa-selected", type: "line", source: "lsoa",
        paint: {
          "line-color": "#ffffff",
          "line-width": 3,
          "line-opacity": ["case", ["boolean", ["feature-state", "selected"], false], 1, 0],
        },
      });

      map.addSource("streets", { type: "geojson", data: data.streetsGeo as GeoJSON.FeatureCollection });
      map.addLayer({
        id: "streets-line", type: "line", source: "streets",
        paint: {
          "line-color": streetPaintExpression(1) as never,
          "line-width": ["interpolate", ["linear"], ["zoom"], 10, 0.6, 13, 1.6, 16, 3],
          "line-opacity": 0.85,
        },
      });

      map.addSource("sensors", {
        type: "geojson",
        data: data.sensorsGeo as GeoJSON.FeatureCollection,
      });
      map.addLayer({
        id: "sensors-circle", type: "circle", source: "sensors",
        paint: {
          "circle-color": "#334155",
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 10, 4, 14, 6] as never,
          "circle-stroke-color": "#475569",
          "circle-stroke-width": 1.5,
          "circle-opacity": 0,
        },
      });
      // Fade-in transition — fires whenever circle-opacity changes from 0
      map.setPaintProperty("sensors-circle", "circle-opacity-transition" as never, { duration: 700, delay: 0 });

      // Initial feature-states for LSOAs
      for (const [id, mean] of means) {
        if (Number.isFinite(mean)) {
          map.setFeatureState({ source: "lsoa", id }, { meanPM25: mean });
        }
      }

      // Initial sensor paint state
      {
        const initToYM = useAppStore.getState().toYM;
        const keys = Object.keys(data.sensorTimeline).sort();
        const effectiveMonth = (initToYM in data.sensorTimeline)
          ? initToYM
          : (keys[keys.length - 1] ?? initToYM);
        applySensorState(map, new Set(data.sensorTimeline[effectiveMonth] ?? []));
      }

      applyVisibility(map, useAppStore.getState().viewMode, useAppStore.getState().showOverlay);

      map.on("click", "streets-line", (e) => {
        const f = e.features?.[0];
        if (!f) return;
        const p = f.properties as { name: string | null; highway: string; pm25: number; pm10?: number };
        const st = useAppStore.getState();
        const currentFactor = windowedTemporalFactor(data.series, st.fromYM, st.toYM);
        activeStreetRef.current = { props: p, lngLat: e.lngLat };
        showPopup(map, popupRef, e.lngLat, streetPopupHTML(p, currentFactor, st.fromYM, st.toYM, st.pollutant));
        popupRef.current?.on("close", () => { activeStreetRef.current = null; });
      });
      map.on("click", "lsoa-fill", (e) => {
        const f = e.features?.[0];
        if (!f) return;
        const p = f.properties as { LSOA21CD: string };
        setSelected(p.LSOA21CD);
        activeStreetRef.current = null;
        popupRef.current?.remove();
      });
      map.on("click", "sensors-circle", (e) => {
        const f = e.features?.[0];
        if (!f) return;
        const p = f.properties as { name: string; device_id: string; status: string; is_final?: boolean; date_from?: string; date_to?: string };
        const [lng, lat] = (f.geometry as GeoJSON.Point).coordinates as [number, number];
        const center: [number, number] = [lng, lat];
        const st = useAppStore.getState();
        const keys = Object.keys(data.sensorTimeline).sort();
        const effectiveMonth = (st.toYM in data.sensorTimeline) ? st.toYM : (keys[keys.length - 1] ?? st.toYM);
        const isInActiveMonth = (data.sensorTimeline[effectiveMonth] ?? []).includes(p.device_id);
        const rippleColor = !isInActiveMonth ? "#475569" : p.is_final ? "#10b981" : "#f97316";
        spawnRipple(map, center, rippleColor);
        showPopup(map, popupRef, center, sensorPopupHTML(p, isInActiveMonth));
      });
      map.on("click", (e) => {
        const hits = map.queryRenderedFeatures(e.point, { layers: ["streets-line", "lsoa-fill", "sensors-circle"] });
        if (hits.length === 0) popupRef.current?.remove();
      });
      for (const id of ["streets-line", "lsoa-fill", "sensors-circle"] as const) {
        map.on("mouseenter", id, () => (map.getCanvas().style.cursor = "pointer"));
        map.on("mouseleave", id, () => (map.getCanvas().style.cursor = ""));
      }
    });

    return () => {
      ro.disconnect();
      popupRef.current?.remove();
      for (const m of rippleMarkersRef.current) m.remove();
      rippleMarkersRef.current = [];
      map.remove();
      mapRef.current = null;
    };
  }, [data, setSelected]);

  // LSOA feature-state on slider or pollutant change
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getSource("lsoa")) return;
    const stateKey = pollutant === "PM10" ? "meanPM10" : "meanPM25";
    for (const [id, mean] of means) {
      map.setFeatureState({ source: "lsoa", id }, { [stateKey]: Number.isFinite(mean) ? mean : null });
    }
    // Switch fill paint expression
    if (map.getLayer("lsoa-fill")) {
      const expr = pollutant === "PM10" ? PM10_STEP_LSOA_DYNAMIC : PM25_STEP_LSOA_DYNAMIC;
      map.setPaintProperty("lsoa-fill", "fill-color", expr as never);
    }
    // Switch overlay threshold
    if (map.getLayer("lsoa-overlay")) {
      const threshold = pollutant === "PM10" ? UK_PM10 : 10;
      const stateKeyOverlay = pollutant === "PM10" ? "meanPM10" : "meanPM25";
      map.setPaintProperty("lsoa-overlay", "line-opacity", [
        "case",
        [">", ["coalesce", ["feature-state", stateKeyOverlay], 0], threshold],
        1, 0,
      ] as never);
    }
  }, [means, pollutant]);

  // Streets paint expression on slider or pollutant change
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getLayer("streets-line")) return;
    map.setPaintProperty("streets-line", "line-color", streetPaintExpression(factor, pollutant) as never);
  }, [factor, pollutant]);

  // Street popup — re-render HTML when temporal window or pollutant changes
  useEffect(() => {
    if (!activeStreetRef.current || !popupRef.current) return;
    popupRef.current.setHTML(streetPopupHTML(activeStreetRef.current.props, factor, fromYM, toYM, pollutant));
  }, [factor, fromYM, toYM, pollutant]);

  // Sensor paint state — updates whenever toYM changes; forecast months fall back to last known month
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getLayer("sensors-circle")) return;
    const keys = Object.keys(data.sensorTimeline).sort();
    const effectiveMonth = (toYM in data.sensorTimeline) ? toYM : (keys[keys.length - 1] ?? toYM);
    applySensorState(map, new Set(data.sensorTimeline[effectiveMonth] ?? []));
  }, [toYM, data]);

  // Ripple markers — CSS-animated rings on active sensors, only in sensors view
  useEffect(() => {
    const map = mapRef.current;
    for (const m of rippleMarkersRef.current) m.remove();
    rippleMarkersRef.current = [];
    if (!map || viewMode !== "sensors") return;

    const keys = Object.keys(data.sensorTimeline).sort();
    const effectiveMonth = (toYM in data.sensorTimeline) ? toYM : (keys[keys.length - 1] ?? toYM);
    const activeIds = new Set(data.sensorTimeline[effectiveMonth] ?? []);

    const addMarkers = () => {
      let i = 0;
      for (const feature of data.sensorsGeo.features) {
        if (!activeIds.has(feature.properties.device_id)) continue;
        const [lng, lat] = (feature.geometry as GeoJSON.Point).coordinates as [number, number];
        const color = feature.properties.is_final ? "#10b981" : "#f97316";

        const wrap = document.createElement("div");
        wrap.style.cssText = "position:relative;width:0;height:0;pointer-events:none;overflow:visible";
        const ring = document.createElement("div");
        ring.className = "sensor-ripple-ring";
        ring.style.borderColor = color;
        ring.style.animationDelay = `${i * 55}ms`;
        wrap.appendChild(ring);

        const marker = new mapboxgl.Marker({ element: wrap, anchor: "center" })
          .setLngLat([lng, lat])
          .addTo(map);
        rippleMarkersRef.current.push(marker);

        ring.addEventListener("animationend", () => {
          marker.remove();
          const idx = rippleMarkersRef.current.indexOf(marker);
          if (idx !== -1) rippleMarkersRef.current.splice(idx, 1);
        }, { once: true });

        i++;
      }
    };

    if (map.isStyleLoaded()) {
      addMarkers();
    } else {
      map.once("load", addMarkers);
    }

    return () => {
      for (const m of rippleMarkersRef.current) m.remove();
      rippleMarkersRef.current = [];
    };
  }, [viewMode, toYM, data]);

  // Selected LSOA — highlight border + fly to
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getSource("lsoa")) return;
    if (prevSelectedRef.current) {
      map.setFeatureState({ source: "lsoa", id: prevSelectedRef.current }, { selected: false });
    }
    prevSelectedRef.current = selectedLsoa;
    if (!selectedLsoa) return;
    map.setFeatureState({ source: "lsoa", id: selectedLsoa }, { selected: true });
    const feature = data.lsoaGeo.features.find((f) => f.properties.LSOA21CD === selectedLsoa);
    if (feature) {
      const [w, s, e, n] = lsoaBbox(feature as GeoJSON.Feature<GeoJSON.Polygon | GeoJSON.MultiPolygon>);
      map.fitBounds([[w, s], [e, n]], { padding: 100, duration: 800, maxZoom: 14 });
    }
  }, [selectedLsoa, data]);

  // viewMode / overlay — also re-applies sensor paint when entering sensors view
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const apply = () => {
      applyVisibility(map, viewMode, showOverlay);
      if (viewMode === "sensors" && map.getLayer("sensors-circle")) {
        const st = useAppStore.getState();
        const keys = Object.keys(data.sensorTimeline).sort();
        const effectiveMonth = (st.toYM in data.sensorTimeline)
          ? st.toYM
          : (keys[keys.length - 1] ?? st.toYM);
        applySensorState(map, new Set(data.sensorTimeline[effectiveMonth] ?? []));
      }
    };
    if (!map.isStyleLoaded()) {
      map.once("load", apply);
    } else {
      apply();
    }
    popupRef.current?.remove();
  }, [viewMode, showOverlay, data]);

  return (
    <div className="relative w-full h-screen">
      <div className="absolute inset-0">
        <div ref={containerRef} className="absolute inset-0" />

        <div className="absolute top-3 left-3 z-10 flex flex-col gap-1.5">
          <div className="flex overflow-hidden" style={{ background: 'rgba(2,6,23,0.80)', backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)', border: '1px solid rgba(255,255,255,0.10)', borderRadius: 12 }}>
            <ToggleBtn active={viewMode === "streets"} onClick={() => setViewMode("streets")}>
              Streets <span style={{ opacity: 0.4 }}>(8 450)</span>
            </ToggleBtn>
            <span className="w-px self-stretch" style={{ background: 'rgba(255,255,255,0.10)' }} />
            <ToggleBtn active={viewMode === "lsoa"} onClick={() => setViewMode("lsoa")}>
              Neighbourhoods <span style={{ opacity: 0.4 }}>(302)</span>
            </ToggleBtn>
            <span className="w-px self-stretch" style={{ background: 'rgba(255,255,255,0.10)' }} />
            <ToggleBtn active={viewMode === "sensors"} onClick={() => setViewMode("sensors")}>
              Sensors <span style={{ opacity: 0.4 }}>(68)</span>
            </ToggleBtn>
          </div>
          {viewMode !== "sensors" && (
            <div className="flex overflow-hidden self-start" style={{ background: 'rgba(2,6,23,0.80)', backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)', border: '1px solid rgba(255,255,255,0.10)', borderRadius: 12 }}>
              <ToggleBtn active={pollutant === "PM2.5"} onClick={() => setPollutant("PM2.5")}>PM2.5</ToggleBtn>
              <span className="w-px self-stretch" style={{ background: 'rgba(255,255,255,0.10)' }} />
              <ToggleBtn active={pollutant === "PM10"}  onClick={() => setPollutant("PM10")}>PM10</ToggleBtn>
            </div>
          )}
        </div>

        {/* Slider always visible — applies to both views. */}
        <DateRangeSlider months={data.months} />

        {viewMode === "lsoa" && (
          <button
            onClick={toggleOverlay}
            title={`Toggle outline on LSOAs above ${pollutant === "PM10" ? "UK LAQM 40 µg/m³" : "UK 2040 10 µg/m³"}`}
            style={{
              position: 'absolute', top: 12, right: 64, zIndex: 10,
              background: showOverlay ? 'rgba(245,158,11,0.20)' : 'transparent',
              color: showOverlay ? '#FCD34D' : '#94A3B8',
              border: showOverlay ? '1px solid rgba(245,158,11,0.40)' : '1px solid rgba(255,255,255,0.10)',
              padding: '6px 12px', borderRadius: 12,
              font: '500 11px Inter, system-ui, sans-serif',
              cursor: 'pointer', transition: 'all 150ms',
            }}
          >
            {showOverlay ? "● " : "○ "}
            Above {pollutant === "PM10" ? "UK LAQM" : "UK 2040"}: <strong style={{ fontWeight: 600 }}>{aboveUK} / {totalLsoas}</strong>
            <span style={{ opacity: 0.6 }}> ({((aboveUK / totalLsoas) * 100).toFixed(0)} %)</span>
          </button>
        )}

        {viewMode === "streets" && (
          <div className="absolute top-3 right-16 z-10 font-mono text-[11px]" style={{ background: 'rgba(2,6,23,0.80)', backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)', border: '1px solid rgba(255,255,255,0.10)', borderRadius: 12, padding: '6px 12px', color: '#CBD5E1' }}>
            Seasonal factor <span style={{ color: '#fff', fontWeight: 600 }}>× {factor.toFixed(2)}</span>
            <span style={{ opacity: 0.5, marginLeft: 8 }}>{fromYM} → {toYM}</span>
          </div>
        )}

        {/* Legend — only shown when sidebar is collapsed */}
        {!showSidebar && <div className="absolute bottom-6 right-3 z-10 text-xs" style={{ background: 'rgba(2,6,23,0.80)', backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)', border: '1px solid rgba(255,255,255,0.10)', borderRadius: 12, padding: '14px 16px', boxShadow: '0 18px 40px rgba(0,0,0,0.50)', width: 348 }}>
          <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest mb-3">{pollutant} — A–F scale</div>

          {/* Spectrum strip */}
          <div style={{ height: 6, borderRadius: 999, background: 'linear-gradient(90deg, #00C864 0%, #C8E632 20%, #FFC800 40%, #FF8200 60%, #E63232 80%, #960096 100%)', boxShadow: 'inset 0 0 0 1px rgba(255,255,255,0.06)' }} />
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6,1fr)', marginTop: 6, fontFamily: 'monospace', fontSize: 10, color: '#475569' }}>
            {binsForPollutant(pollutant).map((b, i, arr) => (
              <span key={b.grade} style={{ textAlign: i === 0 ? 'left' : i === arr.length - 1 ? 'right' : 'center' }}>{b.grade}</span>
            ))}
          </div>

          {/* Specimen tiles — wider with more room per tile */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6,1fr)', gap: 6, marginTop: 10 }}>
            {binsForPollutant(pollutant).map((b) => (
              <div key={b.grade} style={{ position: 'relative', display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '10px 4px 8px', background: 'rgba(10,18,11,0.50)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: 8, overflow: 'hidden' }}>
                <span style={{ position: 'absolute', top: 5, left: 5, width: 3, height: 3, background: b.color, opacity: 0.9 }} />
                <span style={{ fontFamily: 'monospace', fontSize: 24, fontWeight: 500, lineHeight: 1, color: '#F2F2F2', letterSpacing: '-0.02em' }}>{b.grade}</span>
                <div style={{ width: 22, height: 2, borderRadius: 1, margin: '7px 0 6px', background: b.color }} />
                <span style={{ fontFamily: 'monospace', fontSize: 9, textAlign: 'center', color: '#64748b', lineHeight: 1.2 }}>
                  {b.max === Infinity ? `${b.min}+` : `${b.min}–${b.max}`}
                  <span style={{ display: 'block', fontSize: 8, marginTop: 1 }}>µg/m³</span>
                </span>
              </div>
            ))}
          </div>

          <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px dashed rgba(255,255,255,0.06)', fontSize: 10, color: '#475569' }}>
            {viewMode === "streets" ? "Streets · annual × seasonal factor" : "LSOA mean over window"}
          </div>
        </div>}

        {/* Floating chart panel — visible when sidebar is hidden and an LSOA is selected */}
        {!showSidebar && selectedLsoa && (
          <FloatingChartPanel data={data} />
        )}

      </div>

      {/* Sidebar — absolute overlay so the map canvas never resizes (avoids black flash) */}
      <div style={{
        position: 'absolute', top: 0, right: 0, bottom: 0, width: 420, zIndex: 30,
        transform: showSidebar ? 'translateX(0)' : 'translateX(100%)',
        transition: 'transform 250ms cubic-bezier(0.4,0,0.2,1)',
      }}>
        {/* Toggle tab — sticks out to the left of the sidebar */}
        <button
          onClick={toggleSidebar}
          title={showSidebar ? "Hide panel" : "Show panel"}
          style={{
            position: 'absolute', left: -20, top: '50%', transform: 'translateY(-50%)',
            zIndex: 31, width: 20, height: 56,
            background: 'rgba(2,6,23,0.85)', backdropFilter: 'blur(8px)', WebkitBackdropFilter: 'blur(8px)',
            border: '1px solid rgba(255,255,255,0.10)', borderRight: 'none',
            borderRadius: '8px 0 0 8px',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'pointer', color: '#94A3B8', transition: 'color 150ms',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.color = '#F1F5F9'; }}
          onMouseLeave={(e) => { e.currentTarget.style.color = '#94A3B8'; }}
        >
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            {showSidebar
              ? <polyline points="3,2 7,5 3,8" />
              : <polyline points="7,2 3,5 7,8" />}
          </svg>
        </button>
        <SidePanel data={data} />
      </div>
    </div>
  );
}

/** Floating chart panel — shows when sidebar is collapsed and an LSOA is selected. */
function FloatingChartPanel({ data }: { data: LoadedData }) {
  const selectedLsoa = useAppStore((s) => s.selectedLsoa);
  const setSelected   = useAppStore((s) => s.setSelected);
  const pollutant     = useAppStore((s) => s.pollutant);
  const fromYM        = useAppStore((s) => s.fromYM);
  const toYM          = useAppStore((s) => s.toYM);

  const rows    = selectedLsoa ? data.series.get(selectedLsoa) ?? null : null;
  const feature = selectedLsoa ? data.lsoaGeo.features.find((f) => f.properties.LSOA21CD === selectedLsoa) ?? null : null;
  const ward    = selectedLsoa ? (data.wardLookup[selectedLsoa] ?? null) : null;

  const windowMean = useMemo(() => {
    if (!rows) return NaN;
    const field = pollutant === "PM10" ? "PM10_pred" : "PM2.5_pred";
    let s = 0, n = 0;
    for (const r of rows) {
      if (r.year_month >= fromYM && r.year_month <= toYM) {
        const v = r[field]; if (v !== undefined) { s += v; n++; }
      }
    }
    return n > 0 ? s / n : NaN;
  }, [rows, fromYM, toYM, pollutant]);

  if (!rows || !feature) return null;

  const grade = gradeForPollutant(windowMean, pollutant);
  const color = binsForPollutant(pollutant).find((b) => b.grade === grade)!.color;
  const whoLimit = pollutant === "PM10" ? WHO_PM10 : WHO_PM25;

  return (
    <div
      style={{
        position: 'absolute', top: 108, right: 12, zIndex: 15, width: 420,
        background: 'rgba(2,6,23,0.88)', backdropFilter: 'blur(14px)', WebkitBackdropFilter: 'blur(14px)',
        border: '1px solid rgba(255,255,255,0.10)', borderRadius: 14,
        padding: '16px 18px', boxShadow: '0 20px 48px rgba(0,0,0,0.60)',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          {ward && <div style={{ fontSize: 14, fontWeight: 600, color: '#F1F5F9', lineHeight: 1.2, marginBottom: 2 }}>{ward}</div>}
          <div style={{ fontFamily: 'monospace', fontSize: 11, color: '#64748b' }}>{feature.properties.LSOA21NM}</div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginLeft: 12 }}>
          {/* Datum grade */}
          {Number.isFinite(windowMean) && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <span style={{ fontFamily: 'monospace', fontSize: 28, fontWeight: 500, color: '#F2F2F2', lineHeight: 1, letterSpacing: '-0.02em' }}>{grade}</span>
              <div style={{ width: 20, height: 2, borderRadius: 1, marginTop: 6, background: color }} />
              <span style={{ fontFamily: 'monospace', fontSize: 10, color: '#64748b', marginTop: 4 }}>{windowMean.toFixed(1)} µg/m³</span>
              <span style={{ fontFamily: 'monospace', fontSize: 9, color: '#475569' }}>×{(windowMean / whoLimit).toFixed(1)} WHO</span>
            </div>
          )}
          <button
            onClick={() => setSelected(null)}
            style={{ width: 24, height: 24, borderRadius: 8, background: 'rgba(255,255,255,0.06)', border: 0, color: '#94A3B8', fontSize: 14, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}
          >×</button>
        </div>
      </div>

      {/* Chart — fixed height for good fitting */}
      <div style={{ height: 220 }}>
        <TimeSeriesChart rows={rows} fromYM={fromYM} toYM={toYM} pollutant={pollutant} />
      </div>

      {/* Legend */}
      <div style={{ display: 'flex', gap: 12, marginTop: 8, fontSize: 10, color: '#475569' }}>
        <span><span style={{ display: 'inline-block', width: 8, height: 8, background: '#60a5fa', borderRadius: 2, marginRight: 4, verticalAlign: 'middle' }} />Monthly {pollutant}</span>
        <span><span style={{ display: 'inline-block', width: 12, height: 8, background: 'rgba(96,165,250,0.30)', borderRadius: 2, marginRight: 4, verticalAlign: 'middle' }} />CI 90 %</span>
        <span><span style={{ display: 'inline-block', width: 16, borderTop: '2px dashed #f43f5e', marginRight: 4, verticalAlign: 'middle' }} />Forecast</span>
      </div>
    </div>
  );
}

function applyVisibility(map: mapboxgl.Map, viewMode: "streets" | "lsoa" | "sensors", showOverlay: boolean) {
  const set = (id: string, vis: "visible" | "none") => {
    if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", vis);
  };
  if (viewMode === "streets") {
    resetSensorOpacity(map);
    set("streets-line", "visible");
    set("lsoa-fill", "none");
    set("lsoa-outline", "none");
    set("lsoa-overlay", "none");
    set("lsoa-selected", "none");
    set("sensors-circle", "none");
  } else if (viewMode === "lsoa") {
    resetSensorOpacity(map);
    set("streets-line", "none");
    set("lsoa-fill", "visible");
    set("lsoa-outline", "visible");
    set("lsoa-overlay", showOverlay ? "visible" : "none");
    set("lsoa-selected", "visible");
    set("sensors-circle", "none");
  } else {
    set("streets-line", "none");
    set("lsoa-fill", "none");
    set("lsoa-outline", "none");
    set("lsoa-overlay", "none");
    set("lsoa-selected", "none");
    set("sensors-circle", "visible");
  }
}

/** Instantly resets sensor opacity to 0 so the next entry always fades in. */
function resetSensorOpacity(map: mapboxgl.Map) {
  if (!map.getLayer("sensors-circle")) return;
  map.setPaintProperty("sensors-circle", "circle-opacity-transition" as never, { duration: 0 });
  map.setPaintProperty("sensors-circle", "circle-opacity", 0);
  map.setPaintProperty("sensors-circle", "circle-opacity-transition" as never, { duration: 700, delay: 0 });
}

function spawnRipple(map: mapboxgl.Map, lngLat: [number, number], color: string) {
  const wrap = document.createElement("div");
  wrap.style.cssText = "position:relative;width:0;height:0;pointer-events:none;overflow:visible";
  const ring = document.createElement("div");
  ring.className = "sensor-ripple-ring";
  ring.style.borderColor = color;
  wrap.appendChild(ring);
  const marker = new mapboxgl.Marker({ element: wrap, anchor: "center" })
    .setLngLat(lngLat)
    .addTo(map);
  ring.addEventListener("animationend", () => marker.remove(), { once: true });
}

function showPopup(map: mapboxgl.Map, ref: React.RefObject<mapboxgl.Popup | null>, lngLat: mapboxgl.LngLatLike, html: string) {
  ref.current?.remove();
  ref.current = new mapboxgl.Popup({ closeButton: true, maxWidth: "280px" }).setLngLat(lngLat).setHTML(html).addTo(map);
}

function streetPopupHTML(
  p: { name: string | null; highway: string; pm25: number; pm10?: number },
  factor: number,
  fromYM: string,
  toYM: string,
  pollutant: Pollutant = "PM2.5",
) {
  const base   = pollutant === "PM10" ? (p.pm10 ?? p.pm25 * 2) : p.pm25;
  const scaled = base * factor;
  const grade  = pollutant === "PM10" ? gradeOfPM10(scaled) : gradeOf(scaled);
  const bins   = pollutant === "PM10" ? GRADE_BINS_PM10 : GRADE_BINS;
  const color  = bins.find((b) => b.grade === grade)!.color;
  const whoLimit = pollutant === "PM10" ? UK_PM10 : WHO_PM25;
  const ratio  = (scaled / whoLimit).toFixed(1);
  const name   = p.name ?? "Unnamed road";
  const factorLabel = factor === 1 ? "" : ` · × ${factor.toFixed(2)} seasonal`;
  return `<div style="font-family:system-ui;color:#0f172a;padding:2px 4px"><div style="font-weight:600">${esc(name)}</div><div style="font-size:11px;color:#64748b;margin-bottom:8px">${esc(p.highway)}${factorLabel}</div><div style="display:flex;align-items:center;gap:8px"><span style="display:inline-block;width:30px;height:30px;border-radius:6px;background:${color};color:#fff;font-weight:700;text-align:center;line-height:30px">${grade}</span><span style="font-size:18px;font-weight:600">${scaled.toFixed(1)} µg/m³</span></div><div style="font-size:11px;color:#475569;margin-top:6px">× ${ratio} above WHO · annual base ${base.toFixed(1)} µg/m³ (${pollutant})</div><div style="font-size:10px;color:#94a3b8;margin-top:2px">Window ${fromYM} → ${toYM}</div></div>`;
}

function sensorPopupHTML(
  p: { name: string; device_id: string; is_final?: boolean; date_from?: string; date_to?: string },
  isInActiveMonth: boolean,
) {
  // Grey  → not in current month's active set → Inactive
  // Green → in active set AND is_final        → Active
  // Orange → in active set AND !is_final      → Active · excluded
  let color: string;
  let label: string;
  if (!isInActiveMonth) {
    color = "#475569"; label = "Inactive";
  } else if (p.is_final) {
    color = "#10b981"; label = "Active";
  } else {
    color = "#f97316"; label = "Active · excluded";
  }
  const dateRange = p.date_from ? `<div style="font-size:10px;color:#94a3b8;margin-top:4px">${p.date_from} → ${p.date_to ?? "?"}</div>` : "";
  return `<div style="font-family:system-ui;color:#0f172a;padding:2px 4px"><div style="display:flex;align-items:center;gap:6px;margin-bottom:4px"><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${color}"></span><span style="font-weight:600">${esc(p.name)}</span></div><div style="font-size:11px;color:#64748b">ID: ${esc(p.device_id)}</div><div style="font-size:11px;font-weight:500;color:${color}">${label}</div>${dateRange}</div>`;
}

function esc(s: string) {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!));
}

function ToggleBtn({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '8px 14px',
        background: active ? 'rgba(255,255,255,0.10)' : 'transparent',
        color: active ? '#fff' : '#94A3B8',
        border: 0,
        font: '500 12px Inter, system-ui, sans-serif',
        cursor: 'pointer',
        transition: 'background 150ms, color 150ms',
        whiteSpace: 'nowrap' as const,
      }}
      onMouseEnter={(e) => { if (!active) e.currentTarget.style.color = '#CBD5E1'; }}
      onMouseLeave={(e) => { if (!active) e.currentTarget.style.color = '#94A3B8'; }}
    >
      {children}
    </button>
  );
}

function FullScreenMessage({ title, body, tone = "info" }: { title: string; body: string; tone?: "info" | "error" }) {
  const isError = tone === "error";
  return (
    <div className="flex w-full h-screen items-center justify-center bg-slate-950">
      <div className="max-w-md text-center px-6">
        <div className={`w-12 h-12 rounded-2xl mx-auto mb-5 flex items-center justify-center ${isError ? "bg-red-500/15" : "bg-emerald-500/15"}`}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={isError ? "#f87171" : "#34d399"} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            {isError
              ? <><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></>
              : <><path d="M9.59 4.59A2 2 0 1 1 11 8H2m10.59 11.41A2 2 0 1 0 14 16H2m15.73-8.27A2.5 2.5 0 1 1 19.5 12H2"/></>
            }
          </svg>
        </div>
        <h1 className={`text-xl font-semibold ${isError ? "text-red-400" : "text-slate-100"}`}>{title}</h1>
        <p className="mt-2 text-slate-500 text-sm leading-relaxed">{body}</p>
      </div>
    </div>
  );
}
