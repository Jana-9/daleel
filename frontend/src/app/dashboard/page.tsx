"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { AppHeader } from "@/components/app-header";
import { useMe } from "@/features/auth/hooks";
import { DocumentList } from "@/features/documents/document-list";
import { useDocuments } from "@/features/documents/hooks";
import { UploadDropzone } from "@/features/documents/upload-dropzone";
import { errorMessage } from "@/lib/api/errors";

function Spinner() {
  return (
    <div className="flex flex-1 items-center justify-center py-16" aria-busy>
      <span className="size-6 animate-spin rounded-full border-2 border-accent border-t-transparent" />
    </div>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const me = useMe();

  // The server is the real gatekeeper (every API call checks the session).
  // This redirect only keeps logged-out visitors from seeing an empty page.
  useEffect(() => {
    if (me.isSuccess && me.data === null) router.replace("/login");
  }, [me.isSuccess, me.data, router]);

  if (me.isPending || !me.data) return <Spinner />;

  return (
    <div className="flex flex-1 flex-col">
      <AppHeader user={me.data} />
      <main className="mx-auto w-full max-w-5xl flex-1 px-5 py-10">
        <h1 className="animate-rise text-[28px] font-bold">أهلًا {me.data.name}</h1>
        <p className="mt-1 text-muted">ارفعي وثائقك هنا، وبعد ما تجهز تقدرين تسألينها.</p>

        <div className="animate-rise mt-8 [animation-delay:60ms]">
          <UploadDropzone />
        </div>

        <section className="mt-10" aria-labelledby="library-heading">
          <h2 id="library-heading" className="mb-4 text-[20px] font-bold">
            وثائقك
          </h2>
          <Library />
        </section>
      </main>
    </div>
  );
}

function Library() {
  const documents = useDocuments();

  if (documents.isPending) return <Spinner />;
  if (documents.isError) {
    return (
      <p role="alert" className="rounded-2xl bg-danger-soft px-4 py-3 text-[15px] text-danger">
        {errorMessage(documents.error)}
      </p>
    );
  }
  if (documents.data.length === 0) {
    return (
      <div className="rounded-3xl border border-line bg-surface px-6 py-12 text-center">
        <h3 className="text-[18px] font-bold">لا توجد وثائق بعد</h3>
        <p className="mt-1 text-[15px] text-muted">أول وثيقة ترفعينها بتظهر هنا مع حالة معالجتها.</p>
      </div>
    );
  }
  return <DocumentList documents={documents.data} />;
}
