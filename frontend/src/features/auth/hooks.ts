"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { ApiError, unwrap } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";

export type User = components["schemas"]["UserOut"];
type LoginInput = components["schemas"]["LoginRequest"];
type RegisterInput = components["schemas"]["RegisterRequest"];

const ME_KEY = ["auth", "me"] as const;

/** The logged-in user, or null when there is no valid session. */
export function useMe() {
  return useQuery({
    queryKey: ME_KEY,
    queryFn: async (): Promise<User | null> => {
      try {
        return unwrap(await api.GET("/api/v1/auth/me"));
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) return null;
        throw error;
      }
    },
    staleTime: 60_000,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: LoginInput) => unwrap(await api.POST("/api/v1/auth/login", { body: input })),
    onSuccess: (user) => queryClient.setQueryData(ME_KEY, user),
  });
}

export function useRegister() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: RegisterInput) =>
      unwrap(await api.POST("/api/v1/auth/register", { body: input })),
    onSuccess: (user) => queryClient.setQueryData(ME_KEY, user),
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { response } = await api.POST("/api/v1/auth/logout");
      if (!response.ok) throw new ApiError(response.status, "unknown");
    },
    onSuccess: () => queryClient.clear(),
  });
}
