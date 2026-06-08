import { Search, X } from 'lucide-react'

type SearchToolbarProps = {
  query: string
  onQueryChange: (query: string) => void
  onClear: () => void
  resultCount?: number
  selectedIndex?: number // zero-based index of the currently selected search result
}

export function SearchToolbar({ query, onQueryChange, onClear, resultCount, selectedIndex }: SearchToolbarProps) {
  return (
    <div className="mindocu-searchbar" role="search" aria-label="Suche">
      <div className="mindocu-searchbar-inputwrap">
        <input
          type="search"
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Suchbegriff eingeben..."
          className="mindocu-searchbar-input"
        />
        <Search size={16} />
        {query ? (
          <button type="button" className="mindocu-searchbar-clear" onClick={onClear} aria-label="Suche leeren">
            <X size={15} />
          </button>
        ) : null}
      </div>
      <div className="mindocu-searchbar-meta">
        {typeof resultCount === 'number' && resultCount > 0 ? (
          typeof selectedIndex === 'number' ? (
            `Ergebnis ${Math.max(1, Math.min(resultCount, selectedIndex + 1))} / ${resultCount}`
          ) : (
            `Ergebnis ${resultCount}`
          )
        ) : (
          `Ergebnis ${resultCount ?? 0}`
        )}
      </div>
    </div>
  )
}
