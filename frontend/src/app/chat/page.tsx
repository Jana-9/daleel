"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

import { AppHeader } from "@/components/app-header";
import { Button, buttonClass } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { useMe } from "@/features/auth/hooks";
import { Composer } from "@/features/chat/composer";
import {
  type Source,
  useAsk,
  useConversation,
  useConversations,
  useDeleteConversation,
  useRenameConversation,
} from "@/features/chat/hooks";
import { MessageView, PendingAnswer } from "@/features/chat/message-view";
import { SourceViewer } from "@/features/chat/source-viewer";
import { useDocuments } from "@/features/documents/hooks";
import { errorMessage } from "@/lib/api/errors";

const EXAMPLES = ["وش شروط التسجيل في التدريب التعاوني؟", "متى آخر موعد للاعتذار عن الفصل؟", "كم رسوم السكن؟"];

function Spinner() {
  return (
    <div className="flex flex-1 items-center justify-center py-16" aria-busy>
      <span className="size-6 animate-spin rounded-full border-2 border-accent border-t-transparent" />
    </div>
  );
}

export default function ChatPage() {
  // useSearchParams needs a Suspense boundary so the page shell can be prerendered.
  return (
    <Suspense fallback={<Spinner />}>
      <Chat />
    </Suspense>
  );
}

function Chat() {
  const router = useRouter();
  const me = useMe();
  const conversationId = useSearchParams().get("c");

  useEffect(() => {
    if (me.isSuccess && me.data === null) router.replace("/login");
  }, [me.isSuccess, me.data, router]);

  if (me.isPending || !me.data) return <Spinner />;

  return (
    <div className="flex h-dvh flex-col">
      <AppHeader user={me.data} />
      <div className="mx-auto flex min-h-0 w-full max-w-6xl flex-1 gap-6 px-4 sm:px-5">
        <Sidebar activeId={conversationId} />
        <Thread key={conversationId ?? "new"} conversationId={conversationId} />
      </div>
    </div>
  );
}

function Sidebar({ activeId }: { activeId: string | null }) {
  const conversations = useConversations();
  return (
    <aside className="hidden w-64 shrink-0 flex-col gap-3 overflow-y-auto py-6 lg:flex" aria-label="المحادثات">
      <Link href="/chat" className={buttonClass("primary", "w-full")}>
        محادثة جديدة
      </Link>
      {conversations.data && conversations.data.length > 0 && (
        <nav className="flex flex-col gap-1">
          {conversations.data.map((c) => (
            <Link
              key={c.id}
              href={`/chat?c=${c.id}`}
              aria-current={c.id === activeId ? "page" : undefined}
              className={`truncate rounded-xl px-3 py-2 text-[15px] transition-colors hover:bg-surface-2 ${
                c.id === activeId ? "bg-surface-2 font-semibold" : "text-muted"
              }`}
              dir="auto"
            >
              {c.title}
            </Link>
          ))}
        </nav>
      )}
    </aside>
  );
}

function Thread({ conversationId }: { conversationId: string | null }) {
  const router = useRouter();
  const conversation = useConversation(conversationId);
  const documents = useDocuments();
  const ask = useAsk();
  const [pending, setPending] = useState<string | null>(null);
  const [source, setSource] = useState<Source | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  const messages = conversation.data?.messages ?? [];
  const hasReadyDocument = documents.data?.some((d) => d.status === "ready") ?? true;

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages.length, pending]);

  function submit(question: string) {
    setPending(question);
    ask.mutate(
      { conversationId, question },
      {
        onSuccess: (result) => {
          setPending(null);
          if (!conversationId) router.replace(`/chat?c=${result.conversation.id}`);
        },
      },
    );
  }

  if (conversationId && conversation.isError) {
    return (
      <main className="flex flex-1 flex-col items-center justify-center gap-3 py-16 text-center">
        <p className="text-muted">{errorMessage(conversation.error)}</p>
        <Link href="/chat" className={buttonClass("ghost", "border border-line")}>
          محادثة جديدة
        </Link>
      </main>
    );
  }

  return (
    <main className="flex min-w-0 flex-1 flex-col">
      {conversation.data && <ThreadHeader id={conversation.data.id} title={conversation.data.title} />}

      <div className="flex-1 overflow-y-auto py-6" aria-live="polite">
        {conversationId && conversation.isPending ? (
          <Spinner />
        ) : messages.length === 0 && !pending ? (
          <EmptyThread hasReadyDocument={hasReadyDocument} onPick={submit} />
        ) : (
          <div className="flex flex-col gap-5">
            {messages.map((message) => (
              <MessageView key={message.id} message={message} onOpenSource={setSource} />
            ))}
            {pending && (
              <>
                <MessageView
                  message={{ id: "pending", role: "user", content: pending, status: null, created_at: "", sources: [] }}
                  onOpenSource={setSource}
                />
                {ask.isPending ? (
                  <PendingAnswer />
                ) : (
                  ask.isError && (
                    <div role="alert" className="flex flex-wrap items-center justify-end gap-3 text-[15px] text-danger">
                      {errorMessage(ask.error)}
                      <Button variant="ghost" className="h-9 border border-line px-3 text-[14px]" onClick={() => submit(pending)}>
                        إعادة المحاولة
                      </Button>
                    </div>
                  )
                )}
              </>
            )}
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div className="pb-4 pt-2">
        <Composer disabled={!hasReadyDocument} loading={ask.isPending} onSubmit={submit} />
        <p className="mt-2 text-center text-[12px] text-muted">
          الإجابات من وثائقك فقط. تحقّقي من المصدر قبل الاعتماد على أي إجابة.
        </p>
      </div>

      <SourceViewer source={source} onClose={() => setSource(null)} />
    </main>
  );
}

function EmptyThread({ hasReadyDocument, onPick }: { hasReadyDocument: boolean; onPick: (q: string) => void }) {
  if (!hasReadyDocument) {
    return (
      <div className="mx-auto mt-10 max-w-md rounded-3xl border border-line bg-surface p-8 text-center">
        <h1 className="text-[20px] font-bold">ما فيه وثائق جاهزة</h1>
        <p className="mt-2 text-[15px] text-muted">ارفعي وثيقة وانتظري لين تصير جاهزة، بعدها تقدرين تسألينها.</p>
        <Link href="/dashboard" className={buttonClass("primary", "mt-5")}>
          رفع وثيقة
        </Link>
      </div>
    );
  }
  return (
    <div className="animate-rise mx-auto mt-10 max-w-xl text-center">
      <h1 className="text-[26px] font-bold">وش تبين تعرفين؟</h1>
      <p className="mt-2 text-[16px] text-muted">
        اسألي بالعربي أو الإنجليزي. كل إجابة معها رقم الصفحة، واضغطي على الرقم عشان تشوفين النص في الصفحة نفسها.
      </p>
      <p className="mt-6 text-[13px] font-semibold text-muted">أمثلة على ملف التجربة</p>
      <div className="mt-2 flex flex-wrap justify-center gap-2">
        {EXAMPLES.map((example) => (
          <button
            key={example}
            type="button"
            onClick={() => onPick(example)}
            className="rounded-full border border-line bg-surface px-4 py-2 text-[14px] transition-colors hover:border-accent hover:text-accent"
          >
            {example}
          </button>
        ))}
      </div>
    </div>
  );
}

function ThreadHeader({ id, title }: { id: string; title: string }) {
  const router = useRouter();
  const rename = useRenameConversation();
  const remove = useDeleteConversation();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(title);
  const [confirming, setConfirming] = useState(false);

  return (
    <div className="flex flex-wrap items-center gap-x-2 gap-y-1 border-b border-line py-3">
      {editing ? (
        <form
          className="flex flex-1 gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (draft.trim()) rename.mutate({ id, title: draft.trim() }, { onSuccess: () => setEditing(false) });
          }}
        >
          <label htmlFor="conversation-title" className="sr-only">
            اسم المحادثة
          </label>
          <input
            id="conversation-title"
            value={draft}
            maxLength={120}
            autoFocus
            dir="auto"
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => e.key === "Escape" && setEditing(false)}
            className="h-9 flex-1 rounded-lg border border-line bg-surface px-3 text-[15px] outline-none focus:border-accent"
          />
          <Button className="h-9 px-3 text-[14px]" loading={rename.isPending}>
            حفظ
          </Button>
        </form>
      ) : (
        <>
          <h1 className="min-w-0 basis-full truncate text-[17px] font-bold sm:flex-1 sm:basis-auto" dir="auto">
            {title}
          </h1>
          <Link href="/chat" className={buttonClass("ghost", "h-9 px-3 text-[14px] lg:hidden")}>
            جديدة
          </Link>
          <Button
            variant="ghost"
            className="h-9 px-3 text-[14px]"
            onClick={() => {
              setDraft(title);
              setEditing(true);
            }}
          >
            إعادة تسمية
          </Button>
          <Button variant="ghost" className="h-9 px-3 text-[14px] text-danger" onClick={() => setConfirming(true)}>
            حذف
          </Button>
        </>
      )}
      <ConfirmDialog
        open={confirming}
        title="حذف المحادثة؟"
        body="بتنحذف المحادثة وكل الأسئلة والإجابات اللي فيها. وثائقك ما تتأثر."
        confirmLabel="حذف"
        loading={remove.isPending}
        onCancel={() => setConfirming(false)}
        onConfirm={() =>
          remove.mutate(id, {
            onSuccess: () => {
              setConfirming(false);
              router.replace("/chat");
            },
          })
        }
      />
    </div>
  );
}
