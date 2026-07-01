/**
 * TanStack Query hooks over the backend API — the replacement for the old
 * local CasesContext. Polling lists/status use a 10s refetch interval.
 */

import { useMutation, useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query';

import { del, getJson, patchJson, postForm, postJson } from './client';
import type {
  BlockOut,
  CaseDetail,
  CaseStatus,
  CaseSummary,
  DocumentStatus,
  SegmentDetail,
  SegmentSummary,
} from './types';

const POLL_INTERVAL_MS = 10_000;

// Segment/block detail barely changes once processed, so keep it fresh for a
// while: this makes prefetched neighbors a real cache hit on click (no refetch).
const DETAIL_STALE_MS = 5 * 60_000;

export const caseKeys = {
  all: ['cases'] as const,
  detail: (caseId: string) => ['cases', caseId, 'detail'] as const,
  status: (caseId: string) => ['cases', caseId, 'status'] as const,
};

export const documentKeys = {
  segments: (documentId: string) => ['documents', documentId, 'segments'] as const,
  block: (documentId: string, blockId: number) =>
    ['documents', documentId, 'blocks', blockId] as const,
};

export const segmentKeys = {
  detail: (segmentId: string) => ['segments', segmentId, 'detail'] as const,
};

// Shared fetchers so the hooks and the prefetch/imperative helpers below hit the
// exact same query key + fetcher (no drift between fetch and prefetch).
const fetchDocumentSegments = (documentId: string) =>
  getJson<SegmentSummary[]>(`/documents/${documentId}/segments`);

const fetchSegmentDetail = (segmentId: string) =>
  getJson<SegmentDetail>(`/segments/${segmentId}`);

const fetchBlockById = (documentId: string, blockId: number) =>
  getJson<BlockOut>(`/documents/${documentId}/blocks/${blockId}`);

/** All cases, polled every 10s (homepage list). */
export function useCases() {
  return useQuery({
    queryKey: caseKeys.all,
    queryFn: () => getJson<CaseSummary[]>('/cases'),
    refetchInterval: POLL_INTERVAL_MS,
  });
}

/** Full case detail incl. documents + segment summaries (workspace). */
export function useCaseDetail(caseId: string | undefined) {
  return useQuery({
    queryKey: caseKeys.detail(caseId ?? ''),
    queryFn: () => getJson<CaseDetail>(`/cases/${caseId}`),
    enabled: Boolean(caseId),
  });
}

/** Per-case processing status, polled every 10s (loading screen). */
export function useCaseStatus(caseId: string | undefined, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: caseKeys.status(caseId ?? ''),
    queryFn: () => getJson<CaseStatus>(`/cases/${caseId}/status`),
    enabled: Boolean(caseId) && (options?.enabled ?? true),
    refetchInterval: POLL_INTERVAL_MS,
  });
}

export function useCreateCase() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => postJson<CaseSummary>('/cases', { name }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: caseKeys.all }),
  });
}

export function useRenameCase() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ caseId, name }: { caseId: string; name: string }) =>
      patchJson<CaseSummary>(`/cases/${caseId}`, { name }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: caseKeys.all }),
  });
}

export function useDeleteCase() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (caseId: string) => del(`/cases/${caseId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: caseKeys.all }),
  });
}

/** Upload 1–3 PDFs to a case as multipart/form-data (field name "files"). */
export function useUploadDocuments(caseId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (files: File[]) => {
      const form = new FormData();
      files.forEach((file) => form.append('files', file));
      return postForm<DocumentStatus[]>(`/cases/${caseId}/documents`, form);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: caseKeys.all });
      if (caseId) {
        queryClient.invalidateQueries({ queryKey: caseKeys.status(caseId) });
      }
    },
  });
}

/** Segment summaries of one document (drives the left sidebar list). */
export function useDocumentSegments(documentId: string | undefined) {
  return useQuery({
    queryKey: documentKeys.segments(documentId ?? ''),
    queryFn: () => fetchDocumentSegments(documentId as string),
    enabled: Boolean(documentId),
    staleTime: DETAIL_STALE_MS,
  });
}

/** Full detail of one segment incl. references/block_ids (loaded on select). */
export function useSegmentDetail(segmentId: string | undefined) {
  return useQuery({
    queryKey: segmentKeys.detail(segmentId ?? ''),
    queryFn: () => fetchSegmentDetail(segmentId as string),
    enabled: Boolean(segmentId),
    staleTime: DETAIL_STALE_MS,
  });
}

/** Warm the cache for a segment's detail -- used to prefetch the ±2 neighbors. */
export function prefetchSegmentDetail(queryClient: QueryClient, segmentId: string) {
  return queryClient.prefetchQuery({
    queryKey: segmentKeys.detail(segmentId),
    queryFn: () => fetchSegmentDetail(segmentId),
    staleTime: DETAIL_STALE_MS,
  });
}

/** Fetch (and cache) a single block by id -- imperative, for on-click lookups. */
export function fetchBlock(queryClient: QueryClient, documentId: string, blockId: number) {
  return queryClient.fetchQuery({
    queryKey: documentKeys.block(documentId, blockId),
    queryFn: () => fetchBlockById(documentId, blockId),
    staleTime: DETAIL_STALE_MS,
  });
}
