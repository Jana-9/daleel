"use client";

import { useEffect, useRef } from "react";

import { buttonClass } from "@/components/ui/button";

import type { Source } from "./hooks";
import { PdfPageViewer } from "./pdf-page-viewer";

/** A side sheet (full screen on phones) showing the cited page with the passage highlighted. */
export function SourceViewer({ source, onClose }: { source: Source | null; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (source && !dialog.open) dialog.showModal();
    if (!source && dialog.open) dialog.close();
  }, [source]);

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      aria-labelledby="source-title"
      className="m-0 ms-auto h-dvh max-h-dvh w-full max-w-none bg-bg text-ink backdrop:bg-black/40 sm:w-[min(40rem,100%)] sm:border-s sm:border-line"
    >
      {source && (
        <div className="flex h-full flex-col">
          <div className="flex items-start justify-between gap-3 border-b border-line bg-surface px-5 py-4">
            <div className="min-w-0">
              <p className="text-[13px] font-semibold text-accent">المصدر {source.marker}</p>
              <h2 id="source-title" className="truncate text-[17px] font-bold" dir="auto">
                {source.document_title}
              </h2>
              <p className="text-[14px] text-muted">صفحة {source.page_number}</p>
            </div>
            <button type="button" onClick={onClose} className={buttonClass("ghost", "h-9 px-3")} aria-label="إغلاق">
              <svg viewBox="0 0 24 24" className="size-5" fill="none" aria-hidden>
                <path d="M6 6l12 12M18 6 6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </button>
          </div>

          <div className="flex-1 overflow-y-auto px-5 py-5">
            <blockquote className="mb-5 rounded-xl border-s-4 border-accent bg-surface px-4 py-3 text-[15px] leading-7" dir="auto">
              {source.excerpt}
            </blockquote>
            {source.document_id ? (
              <>
                <PdfPageViewer documentId={source.document_id} pageNumber={source.page_number} boxes={source.bboxes} />
                <a
                  href={`/api/v1/documents/${source.document_id}/file#page=${source.page_number}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-4 inline-block text-[14px] font-semibold text-accent underline-offset-4 hover:underline"
                >
                  فتح الملف كامل
                </a>
              </>
            ) : (
              <p className="rounded-xl bg-surface-2 px-4 py-3 text-[14px] text-muted">
                الوثيقة الأصلية انحذفت، لكن النص اللي بُنيت عليه الإجابة محفوظ أعلاه.
              </p>
            )}
          </div>
        </div>
      )}
    </dialog>
  );
}
