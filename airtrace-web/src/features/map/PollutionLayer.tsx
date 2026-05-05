import { useEffect } from 'react'
import type { Map as MapboxMap } from 'mapbox-gl'
import type { FeatureCollection } from 'geojson'
import useAppStore from '../../store/useAppStore'
import { SCORE_COLORS } from '../../utils/colorScale'

const BASE = import.meta.env.VITE_SUPABASE_URL as string | undefined
const SUPABASE_GEOJSON_URL = BASE
  ? `${BASE}/storage/v1/object/public/geojson/liverpool_pollution_map.geojson`
  : null
const LOCAL_GEOJSON_URL = '/data/liverpool_pollution_map.geojson'

function hasScoreField(fc: FeatureCollection): boolean {
  const first = fc.features[0]
  return first != null && first.properties != null && 'score' in first.properties
}

async function fetchGeoJSON(): Promise<FeatureCollection> {
  if (SUPABASE_GEOJSON_URL) {
    try {
      const res = await fetch(SUPABASE_GEOJSON_URL)
      if (res.ok) {
        const fc = await res.json() as FeatureCollection
        if (hasScoreField(fc)) return fc
        console.warn('[AirTrace] GeoJSON de Supabase no tiene campo "score" — usando GeoJSON local')
      } else {
        console.warn('[AirTrace] Supabase respondió', res.status, '— usando GeoJSON local')
      }
    } catch {
      console.warn('[AirTrace] Supabase no accesible — usando GeoJSON local')
    }
  }
  const res = await fetch(LOCAL_GEOJSON_URL)
  if (!res.ok) throw new Error(`HTTP ${res.status} al cargar GeoJSON`)
  return res.json() as Promise<FeatureCollection>
}

interface Props {
  map: MapboxMap | null
}

export default function PollutionLayer({ map }: Props) {
  const setIsLoading = useAppStore((s) => s.setIsLoading)
  const setCache = useAppStore((s) => s.setCache)
  const setError = useAppStore((s) => s.setError)

  useEffect(() => {
    if (!map) return

    let cancelled = false

    const onLoad = async () => {
      if (cancelled) return
      setIsLoading(true)
      try {
        const fc = await fetchGeoJSON()
        if (cancelled) return

        map.addSource('pollution-source', { type: 'geojson', data: fc })

        // DEBUG: add multiple layers with different colors to test match
        const testColors = [
          { color: SCORE_COLORS.A, score: 'A' },
          { color: SCORE_COLORS.B, score: 'B' },
          { color: SCORE_COLORS.C, score: 'C' },
          { color: SCORE_COLORS.D, score: 'D' },
          { color: SCORE_COLORS.E, score: 'E' },
          { color: SCORE_COLORS.F, score: 'F' },
        ]

        testColors.forEach(({ color, score }) => {
          map.addLayer({
            id: `streets-line-${score}`,
            type: 'line',
            source: 'pollution-source',
            filter: ['==', ['get', 'score'], score],
            paint: {
              'line-color': color,
              'line-width': ['interpolate', ['linear'], ['zoom'], 13, 1.5, 15, 3.5],
              'line-opacity': 1,
            },
          })
        })

        // Fallback layer for any score that doesn't match
        map.addLayer({
          id: 'streets-line-fallback',
          type: 'line',
          source: 'pollution-source',
          filter: ['!', ['in', ['get', 'score'], ['literal', ['A', 'B', 'C', 'D', 'E', 'F']]]],
          paint: {
            'line-color': '#888888',
            'line-width': ['interpolate', ['linear'], ['zoom'], 13, 1.5, 15, 3.5],
            'line-opacity': 1,
          },
        })

        setCache('annual', fc)
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Error al cargar el mapa')
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }

    if (map.loaded()) {
      void onLoad()
    } else {
      map.on('load', onLoad)
    }

    return () => {
      cancelled = true
      map.off('load', onLoad)
      try {
        // Remove all our layers
        const layers = ['streets-line-A', 'streets-line-B', 'streets-line-C', 'streets-line-D', 'streets-line-E', 'streets-line-F', 'streets-line-fallback']
        layers.forEach(id => {
          if (map.getLayer(id)) map.removeLayer(id)
        })
        if (map.getSource('pollution-source')) map.removeSource('pollution-source')
      } catch {
        // mapa ya destruido por useMapbox cleanup — ignorar
      }
    }
  }, [map, setIsLoading, setCache, setError])

  return null
}
