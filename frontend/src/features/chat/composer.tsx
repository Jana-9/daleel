"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";

type Props = { disabled?: boolean; loading?: boolean; onSubmit: (question: string) => void };

export function Composer({ disabled, loading, onSubmit }: Props) {
  const [value, setValue] = useState("");
  const question = value.trim();

  function submit() {
    if (question.length < 2 || loading || disabled) return;
    onSubmit(question);
    setValue("");
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
      className="flex items-end gap-2 rounded-2xl border border-line bg-surface p-2 shadow-[var(--shadow)] focus-within:border-accent"
    >
      <label htmlFor="question" className="sr-only">
        سؤالك
      </label>
      <textarea
        id="question"
        rows={1}
        value={value}
        maxLength={1000}
        disabled={disabled}
        dir="auto"
        placeholder="اسألي عن أي شيء في وثائقك…"
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          // Enter sends, Shift+Enter adds a new line (skipped while an IME is composing).
          if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
            e.preventDefault();
            submit();
          }
        }}
        className="max-h-40 min-h-11 flex-1 resize-none bg-transparent px-3 py-2.5 text-[16px] outline-none [field-sizing:content] placeholder:text-muted/70 disabled:opacity-60"
      />
      <Button type="submit" loading={loading} disabled={disabled || question.length < 2} aria-label="إرسال">
        إرسال
      </Button>
    </form>
  );
}
