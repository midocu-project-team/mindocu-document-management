/**
 * TypeScript mirror of the backend API response contract (backend/api/schemas).
 * Field names match the JSON 1:1 (snake_case) so responses are used as-is.
 */

/** Per-document processing stage (backend ProcessingStatus enum). */
export type ProcessingStatus =
  | 'pending'
  | 'extracting'
  | 'segmenting'
  | 'enriching'
  | 'done'
  | 'failed';

/** Aggregated case status (any document in-flight => "processing"). */
export type CaseAggregateStatus = 'processing' | 'done';

export interface CaseSummary {
  id: string;
  name: string;
  created_at: string;
  status: CaseAggregateStatus;
  document_count: number;
}

export interface SegmentSummary {
  segment_id: string;
  title: string | null;
  summary: string | null;
  relevance: boolean;
  matched_keywords: string[];
  start_page: number;
  end_page: number;
}

export interface DocumentSummary {
  document_id: string;
  file_name: string;
  processing_status: ProcessingStatus;
  total_pages: number;
  segment_count: number;
}

/** One grounded reference of a segment summary (a sentence + its source blocks). */
export interface SummaryReference {
  text: string;
  block_ids: number[];
}

/** Full detail of a single segment (GET /segments/{id}) incl. references. */
export interface SegmentDetail {
  segment_id: string;
  document_id: string;
  start_page: number;
  end_page: number;
  confidence: number | null;
  title: string | null;
  summary: string | null;
  relevance: boolean;
  matched_keywords: string[];
  references: SummaryReference[];
}

/**
 * A bounding box in PDF points with a bottom-left origin: (x0, y0, x1, y1).
 * A top-left-origin consumer flips y via the page height (see BlockHighlightLayer).
 */
export type BoundingBox = [number, number, number, number];

/** One content block (GET /documents/{id}/blocks/{block_id}). */
export interface BlockOut {
  document_id: string;
  block_id: number;
  page_number: number;
  text: string;
  block_type: string;
  bbox: BoundingBox | null;
  source_ref: string | null;
}

export interface CaseDetail {
  id: string;
  name: string;
  created_at: string;
  status: CaseAggregateStatus;
  documents: DocumentSummary[];
}

export interface DocumentStatus {
  document_id: string;
  file_name: string;
  processing_status: ProcessingStatus;
  error_message: string | null;
}

export interface CaseStatus {
  case_id: string;
  status: CaseAggregateStatus;
  documents: DocumentStatus[];
}
