/** A document segment as consumed by the workspace UI (view model of the API's SegmentSummary). */
export type Segment = {
  id: string;
  title: string | null;
  summary: string | null;
  relevant: boolean;
  start_page: number;
  end_page: number;
};
