"use client";

import { useRouter } from "next/navigation";

import { Logo } from "@/components/logo";
import { Button } from "@/components/ui/button";
import { type User, useLogout } from "@/features/auth/hooks";

export function AppHeader({ user }: { user: User }) {
  const router = useRouter();
  const logout = useLogout();
  return (
    <header className="border-b border-line bg-surface">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-5 py-4">
        <Logo href="/dashboard" />
        <div className="flex items-center gap-3">
          <span className="hidden text-[15px] text-muted sm:inline" dir="ltr">
            {user.email}
          </span>
          <Button
            variant="ghost"
            loading={logout.isPending}
            onClick={() => logout.mutate(undefined, { onSuccess: () => router.replace("/login") })}
          >
            تسجيل الخروج
          </Button>
        </div>
      </div>
    </header>
  );
}
