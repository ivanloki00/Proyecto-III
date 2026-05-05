import { useState, useEffect } from 'react'
import SidePanel from './components/SidePanel'
import LoadingOverlay from './components/LoadingOverlay'
import useAppStore from './store/useAppStore'

function App() {
  const [isPanelOpen, setIsPanelOpen] = useState(false)
  const setIsLoading = useAppStore((s) => s.setIsLoading)

  // TODO Story 2.1: reemplazar con carga real de Mapbox
  useEffect(() => {
    setIsLoading(true)
    const t = setTimeout(() => setIsLoading(false), 2000)
    return () => clearTimeout(t)
  }, [setIsLoading])

  return (
    <div className="flex flex-col min-h-screen bg-background text-text-primary">
      <header className="h-12 shrink-0 flex items-center px-4 bg-surface border-b border-border">
        <span className="font-semibold text-text-primary">AirTrace</span>
        <button
          className="ml-auto lg:hidden min-h-11 min-w-11 flex items-center justify-center
                     rounded text-text-muted hover:text-text-primary
                     focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
          onClick={() => setIsPanelOpen(o => !o)}
          aria-label={isPanelOpen ? 'Cerrar panel de análisis' : 'Abrir panel de análisis'}
          aria-expanded={isPanelOpen}
        >
          ☰
        </button>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <main
          className="flex-1 relative bg-background min-h-0 flex items-center justify-center"
          role="main"
        >
          <LoadingOverlay />
          {/* Story 2.1 montará PollutionMap aquí */}
          <p className="text-text-muted text-sm">Mapa — Story 2.1</p>
        </main>

        <SidePanel isOpen={isPanelOpen} />
      </div>
    </div>
  )
}

export default App
