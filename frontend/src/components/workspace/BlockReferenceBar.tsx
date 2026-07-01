import { ChevronLeft, ChevronRight, X } from 'lucide-react';
import type { BlockOut } from '@/api/types';

type BlockReferenceBarProps = {
  /** One slot per reference block, aligned to the reference's block_ids order;
   *  `undefined` while a block is still loading (keeps the "hit i/n" count stable). */
  hits: (BlockOut | undefined)[];
  activeIndex: number;
  onPrev: () => void;
  onNext: () => void;
  onClose: () => void;
};

const PREVIEW_MAX_CHARS = 90;

function previewText(block: BlockOut | undefined): string {
  if (!block) {
    return 'Block wird geladen …';
  }
  const text = block.text.trim().replace(/\s+/g, ' ');
  return text.length > PREVIEW_MAX_CHARS ? `${text.slice(0, PREVIEW_MAX_CHARS)}…` : text;
}

/**
 * A reusable navigation bar over the PDF for stepping through the source blocks
 * ("hits") of a clicked reference. Presentation only -- page jump + highlight are
 * driven by the parent from the active hit. Renders nothing without hits.
 */
export function BlockReferenceBar({
  hits,
  activeIndex,
  onPrev,
  onNext,
  onClose,
}: BlockReferenceBarProps) {
  if (hits.length === 0) {
    return null;
  }

  const active = hits[activeIndex];

  return (
    <div className="mindocu-reference-bar" role="toolbar" aria-label="Referenz-Treffer">

      <span className="mindocu-reference-bar-counter">
        Treffer {activeIndex + 1}/{hits.length}
      </span>

      <div className="mindocu-reference-bar-info">
        {active ? <span className="mindocu-reference-bar-page">Seite {active.page_number}</span> : null}
        <span className="mindocu-reference-bar-preview">{previewText(active)}</span>
      </div>

      <button
        type="button"
        className="mindocu-reference-bar-nav"
        onClick={onPrev}
        disabled={activeIndex <= 0}
        aria-label="Vorheriger Treffer"
      >
        <ChevronLeft size={18} />
      </button>
      <button
        type="button"
        className="mindocu-reference-bar-nav"
        onClick={onNext}
        disabled={activeIndex >= hits.length - 1}
        aria-label="Nächster Treffer"
      >
        <ChevronRight size={18} />
      </button>

      <button
        type="button"
        className="mindocu-reference-bar-close"
        onClick={onClose}
        aria-label="Treffer-Ansicht schließen"
      >
        <X size={16} />
      </button>
    </div>
  );
}
