import { PanelLeftClose, PanelLeftOpen, PanelRightClose, PanelRightOpen } from 'lucide-react'

type TopbarProps = {
  title: string
  leftSidebarOpen: boolean
  rightSidebarOpen: boolean
  onToggleLeftSidebar: () => void
  onToggleRightSidebar: () => void
}

export function Topbar({
  title,
  leftSidebarOpen,
  rightSidebarOpen,
  onToggleLeftSidebar,
  onToggleRightSidebar,
}: TopbarProps) {
  return (
    <header className="mindocu-topbar">
      <div className="mindocu-topbar-shell">

        <div className="mindocu-topbar-left">
          <button
            type="button"
            className="mindocu-topbar-chip"
            onClick={onToggleLeftSidebar}
            aria-label={leftSidebarOpen ? 'Linke Sidebar schließen' : 'Linke Sidebar öffnen'}
          >
            {leftSidebarOpen ? <PanelLeftClose size={32} /> : <PanelLeftOpen size={32} />}
          </button>
        </div>

        <div className="mindocu-topbar-titlewrap">
          <div className="mindocu-topbar-title">{title}</div>
        </div>

        <div className="mindocu-topbar-right">
          <button
            type="button"
            className="mindocu-topbar-chip"
            onClick={onToggleRightSidebar}
            aria-label={rightSidebarOpen ? 'Rechte Sidebar schließen' : 'Rechte Sidebar öffnen'}
          >
            {rightSidebarOpen ? <PanelRightClose size={32} /> : <PanelRightOpen size={32} />}
          </button>
        </div>
      </div>
    </header>
  )
}
