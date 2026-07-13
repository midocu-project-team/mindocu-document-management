import { useEffect, useMemo, useRef, useState } from 'react';
import { useBlocks } from '@/api/hooks';
import type { BlockOut, BoundingBox, SummaryReference } from '@/api/types';

const NO_BLOCK_IDS: number[] = [];

export interface ReferenceHighlight {
  /** Index into `references` of the clicked reference; `null` => bar closed. */
  activeReferenceIndex: number | null;
  /** Which of the clicked reference's source blocks ("hits") is active. */
  activeHitIndex: number;
  /** The clicked reference's source blocks, one slot per block_id (`undefined` while loading). */
  referenceHits: (BlockOut | undefined)[];
  /** The active hit's bbox, for the strong highlight on the PDF page. */
  highlight: { pageNumber: number; bbox: BoundingBox } | null;
  /** Faint pre-marks for the reference's other hits (all but the active one). */
  markers: { pageNumber: number; bbox: BoundingBox; blockId: number }[];
  handleReferenceClick: (index: number) => void;
  handlePrevHit: () => void;
  handleNextHit: () => void;
  handleCloseReferenceBar: () => void;
}

/**
 * Reference-click -> highlight/hit-bar state, shared by every place that
 * renders a `SummaryReference[]` (a segment's summary, a chat message's
 * grounded answer): clicking a reference loads its source blocks, jumps the
 * PDF to the first one and highlights its bbox, with prev/next stepping
 * through the rest. One instance drives the PDF's single highlight overlay;
 * callers own *which* `references` array is currently fed in and must call
 * `handleCloseReferenceBar` when that switches (new segment, new chat
 * message, ...) so a stale hit bar never lingers.
 */
export function useReferenceHighlight(
  documentId: string | undefined,
  references: SummaryReference[],
  onActiveHitPageChange: (page: number) => void,
): ReferenceHighlight {
  const [activeReferenceIndex, setActiveReferenceIndex] = useState<number | null>(null);
  const [activeHitIndex, setActiveHitIndex] = useState(0);

  const activeReferenceBlockIds =
    activeReferenceIndex != null ? (references[activeReferenceIndex]?.block_ids ?? null) : null;

  const referenceHits = useBlocks(documentId, activeReferenceBlockIds ?? NO_BLOCK_IDS);
  const activeHit = referenceHits[activeHitIndex];
  const activeHitPage = activeHit?.page_number;
  const highlight = activeHit?.bbox
    ? { pageNumber: activeHit.page_number, bbox: activeHit.bbox }
    : null;

  // Faint dashed pre-marks for the other blocks of the clicked reference (all
  // of its block_ids except the active hit, which gets the strong highlight
  // on top), so every spot that reference points to is visible while stepping.
  const markers = useMemo(() => {
    const list: { pageNumber: number; bbox: BoundingBox; blockId: number }[] = [];
    referenceHits.forEach((block) => {
      if (block && block.bbox && block.block_id !== activeHit?.block_id) {
        list.push({ pageNumber: block.page_number, bbox: block.bbox, blockId: block.block_id });
      }
    });
    return list;
  }, [referenceHits, activeHit?.block_id]);

  // Latest-callback ref: keeps the page-jump effect below from re-running
  // just because the caller passed a fresh inline function this render. Kept
  // current via its own effect (never mutated during render).
  const onActiveHitPageChangeRef = useRef(onActiveHitPageChange);
  useEffect(() => {
    onActiveHitPageChangeRef.current = onActiveHitPageChange;
  });

  // Scroll the PDF to the active hit's page -- both when the user steps
  // through hits and when the active block finishes loading (page becomes known).
  useEffect(() => {
    if (activeHitPage) {
      onActiveHitPageChangeRef.current(activeHitPage);
    }
  }, [activeHitPage, activeHitIndex]);

  const handleReferenceClick = (index: number) => {
    setActiveReferenceIndex(index);
    setActiveHitIndex(0);
  };

  const handlePrevHit = () => setActiveHitIndex((index) => Math.max(0, index - 1));
  const handleNextHit = () =>
    setActiveHitIndex((index) => Math.min(referenceHits.length - 1, index + 1));
  const handleCloseReferenceBar = () => setActiveReferenceIndex(null);

  return {
    activeReferenceIndex,
    activeHitIndex,
    referenceHits,
    highlight,
    markers,
    handleReferenceClick,
    handlePrevHit,
    handleNextHit,
    handleCloseReferenceBar,
  };
}
