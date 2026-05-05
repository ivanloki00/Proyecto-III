import { useRef } from 'react'
import 'mapbox-gl/dist/mapbox-gl.css'
import { useMapbox } from '../../hooks/useMapbox'
import PollutionLayer from './PollutionLayer'
import LegendOverlay from './LegendOverlay'

export default function PollutionMap() {
  const containerRef = useRef<HTMLDivElement>(null)
  const { map } = useMapbox(containerRef)

  return (
    <div className="absolute inset-0">
      <div
        ref={containerRef}
        className="w-full h-full"
        role="application"
        aria-label="Mapa de calidad del aire de Liverpool"
      />
      <PollutionLayer map={map} />
      <LegendOverlay />
    </div>
  )
}
