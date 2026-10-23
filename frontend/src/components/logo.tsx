import Link from "next/link";

/** Wordmark: an open page with a marker on it, plus the name. */
export function Logo({ href = "/" }: { href?: string }) {
  return (
    <Link href={href} className="inline-flex items-center gap-2.5 font-bold text-[19px] text-ink">
      <svg viewBox="0 0 32 32" className="size-8" aria-hidden>
        <rect x="3" y="5" width="26" height="22" rx="6" className="fill-accent" />
        <path d="M16 9v14M9 11.5h4.5M9 15.5h4.5M18.5 11.5H23M18.5 15.5H21" stroke="var(--accent-ink)" strokeWidth="1.8" strokeLinecap="round" />
        <circle cx="22.5" cy="20.5" r="2.2" fill="var(--accent-ink)" />
      </svg>
      دليل
    </Link>
  );
}
