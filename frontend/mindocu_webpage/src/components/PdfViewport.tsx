import { useEffect, useMemo, useRef, useState } from 'react'
import { ChevronDown, ChevronUp, Minus, Plus } from 'lucide-react'
import { Document, Page, pdfjs } from 'react-pdf'

pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString()

type PdfViewportProps = {
  pdfUrl?: string | null
  currentPage: number
  pageCount: number
  zoom: number
  onPageChange: (page: number) => void
  onPageCountChange: (pageCount: number) => void
  onZoomIn: () => void
  onZoomOut: () => void
  onFitToPage: () => void
}

const demoParagraphs = [
  {
    title: 'Amtsgericht Würzburg',
    content: 'e-Aktendeckel / Stammdatenblatt',
  },
  {
    title: 'Fall',
    content: 'Würzburg, 12.02.2026',
  },
  {
    title: 'Beteiligte',
    content: 'Anna Musterfrau, Kevin Musterfrau, Josephine Musterfrau',
  },
]

export function PdfViewport({
  pdfUrl,
  currentPage,
  pageCount,
  zoom,
  onPageChange,
  onPageCountChange,
  onZoomIn,
  onZoomOut,
  onFitToPage,
}: PdfViewportProps) {
  const pageRefs = useRef<Array<HTMLDivElement | null>>([])
  const viewportRef = useRef<HTMLDivElement | null>(null)
  const [loadedPages, setLoadedPages] = useState(0)

  const displayPageCount = pdfUrl ? loadedPages || pageCount : pageCount

  const pageWidth = useMemo(() => {
    const baseWidth = pdfUrl ? 720 : 760
    return Math.round(baseWidth * zoom)
  }, [pdfUrl, zoom])

  useEffect(() => {
    const root = viewportRef.current
    if (!root) {
      return undefined
    }

    const observer = new IntersectionObserver(
      (entries) => {
        const mostVisibleEntry = entries
          .filter((entry) => entry.isIntersecting)
          .sort((left, right) => right.intersectionRatio - left.intersectionRatio)[0]

        if (!mostVisibleEntry) {
          return
        }

        const page = Number((mostVisibleEntry.target as HTMLElement).dataset.page)
        if (!Number.isNaN(page)) {
          onPageChange(page)
        }
      },
      {
        root,
        threshold: [0.35, 0.55, 0.75],
      },
    )

    pageRefs.current.forEach((pageRef) => {
      if (pageRef) {
        observer.observe(pageRef)
      }
    })

    return () => observer.disconnect()
  }, [currentPage, onPageChange, pdfUrl, pageCount, zoom])

  useEffect(() => {
    pageRefs.current[currentPage - 1]?.scrollIntoView({ block: 'start', behavior: 'smooth' })
  }, [currentPage])

  const goToPage = (page: number) => {
    const safePage = Math.min(Math.max(page, 1), displayPageCount)
    onPageChange(safePage)
    pageRefs.current[safePage - 1]?.scrollIntoView({ block: 'start', behavior: 'smooth' })
  }

  const handlePdfLoad = ({ numPages }: { numPages: number }) => {
    setLoadedPages(numPages)
    onPageCountChange(numPages)
  }

  return (
    <section className="mindocu-pdf-stage" aria-label="Dokumentansicht">

      <div ref={viewportRef} className="mindocu-pdf-scrollarea">
        {pdfUrl ? (
          <Document
            file={pdfUrl}
            onLoadSuccess={handlePdfLoad}
            loading={<div className="mindocu-pdf-loading">PDF wird geladen ...</div>}
            error={<div className="mindocu-pdf-loading">PDF konnte nicht geladen werden.</div>}
          >
            {Array.from({ length: displayPageCount }, (_, index) => {
              const pageNumber = index + 1
              return (
                <div
                  key={pageNumber}
                  ref={(element) => {
                    pageRefs.current[index] = element
                  }}
                  data-page={pageNumber}
                  className="mindocu-pdf-pagewrap"
                >
                  <Page
                    pageNumber={pageNumber}
                    width={pageWidth}
                    renderTextLayer={false}
                    renderAnnotationLayer={false}
                  />
                </div>
              )
            })}
          </Document>
        ) : (
          <div
            ref={(element) => {
              pageRefs.current[0] = element
            }}
            data-page={1}
            className="mindocu-demo-page"
          >
            <div className="mindocu-demo-page-header">
              <div>
                <div className="mindocu-demo-page-kicker">Amtsgericht Würzburg</div>
                <div className="mindocu-demo-page-subtitle">e-Aktendeckel / Stammdatenblatt</div>
              </div>
              <div className="mindocu-demo-page-meta">Würzburg, 12.02.2026</div>
            </div>

            <div className="mindocu-demo-page-body">
              <div className="mindocu-demo-meta-grid">
                <div>
                  <div className="mindocu-demo-meta-label">Stand</div>
                  <div className="mindocu-demo-meta-value">30.09.2025</div>
                </div>
                <div>
                  <div className="mindocu-demo-meta-label">Sachgebiet</div>
                  <div className="mindocu-demo-meta-value">10 Familiensachen_AG</div>
                </div>
                <div>
                  <div className="mindocu-demo-meta-label">Eingangsdatum</div>
                  <div className="mindocu-demo-meta-value">5.02.2026</div>
                </div>
                <div>
                  <div className="mindocu-demo-meta-label">Verfahrenswert</div>
                  <div className="mindocu-demo-meta-value">-</div>
                </div>
              </div>

              <div className="mindocu-demo-paragraphs">
                {demoParagraphs.map((paragraph) => (
                  <div key={paragraph.title} className="mindocu-demo-paragraph">
                    <div className="mindocu-demo-paragraph-title">{paragraph.title}</div>
                    <div className="mindocu-demo-paragraph-content">{paragraph.content}</div>
                  </div>
                ))}
              </div>

              <div className="mindocu-demo-textblock">
                <span className="mindocu-demo-emphasis">Verfahrensbeteiligte</span>
                <div>Rechtsanwaltskanzlei Breitmoser & Kollegen</div>
                <div>Jugendamt Steglitz-Zehlendorf von Berlin</div>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="mindocu-page-controls" aria-label="Seitensteuerung">
        <div className="mindocu-page-counter">
          <div className="mindocu-page-counter-current">{currentPage}</div>
        </div>
        <div className="mindocu-page-counter-total">{displayPageCount}</div>
          <button
          type="button"
          className="mindocu-page-control"
          onClick={() => goToPage(currentPage - 1)}
          aria-label="Vorherige Seite"
        >
          <ChevronUp size={18} />
        </button>
        <button
          type="button"
          className="mindocu-page-control"
          onClick={() => goToPage(currentPage + 1)}
          aria-label="Nächste Seite"
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
}
