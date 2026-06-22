import { useEffect, useRef, useState } from 'react';
import { ChevronDown, Eye, EyeOff, Filter } from 'lucide-react';

type SegmentFilterDropdownProps = {
  showRelevantSegments: boolean;
  showIrrelevantSegments: boolean;
  onToggleShowRelevantSegments: () => void;
  onToggleShowIrrelevantSegments: () => void;
};

export function SegmentFilterDropdown({
  showRelevantSegments,
  showIrrelevantSegments,
  onToggleShowRelevantSegments,
  onToggleShowIrrelevantSegments,
}: SegmentFilterDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }

    const handlePointerDown = (event: MouseEvent) => {
      if (!dropdownRef.current?.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleEscape);

    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen]);

  return (
    <div className="mindocu-segment-filter" ref={dropdownRef}>
      <button
        type="button"
        className={`mindocu-segment-filter-trigger${isOpen ? ' is-open' : ''}`}
        onClick={() => setIsOpen((open) => !open)}
        aria-haspopup="menu"
        aria-expanded={isOpen}
        aria-label="Segmentfilter"
      >
        <Filter size={14} />
        <ChevronDown size={14} className={isOpen ? 'is-rotated' : undefined} />
      </button>

      {isOpen ? (
        <div className="mindocu-segment-filter-menu" role="menu" aria-label="Segmentfilter">
          <div className="mindocu-segment-filter-row" role="none">
            <button
              type="button"
              className="mindocu-segment-filter-visibility"
              onClick={onToggleShowRelevantSegments}
              aria-label={
                showRelevantSegments
                  ? 'Relevante Segmente ausblenden'
                  : 'Relevante Segmente einblenden'
              }
              aria-pressed={showRelevantSegments}
            >
              {showRelevantSegments ? <Eye size={15} /> : <EyeOff size={15} />}
            </button>
            <span className="mindocu-segment-filter-label">Relevante Segmente</span>
          </div>

          <div className="mindocu-segment-filter-row" role="none">
            <button
              type="button"
              className="mindocu-segment-filter-visibility"
              onClick={onToggleShowIrrelevantSegments}
              aria-label={
                showIrrelevantSegments
                  ? 'Irrelevante Segmente ausblenden'
                  : 'Irrelevante Segmente einblenden'
              }
              aria-pressed={showIrrelevantSegments}
            >
              {showIrrelevantSegments ? <Eye size={15} /> : <EyeOff size={15} />}
            </button>
            <span className="mindocu-segment-filter-label">Irrelevante Segmente</span>
          </div>
        </div>
      ) : null}
    </div>
  );
}
