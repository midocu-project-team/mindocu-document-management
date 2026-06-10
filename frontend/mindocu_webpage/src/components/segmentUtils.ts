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

export function findSegmentIndexForPage(segments: Segment[], page: number): number {
  return segments.findIndex((segment) => pageIsInSegmentRange(page, segment.range))
}
