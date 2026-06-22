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
  segments: SegmentSummary[];
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
