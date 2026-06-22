import { useEffect, useRef } from 'react';
import { SearchToolbar } from './SearchToolbar';
import { SegmentFilterDropdown } from './SegmentFilterDropdown';
import { formatPageRange, isSegmentShown } from './segmentUtils';
import { SEGMENT_TITLE_FALLBACK } from './workspaceTypes';

export type Segment = {
  id: string;
  title: string | null;
  summary: string | null;
  relevant: boolean;
  start_page: number;
  end_page: number;
};

type InnerSidebarLeftProps = {
  segments: Segment[];
  selectedSegmentIndex: number;
  onSelectSegment: (index: number) => void;
  showRelevantSegments: boolean;
  showIrrelevantSegments: boolean;
  onToggleShowRelevantSegments: () => void;
  onToggleShowIrrelevantSegments: () => void;
  query: string;
  onQueryChange: (query: string) => void;
  onClearQuery: () => void;
};

export function InnerSidebarLeft({
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
  const segmentListRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const list = segmentListRef.current;
    if (!list) {
      return;
    }

    const activeCard = list.querySelector<HTMLElement>('.mindocu-segment-card.is-active');
    activeCard?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, [selectedSegmentIndex]);

  const filteredSegments = segments.filter((segment) =>
    isSegmentShown(segment, showRelevantSegments, showIrrelevantSegments, query),
  );

  return (
    <aside className="mindocu-inner-sidebar mindocu-inner-sidebar--left">
      <div className="mindocu-inner-panel">
        <div className="mindocu-leftbar-toolbar">
          <SegmentFilterDropdown
            showRelevantSegments={showRelevantSegments}
            showIrrelevantSegments={showIrrelevantSegments}
            onToggleShowRelevantSegments={onToggleShowRelevantSegments}
            onToggleShowIrrelevantSegments={onToggleShowIrrelevantSegments}
          />

          <SearchToolbar
            query={query}
            onQueryChange={onQueryChange}
            onClear={onClearQuery}
            resultCount={filteredSegments.length}
          />
        </div>

        <div ref={segmentListRef} className="mindocu-segment-list" aria-label="Segmentliste">
          {filteredSegments.map((segment) => {
            const segmentIndex = segments.findIndex((candidate) => candidate.id === segment.id);
            const isSelected = segmentIndex === selectedSegmentIndex;

            return (
              <button
                key={segment.id}
                type="button"
                className={`mindocu-segment-card${isSelected ? ' is-active' : ''}${segment.relevant ? '' : ' is-irrelevant'}`}
                onClick={() => {
                  if (segmentIndex >= 0) {
                    onSelectSegment(segmentIndex);
                  }
                }}
              >
                <div className="mindocu-segment-card-title">
                  {segment.title ?? SEGMENT_TITLE_FALLBACK}
                </div>
                <div className="mindocu-segment-card-meta">
                  <span>{formatPageRange(segment.start_page, segment.end_page)}</span>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </aside>
  );
}
