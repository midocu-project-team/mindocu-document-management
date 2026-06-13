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

export function getVisiblePages(
  segments: Segment[],
  pageCount: number,
  showRelevantSegments: boolean,
  showIrrelevantSegments: boolean,
): number[] {
  if (pageCount <= 0) {
    return []
  }

  const visiblePages: number[] = []

  for (let page = 1; page <= pageCount; page += 1) {
    const segmentIndex = findSegmentIndexForPage(segments, page)
    if (segmentIndex < 0) {
      visiblePages.push(page)
      continue
    }

    const segment = segments[segmentIndex]
    if (isSegmentVisible(segment, showRelevantSegments, showIrrelevantSegments)) {
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
