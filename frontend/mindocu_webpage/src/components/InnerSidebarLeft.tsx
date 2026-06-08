import { SearchToolbar } from './SearchToolbar'

export type Segment = {
  title: string
  date: string
  range: string
}

type InnerSidebarLeftProps = {
  activeTab: 'Segmente' | 'Suche'
  onTabChange: (tab: 'Segmente' | 'Suche') => void
  segments: Segment[]
  selectedSegmentIndex: number
  onSelectSegment: (index: number) => void
  query: string
  onQueryChange: (query: string) => void
  onClearQuery: () => void
}

export function InnerSidebarLeft({
  activeTab,
  onTabChange,
  segments,
  selectedSegmentIndex,
  onSelectSegment,
  query,
  onQueryChange,
  onClearQuery,
}: InnerSidebarLeftProps) {
  const filteredSegments = segments.filter((segment) => {
    const haystack = `${segment.title} ${segment.date} ${segment.range}`.toLowerCase()
    return haystack.includes(query.trim().toLowerCase())
  })

  return (
    <aside className="mindocu-inner-sidebar mindocu-inner-sidebar--left">
      <div className="mindocu-inner-tabs" role="tablist" aria-label="Dokumentnavigation">
        <button
          type="button"
          className={`mindocu-inner-tab${activeTab === 'Segmente' ? ' is-active' : ''}`}
          onClick={() => onTabChange('Segmente')}
        >
          <span>Segmente</span>
        </button>
        <button
          type="button"
          className={`mindocu-inner-tab${activeTab === 'Suche' ? ' is-active' : ''}`}
          onClick={() => onTabChange('Suche')}
        >
          <span>Suche</span>
        </button>
      </div>

      {activeTab === 'Suche' ? (
        <div className="mindocu-inner-panel">
          <SearchToolbar
            query={query}
            onQueryChange={onQueryChange}
            onClear={onClearQuery}
            resultCount={filteredSegments.length}
          />
        </div>
      ) : null}

      {activeTab === 'Segmente' ? (
        <div className="mindocu-inner-panel">
          <div className="mindocu-segment-list" aria-label="Segmentliste">
            {filteredSegments.map((segment, index) => {
              const isSelected = index === selectedSegmentIndex

              return (
                <button
                  key={`${segment.title}-${segment.date}`}
                  type="button"
                  className={`mindocu-segment-card${isSelected ? ' is-active' : ''}`}
                  onClick={() => onSelectSegment(index)}
                >
                  <div className="mindocu-segment-card-title">{segment.title}</div>
                  <div className="mindocu-segment-card-meta">
                    <span>{segment.date}</span>
                    <span>{segment.range}</span>
                  </div>
                </button>
              )
            })}
          </div>
        </div>
      ) : null}
    </aside>
  )
}
