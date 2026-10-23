"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { ApiError, unwrap } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";

export type Conversation = components["schemas"]["ConversationOut"];
export type ConversationDetail = components["schemas"]["ConversationDetailOut"];
export type Message = components["schemas"]["MessageOut"];
export type Source = components["schemas"]["SourceOut"];

const LIST_KEY = ["conversations"] as const;
const detailKey = (id: string) => ["conversations", id] as const;

export function useConversations() {
  return useQuery({
    queryKey: LIST_KEY,
    queryFn: async () => unwrap(await api.GET("/api/v1/conversations")).items,
  });
}

export function useConversation(id: string | null) {
  return useQuery({
    queryKey: detailKey(id ?? "none"),
    enabled: id !== null,
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/conversations/{conversation_id}", { params: { path: { conversation_id: id! } } })),
  });
}

/** Ask a question. Creates the conversation first when there is none yet. */
export function useAsk() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ conversationId, question }: { conversationId: string | null; question: string }) => {
      let id = conversationId;
      if (id === null) {
        id = unwrap(await api.POST("/api/v1/conversations", { body: {} })).id;
      }
      return unwrap(
        await api.POST("/api/v1/conversations/{conversation_id}/messages", {
          params: { path: { conversation_id: id } },
          body: { question },
        }),
      );
    },
    onSuccess: (result) => {
      const id = result.conversation.id;
      queryClient.setQueryData<ConversationDetail>(detailKey(id), (current) => ({
        ...result.conversation,
        messages: [...(current?.messages ?? []), result.question, result.answer],
      }));
      void queryClient.invalidateQueries({ queryKey: LIST_KEY, exact: true });
    },
  });
}

export function useRenameConversation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, title }: { id: string; title: string }) =>
      unwrap(
        await api.PATCH("/api/v1/conversations/{conversation_id}", {
          params: { path: { conversation_id: id } },
          body: { title },
        }),
      ),
    onSuccess: (conversation) => {
      queryClient.setQueryData<ConversationDetail>(detailKey(conversation.id), (c) => c && { ...c, ...conversation });
      void queryClient.invalidateQueries({ queryKey: LIST_KEY, exact: true });
    },
  });
}

export function useDeleteConversation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { response } = await api.DELETE("/api/v1/conversations/{conversation_id}", {
        params: { path: { conversation_id: id } },
      });
      if (!response.ok && response.status !== 404) throw new ApiError(response.status, "unknown");
    },
    onSuccess: (_, id) => {
      queryClient.setQueryData<Conversation[]>(LIST_KEY, (items) => items?.filter((c) => c.id !== id));
      queryClient.removeQueries({ queryKey: detailKey(id) });
    },
  });
}
