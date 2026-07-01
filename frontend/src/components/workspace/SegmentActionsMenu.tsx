import { useEffect, useRef, useState } from 'react';
import { Ban, Check, MoreVertical } from 'lucide-react';
import type { Segment } from '@/types/segment';

type SegmentActionsMenuProps = {
  segment: Segment | undefined;
  onToggleRelevance: () => void;
  isPending: boolean;
};

/**
 * Kebab menu in the left toolbar acting on the *currently selected* segment.
 * The single action is a two-way relevance toggle whose label spells out the
 * target ("Segment als irrelevant/relevant markieren") and flips with the
 * segment's current state. Disabled while no segment is selected.
 */
export function SegmentActionsMenu({
  segment,
  onToggleRelevance,
  isPending,
}: SegmentActionsMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }

    const handlePointerDown = (event: MouseEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) {
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

  // Default to the "mark irrelevant" wording when no segment is selected; the
  // trigger is disabled in that case anyway, so the label is never shown.
  const markIrrelevant = segment?.relevant ?? true;
  const actionLabel = markIrrelevant ? 'Segment als irrelevant markieren' : 'Segment als relevant markieren';

  const handleAction = () => {
    onToggleRelevance();
    setIsOpen(false);
  };

  return (
    <div className="mindocu-segment-actions" ref={menuRef}>
      <button
        type="button"
        className={`mindocu-segment-actions-trigger${isOpen ? ' is-open' : ''}`}
        onClick={() => setIsOpen((open) => !open)}
        disabled={!segment}
        aria-haspopup="menu"
        aria-expanded={isOpen}
        aria-label="Segmentaktionen"
      >
        <MoreVertical size={16} />
      </button>

      {isOpen && segment ? (
        <div className="mindocu-segment-actions-menu" role="menu" aria-label="Segmentaktionen">
          <button
            type="button"
            role="menuitem"
            className="mindocu-segment-actions-item"
            onClick={handleAction}
            disabled={isPending}
          >
            {markIrrelevant ? <Ban size={15} /> : <Check size={15} />}
            <span>{actionLabel}</span>
          </button>
        </div>
      ) : null}
    </div>
  );
}
