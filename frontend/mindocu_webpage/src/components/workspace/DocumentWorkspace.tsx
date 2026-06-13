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
import { toWorkspaceDocument } from './workspaceTypes'
import { useCaseDetail } from '../../api/hooks'

const NO_SEGMENTS: Segment[] = []

export function DocumentWorkspace() {
  const { caseId } = useParams<{ caseId: string }>()
  const { data: caseDetail, isLoading, isError } = useCaseDetail(caseId)

  const [leftTab, setLeftTab] = useState<'Segmente' | 'Suche'>('Segmente')
  const [rightTab, setRightTab] = useState<'Zusammenfassung' | 'Chat' | 'Chat Sessions'>('Zusammenfassung')
  const [leftSidebarOpen, setLeftSidebarOpen] = useState(true)
  const [rightSidebarOpen, setRightSidebarOpen] = useState(true)
  const [selectedSegmentIndex, setSelectedSegmentIndex] = useState(0)
  const [searchQuery, setSearchQuery] = useState('')
  const [activeTool, setActiveTool] = useState<'select' | 'pen' | 'comment'>('select')
  const [currentPage, setCurrentPage] = useState(1)
  const [pageCount, setPageCount] = useState(1)
  const [zoom, setZoom] = useState(1)
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null)
  const [showRelevantSegments, setShowRelevantSegments] = useState(true)
  const [showIrrelevantSegments, setShowIrrelevantSegments] = useState(false)
  const pdfViewportRef = useRef<PdfViewportHandle>(null)

  const workspaceDocuments = useMemo(
    () => (caseDetail?.documents ?? []).map(toWorkspaceDocument),
    [caseDetail],
  )

  const activeDocument =
    workspaceDocuments.find((document) => document.id === selectedDocumentId) ?? workspaceDocuments[0]

  const activeSegments = activeDocument?.segments ?? NO_SEGMENTS

  const activeSegment = activeSegments[selectedSegmentIndex] ?? activeSegments[0]

  const visiblePages = useMemo(
    () => getVisiblePages(activeSegments, pageCount, showRelevantSegments, showIrrelevantSegments),
    [activeSegments, pageCount, showRelevantSegments, showIrrelevantSegments],
  )

  // Seed the page count from the document metadata; react-pdf refines it on load.
  useEffect(() => {
    if (activeDocument) {
      setPageCount(activeDocument.totalPages)
    }
  }, [activeDocument])

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
    gridTemplateColumns: `${leftSidebarOpen ? '284px' : '0px'} minmax(0, 1fr) ${rightSidebarOpen ? '380px' : '0px'}`,
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
          <div className={`mindocu-grid-pane${leftSidebarOpen ? '' : ' is-collapsed'}`} aria-hidden={!leftSidebarOpen}>
            <InnerSidebarLeft
              activeTab={leftTab}
              onTabChange={setLeftTab}
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
              pageCount={pageCount}
              visiblePages={visiblePages}
              zoom={zoom}
              onPageChange={handlePageChange}
              onPageCountChange={setPageCount}
              onZoomIn={() => setZoom((value) => clampZoom(value + 0.08))}
              onZoomOut={() => setZoom((value) => clampZoom(value - 0.08))}
            />
          </main>

          <div className={`mindocu-grid-pane${rightSidebarOpen ? '' : ' is-collapsed'}`} aria-hidden={!rightSidebarOpen}>
            <InnerSidebarRight
              activeTab={rightTab}
              onTabChange={setRightTab}
              segmentTitle={activeSegment?.title ?? ''}
              summary={activeSegment?.summary ?? ''}
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
