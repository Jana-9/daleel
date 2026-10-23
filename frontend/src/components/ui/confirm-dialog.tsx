"use client";

import { type ReactNode, useEffect, useRef } from "react";

import { Button } from "./button";

type Props = {
  open: boolean;
  title: string;
  body: ReactNode;
  confirmLabel: string;
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
};

/** Built on the native <dialog>: focus trapping, Escape to close and the backdrop come free. */
export function ConfirmDialog({ open, title, body, confirmLabel, loading, onConfirm, onCancel }: Props) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      onClose={onCancel}
      className="m-auto w-[min(26rem,calc(100%-2rem))] rounded-3xl border border-line bg-surface p-6 text-ink shadow-[var(--shadow)] backdrop:bg-black/40"
    >
      <h2 className="text-[19px] font-bold">{title}</h2>
      <p className="mt-2 text-[15px] text-muted">{body}</p>
      <div className="mt-6 flex justify-end gap-2">
        <Button variant="ghost" onClick={onCancel} disabled={loading}>
          إلغاء
        </Button>
        <Button variant="danger" onClick={onConfirm} loading={loading}>
          {confirmLabel}
        </Button>
      </div>
    </dialog>
  );
}
