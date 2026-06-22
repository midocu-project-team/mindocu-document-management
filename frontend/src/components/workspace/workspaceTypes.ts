import { pdfUrl } from '../../api/client';
import type { DocumentSummary, SegmentSummary } from '../../api/types';
import type { Segment } from './InnerSidebarLeft';

/** One PDF of a case as consumed by the workspace UI. */
export type WorkspaceDocument = {
  id: string;
  label: string;
  pdfUrl: string;
  totalPages: number;
  segments: Segment[];
};

/**
 * Display fallbacks for segments the enrichment stage left without title/summary.
 * These are a *view* concern only — the model keeps `null` (see `Segment`), so the
 * absence of a title is distinguishable from a segment literally named "Ohne Titel".
 */
export const SEGMENT_TITLE_FALLBACK = 'Ohne Titel';
export const SEGMENT_SUMMARY_FALLBACK = 'Keine Zusammenfassung verfügbar.';

/** Map an API segment summary to the workspace view model (1:1 page numbers). */
export function toSegment(summary: SegmentSummary): Segment {
  return {
    id: summary.segment_id,
    title: summary.title,
    summary: summary.summary,
    relevant: summary.relevance,
    start_page: summary.start_page,
    end_page: summary.end_page,
  };
}

/** Map an API document summary to a workspace document (PDF served by the API). */
export function toWorkspaceDocument(document: DocumentSummary): WorkspaceDocument {
  return {
    id: document.document_id,
    label: document.file_name,
    pdfUrl: pdfUrl(document.document_id),
    totalPages: document.total_pages,
    segments: document.segments.map(toSegment),
  };
}
