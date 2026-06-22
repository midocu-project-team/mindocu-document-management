import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef } from 'react';
import { ChevronDown, ChevronUp, Minus, Plus } from 'lucide-react';
import { Document, Page, pdfjs } from 'react-pdf';
import { usePdfPageVirtualizer, PDF_DEFAULT_ASPECT } from '../../hooks/usePdfPageVirtualizer';
import { getNextVisiblePage, getPreviousVisiblePage } from '../../utils/segmentUtils';

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

export type PdfViewportHandle = {
  goToPage: (page: number, behavior?: ScrollBehavior) => void;
};

type PdfViewportProps = {
  pdfUrl?: string | null;
  currentPage: number;
  visiblePages: number[];
  zoom: number;
  onPageChange: (page: number) => void;
  onPageCountChange: (pageCount: number) => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
};

const PDF_BASE_WIDTH = 720;
const PDF_PAGE_GAP = 18; // vertical gap between rendered pages (px)

// Tells pdf.js where to fetch its WASM decoders (served from /wasm/ by the
// pdfjsWasm Vite plugin). Without this, JPEG2000-encoded scan pages render
// blank ("JpxError: OpenJPEG failed to initialize"). Module-level constant so
// the reference stays stable — a fresh object would make react-pdf reload the PDF.
const PDF_OPTIONS = { wasmUrl: '/wasm/' };

export const PdfViewport = forwardRef<PdfViewportHandle, PdfViewportProps>(function PdfViewport(
  { pdfUrl, currentPage, visiblePages, zoom, onPageChange, onPageCountChange, onZoomIn, onZoomOut },
  ref,
) {
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const onPageChangeRef = useRef(onPageChange);

  const renderedPages = visiblePages;
  const displayPageCount = visiblePages.length;
  const pageWidth = Math.round(PDF_BASE_WIDTH * zoom);
  const visibleKey = renderedPages.join(',');

  onPageChangeRef.current = onPageChange;

  // Virtualize the (filtered) visible pages: only the slots in/just outside the
  // viewport mount a real <Page> canvas; every other slot is a sized placeholder.
  // Each virtual index maps to renderedPages[index], so the filter stays intact.
  // Re-measure when zoom, document or filter changes (all resize/reorder pages).
  const { virtualItems, totalSize, measureElement, scrollToIndex, getCenteredIndex } =
    usePdfPageVirtualizer({
      scrollRef: viewportRef,
      count: renderedPages.length,
      pageWidth,
      pageGap: PDF_PAGE_GAP,
      resetKey: `${zoom}|${pdfUrl ?? ''}|${visibleKey}`,
    });

  // The page whose virtual slot straddles the viewport's vertical centre is
  // "current". Works with placeholder slots that have never been rendered.
  const handleViewportScroll = () => {
    const index = getCenteredIndex();
    if (index === null) {
      return;
    }
    const page = renderedPages[index];
    if (page !== currentPage) {
      onPageChangeRef.current(page);
    }
  };

  const getVisiblePageIndex = useCallback(
    (page: number): number => {
      return renderedPages.indexOf(page);
    },
    [renderedPages],
  );

  const getVirtualCurrentPage = useCallback(() => {
    const idx = getVisiblePageIndex(currentPage);
    return idx >= 0 ? idx + 1 : 1;
  }, [currentPage, getVisiblePageIndex]);

  const virtualCurrent = getVirtualCurrentPage();

  const goToPage = useCallback(
    (page: number, behavior: ScrollBehavior = 'auto') => {
      const index = renderedPages.indexOf(page);
      if (index < 0) {
        return;
      }

      onPageChange(page);
      scrollToIndex(index, behavior);
    },
    [onPageChange, renderedPages, scrollToIndex],
  );

  useEffect(() => {
    if (renderedPages.length === 0) return;
    if (!renderedPages.includes(currentPage)) {
      onPageChange(renderedPages[0]);
    }
  }, [renderedPages, currentPage, onPageChange]);

  useImperativeHandle(ref, () => ({ goToPage }), [goToPage]);

  const handlePdfLoad = ({ numPages }: { numPages: number }) => {
    onPageCountChange(numPages);
  };

  return (
    <section className="mindocu-pdf-stage" aria-label="Dokumentansicht">
      <div ref={viewportRef} className="mindocu-pdf-scrollarea" onScroll={handleViewportScroll}>
        {pdfUrl ? (
          // Keep <Document> mounted across filter changes: unmounting it would make
          // react-pdf reload (and re-fetch/re-parse) the whole PDF when pages reappear.
          // Only the inner content switches between the page list and the empty hint.
          <Document
            file={pdfUrl}
            options={PDF_OPTIONS}
            onLoadSuccess={handlePdfLoad}
            loading={<div className="mindocu-pdf-loading">PDF wird geladen ...</div>}
            error={<div className="mindocu-pdf-loading">PDF konnte nicht geladen werden.</div>}
          >
            {renderedPages.length === 0 ? (
              <div className="mindocu-pdf-loading">
                Keine Seiten für die aktuelle Filterauswahl sichtbar.
              </div>
            ) : (
              <div style={{ position: 'relative', width: '100%', height: totalSize }}>
                {virtualItems.map((item) => {
                  const pageNumber = renderedPages[item.index];
                  return (
                    <div
                      key={item.key}
                      data-index={item.index}
                      ref={measureElement}
                      style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        width: '100%',
                        transform: `translateY(${item.start}px)`,
                        display: 'flex',
                        justifyContent: 'center',
                        paddingBottom: PDF_PAGE_GAP,
                      }}
                    >
                      <div
                        className="mindocu-pdf-pagewrap"
                        data-page={pageNumber}
                        style={{ margin: 0 }}
                      >
                        <Page
                          pageNumber={pageNumber}
                          width={pageWidth}
                          renderTextLayer={false}
                          renderAnnotationLayer={false}
                          loading={
                            <div
                              style={{
                                width: pageWidth,
                                height: Math.round(pageWidth * PDF_DEFAULT_ASPECT),
                              }}
                            />
                          }
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </Document>
        ) : (
          <div className="mindocu-pdf-loading">Kein PDF ausgewählt.</div>
        )}
      </div>

      <div className="mindocu-page-controls" aria-label="Seitensteuerung">
        <div className="mindocu-page-counter">
          <div className="mindocu-page-counter-current">{virtualCurrent}</div>
        </div>
        <div className="mindocu-page-counter-total">{displayPageCount}</div>
        <button
          type="button"
          className="mindocu-page-control"
          onClick={() => {
            const previousPage = getPreviousVisiblePage(currentPage, renderedPages);
            if (previousPage) {
              goToPage(previousPage);
            }
          }}
          aria-label="Vorherige Seite"
          disabled={!getPreviousVisiblePage(currentPage, renderedPages)}
        >
          <ChevronUp size={18} />
        </button>
        <button
          type="button"
          className="mindocu-page-control"
          onClick={() => {
            const nextPage = getNextVisiblePage(currentPage, renderedPages);
            if (nextPage) {
              goToPage(nextPage);
            }
          }}
          aria-label="Nächste Seite"
          disabled={!getNextVisiblePage(currentPage, renderedPages)}
        >
          <ChevronDown size={18} />
        </button>
        <div className="mindocu-page-control-group">
          <button
            type="button"
            className="mindocu-page-control"
            onClick={onZoomIn}
            aria-label="Vergrößern"
          >
            <Plus size={17} />
          </button>
          <button
            type="button"
            className="mindocu-page-control"
            onClick={onZoomOut}
            aria-label="Verkleinern"
          >
            <Minus size={17} />
          </button>
        </div>
      </div>
    </section>
  );
});
