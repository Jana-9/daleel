"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { Logo } from "@/components/logo";
import { Button } from "@/components/ui/button";
import { type User, useLogout } from "@/features/auth/hooks";

const LINKS = [
  { href: "/dashboard", label: "الوثائق" },
  { href: "/chat", label: "اسأل" },
];

export function AppHeader({ user }: { user: User }) {
  const router = useRouter();
  const pathname = usePathname();
  const logout = useLogout();
  return (
    <header className="shrink-0 border-b border-line bg-surface">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 sm:px-5">
        <div className="flex items-center gap-4 sm:gap-6">
          <Logo href="/dashboard" />
          <nav className="flex items-center gap-1" aria-label="الأقسام">
            {LINKS.map((link) => {
              const active = pathname.startsWith(link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  aria-current={active ? "page" : undefined}
                  className={`rounded-lg px-3 py-1.5 text-[15px] font-semibold transition-colors ${
                    active ? "bg-accent-soft text-accent" : "text-muted hover:bg-surface-2 hover:text-ink"
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>
        </div>
        <div className="flex items-center gap-3">
          <span className="hidden text-[14px] text-muted md:inline" dir="ltr">
            {user.email}
          </span>
          <Button
            variant="ghost"
            className="px-3"
            loading={logout.isPending}
            onClick={() => logout.mutate(undefined, { onSuccess: () => router.replace("/login") })}
          >
            خروج
          </Button>
        </div>
      </div>
    </header>
  );
}
