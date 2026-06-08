import { useMemo, useState } from 'react'
import { WorkspaceSidebar } from './WorkspaceSidebar'
import { Topbar } from './Topbar'
import { InnerSidebarLeft, type Segment } from './InnerSidebarLeft'
import { InnerSidebarRight } from './InnerSidebarRight'
import { WorkspaceToolbar } from './WorkspaceToolbar'
import { PdfViewport } from './PdfViewport'

type WorkspaceProps = {
  pdfUrl?: string | null
}

const demoSegments: Segment[] = [
  { title: 'Aktendeckel', date: '12.02.2026', range: '1' },
  { title: 'Antrag auf Umgangsänderung', date: '07.03.2026', range: '3-8' },
  { title: 'Polizeibericht', date: '14.03.2026', range: '10-15' },
  { title: 'Pflegebericht', date: '08.05.2026', range: '17-28' },
]

const demoSummary =
  'Dem Aktendeckel des Amtsgerichts Würzburg vom 12.02.2026 entnehmen wir, dass es um eine familienrechtliche Auseinandersetzung mit mehreren Beteiligten geht. Die Verfahrensstruktur ist bereits vorgegeben und eignet sich gut für eine segmentierte Dokumentansicht mit Zusammenfassung, Chat und Folgefragen.'

export function DocumentWorkspace({ pdfUrl }: WorkspaceProps) {
  const [leftTab, setLeftTab] = useState<'Segmente' | 'Suche'>('Segmente')
  const [rightTab, setRightTab] = useState<'Zusammenfassung' | 'Chat' | 'Chat Sessions'>('Zusammenfassung')
  const [leftSidebarOpen, setLeftSidebarOpen] = useState(true)
  const [rightSidebarOpen, setRightSidebarOpen] = useState(true)
  const [selectedSegmentIndex, setSelectedSegmentIndex] = useState(0)
  const [searchQuery, setSearchQuery] = useState('')
  const [activeTool, setActiveTool] = useState<'select' | 'pen' | 'comment' | 'erase'>('select')
  const [currentPage, setCurrentPage] = useState(1)
  const [pageCount, setPageCount] = useState(23)
  const [zoom, setZoom] = useState(1)

  const filteredSegments = useMemo(() => {
    const query = searchQuery.trim().toLowerCase()
    if (!query) {
      return demoSegments
    }

    return demoSegments.filter((segment) => {
      const haystack = `${segment.title} ${segment.date} ${segment.range}`.toLowerCase()
      return haystack.includes(query)
    })
  }, [searchQuery])

  const clampZoom = (value: number) => Math.min(1.5, Math.max(0.72, value))

  const workspaceGridStyle = {
    gridTemplateColumns: `${leftSidebarOpen ? '284px' : '0px'} minmax(0, 1fr) ${rightSidebarOpen ? '380px' : '0px'}`,
  } as const

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
              segments={filteredSegments}
              selectedSegmentIndex={selectedSegmentIndex}
              onSelectSegment={setSelectedSegmentIndex}
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
                documentLabel="Hauptakte"
                currentPage={currentPage}
                pageCount={pageCount}
                zoom={zoom}
                onZoomOut={() => setZoom((value) => clampZoom(value - 0.08))}
                onZoomIn={() => setZoom((value) => clampZoom(value + 0.08))}
                onFitToPage={() => setZoom(0.92)}
              />
            </div>

            <PdfViewport
              pdfUrl={pdfUrl}
              currentPage={currentPage}
              pageCount={pageCount}
              zoom={zoom}
              onPageChange={setCurrentPage}
              onPageCountChange={setPageCount}
              onZoomIn={() => setZoom((value) => clampZoom(value + 0.08))}
              onZoomOut={() => setZoom((value) => clampZoom(value - 0.08))}
              onFitToPage={() => setZoom(0.92)}
            />
          </main>

          <div className={`mindocu-grid-pane${rightSidebarOpen ? '' : ' is-collapsed'}`} aria-hidden={!rightSidebarOpen}>
            <InnerSidebarRight activeTab={rightTab} onTabChange={setRightTab} summary={demoSummary} />
          </div>
        </div>
      </div>
    </div>
  )
}
