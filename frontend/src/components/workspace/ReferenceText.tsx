import type { ReactNode } from 'react';
import type { SummaryReference } from '@/api/types';

type ReferenceTextProps = {
  /** The grounded sentences to render (a segment summary or a chat answer). */
  references: SummaryReference[];
  /** Index into `references` that stays underlined while its hit bar is open. */
  activeReferenceIndex: number | null;
  onReferenceClick: (index: number) => void;
  /** Rendered instead when `references` is empty. */
  fallback: ReactNode;
};

/**
 * A block of text made of clickable, grounded reference sentences -- shared by
 * the segment summary and chat answers so both drive the same PDF highlight
 * mechanism (see useReferenceHighlight) identically.
 */
export function ReferenceText({
  references,
  activeReferenceIndex,
  onReferenceClick,
  fallback,
}: ReferenceTextProps) {
  if (references.length === 0) {
    return <>{fallback}</>;
  }

  return (
    <div className="mindocu-summary-references">
      {references.map((reference, index) => (
        <span
          key={index}
          className={`mindocu-reference${index === activeReferenceIndex ? ' is-active' : ''}`}
          role="button"
          tabIndex={0}
          aria-pressed={index === activeReferenceIndex}
          onClick={() => onReferenceClick(index)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' || event.key === ' ') {
              event.preventDefault();
              onReferenceClick(index);
            }
          }}
        >
          {reference.text}
        </span>
      ))}
    </div>
  );
}
