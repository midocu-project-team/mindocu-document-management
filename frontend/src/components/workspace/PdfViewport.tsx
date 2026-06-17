import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef } from 'react'
import { ChevronDown, ChevronUp, Minus, Plus } from 'lucide-react'
import { Document, Page, pdfjs } from 'react-pdf'
import { useVirtualizer } from '@tanstack/react-virtual'
import { getNextVisiblePage, getPreviousVisiblePage } from './segmentUtils'

pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString()

export type PdfViewportHandle = {
  goToPage: (page: number) => void
}

type PdfViewportProps = {
  pdfUrl?: string | null
  currentPage: number
  visiblePages: number[]
  zoom: number
  onPageChange: (page: number) => void
  onPageCountChange: (pageCount: number) => void
  onZoomIn: () => void
  onZoomOut: () => void
}

const PDF_BASE_WIDTH = 720
const PDF_PAGE_GAP = 18            // vertical gap between rendered pages (px)
const PDF_DEFAULT_ASPECT = 1.414  // A4 portrait fallback until a page is measured

export const PdfViewport = forwardRef<PdfViewportHandle, PdfViewportProps>(function PdfViewport(
  {
    pdfUrl,
    currentPage,
    visiblePages,
    zoom,
    onPageChange,
    onPageCountChange,
    onZoomIn,
    onZoomOut,
  },
  ref,
) {
  const viewportRef = useRef<HTMLDivElement | null>(null)
  const onPageChangeRef = useRef(onPageChange)

  const renderedPages = visiblePages
  const displayPageCount = visiblePages.length
  const pageWidth = Math.round(PDF_BASE_WIDTH * zoom)
  const visibleKey = renderedPages.join(',')

  onPageChangeRef.current = onPageChange

  // Virtualize the (filtered) visible pages: only the slots in/just outside the
  // viewport mount a real <Page> canvas; every other slot is a sized placeholder.
  // Each virtual index maps to renderedPages[index], so the filter stays intact.
  const rowVirtualizer = useVirtualizer({
    count: renderedPages.length,
    getScrollElement: () => viewportRef.current,
    estimateSize: () => Math.round(pageWidth * PDF_DEFAULT_ASPECT) + PDF_PAGE_GAP,
    overscan: 2,
  })

  // Zoom or filter changes invalidate the cached page heights — drop them back
  // to the (zoom-scaled) estimate and let measureElement re-measure on render.
  useEffect(() => {
    rowVirtualizer.measure()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [zoom, pdfUrl, visibleKey])

  // The page whose virtual slot straddles the viewport's vertical centre is
  // "current". Derived from the virtualizer's measured offsets, so it works
  // with placeholder slots that have never been rendered.
  const handleViewportScroll = () => {
    const root = viewportRef.current
    if (!root || renderedPages.length === 0) {
      return
    }

    const center = root.scrollTop + root.clientHeight / 2
    for (const item of rowVirtualizer.getVirtualItems()) {
      if (center >= item.start && center < item.start + item.size) {
        const page = renderedPages[item.index]
        if (page !== currentPage) {
          onPageChangeRef.current(page)
        }
        break
      }
    }
  }

  const getVisiblePageIndex = useCallback((page: number): number => {
    return renderedPages.indexOf(page)
  }, [renderedPages])
  
  const getVirtualCurrentPage = useCallback(() => {
    const idx = getVisiblePageIndex(currentPage)
    return idx >= 0 ? idx + 1 : 1
  }, [currentPage, getVisiblePageIndex])

  const virtualCurrent = getVirtualCurrentPage()

  const goToPage = useCallback(
    (page: number) => {
      const index = renderedPages.indexOf(page)
      if (index < 0) {
        return
      }

      onPageChange(page)
      rowVirtualizer.scrollToIndex(index, { align: 'start', behavior: 'smooth' })
    },
    [onPageChange, renderedPages, rowVirtualizer],
  )

  useEffect(() => {
    if (renderedPages.length === 0) return
    if (!renderedPages.includes(currentPage)) {
      onPageChange(renderedPages[0])
    }
  }, [renderedPages, currentPage, onPageChange])

  useImperativeHandle(ref, () => ({ goToPage }), [goToPage])

  const handlePdfLoad = ({ numPages }: { numPages: number }) => {
    onPageCountChange(numPages)
  }

  return (
    <section className="mindocu-pdf-stage" aria-label="Dokumentansicht">

      <div ref={viewportRef} className="mindocu-pdf-scrollarea" onScroll={handleViewportScroll}>
        {pdfUrl && renderedPages.length === 0 ? (
          <div className="mindocu-pdf-loading">Keine Seiten für die aktuelle Filterauswahl sichtbar.</div>
        ) : pdfUrl ? (
          <Document
            file={pdfUrl}
            onLoadSuccess={handlePdfLoad}
            loading={<div className="mindocu-pdf-loading">PDF wird geladen ...</div>}
            error={<div className="mindocu-pdf-loading">PDF konnte nicht geladen werden.</div>}
          >
            <div style={{ position: 'relative', width: '100%', height: rowVirtualizer.getTotalSize() }}>
              {rowVirtualizer.getVirtualItems().map((item) => {
                const pageNumber = renderedPages[item.index]
                return (
                  <div
                    key={item.key}
                    data-index={item.index}
                    ref={rowVirtualizer.measureElement}
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
                    <div className="mindocu-pdf-pagewrap" data-page={pageNumber} style={{ margin: 0 }}>
                      <Page
                        pageNumber={pageNumber}
                        width={pageWidth}
                        renderTextLayer={false}
                        renderAnnotationLayer={false}
                        loading={<div style={{ width: pageWidth, height: Math.round(pageWidth * PDF_DEFAULT_ASPECT) }} />}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
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
            const previousPage = getPreviousVisiblePage(currentPage, renderedPages)
            if (previousPage) {
              goToPage(previousPage)
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
            const nextPage = getNextVisiblePage(currentPage, renderedPages)
            if (nextPage) {
              goToPage(nextPage)
            }
          }}
          aria-label="Nächste Seite"
          disabled={!getNextVisiblePage(currentPage, renderedPages)}
        >
          <ChevronDown size={18} />
        </button>
        <div className="mindocu-page-control-group">
          <button type="button" className="mindocu-page-control" onClick={onZoomIn} aria-label="Vergrößern">
            <Plus size={17} />
          </button>
          <button type="button" className="mindocu-page-control" onClick={onZoomOut} aria-label="Verkleinern">
            <Minus size={17} />
          </button>
        </div>
      </div>
    </section>
  )
})
