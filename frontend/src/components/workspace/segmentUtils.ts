import type { Segment } from './InnerSidebarLeft'

/** Human-readable page range such as "7" or "3-8". */
export function formatPageRange(startPage: number, endPage: number): string {
  return startPage === endPage ? `${startPage}` : `${startPage}-${endPage}`
}

export function pageIsInSegmentRange(page: number, segment: Segment): boolean {
  return page >= segment.start_page && page <= segment.end_page
}

export function isSegmentVisible(
  segment: Segment,
  showRelevantSegments: boolean,
  showIrrelevantSegments: boolean,
): boolean {
  if (segment.relevant) {
    return showRelevantSegments
  }

  return showIrrelevantSegments
}

/** Case-insensitive substring match against the segment's title, summary and page range. */
export function segmentMatchesQuery(segment: Segment, query: string): boolean {
  const needle = query.trim().toLowerCase()
  if (!needle) {
    return true
  }

  const pageRange = formatPageRange(segment.start_page, segment.end_page)
  const haystack = `${segment.title ?? ''} ${segment.summary ?? ''} ${pageRange}`.toLowerCase()
  return haystack.includes(needle)
}

/** A segment is shown when it passes both the relevance toggles and the search query. */
export function isSegmentShown(
  segment: Segment,
  showRelevantSegments: boolean,
  showIrrelevantSegments: boolean,
  query: string,
): boolean {
  return (
    isSegmentVisible(segment, showRelevantSegments, showIrrelevantSegments) &&
    segmentMatchesQuery(segment, query)
  )
}

export function getVisiblePages(
  segments: Segment[],
  pageCount: number,
  showRelevantSegments: boolean,
  showIrrelevantSegments: boolean,
  query = '',
): number[] {
  if (pageCount <= 0) {
    return []
  }

  // During an active search only matching segments' pages stay visible, so
  // segment-less "orphan" pages are hidden; without a query they stay visible.
  const hasQuery = query.trim().length > 0
  const visiblePages: number[] = []

  for (let page = 1; page <= pageCount; page += 1) {
    const segmentIndex = findSegmentIndexForPage(segments, page)
    if (segmentIndex < 0) {
      if (!hasQuery) {
        visiblePages.push(page)
      }
      continue
    }

    const segment = segments[segmentIndex]
    if (isSegmentShown(segment, showRelevantSegments, showIrrelevantSegments, query)) {
      visiblePages.push(page)
    }
  }

  return visiblePages
}

export function getNearestVisiblePage(currentPage: number, visiblePages: number[]): number {
  if (visiblePages.length === 0) {
    return 1
  }

  if (visiblePages.includes(currentPage)) {
    return currentPage
  }

  const nextPage = visiblePages.find((page) => page >= currentPage)
  return nextPage ?? visiblePages[visiblePages.length - 1]
}

export function getNextVisiblePage(currentPage: number, visiblePages: number[]): number | null {
  const currentIndex = visiblePages.indexOf(currentPage)
  if (currentIndex < 0) {
    return visiblePages.find((page) => page > currentPage) ?? visiblePages[0] ?? null
  }

  return visiblePages[currentIndex + 1] ?? null
}

export function getPreviousVisiblePage(currentPage: number, visiblePages: number[]): number | null {
  const currentIndex = visiblePages.indexOf(currentPage)
  if (currentIndex < 0) {
    const previousPages = visiblePages.filter((page) => page < currentPage)
    return previousPages[previousPages.length - 1] ?? null
  }

  return visiblePages[currentIndex - 1] ?? null
}

export function findSegmentIndexForPage(segments: Segment[], page: number): number {
  return segments.findIndex((segment) => pageIsInSegmentRange(page, segment))
}
