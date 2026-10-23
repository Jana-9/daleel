"use client";

import { Fragment } from "react";

import type { Message, Source } from "./hooks";

/** Turns "text [1] more [2]." into text with clickable citation chips. */
function AnswerText({ content, sources, onCite }: { content: string; sources: Source[]; onCite: (s: Source) => void }) {
  const byMarker = new Map(sources.map((s) => [s.marker, s]));
  const parts = content.split(/(\[\d+\])/g);
  return (
    <p className="whitespace-pre-line text-[16px] leading-8" dir="auto">
      {parts.map((part, index) => {
        const match = /^\[(\d+)\]$/.exec(part);
        const source = match ? byMarker.get(Number(match[1])) : undefined;
        if (!source) return <Fragment key={index}>{part}</Fragment>;
        return (
          <button
            key={index}
            type="button"
            onClick={() => onCite(source)}
            className="mx-0.5 inline-flex h-5 min-w-5 -translate-y-0.5 items-center justify-center rounded-md bg-accent-soft px-1 align-middle text-[12px] font-bold text-accent [unicode-bidi:isolate] transition-transform duration-150 hover:scale-110 focus-visible:outline-2 focus-visible:outline-accent active:scale-95"
            aria-label={`المصدر ${source.marker}: ${source.document_title}، صفحة ${source.page_number}`}
          >
            {source.marker}
          </button>
        );
      })}
    </p>
  );
}

function SourceList({ sources, onOpen }: { sources: Source[]; onOpen: (s: Source) => void }) {
  return (
    <ol className="mt-4 flex flex-col gap-2 border-t border-line pt-3" aria-label="المصادر">
      {sources.map((source) => (
        <li key={source.marker}>
          <button
            type="button"
            onClick={() => onOpen(source)}
            className="group flex w-full items-start gap-3 rounded-xl p-2 text-start transition-colors hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-accent"
          >
            <span className="mt-0.5 grid size-6 shrink-0 place-items-center rounded-md bg-accent-soft text-[12px] font-bold text-accent">
              {source.marker}
            </span>
            <span className="min-w-0">
              <span className="block text-[14px] font-semibold">
                <bdi>{source.document_title}</bdi> · صفحة {source.page_number}
              </span>
              <span className="line-clamp-2 text-[14px] text-muted" dir="auto">
                {source.excerpt}
              </span>
              <span className="mt-0.5 block text-[13px] font-semibold text-accent opacity-80 group-hover:opacity-100">
                عرض في الصفحة
              </span>
            </span>
          </button>
        </li>
      ))}
    </ol>
  );
}

export function MessageView({ message, onOpenSource }: { message: Message; onOpenSource: (s: Source) => void }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-start">
        <div className="max-w-[85%] rounded-2xl rounded-ss-md bg-accent px-4 py-2.5 text-[16px] text-accent-ink" dir="auto">
          {message.content}
        </div>
      </div>
    );
  }
  const notFound = message.status === "not_found";
  return (
    <div className="flex justify-end">
      <div
        className={`w-full max-w-[min(42rem,100%)] rounded-2xl rounded-se-md border px-4 py-3 sm:px-5 sm:py-4 ${
          notFound ? "border-line bg-surface-2" : "border-line bg-surface"
        }`}
      >
        {notFound && <p className="mb-1 text-[13px] font-semibold text-muted">ما لقيت إجابة في وثائقك</p>}
        <AnswerText content={message.content} sources={message.sources} onCite={onOpenSource} />
        {message.sources.length > 0 && <SourceList sources={message.sources} onOpen={onOpenSource} />}
      </div>
    </div>
  );
}

export function PendingAnswer() {
  return (
    <div className="flex justify-end" aria-live="polite">
      <div className="flex w-full max-w-[min(42rem,100%)] items-center gap-3 rounded-2xl rounded-se-md border border-line bg-surface px-5 py-4 text-[15px] text-muted">
        <span aria-hidden className="size-4 animate-spin rounded-full border-2 border-accent border-t-transparent" />
        أدوّر في وثائقك وأكتب الإجابة…
      </div>
    </div>
  );
}
