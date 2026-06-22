import { MousePointer, Search } from 'lucide-react';

type RightSidebarToolbarProps = {
  onRefresh?: () => void;
  onToggleLayout?: () => void;
  className?: string;
};

export function RightSidebarToolbar({ onRefresh, onToggleLayout }: RightSidebarToolbarProps) {
  return (
    <div className="mindocu-right-toolbar" role="toolbar" aria-label="Segment Werkzeuge">
      <button
        type="button"
        className="mindocu-sidebar-button"
        onClick={onRefresh}
        aria-label="Aktualisieren"
      >
        <MousePointer size={18} strokeWidth={2} />
      </button>
      <button
        type="button"
        className="mindocu-sidebar-button"
        onClick={onToggleLayout}
        aria-label="Layout"
      >
        <Search size={18} strokeWidth={2} />
      </button>
    </div>
  );
}

export default RightSidebarToolbar;
