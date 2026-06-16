import { useColorScheme } from '@mui/material/styles'
import { Moon, Sun } from 'lucide-react'

/**
 * Light/dark toggle for the global navigation rail. Defaults follow the OS
 * (the provider's `defaultMode="system"`); clicking pins an explicit mode,
 * persisted by MUI in localStorage. Renders nothing until `mode` is hydrated
 * to avoid a wrong-icon flash on first paint.
 */
export function ThemeToggle() {
  const { mode, systemMode, setMode } = useColorScheme()
  if (!mode) return null

  const resolved = mode === 'system' ? systemMode : mode
  const isDark = resolved === 'dark'

  return (
    <button
      type="button"
      className="mindocu-sidebar-button"
      aria-label={isDark ? 'Hellen Modus aktivieren' : 'Dunklen Modus aktivieren'}
      title={isDark ? 'Heller Modus' : 'Dunkler Modus'}
      onClick={() => setMode(isDark ? 'light' : 'dark')}
    >
      {isDark ? <Sun size={26} strokeWidth={2.1} /> : <Moon size={26} strokeWidth={2.1} />}
    </button>
  )
}

export default ThemeToggle
