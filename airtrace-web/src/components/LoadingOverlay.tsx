import useAppStore from '../store/useAppStore'

export default function LoadingOverlay() {
  const isLoading = useAppStore((s) => s.isLoading)

  return (
    <div
      className={[
        'absolute inset-0 z-50 flex flex-col items-center justify-center',
        'bg-background/80 transition-opacity duration-150',
        isLoading
          ? 'opacity-100 pointer-events-auto'
          : 'opacity-0 pointer-events-none',
      ].join(' ')}
      aria-hidden={!isLoading}
    >
      <svg
        className="animate-spin h-10 w-10 text-accent"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
        />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
        />
      </svg>

      <p className="text-text-muted text-sm mt-3" role="status" aria-live="polite">
        {isLoading ? 'Cargando mapa de Liverpool...' : ''}
      </p>
    </div>
  )
}
