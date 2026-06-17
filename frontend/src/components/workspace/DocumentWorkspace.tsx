import { useEffect, useMemo, useRef, useState } from 'react'
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
import { useCaseDetail } from '../../api/hooks'

const NO_SEGMENTS: Segment[] = []

const LEFT_SIDEBAR = { initial: 284, min: 220, max: 560, storageKey: 'mindocu:left-sidebar-width' }
const RIGHT_SIDEBAR = { initial: 380, min: 300, max: 640, storageKey: 'mindocu:right-sidebar-width' }

export function DocumentWorkspace() {
  const { caseId } = useParams<{ caseId: string }>()
  const { data: caseDetail, isLoading, isError } = useCaseDetail(caseId)

  const [rightTab, setRightTab] = useState<'Zusammenfassung' | 'Chat' | 'Chat Sessions'>('Zusammenfassung')
  const [leftSidebarOpen, setLeftSidebarOpen] = useState(true)
  const [rightSidebarOpen, setRightSidebarOpen] = useState(true)
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

  const workspaceGridStyle = {
    gridTemplateColumns: `${leftSidebarOpen ? `${leftResize.width}px` : '0px'} minmax(0, 1fr) ${
      rightSidebarOpen ? `${rightResize.width}px` : '0px'
    }`,
  } as const

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
          {leftSidebarOpen ? (
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

          {rightSidebarOpen ? (
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

          <div className={`mindocu-grid-pane${leftSidebarOpen ? '' : ' is-collapsed'}`} aria-hidden={!leftSidebarOpen}>
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

          <div className={`mindocu-grid-pane${rightSidebarOpen ? '' : ' is-collapsed'}`} aria-hidden={!rightSidebarOpen}>
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
