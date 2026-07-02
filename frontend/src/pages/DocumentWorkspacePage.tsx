import { useEffect, useMemo, useRef, useState, type CSSProperties } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { AppSidebar } from '@/components/common/AppSidebar';
import { Topbar } from '@/components/workspace/Topbar';
import { InnerSidebarLeft } from '@/components/workspace/InnerSidebarLeft';
import { InnerSidebarRight } from '@/components/workspace/InnerSidebarRight';
import { WorkspaceToolbar } from '@/components/workspace/WorkspaceToolbar';
import { PdfViewport, type PdfViewportHandle } from '@/components/workspace/PdfViewport';
import { BlockReferenceBar } from '@/components/workspace/BlockReferenceBar';
import {
  findSegmentIndexForPage,
  getNearestVisiblePage,
  getVisiblePages,
  isSegmentShown,
  visibleSegmentDistance,
} from '@/utils/segmentUtils';
import {
  SEGMENT_TITLE_FALLBACK,
  toSegment,
  toWorkspaceDocument,
} from '@/utils/workspaceMappers';
import type { Segment } from '@/types/segment';
import type { BoundingBox, SummaryReference } from '@/api/types';
import { useResizableWidth } from '@/hooks/useResizableWidth';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import {
  prefetchSegmentDetail,
  useBlocks,
  useCaseDetail,
  useDocumentSegments,
  useSegmentDetail,
  useUpdateSegmentRelevance,
} from '@/api/hooks';

const NO_SEGMENTS: Segment[] = [];
const NO_REFERENCES: SummaryReference[] = [];
const NO_BLOCK_IDS: number[] = [];

const LEFT_SIDEBAR = { initial: 284, min: 220, max: 560, storageKey: 'mindocu:left-sidebar-width' };
const RIGHT_SIDEBAR = {
  initial: 380,
  min: 300,
  max: 640,
  storageKey: 'mindocu:right-sidebar-width',
};

// Below this width the sidebars stop being resizable grid columns and become
// off-canvas drawers that slide over the PDF (see workspace.css). Keep the
// value in sync with the matching @media breakpoint there.
const COMPACT_QUERY = '(max-width: 1100px)';

// Selecting a segment within this many segments of the current one smooth-scrolls
// the PDF; jumping further away snaps instantly so the viewport doesn't scroll
// through the whole document.
const SMOOTH_SCROLL_SEGMENT_DISTANCE = 2;

export function DocumentWorkspacePage() {
  const { caseId } = useParams<{ caseId: string }>();
  const { data: caseDetail, isLoading, isError } = useCaseDetail(caseId);
  const queryClient = useQueryClient();

  const isCompact = useMediaQuery(COMPACT_QUERY);

  const [rightTab, setRightTab] = useState<'Zusammenfassung' | 'Chat' | 'Chat Sessions'>(
    'Zusammenfassung',
  );
  // Start closed in the compact (drawer) layout so a drawer never covers the
  // PDF on first paint; start open on desktop.
  const [leftSidebarOpen, setLeftSidebarOpen] = useState(!isCompact);
  const [rightSidebarOpen, setRightSidebarOpen] = useState(!isCompact);
  const [selectedSegmentIndex, setSelectedSegmentIndex] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTool, setActiveTool] = useState<'select' | 'pen' | 'comment'>('select');
  const [currentPage, setCurrentPage] = useState(1);
  const [reportedPageCount, setReportedPageCount] = useState<number | null>(null);
  const [zoom, setZoom] = useState(1);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const [showRelevantSegments, setShowRelevantSegments] = useState(true);
  const [showIrrelevantSegments, setShowIrrelevantSegments] = useState(false);
  // Which reference (index into the segment's references) the user clicked, and
  // which of its hits is active. `null` => the reference bar is closed.
  const [activeReferenceIndex, setActiveReferenceIndex] = useState<number | null>(null);
  const [activeHitIndex, setActiveHitIndex] = useState(0);
  const pdfViewportRef = useRef<PdfViewportHandle>(null);

  const leftResize = useResizableWidth(LEFT_SIDEBAR.initial, { ...LEFT_SIDEBAR, edge: 'left' });
  const rightResize = useResizableWidth(RIGHT_SIDEBAR.initial, { ...RIGHT_SIDEBAR, edge: 'right' });

  // Crossing the compact breakpoint at runtime re-resets the sidebars (closed
  // in the drawer layout, open on desktop). Done during render via a
  // previous-value guard rather than an effect, so it applies before paint
  // without a cascading re-render.
  const [wasCompact, setWasCompact] = useState(isCompact);
  if (wasCompact !== isCompact) {
    setWasCompact(isCompact);
    setLeftSidebarOpen(!isCompact);
    setRightSidebarOpen(!isCompact);
  }

  const workspaceDocuments = useMemo(
    () => (caseDetail?.documents ?? []).map(toWorkspaceDocument),
    [caseDetail],
  );

  const activeDocument =
    workspaceDocuments.find((document) => document.id === selectedDocumentId) ??
    workspaceDocuments[0];

  // Segments are fetched per document now (not embedded in the case detail).
  const { data: segmentSummaries } = useDocumentSegments(activeDocument?.id);
  const activeSegments = useMemo(
    () => (segmentSummaries ? segmentSummaries.map(toSegment) : NO_SEGMENTS),
    [segmentSummaries],
  );

  const activeSegment = activeSegments[selectedSegmentIndex] ?? activeSegments[0];

  // The active segment's detail (references/block_ids) is loaded on selection;
  // title/summary already come from the summary list above.
  const { data: segmentDetail } = useSegmentDetail(activeSegment?.id);
  const references = segmentDetail?.references ?? NO_REFERENCES;

  // The clicked reference's block_ids (drives the hit bar); `null` => bar closed.
  const activeReferenceBlockIds =
    activeReferenceIndex != null ? (references[activeReferenceIndex]?.block_ids ?? null) : null;

  // Reference "hits": the source blocks of the clicked reference, loaded reactively
  // (one slot per block_id, `undefined` while loading). The active hit drives the
  // page jump + the strong highlight; `activeReferenceBlockIds === null` => closed.
  const referenceHits = useBlocks(activeDocument?.id, activeReferenceBlockIds ?? NO_BLOCK_IDS);
  const activeHit = referenceHits[activeHitIndex];
  const activeHitPage = activeHit?.page_number;
  const highlight = activeHit?.bbox
    ? { pageNumber: activeHit.page_number, bbox: activeHit.bbox }
    : null;

  // Faint dashed pre-marks for the other blocks of the *clicked* reference (all
  // of its block_ids except the active hit, which gets the strong highlight on
  // top), so every spot that reference points to is visible while stepping.
  const markers = useMemo(() => {
    const list: { pageNumber: number; bbox: BoundingBox; blockId: number }[] = [];
    referenceHits.forEach((block) => {
      if (block && block.bbox && block.block_id !== activeHit?.block_id) {
        list.push({ pageNumber: block.page_number, bbox: block.bbox, blockId: block.block_id });
      }
    });
    return list;
  }, [referenceHits, activeHit?.block_id]);

  // Scroll the PDF to the active hit's page -- both when the user steps through
  // hits and when the active block finishes loading (page becomes known).
  useEffect(() => {
    if (activeHitPage) {
      pdfViewportRef.current?.goToPage(activeHitPage);
    }
  }, [activeHitPage, activeHitIndex]);

  // Manual relevance override for the currently selected segment (kebab menu in
  // the left toolbar). Two-way toggle; the mutation refreshes the segment list
  // so the card's relevance styling + the relevant/irrelevant filters update.
  const updateRelevance = useUpdateSegmentRelevance(activeDocument?.id);
  const handleToggleActiveSegmentRelevance = () => {
    if (!activeSegment) {
      return;
    }
    updateRelevance.mutate({ segmentId: activeSegment.id, relevance: !activeSegment.relevant });
  };

  // The PDF's reported count wins once loaded; until then fall back to the
  // document metadata so the visible-page list isn't briefly clamped.
  const pageCount = reportedPageCount ?? activeDocument?.totalPages ?? 1;

  const visiblePages = useMemo(
    () =>
      getVisiblePages(
        activeSegments,
        pageCount,
        showRelevantSegments,
        showIrrelevantSegments,
        searchQuery,
      ),
    [activeSegments, pageCount, showRelevantSegments, showIrrelevantSegments, searchQuery],
  );

  useEffect(() => {
    if (visiblePages.length === 0) {
      return;
    }

    setCurrentPage((page) => {
      if (visiblePages.includes(page)) {
        return page;
      }

      const nearestPage = getNearestVisiblePage(page, visiblePages);
      pdfViewportRef.current?.goToPage(nearestPage);
      return nearestPage;
    });
  }, [visiblePages]);

  const handlePageChange = (page: number) => {
    setCurrentPage(page);

    const segmentIndex = findSegmentIndexForPage(activeSegments, page);
    if (segmentIndex >= 0) {
      setSelectedSegmentIndex(segmentIndex);
    }
  };

  const handleSelectDocument = (documentId: string) => {
    setSelectedDocumentId(documentId);
    setReportedPageCount(null);
    setCurrentPage(1);
    setSelectedSegmentIndex(0);
    setSearchQuery('');
    setActiveReferenceIndex(null);
  };

  const handleSelectSegment = (index: number) => {
    // Distance is measured across the *visible* (filtered) segments, not absolute
    // indices: with irrelevant segments hidden, two cards adjacent in the sidebar
    // must smooth-scroll even when many hidden segments separate them underneath.
    const distance = visibleSegmentDistance(
      activeSegments,
      selectedSegmentIndex,
      index,
      showRelevantSegments,
      showIrrelevantSegments,
      searchQuery,
    );
    setSelectedSegmentIndex(index);
    // Switching segment changes the right-sidebar references, so close any open
    // hit bar from the previous segment's reference.
    setActiveReferenceIndex(null);

    const segment = activeSegments[index];
    if (!segment) {
      return;
    }

    const behavior: ScrollBehavior = distance <= SMOOTH_SCROLL_SEGMENT_DISTANCE ? 'smooth' : 'auto';
    pdfViewportRef.current?.goToPage(segment.start_page, behavior);
  };

  // Prefetch the detail of the ±2 visible neighbors so switching to an adjacent
  // segment card is instant (cache hit). Visibility uses the same filter as the
  // left sidebar, so hidden segments never count as neighbors.
  useEffect(() => {
    const visibleIndices = activeSegments
      .map((_, index) => index)
      .filter((index) =>
        isSegmentShown(
          activeSegments[index],
          showRelevantSegments,
          showIrrelevantSegments,
          searchQuery,
        ),
      );
    const position = visibleIndices.indexOf(selectedSegmentIndex);
    if (position < 0) {
      return;
    }
    [position - 2, position - 1, position + 1, position + 2]
      .filter((neighbor) => neighbor >= 0 && neighbor < visibleIndices.length)
      .map((neighbor) => activeSegments[visibleIndices[neighbor]])
      .forEach((segment) => {
        if (segment) {
          prefetchSegmentDetail(queryClient, segment.id);
        }
      });
  }, [
    activeSegments,
    selectedSegmentIndex,
    showRelevantSegments,
    showIrrelevantSegments,
    searchQuery,
    queryClient,
  ]);

  // Clicking a reference sentence opens the hit bar over the PDF: it loads the
  // reference's source blocks and jumps to / highlights the first one. The
  // clicked reference stays underlined (via activeReferenceIndex) until closed.
  const handleReferenceClick = (index: number) => {
    setActiveReferenceIndex(index);
    setActiveHitIndex(0);
  };

  const handlePrevHit = () => setActiveHitIndex((index) => Math.max(0, index - 1));
  const handleNextHit = () =>
    setActiveHitIndex((index) => Math.min(referenceHits.length - 1, index + 1));
  const handleCloseReferenceBar = () => setActiveReferenceIndex(null);

  const clampZoom = (value: number) => Math.min(2, Math.max(0.5, value));

  // The sidebar widths are exposed as CSS custom properties (not a direct
  // grid-template-columns) so the @media(compact) rules in workspace.css can
  // override the template wholesale — an inline grid-template-columns would
  // win over any media query and defeat the drawer layout. On desktop a closed
  // sidebar collapses its track to 0; in compact mode the panes leave the flow
  // entirely (absolute drawers), so the track width no longer matters.
  const workspaceGridStyle = {
    '--mindocu-left-w': leftSidebarOpen ? `${leftResize.width}px` : '0px',
    '--mindocu-right-w': rightSidebarOpen ? `${rightResize.width}px` : '0px',
  } as CSSProperties;

  const closeSidebars = () => {
    setLeftSidebarOpen(false);
    setRightSidebarOpen(false);
  };

  const toggleShowRelevant = () => {
    setShowRelevantSegments((current) => {
      if (current && !showIrrelevantSegments) {
        return true;
      }
      return !current;
    });
  };

  const toggleShowIrrelevant = () => {
    setShowIrrelevantSegments((current) => {
      if (current && !showRelevantSegments) {
        return true;
      }
      return !current;
    });
  };

  if (isLoading) {
    return <WorkspaceStatus message="Akte wird geladen …" />;
  }

  if (isError || !caseDetail) {
    return <WorkspaceStatus message="Akte konnte nicht geladen werden." />;
  }

  if (!activeDocument) {
    return <WorkspaceStatus message="Diese Akte enthält keine Dokumente." />;
  }

  return (
    <div className="mindocu-app-shell">
      <AppSidebar />

      <div className="mindocu-app-main">
        <Topbar
          title={caseDetail.name}
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
            <div
              className="mindocu-workspace-backdrop"
              onClick={closeSidebars}
              aria-hidden="true"
            />
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
              activeSegment={activeSegment}
              onToggleActiveSegmentRelevance={handleToggleActiveSegmentRelevance}
              isRelevanceUpdating={updateRelevance.isPending}
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

            <BlockReferenceBar
              hits={referenceHits}
              activeIndex={activeHitIndex}
              onPrev={handlePrevHit}
              onNext={handleNextHit}
              onClose={handleCloseReferenceBar}
            />

            <PdfViewport
              ref={pdfViewportRef}
              key={activeDocument.id}
              pdfUrl={activeDocument.pdfUrl}
              currentPage={currentPage}
              visiblePages={visiblePages}
              totalPages={pageCount}
              zoom={zoom}
              onPageChange={handlePageChange}
              onPageCountChange={setReportedPageCount}
              onZoomIn={() => setZoom((value) => clampZoom(value + 0.08))}
              onZoomOut={() => setZoom((value) => clampZoom(value - 0.08))}
              highlight={highlight}
              markers={markers}
            />
          </main>

          <div
            className={`mindocu-grid-pane mindocu-grid-pane--right${rightSidebarOpen ? '' : ' is-collapsed'}`}
            aria-hidden={!rightSidebarOpen}
          >
            <InnerSidebarRight
              activeTab={rightTab}
              onTabChange={setRightTab}
              segmentTitle={activeSegment ? (activeSegment.title ?? SEGMENT_TITLE_FALLBACK) : ''}
              references={references}
              onReferenceClick={handleReferenceClick}
              activeReferenceIndex={activeReferenceIndex}
            />
          </div>
        </div>
      </div>
    </div>
  );
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
  );
}
