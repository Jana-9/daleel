"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { AuthCard, FormError } from "@/features/auth/auth-card";
import { useLogin } from "@/features/auth/hooks";
import { errorMessage } from "@/lib/api/errors";

export default function LoginPage() {
  const router = useRouter();
  const login = useLogin();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    login.mutate({ email, password }, { onSuccess: () => router.replace("/dashboard") });
  }

  return (
    <AuthCard
      title="أهلًا من جديد"
      subtitle="سجّلي الدخول للوصول إلى وثائقك."
      footer={{ text: "ما عندك حساب؟", linkLabel: "أنشئي حسابًا", href: "/register" }}
    >
      <FormError message={login.isError ? errorMessage(login.error) : null} />
      <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
        <Field
          label="البريد الإلكتروني"
          type="email"
          dir="ltr"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <Field
          label="كلمة المرور"
          type="password"
          dir="ltr"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <Button type="submit" loading={login.isPending} className="mt-2 w-full">
          تسجيل الدخول
        </Button>
      </form>
    </AuthCard>
  );
}
