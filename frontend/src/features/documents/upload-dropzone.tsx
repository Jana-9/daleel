"use client";

import { useRef, useState } from "react";

import { errorMessage } from "@/lib/api/errors";
import { formatBytes } from "@/lib/format";

import { uploadDocument, useRefreshDocuments } from "./hooks";

// Mirrors the backend limit, so obviously-too-big files fail instantly instead of after uploading.
const MAX_BYTES = 20 * 1024 * 1024;

type Upload = { id: number; name: string; size: number; progress: number; error?: string };

function localError(file: File): string | undefined {
  const looksLikePdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
  if (!looksLikePdf) return "الملف لازم يكون بصيغة PDF.";
  if (file.size > MAX_BYTES) return "حجم الملف أكبر من 20 ميجابايت.";
  if (file.size === 0) return "الملف فاضي.";
}

export function UploadDropzone() {
  const inputRef = useRef<HTMLInputElement>(null);
  const nextId = useRef(0);
  const [dragging, setDragging] = useState(false);
  const [uploads, setUploads] = useState<Upload[]>([]);
  const refresh = useRefreshDocuments();

  const update = (id: number, patch: Partial<Upload>) =>
    setUploads((list) => list.map((u) => (u.id === id ? { ...u, ...patch } : u)));

  async function handleFiles(files: FileList | File[]) {
    // One at a time: keeps progress readable and does not flood the server.
    for (const file of Array.from(files)) {
      const id = nextId.current++;
      const problem = localError(file);
      setUploads((list) => [...list, { id, name: file.name, size: file.size, progress: 0, error: problem }]);
      if (problem) continue;
      try {
        await uploadDocument(file, (progress) => update(id, { progress }));
        setUploads((list) => list.filter((u) => u.id !== id)); // it now appears in the list below
        await refresh();
      } catch (error) {
        update(id, { error: errorMessage(error) });
      }
    }
  }

  return (
    <section aria-label="رفع وثيقة">
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          void handleFiles(e.dataTransfer.files);
        }}
        className={
          "flex w-full flex-col items-center gap-2 rounded-3xl border-2 border-dashed px-6 py-10 text-center " +
          "transition-colors duration-150 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent " +
          (dragging ? "border-accent bg-accent-soft" : "border-line bg-surface hover:border-accent/60")
        }
      >
        <svg viewBox="0 0 24 24" className="size-9 text-accent" fill="none" aria-hidden>
          <path d="M12 16V4m0 0-4.5 4.5M12 4l4.5 4.5M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <span className="text-[17px] font-semibold">اسحبي ملف PDF هنا أو اضغطي للاختيار</span>
        <span className="text-[14px] text-muted">حتى 20 ميجابايت للملف، بالعربي أو الإنجليزي</span>
      </button>
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf,.pdf"
        multiple
        hidden
        data-testid="file-input"
        onChange={(e) => {
          if (e.target.files) void handleFiles(e.target.files);
          e.target.value = ""; // allow choosing the same file again
        }}
      />

      {uploads.length > 0 && (
        <ul className="mt-3 flex flex-col gap-2" aria-live="polite">
          {uploads.map((u) => (
            <li key={u.id} className="rounded-2xl border border-line bg-surface px-4 py-3">
              <div className="flex items-center justify-between gap-3 text-[15px]">
                <span className="truncate font-medium" dir="auto">
                  {u.name}
                </span>
                <span className="shrink-0 text-[13px] text-muted">{formatBytes(u.size)}</span>
              </div>
              {u.error ? (
                <div className="mt-1.5 flex items-center justify-between gap-3">
                  <p role="alert" className="text-[14px] text-danger">
                    {u.error}
                  </p>
                  <button
                    type="button"
                    className="shrink-0 text-[13px] text-muted underline-offset-4 hover:underline"
                    onClick={() => setUploads((list) => list.filter((x) => x.id !== u.id))}
                  >
                    إخفاء
                  </button>
                </div>
              ) : (
                <div
                  className="mt-2 h-1.5 overflow-hidden rounded-full bg-surface-2"
                  role="progressbar"
                  aria-label={`رفع ${u.name}`}
                  aria-valuenow={Math.round(u.progress * 100)}
                  aria-valuemin={0}
                  aria-valuemax={100}
                >
                  <div
                    className="h-full origin-right rounded-full bg-accent transition-transform duration-200 ease-out-strong"
                    style={{ transform: `scaleX(${Math.max(u.progress, 0.03)})` }}
                  />
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
