interface SidePanelProps {
  isOpen: boolean
  onToggle: () => void
}

export default function SidePanel({ isOpen }: SidePanelProps) {
  return (
    <aside
      className={[
        'w-[340px] xl:w-[400px] shrink-0',
        'bg-surface border-l border-border overflow-y-auto flex-col',
        isOpen ? 'flex lg:flex' : 'hidden lg:flex',
      ].join(' ')}
      aria-label="Panel de análisis"
    >
      <div className="p-4">
        <p className="text-[#8b92a9] text-sm">Panel lateral — Story 4.x</p>
      </div>
    </aside>
  )
}
