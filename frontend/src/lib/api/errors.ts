/** The backend's error shape: {"error": {"code", "message", "details"?}} */
export type ApiErrorBody = {
  error?: { code?: string; message?: string; details?: { field: string; message: string }[] };
};

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
  ) {
    super(code);
  }
}

const MESSAGES: Record<string, string> = {
  email_taken: "يوجد حساب مسجّل بهذا البريد الإلكتروني.",
  invalid_credentials: "البريد الإلكتروني أو كلمة المرور غير صحيحة.",
  not_authenticated: "انتهت الجلسة، سجّلي الدخول مرة أخرى.",
  validation_error: "تحقّقي من البيانات المدخلة.",
  network_error: "تعذّر الاتصال بالخادم. تأكّدي من اتصالك وحاولي مرة أخرى.",
  // Uploads
  not_pdf: "الملف لازم يكون بصيغة PDF.",
  file_too_large: "حجم الملف أكبر من 20 ميجابايت.",
  too_many_pages: "الملف فيه أكثر من 500 صفحة.",
  encrypted_pdf: "الملف محمي بكلمة مرور. احذفي الحماية وارفعيه من جديد.",
  empty_file: "الملف فاضي.",
  invalid_pdf: "الملف تالف أو ما يمكن قراءته.",
  document_not_found: "الوثيقة غير موجودة أو انحذفت.",
  not_retryable: "ما يمكن إعادة معالجة هذي الوثيقة الآن.",
};

/** Why processing failed (documents.error_code). */
const PROCESSING_MESSAGES: Record<string, string> = {
  scanned_pdf: "الملف صور ممسوحة بدون نص قابل للقراءة، ودليل ما يدعم الملفات الممسوحة حاليًا.",
  no_text: "ما لقينا نص في الملف.",
  extraction_failed: "تعذّرت قراءة محتوى الملف.",
  embedding_failed: "تعذّر تجهيز الملف للبحث. جربي إعادة المحاولة.",
  internal_error: "صار خطأ غير متوقع أثناء المعالجة. جربي إعادة المحاولة.",
};

export function processingErrorMessage(code: string | null | undefined): string {
  return (code && PROCESSING_MESSAGES[code]) || PROCESSING_MESSAGES.internal_error;
}

/** Turn any thrown value into a message that is safe and friendly to show in the UI. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return MESSAGES[error.code] ?? "حدث خطأ غير متوقع. حاولي مرة أخرى.";
  return MESSAGES.network_error;
}

/** Throw an ApiError when an openapi-fetch result contains an error. */
export function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): T {
  if (result.error !== undefined || result.data === undefined) {
    const body = result.error as ApiErrorBody | undefined;
    throw new ApiError(result.response.status, body?.error?.code ?? "unknown");
  }
  return result.data;
}
