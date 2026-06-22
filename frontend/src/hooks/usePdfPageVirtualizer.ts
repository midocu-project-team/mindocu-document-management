import { useEffect, type RefObject } from 'react';
import { useVirtualizer, type VirtualItem } from '@tanstack/react-virtual';

// A4 portrait fallback (height / width) used to size a page slot until its
// real rendered height has been measured.
export const PDF_DEFAULT_ASPECT = 1.414;

type UsePdfPageVirtualizerArgs = {
  /** The scrollable viewport element that holds the page slots. */
  scrollRef: RefObject<HTMLDivElement | null>;
  /** Number of (visible) pages to virtualize. */
  count: number;
  /** Rendered page width in px (already zoom-scaled). */
  pageWidth: number;
  /** Vertical gap between pages in px. */
  pageGap: number;
  /**
   * Re-measure trigger: whenever this value changes the cached page heights
   * are dropped back to the estimate (e.g. on zoom, document or filter change),
   * because those events resize or reorder every page.
   */
  resetKey: string | number;
};

export type PdfPageVirtualizer = {
  virtualItems: VirtualItem[];
  totalSize: number;
  measureElement: (element: Element | null) => void;
  /** Scroll the page at this index to the top of the viewport. */
  scrollToIndex: (index: number, behavior?: ScrollBehavior) => void;
  /** Index of the page slot straddling the viewport's vertical centre. */
  getCenteredIndex: () => number | null;
};

/**
 * Shared virtualization mechanics for the PDF viewers: mounts only the page
 * slots in (and just outside) the viewport, measures their real heights, and
 * reports the centred page. Works purely in indices — the caller maps an index
 * to a page number (`index + 1`, or `visiblePages[index]` behind a filter), so
 * styling and state ownership stay in the component.
 */
export function usePdfPageVirtualizer({
  scrollRef,
  count,
  pageWidth,
  pageGap,
  resetKey,
}: UsePdfPageVirtualizerArgs): PdfPageVirtualizer {
  const rowVirtualizer = useVirtualizer({
    count,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => Math.round(pageWidth * PDF_DEFAULT_ASPECT) + pageGap,
    overscan: 2,
  });

  useEffect(() => {
    rowVirtualizer.measure();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resetKey]);

  const getCenteredIndex = (): number | null => {
    const root = scrollRef.current;
    if (!root || count === 0) {
      return null;
    }
    const center = root.scrollTop + root.clientHeight / 2;
    for (const item of rowVirtualizer.getVirtualItems()) {
      if (center >= item.start && center < item.start + item.size) {
        return item.index;
      }
    }
    return null;
  };

  return {
    virtualItems: rowVirtualizer.getVirtualItems(),
    totalSize: rowVirtualizer.getTotalSize(),
    measureElement: rowVirtualizer.measureElement,
    scrollToIndex: (index, behavior = 'smooth') =>
      rowVirtualizer.scrollToIndex(index, { align: 'start', behavior }),
    getCenteredIndex,
  };
}
