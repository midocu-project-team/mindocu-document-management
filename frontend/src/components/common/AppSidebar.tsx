import { House } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ThemeToggle } from './ThemeToggle';

export function AppSidebar() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const isHome = pathname === '/';

  return (
    <aside className="mindocu-sidebar" aria-label="Hauptnavigation">
      <div className="mindocu-sidebar-brand" aria-hidden="true">
        <span className="mindocu-sidebar-brand-mark">M</span>
      </div>

      <nav className="mindocu-sidebar-nav">
        <button
          type="button"
          className={`mindocu-sidebar-button${isHome ? ' is-active' : ''}`}
          aria-label="Startseite"
          onClick={() => navigate('/')}
        >
          <House size={28} strokeWidth={2.1} />
        </button>
      </nav>

      <div className="mindocu-sidebar-footer">
        <ThemeToggle />
      </div>
    </aside>
  );
}
