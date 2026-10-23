"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { ApiError, unwrap, type ApiErrorBody } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";

export type DocumentItem = components["schemas"]["DocumentOut"];

const DOCUMENTS_KEY = ["documents"] as const;
const POLL_MS = 2000;

export const isInProgress = (d: DocumentItem) => d.status === "uploaded" || d.status === "processing";

/** The user's documents. Polls while any document is still being processed, then stops. */
export function useDocuments() {
  return useQuery({
    queryKey: DOCUMENTS_KEY,
    queryFn: async () => unwrap(await api.GET("/api/v1/documents")).items,
    refetchInterval: (query) => (query.state.data?.some(isInProgress) ? POLL_MS : false),
  });
}

/**
 * Upload with progress. fetch() cannot report upload progress, so this uses XMLHttpRequest.
 * Same origin as the page, so the session cookie is sent automatically.
 */
export function uploadDocument(file: File, onProgress: (fraction: number) => void): Promise<DocumentItem> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", "/api/v1/documents");
    request.responseType = "json";
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(event.loaded / event.total);
    };
    request.onload = () => {
      if (request.status === 201) return resolve(request.response as DocumentItem);
      const body = request.response as ApiErrorBody | null;
      reject(new ApiError(request.status, body?.error?.code ?? "unknown"));
    };
    request.onerror = () => reject(new TypeError("network error"));
    const form = new FormData();
    form.append("file", file);
    request.send(form);
  });
}

export function useRefreshDocuments() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: DOCUMENTS_KEY });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { response } = await api.DELETE("/api/v1/documents/{document_id}", {
        params: { path: { document_id: id } },
      });
      if (!response.ok && response.status !== 404) throw new ApiError(response.status, "unknown");
    },
    onSuccess: (_, id) => {
      // Remove it right away instead of waiting for a refetch.
      queryClient.setQueryData<DocumentItem[]>(DOCUMENTS_KEY, (items) => items?.filter((d) => d.id !== id));
    },
  });
}

export function useRetryDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) =>
      unwrap(await api.POST("/api/v1/documents/{document_id}/retry", { params: { path: { document_id: id } } })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: DOCUMENTS_KEY }),
  });
}
