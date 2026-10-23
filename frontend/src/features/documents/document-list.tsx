"use client";

import { useState } from "react";

import { buttonClass } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { errorMessage, processingErrorMessage } from "@/lib/api/errors";
import { formatBytes, formatDate, pagesLabel } from "@/lib/format";

import { type DocumentItem, useDeleteDocument, useRetryDocument } from "./hooks";

const STATUS: Record<DocumentItem["status"], { label: string; className: string }> = {
  uploaded: { label: "في الانتظار", className: "bg-surface-2 text-muted" },
  processing: { label: "قيد المعالجة", className: "bg-surface-2 text-muted" },
  ready: { label: "جاهز", className: "bg-accent-soft text-accent" },
  failed: { label: "فشلت المعالجة", className: "bg-danger-soft text-danger" },
};

function StatusBadge({ status }: { status: DocumentItem["status"] }) {
  const { label, className } = STATUS[status];
  const busy = status === "uploaded" || status === "processing";
  return (
    <span className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-[13px] font-semibold ${className}`}>
      {busy && <span aria-hidden className="size-3 animate-spin rounded-full border-2 border-current border-t-transparent" />}
      {label}
    </span>
  );
}

export function DocumentList({ documents }: { documents: DocumentItem[] }) {
  const [toDelete, setToDelete] = useState<DocumentItem | null>(null);
  const remove = useDeleteDocument();
  const retry = useRetryDocument();

  return (
    <>
      <ul className="flex flex-col gap-3" aria-label="الوثائق">
        {documents.map((document) => (
          <li key={document.id} className="rounded-2xl border border-line bg-surface p-4 sm:p-5">
            <div className="flex items-start gap-3">
              <svg viewBox="0 0 24 24" className="mt-0.5 size-6 shrink-0 text-accent" fill="none" aria-hidden>
                <path d="M7 3h7l5 5v12a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
                <path d="M14 3v5h5M9 13h6M9 17h4" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
              </svg>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1.5">
                  <h3 className="min-w-0 truncate text-[16px] font-bold" dir="auto" title={document.title}>
                    {document.title}
                  </h3>
                  <StatusBadge status={document.status} />
                </div>
                <p className="mt-1 text-[13px] text-muted">
                  <span dir="auto">{document.original_filename}</span> · {pagesLabel(document.page_count)} ·{" "}
                  {formatBytes(document.file_size)} · {formatDate(document.created_at)}
                </p>
                {document.status === "failed" && (
                  <p className="mt-2 text-[14px] text-danger">{processingErrorMessage(document.error_code)}</p>
                )}
                <div className="mt-3 flex flex-wrap gap-2">
                  <a
                    href={`/api/v1/documents/${document.id}/file`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={buttonClass("ghost", "h-9 border border-line px-3 text-[14px]")}
                  >
                    فتح الملف
                  </a>
                  {document.status === "failed" && (
                    <button
                      type="button"
                      className={buttonClass("ghost", "h-9 border border-line px-3 text-[14px]")}
                      disabled={retry.isPending && retry.variables === document.id}
                      onClick={() => retry.mutate(document.id)}
                    >
                      إعادة المحاولة
                    </button>
                  )}
                  <button
                    type="button"
                    className={buttonClass("ghost", "h-9 px-3 text-[14px] text-danger")}
                    onClick={() => setToDelete(document)}
                    aria-label={`حذف ${document.title}`}
                  >
                    حذف
                  </button>
                </div>
              </div>
            </div>
          </li>
        ))}
      </ul>

      {retry.isError && (
        <p role="alert" className="mt-3 text-[14px] text-danger">
          {errorMessage(retry.error)}
        </p>
      )}

      <ConfirmDialog
        open={toDelete !== null}
        title="حذف الوثيقة؟"
        body={
          <>
            {/* <bdi> keeps an English title from scrambling the Arabic sentence around it. */}
            بينحذف «<bdi>{toDelete?.title}</bdi>» نهائيًا مع كل ما تم استخراجه منه. ما يمكن التراجع عن هذا.
          </>
        }
        confirmLabel="حذف نهائي"
        loading={remove.isPending}
        onCancel={() => setToDelete(null)}
        onConfirm={() => toDelete && remove.mutate(toDelete.id, { onSettled: () => setToDelete(null) })}
      />
    </>
  );
}
