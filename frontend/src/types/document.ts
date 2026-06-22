import type { Segment } from './segment';

/** One PDF of a case as consumed by the workspace UI. */
export type WorkspaceDocument = {
  id: string;
  label: string;
  pdfUrl: string;
  totalPages: number;
  segments: Segment[];
};
