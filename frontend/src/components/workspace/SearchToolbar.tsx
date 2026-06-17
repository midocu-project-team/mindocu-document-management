import { Search, X } from 'lucide-react'

type SearchToolbarProps = {
  query: string
  onQueryChange: (query: string) => void
  onClear: () => void
  resultCount?: number
}

export function SearchToolbar({ query, onQueryChange, onClear, resultCount }: SearchToolbarProps) {
  const hasQuery = query.trim().length > 0

  return (
    <div className="mindocu-searchbar" role="search" aria-label="Suche">
      <div className="mindocu-searchbar-inputwrap">
        <Search size={16} className="mindocu-searchbar-icon" />
        <input
          type="search"
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="In Segmenten suchen …"
          className="mindocu-searchbar-input"
        />
        {hasQuery ? (
          <>
            <span className="mindocu-searchbar-count" aria-label="Trefferanzahl">
              {resultCount ?? 0}
            </span>
            <button
              type="button"
              className="mindocu-searchbar-clear"
              onClick={onClear}
              aria-label="Suche leeren"
            >
              <X size={15} />
            </button>
          </>
        ) : null}
      </div>
    </div>
  )
}
