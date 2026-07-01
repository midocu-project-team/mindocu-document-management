import type { CSSProperties } from 'react';
import type { BoundingBox } from '@/api/types';

type BlockHighlightLayerProps = {
  /** Block bbox in PDF points, bottom-left origin: (x0, y0, x1, y1). */
  bbox: BoundingBox;
  /** Intrinsic page size in PDF points (from pdf.js `originalWidth`/`Height`). */
  widthPt: number;
  heightPt: number;
  /** Rendered page width in CSS pixels (PDF_BASE_WIDTH * zoom). */
  renderedWidthPx: number;
};

/**
 * A single highlight rectangle drawn over a rendered PDF page. Converts the
 * bottom-left-origin PDF-point bbox into top-left CSS pixels; must be rendered
 * inside a positioned page wrapper (`.mindocu-pdf-pagewrap`). Purely visual --
 * `pointer-events: none` keeps text selection/scroll on the page underneath.
 */
export function BlockHighlightLayer({
  bbox,
  widthPt,
  heightPt,
  renderedWidthPx,
}: BlockHighlightLayerProps) {
  if (widthPt <= 0 || heightPt <= 0) {
    return null;
  }

  const [x0, y0, x1, y1] = bbox;
  const scale = renderedWidthPx / widthPt;
  const style: CSSProperties = {
    left: x0 * scale,
    top: (heightPt - y1) * scale, // y-flip: y1 is the box's top edge (origin bottom-left)
    width: (x1 - x0) * scale,
    height: (y1 - y0) * scale,
  };

  return <div className="mindocu-block-highlight" style={style} aria-hidden="true" />;
}
