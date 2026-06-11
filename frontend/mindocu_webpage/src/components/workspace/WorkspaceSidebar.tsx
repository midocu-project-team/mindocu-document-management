import type { LucideIcon } from 'lucide-react'
import {
  FolderOpen,
  House,
  IdCard,
  MessageCircleMore,
  Settings2,
} from 'lucide-react'

const sidebarActions: Array<{ icon: LucideIcon; label: string; active: boolean }> = [
  { icon: House, label: 'Dashboard', active: true },
  { icon: FolderOpen, label: 'Akte', active: false },
  { icon: MessageCircleMore, label: 'Chat', active: false },
]

export function WorkspaceSidebar() {
  return (
    <aside className="mindocu-sidebar" aria-label="Hauptnavigation">
      <div className="mindocu-sidebar-brand" aria-hidden="true">
        <span className="mindocu-sidebar-brand-mark">M</span>
      </div>

      <nav className="mindocu-sidebar-nav">
        {sidebarActions.map(({ icon: Icon, label, active }) => (
          <button
            key={label}
            type="button"
            className={`mindocu-sidebar-button${active ? ' is-active' : ''}`}
            aria-label={label}
          >
            <Icon size={28} strokeWidth={2.1} />
          </button>
        ))}
      </nav>

      <div className="mindocu-sidebar-footer">
        <div className="mindocu-sidebar-account">
          <span className="mindocu-sidebar-account-label">Account</span>
          <button type="button" className="mindocu-sidebar-button">
            <IdCard size={26} strokeWidth={2.1} />
          </button>
        </div>

        <button type="button" className="mindocu-sidebar-button mindocu-sidebar-settings">
          <Settings2 size={28} strokeWidth={2.1} />
        </button>
      </div>
    </aside>
  )
}
