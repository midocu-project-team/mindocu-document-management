import { ChevronDown, Filter, MessageCircle, PenLine, MousePointer, Folders } from 'lucide-react'

type WorkspaceToolbarProps = {
  activeTool: 'select' | 'pen' | 'comment' | 'erase'
  onToolChange: (tool: 'select' | 'pen' | 'comment' | 'erase') => void
  documentLabel: string
  currentPage: number
  pageCount: number
  zoom: number
  onZoomOut: () => void
  onZoomIn: () => void
  onFitToPage: () => void
}

const editTools = [
  { id: 'select' as const, icon: MousePointer, label: 'Auswählen' },
  { id: 'pen' as const, icon: PenLine, label: 'Bearbeiten' },
  { id: 'comment' as const, icon: MessageCircle, label: 'Kommentar' },
]

export function WorkspaceToolbar({
  activeTool,
  onToolChange,
  documentLabel,
}: WorkspaceToolbarProps) {
  return (
    <div className="mindocu-toolbar mindocu-toolbar--workspace" role="toolbar" aria-label="Werkzeuge und Ansicht">
      <div className="mindocu-toolbar-group">
        {editTools.map(({ id, icon: Icon, label }) => (
          <button
            key={id}
            type="button"
            className={`mindocu-toolbar-button${activeTool === id ? ' is-active' : ''}`}
            onClick={() => onToolChange(id)}
            aria-pressed={activeTool === id}
            aria-label={label}
          >
            <Icon size={17} />
          </button>
        ))}
      </div>

      <div className="mindocu-toolbar-group mindocu-toolbar-group--divider">
        <button type="button" className="mindocu-toolbar-pill">
            <span>{documentLabel}</span>
            <Folders size={15} />
            <ChevronDown size={15} />
        </button>
        <button type="button" className="mindocu-toolbar-pill mindocu-toolbar-pill--muted">
        <Filter size={15} />
        </button>
      </div>
    </div>
  )
}

export default WorkspaceToolbar
