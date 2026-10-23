"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Logo } from "@/components/logo";
import { Button } from "@/components/ui/button";
import { useLogout, useMe } from "@/features/auth/hooks";

export default function DashboardPage() {
  const router = useRouter();
  const me = useMe();
  const logout = useLogout();

  // The server is the real gatekeeper (every API call checks the session).
  // This redirect only keeps logged-out visitors from seeing an empty page.
  useEffect(() => {
    if (me.isSuccess && me.data === null) router.replace("/login");
  }, [me.isSuccess, me.data, router]);

  if (me.isPending || !me.data) {
    return (
      <div className="flex flex-1 items-center justify-center" aria-busy>
        <span className="size-6 animate-spin rounded-full border-2 border-accent border-t-transparent" />
      </div>
    );
  }

  const user = me.data;

  return (
    <div className="flex flex-1 flex-col">
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4">
          <Logo href="/dashboard" />
          <div className="flex items-center gap-3">
            <span className="hidden text-[15px] text-muted sm:inline">{user.email}</span>
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

      <main className="mx-auto w-full max-w-6xl flex-1 px-5 py-10">
        <h1 className="animate-rise text-[28px] font-bold">أهلًا {user.name}</h1>
        <p className="mt-1 text-muted">هنا بتلقين وثائقك ومحادثاتك.</p>

        <section className="animate-rise mt-8 flex flex-col items-center rounded-3xl border border-dashed border-line bg-surface px-6 py-16 text-center [animation-delay:60ms]">
          <svg viewBox="0 0 48 48" className="size-12 text-accent" aria-hidden fill="none">
            <path d="M14 6h14l10 10v24a2 2 0 0 1-2 2H14a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2Z" stroke="currentColor" strokeWidth="2.5" strokeLinejoin="round" />
            <path d="M28 6v10h10" stroke="currentColor" strokeWidth="2.5" strokeLinejoin="round" />
          </svg>
          <h2 className="mt-4 text-[20px] font-bold">لا توجد وثائق بعد</h2>
          <p className="mt-1 max-w-sm text-[15px] text-muted">
            لما ترفعين أول وثيقة، بتظهر هنا مع حالة معالجتها.
          </p>
        </section>
      </main>
    </div>
  );
}
