import type { Segment } from './InnerSidebarLeft'

export function parseSegmentRange(range: string): { start: number; end: number } {
  const trimmed = range.trim()
  const rangeMatch = trimmed.match(/^(\d+)\s*-\s*(\d+)$/)
  if (rangeMatch) {
    const start = Number.parseInt(rangeMatch[1], 10)
    const end = Number.parseInt(rangeMatch[2], 10)
    return { start: Math.min(start, end), end: Math.max(start, end) }
  }

  const singleMatch = trimmed.match(/^(\d+)$/)
  if (singleMatch) {
    const page = Number.parseInt(singleMatch[1], 10)
    return { start: page, end: page }
  }

  return { start: 1, end: 1 }
}

/** Returns the first page number from a segment range such as "3-8" or "7". */
export function parseSegmentStartPage(range: string): number {
  return parseSegmentRange(range).start
}

export function pageIsInSegmentRange(page: number, range: string): boolean {
  const { start, end } = parseSegmentRange(range)
  return page >= start && page <= end
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
  return segments.findIndex((segment) => pageIsInSegmentRange(page, segment.range))
}
