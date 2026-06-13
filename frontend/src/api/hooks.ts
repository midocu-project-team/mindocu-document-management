/**
 * TanStack Query hooks over the backend API — the replacement for the old
 * local CasesContext. Polling lists/status use a 10s refetch interval.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { del, getJson, patchJson, postForm, postJson } from './client'
import type { CaseDetail, CaseStatus, CaseSummary, DocumentStatus } from './types'

const POLL_INTERVAL_MS = 10_000

export const caseKeys = {
  all: ['cases'] as const,
  detail: (caseId: string) => ['cases', caseId, 'detail'] as const,
  status: (caseId: string) => ['cases', caseId, 'status'] as const,
}

/** All cases, polled every 10s (homepage list). */
export function useCases() {
  return useQuery({
    queryKey: caseKeys.all,
    queryFn: () => getJson<CaseSummary[]>('/cases'),
    refetchInterval: POLL_INTERVAL_MS,
  })
}

/** Full case detail incl. documents + segment summaries (workspace). */
export function useCaseDetail(caseId: string | undefined) {
  return useQuery({
    queryKey: caseKeys.detail(caseId ?? ''),
    queryFn: () => getJson<CaseDetail>(`/cases/${caseId}`),
    enabled: Boolean(caseId),
  })
}

/** Per-case processing status, polled every 10s (loading screen). */
export function useCaseStatus(caseId: string | undefined, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: caseKeys.status(caseId ?? ''),
    queryFn: () => getJson<CaseStatus>(`/cases/${caseId}/status`),
    enabled: Boolean(caseId) && (options?.enabled ?? true),
    refetchInterval: POLL_INTERVAL_MS,
  })
}

export function useCreateCase() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (name: string) => postJson<CaseSummary>('/cases', { name }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: caseKeys.all }),
  })
}

export function useRenameCase() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ caseId, name }: { caseId: string; name: string }) =>
      patchJson<CaseSummary>(`/cases/${caseId}`, { name }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: caseKeys.all }),
  })
}

export function useDeleteCase() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (caseId: string) => del(`/cases/${caseId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: caseKeys.all }),
  })
}

/** Upload 1–3 PDFs to a case as multipart/form-data (field name "files"). */
export function useUploadDocuments(caseId: string | undefined) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (files: File[]) => {
      const form = new FormData()
      files.forEach((file) => form.append('files', file))
      return postForm<DocumentStatus[]>(`/cases/${caseId}/documents`, form)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: caseKeys.all })
      if (caseId) {
        queryClient.invalidateQueries({ queryKey: caseKeys.status(caseId) })
      }
    },
  })
}
