import Link from "next/link";

import { Logo } from "@/components/logo";

type Props = {
  title: string;
  subtitle: string;
  footer: { text: string; linkLabel: string; href: string };
  children: React.ReactNode;
};

export function AuthCard({ title, subtitle, footer, children }: Props) {
  return (
    <main className="flex flex-1 items-center justify-center px-5 py-12">
      <div className="animate-rise w-full max-w-[26rem]">
        <div className="mb-8 flex justify-center">
          <Logo />
        </div>
        <div className="rounded-3xl border border-line bg-surface p-7 shadow-[var(--shadow)]">
          <h1 className="text-[24px] font-bold">{title}</h1>
          <p className="mt-1 mb-6 text-[15px] text-muted">{subtitle}</p>
          {children}
        </div>
        <p className="mt-6 text-center text-[15px] text-muted">
          {footer.text}{" "}
          <Link href={footer.href} className="font-semibold text-accent underline-offset-4 hover:underline">
            {footer.linkLabel}
          </Link>
        </p>
      </div>
    </main>
  );
}

export function FormError({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <div role="alert" className="mb-4 rounded-xl bg-danger-soft px-4 py-3 text-[14px] text-danger">
      {message}
    </div>
  );
}
