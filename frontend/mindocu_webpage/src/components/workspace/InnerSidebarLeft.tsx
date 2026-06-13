import { useEffect, useRef } from 'react'
import { SearchToolbar } from './SearchToolbar'
import { SegmentFilterDropdown } from './SegmentFilterDropdown'
import { formatPageRange, isSegmentVisible } from './segmentUtils'

export type Segment = {
  id: string
  title: string
  summary: string
  relevant: boolean
  start_page: number
  end_page: number
}

type InnerSidebarLeftProps = {
  activeTab: 'Segmente' | 'Suche'
  onTabChange: (tab: 'Segmente' | 'Suche') => void
  segments: Segment[]
  selectedSegmentIndex: number
  onSelectSegment: (index: number) => void
  showRelevantSegments: boolean
  showIrrelevantSegments: boolean
  onToggleShowRelevantSegments: () => void
  onToggleShowIrrelevantSegments: () => void
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
  showRelevantSegments,
  showIrrelevantSegments,
  onToggleShowRelevantSegments,
  onToggleShowIrrelevantSegments,
  query,
  onQueryChange,
  onClearQuery,
}: InnerSidebarLeftProps) {
  const segmentListRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const list = segmentListRef.current
    if (!list) {
      return
    }

    const activeCard = list.querySelector<HTMLElement>('.mindocu-segment-card.is-active')
    activeCard?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [selectedSegmentIndex, activeTab])

  const filteredSegments = segments.filter((segment) => {
    if (!isSegmentVisible(segment, showRelevantSegments, showIrrelevantSegments)) {
      return false
    }

    const haystack = `${segment.title} ${formatPageRange(segment.start_page, segment.end_page)}`.toLowerCase()
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
          <SegmentFilterDropdown
            showRelevantSegments={showRelevantSegments}
            showIrrelevantSegments={showIrrelevantSegments}
            onToggleShowRelevantSegments={onToggleShowRelevantSegments}
            onToggleShowIrrelevantSegments={onToggleShowIrrelevantSegments}
          />

          <div ref={segmentListRef} className="mindocu-segment-list" aria-label="Segmentliste">
            {filteredSegments.map((segment) => {
              const segmentIndex = segments.findIndex((candidate) => candidate.id === segment.id)
              const isSelected = segmentIndex === selectedSegmentIndex

              return (
                <button
                  key={segment.id}
                  type="button"
                  className={`mindocu-segment-card${isSelected ? ' is-active' : ''}${segment.relevant ? '' : ' is-irrelevant'}`}
                  onClick={() => {
                    if (segmentIndex >= 0) {
                      onSelectSegment(segmentIndex)
                    }
                  }}
                >
                  <div className="mindocu-segment-card-title">{segment.title}</div>
                  <div className="mindocu-segment-card-meta">
                    <span>{formatPageRange(segment.start_page, segment.end_page)}</span>
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
