import { useEffect, useMemo, useRef, useState } from "react";
import mapboxgl from "mapbox-gl";
import type { LoadedData } from "@/types/lsoa";
import { loadAll } from "@/lib/data";
import { GRADE_BINS, GRADE_BINS_PM10, WHO_PM25, UK_PM10, gradeOf, gradeOfPM10, binsForPollutant } from "@/lib/scale";
import { windowedMeans, countAbove, windowedTemporalFactor } from "@/lib/exposure";
import type { Pollutant } from "@/types/lsoa";
import { useAppStore } from "@/store/useAppStore";
import { DateRangeSlider } from "@/components/Controls/DateRangeSlider";
import { SidePanel } from "@/components/SidePanel/SidePanel";

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

    map.addControl(new mapboxgl.AttributionControl({ compact: true }), "bottom-left");
    map.addControl(new mapboxgl.NavigationControl({ visualizePitch: false }), "top-right");

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
          "circle-opacity": 0.35,
        },
      });

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
        const p = f.properties as { name: string; device_id: string; status: string; date_from?: string; date_to?: string };
        showPopup(map, popupRef, e.lngLat, sensorPopupHTML(p));
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
      popupRef.current?.remove();
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
    <div className="flex w-full h-screen">
      <div className="flex-1 relative">
        <div ref={containerRef} className="absolute inset-0" />

        <div className="absolute top-3 left-3 z-10 flex flex-col gap-1.5">
          <div className="flex bg-slate-900/85 backdrop-blur rounded-md border border-slate-700 overflow-hidden text-xs">
            <ToggleBtn active={viewMode === "streets"} onClick={() => setViewMode("streets")}>
              Streets <span className="opacity-60">(8 450)</span>
            </ToggleBtn>
            <ToggleBtn active={viewMode === "lsoa"} onClick={() => setViewMode("lsoa")}>
              Neighbourhoods — LSOA <span className="opacity-60">(302)</span>
            </ToggleBtn>
            <ToggleBtn active={viewMode === "sensors"} onClick={() => setViewMode("sensors")}>
              Sensors <span className="opacity-60">(68)</span>
            </ToggleBtn>
          </div>
          {viewMode !== "sensors" && (
            <div className="flex bg-slate-900/85 backdrop-blur rounded-md border border-slate-700 overflow-hidden text-xs self-start">
              <ToggleBtn active={pollutant === "PM2.5"} onClick={() => setPollutant("PM2.5")}>PM2.5</ToggleBtn>
              <ToggleBtn active={pollutant === "PM10"}  onClick={() => setPollutant("PM10")}>PM10</ToggleBtn>
            </div>
          )}
        </div>

        {/* Slider always visible — applies to both views. */}
        <DateRangeSlider months={data.months} />

        {viewMode === "lsoa" && (
          <button
            onClick={toggleOverlay}
            className={`absolute top-3 right-16 z-10 px-3 py-1.5 rounded-md border text-xs transition-colors ${
              showOverlay
                ? "bg-amber-500/20 border-amber-500/50 text-amber-200"
                : "bg-slate-900/85 border-slate-700 text-slate-400 hover:text-slate-200"
            }`}
            title={`Toggle outline on LSOAs above ${pollutant === "PM10" ? "UK LAQM 40 µg/m³" : "UK 2040 10 µg/m³"}`}
          >
            {showOverlay ? "● " : "○ "}
            Above {pollutant === "PM10" ? "UK LAQM" : "UK 2040"}: <span className="font-semibold">{aboveUK} / {totalLsoas}</span>
            <span className="opacity-70"> ({((aboveUK / totalLsoas) * 100).toFixed(0)} %)</span>
          </button>
        )}

        {viewMode === "streets" && (
          <div className="absolute top-3 right-16 z-10 px-3 py-1.5 rounded-md border bg-slate-900/85 border-slate-700 text-xs text-slate-300">
            Seasonal factor <span className="font-semibold text-white">× {factor.toFixed(2)}</span>
            <span className="opacity-60 ml-1">({fromYM} → {toYM})</span>
          </div>
        )}

        <div className="absolute bottom-6 right-3 z-10 bg-slate-900/85 backdrop-blur border border-slate-700 rounded-md p-3 text-xs text-slate-200">
          <div className="font-medium mb-2">{pollutant} — A–F scale</div>
          <ul className="space-y-1">
            {binsForPollutant(pollutant).map((b) => (
              <li key={b.grade} className="flex items-center gap-2">
                <span className="inline-block w-3 h-3 rounded-sm" style={{ backgroundColor: b.color }} />
                <span className="font-mono w-3">{b.grade}</span>
                <span className="text-slate-400">{b.max === Infinity ? `≥ ${b.min}` : `${b.min}–${b.max}`} µg/m³</span>
              </li>
            ))}
          </ul>
          <div className="mt-2 pt-2 border-t border-slate-700 text-slate-500 text-[10px]">
            {viewMode === "streets"
              ? `Streets · annual × seasonal factor`
              : `LSOA mean over window`}
          </div>
        </div>
      </div>

      <SidePanel data={data} />
    </div>
  );
}

function applyVisibility(map: mapboxgl.Map, viewMode: "streets" | "lsoa" | "sensors", showOverlay: boolean) {
  const set = (id: string, vis: "visible" | "none") => {
    if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", vis);
  };
  if (viewMode === "streets") {
    set("streets-line", "visible");
    set("lsoa-fill", "none");
    set("lsoa-outline", "none");
    set("lsoa-overlay", "none");
    set("lsoa-selected", "none");
    set("sensors-circle", "none");
  } else if (viewMode === "lsoa") {
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

function sensorPopupHTML(p: { name: string; device_id: string; status: string; date_from?: string; date_to?: string }) {
  const color = p.status === "active" ? "#10b981" : "#f97316";
  const label = p.status === "active" ? "Active" : "Historical";
  const dateRange = p.date_from ? `<div style="font-size:10px;color:#94a3b8;margin-top:4px">${p.date_from} → ${p.date_to ?? "?"}</div>` : "";
  return `<div style="font-family:system-ui;color:#0f172a;padding:2px 4px"><div style="display:flex;align-items:center;gap:6px;margin-bottom:4px"><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${color}"></span><span style="font-weight:600">${esc(p.name)}</span></div><div style="font-size:11px;color:#64748b">ID: ${esc(p.device_id)}</div><div style="font-size:11px;font-weight:500;color:${color}">${label}</div>${dateRange}</div>`;
}

function esc(s: string) {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!));
}

function ToggleBtn({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return <button onClick={onClick} className={"px-3 py-2 transition-colors " + (active ? "bg-slate-700 text-white" : "text-slate-300 hover:bg-slate-800")}>{children}</button>;
}

function FullScreenMessage({ title, body, tone = "info" }: { title: string; body: string; tone?: "info" | "error" }) {
  const accent = tone === "error" ? "text-red-400" : "text-slate-300";
  return (
    <div className="flex w-full h-screen items-center justify-center">
      <div className="max-w-md text-center">
        <h1 className={`text-2xl font-semibold ${accent}`}>{title}</h1>
        <p className="mt-2 text-slate-400 text-sm">{body}</p>
      </div>
    </div>
  );
}
