import { useEffect, useMemo, useRef, useState, type CSSProperties } from 'react'
import { useParams } from 'react-router-dom'
import { WorkspaceSidebar } from './WorkspaceSidebar'
import { Topbar } from './Topbar'
import { InnerSidebarLeft, type Segment } from './InnerSidebarLeft'
import { InnerSidebarRight } from './InnerSidebarRight'
import { WorkspaceToolbar } from './WorkspaceToolbar'
import { PdfViewport, type PdfViewportHandle } from './PdfViewport'
import {
  findSegmentIndexForPage,
  getNearestVisiblePage,
  getVisiblePages,
} from './segmentUtils'
import { SEGMENT_SUMMARY_FALLBACK, SEGMENT_TITLE_FALLBACK, toWorkspaceDocument } from './workspaceTypes'
import { useResizableWidth } from './useResizableWidth'
import { useMediaQuery } from './useMediaQuery'
import { useCaseDetail } from '../../api/hooks'

const NO_SEGMENTS: Segment[] = []

const LEFT_SIDEBAR = { initial: 284, min: 220, max: 560, storageKey: 'mindocu:left-sidebar-width' }
const RIGHT_SIDEBAR = { initial: 380, min: 300, max: 640, storageKey: 'mindocu:right-sidebar-width' }

// Below this width the sidebars stop being resizable grid columns and become
// off-canvas drawers that slide over the PDF (see workspace.css). Keep the
// value in sync with the matching @media breakpoint there.
const COMPACT_QUERY = '(max-width: 1100px)'

export function DocumentWorkspace() {
  const { caseId } = useParams<{ caseId: string }>()
  const { data: caseDetail, isLoading, isError } = useCaseDetail(caseId)

  const isCompact = useMediaQuery(COMPACT_QUERY)

  const [rightTab, setRightTab] = useState<'Zusammenfassung' | 'Chat' | 'Chat Sessions'>('Zusammenfassung')
  // Start closed in the compact (drawer) layout so a drawer never covers the
  // PDF on first paint; start open on desktop.
  const [leftSidebarOpen, setLeftSidebarOpen] = useState(!isCompact)
  const [rightSidebarOpen, setRightSidebarOpen] = useState(!isCompact)
  const [selectedSegmentIndex, setSelectedSegmentIndex] = useState(0)
  const [searchQuery, setSearchQuery] = useState('')
  const [activeTool, setActiveTool] = useState<'select' | 'pen' | 'comment'>('select')
  const [currentPage, setCurrentPage] = useState(1)
  const [reportedPageCount, setReportedPageCount] = useState<number | null>(null)
  const [zoom, setZoom] = useState(1)
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null)
  const [showRelevantSegments, setShowRelevantSegments] = useState(true)
  const [showIrrelevantSegments, setShowIrrelevantSegments] = useState(false)
  const pdfViewportRef = useRef<PdfViewportHandle>(null)

  const leftResize = useResizableWidth(LEFT_SIDEBAR.initial, { ...LEFT_SIDEBAR, edge: 'left' })
  const rightResize = useResizableWidth(RIGHT_SIDEBAR.initial, { ...RIGHT_SIDEBAR, edge: 'right' })

  // Crossing the compact breakpoint at runtime re-resets the sidebars (closed
  // in the drawer layout, open on desktop). Done during render via a
  // previous-value guard rather than an effect, so it applies before paint
  // without a cascading re-render.
  const [wasCompact, setWasCompact] = useState(isCompact)
  if (wasCompact !== isCompact) {
    setWasCompact(isCompact)
    setLeftSidebarOpen(!isCompact)
    setRightSidebarOpen(!isCompact)
  }

  const workspaceDocuments = useMemo(
    () => (caseDetail?.documents ?? []).map(toWorkspaceDocument),
    [caseDetail],
  )

  const activeDocument =
    workspaceDocuments.find((document) => document.id === selectedDocumentId) ?? workspaceDocuments[0]

  const activeSegments = activeDocument?.segments ?? NO_SEGMENTS

  const activeSegment = activeSegments[selectedSegmentIndex] ?? activeSegments[0]

  // The PDF's reported count wins once loaded; until then fall back to the
  // document metadata so the visible-page list isn't briefly clamped.
  const pageCount = reportedPageCount ?? activeDocument?.totalPages ?? 1

  const visiblePages = useMemo(
    () => getVisiblePages(activeSegments, pageCount, showRelevantSegments, showIrrelevantSegments, searchQuery),
    [activeSegments, pageCount, showRelevantSegments, showIrrelevantSegments, searchQuery],
  )

  useEffect(() => {
    if (visiblePages.length === 0) {
      return
    }

    setCurrentPage((page) => {
      if (visiblePages.includes(page)) {
        return page
      }

      const nearestPage = getNearestVisiblePage(page, visiblePages)
      pdfViewportRef.current?.goToPage(nearestPage)
      return nearestPage
    })
  }, [visiblePages])

  const handlePageChange = (page: number) => {
    setCurrentPage(page)

    const segmentIndex = findSegmentIndexForPage(activeSegments, page)
    if (segmentIndex >= 0) {
      setSelectedSegmentIndex(segmentIndex)
    }
  }

  const handleSelectDocument = (documentId: string) => {
    setSelectedDocumentId(documentId)
    setReportedPageCount(null)
    setCurrentPage(1)
    setSelectedSegmentIndex(0)
    setSearchQuery('')
  }

  const handleSelectSegment = (index: number) => {
    setSelectedSegmentIndex(index)

    const segment = activeSegments[index]
    if (!segment) {
      return
    }

    pdfViewportRef.current?.goToPage(segment.start_page)
  }

  const clampZoom = (value: number) => Math.min(2, Math.max(0.5, value))

  // The sidebar widths are exposed as CSS custom properties (not a direct
  // grid-template-columns) so the @media(compact) rules in workspace.css can
  // override the template wholesale — an inline grid-template-columns would
  // win over any media query and defeat the drawer layout. On desktop a closed
  // sidebar collapses its track to 0; in compact mode the panes leave the flow
  // entirely (absolute drawers), so the track width no longer matters.
  const workspaceGridStyle = {
    '--mindocu-left-w': leftSidebarOpen ? `${leftResize.width}px` : '0px',
    '--mindocu-right-w': rightSidebarOpen ? `${rightResize.width}px` : '0px',
  } as CSSProperties

  const closeSidebars = () => {
    setLeftSidebarOpen(false)
    setRightSidebarOpen(false)
  }

  const toggleShowRelevant = () => {
    setShowRelevantSegments((current) => {
      if (current && !showIrrelevantSegments) {
        return true
      }
      return !current
    })
  }

  const toggleShowIrrelevant = () => {
    setShowIrrelevantSegments((current) => {
      if (current && !showRelevantSegments) {
        return true
      }
      return !current
    })
  }

  if (isLoading) {
    return <WorkspaceStatus message="Akte wird geladen …" />
  }

  if (isError || !caseDetail) {
    return <WorkspaceStatus message="Akte konnte nicht geladen werden." />
  }

  if (!activeDocument) {
    return <WorkspaceStatus message="Diese Akte enthält keine Dokumente." />
  }

  return (
    <div className="mindocu-app-shell">
      <WorkspaceSidebar />

      <div className="mindocu-app-main">
        <Topbar
          title="pdf-viewer"
          leftSidebarOpen={leftSidebarOpen}
          rightSidebarOpen={rightSidebarOpen}
          onToggleLeftSidebar={() => setLeftSidebarOpen((value) => !value)}
          onToggleRightSidebar={() => setRightSidebarOpen((value) => !value)}
        />

        <div className="mindocu-workspace-grid" style={workspaceGridStyle}>
          {leftSidebarOpen && !isCompact ? (
            <div
              className={`mindocu-resize-handle mindocu-resize-handle--left${leftResize.isDragging ? ' is-dragging' : ''}`}
              style={{ left: leftResize.width }}
              onPointerDown={leftResize.onPointerDown}
              onKeyDown={leftResize.onKeyDown}
              onDoubleClick={leftResize.reset}
              role="separator"
              aria-orientation="vertical"
              aria-label="Linke Seitenleiste verbreitern oder verschmälern"
              tabIndex={0}
            />
          ) : null}

          {rightSidebarOpen && !isCompact ? (
            <div
              className={`mindocu-resize-handle mindocu-resize-handle--right${rightResize.isDragging ? ' is-dragging' : ''}`}
              style={{ right: rightResize.width }}
              onPointerDown={rightResize.onPointerDown}
              onKeyDown={rightResize.onKeyDown}
              onDoubleClick={rightResize.reset}
              role="separator"
              aria-orientation="vertical"
              aria-label="Rechte Seitenleiste verbreitern oder verschmälern"
              tabIndex={0}
            />
          ) : null}

          {isCompact && (leftSidebarOpen || rightSidebarOpen) ? (
            <div className="mindocu-workspace-backdrop" onClick={closeSidebars} aria-hidden="true" />
          ) : null}

          <div
            className={`mindocu-grid-pane mindocu-grid-pane--left${leftSidebarOpen ? '' : ' is-collapsed'}`}
            aria-hidden={!leftSidebarOpen}
          >
            <InnerSidebarLeft
              segments={activeSegments}
              selectedSegmentIndex={selectedSegmentIndex}
              onSelectSegment={handleSelectSegment}
              showRelevantSegments={showRelevantSegments}
              showIrrelevantSegments={showIrrelevantSegments}
              onToggleShowRelevantSegments={toggleShowRelevant}
              onToggleShowIrrelevantSegments={toggleShowIrrelevant}
              query={searchQuery}
              onQueryChange={setSearchQuery}
              onClearQuery={() => setSearchQuery('')}
            />
          </div>

          <main className="mindocu-center-column">
            <div className="mindocu-center-toolbarrow">
              <WorkspaceToolbar
                activeTool={activeTool}
                onToolChange={setActiveTool}
                documents={workspaceDocuments}
                selectedDocumentId={activeDocument.id}
                onSelectDocument={handleSelectDocument}
                currentPage={currentPage}
                pageCount={pageCount}
                zoom={zoom}
                onZoomOut={() => setZoom((value) => clampZoom(value - 0.08))}
                onZoomIn={() => setZoom((value) => clampZoom(value + 0.08))}
              />
            </div>

            <PdfViewport
              ref={pdfViewportRef}
              key={activeDocument.id}
              pdfUrl={activeDocument.pdfUrl}
              currentPage={currentPage}
              visiblePages={visiblePages}
              zoom={zoom}
              onPageChange={handlePageChange}
              onPageCountChange={setReportedPageCount}
              onZoomIn={() => setZoom((value) => clampZoom(value + 0.08))}
              onZoomOut={() => setZoom((value) => clampZoom(value - 0.08))}
            />
          </main>

          <div
            className={`mindocu-grid-pane mindocu-grid-pane--right${rightSidebarOpen ? '' : ' is-collapsed'}`}
            aria-hidden={!rightSidebarOpen}
          >
            <InnerSidebarRight
              activeTab={rightTab}
              onTabChange={setRightTab}
              segmentTitle={activeSegment ? activeSegment.title ?? SEGMENT_TITLE_FALLBACK : ''}
              summary={activeSegment ? activeSegment.summary ?? SEGMENT_SUMMARY_FALLBACK : ''}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

function WorkspaceStatus({ message }: { message: string }) {
  return (
    <div className="mindocu-app-shell">
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: '100%',
          height: '100vh',
        }}
      >
        {message}
      </div>
    </div>
  )
}
