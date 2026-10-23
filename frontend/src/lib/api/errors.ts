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
};

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
