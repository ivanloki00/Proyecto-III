import { useState, useEffect } from 'react'
import mapboxgl from 'mapbox-gl'

export function useMapbox(containerRef: React.RefObject<HTMLDivElement | null>) {
  const [map, setMap] = useState<mapboxgl.Map | null>(null)

  useEffect(() => {
    if (!containerRef.current) return

    const token = import.meta.env.VITE_MAPBOX_TOKEN
    if (!token) {
      console.error('[AirTrace] VITE_MAPBOX_TOKEN no definido — el mapa no cargará')
      return
    }

    mapboxgl.accessToken = token

    const m = new mapboxgl.Map({
      container: containerRef.current,
      style: 'mapbox://styles/mapbox/dark-v11',
      center: [-2.978, 53.41],
      zoom: 12,
    })

    setMap(m)

    return () => {
      m.remove()
      setMap(null)
    }
  }, [containerRef])

  return { map }
}
