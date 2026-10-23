"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { AuthCard, FormError } from "@/features/auth/auth-card";
import { useRegister } from "@/features/auth/hooks";
import { errorMessage } from "@/lib/api/errors";

type Errors = Partial<Record<"name" | "email" | "password", string>>;

/** Same rules as the backend schema, checked early so users get instant feedback. */
function validate(name: string, email: string, password: string): Errors {
  const errors: Errors = {};
  if (name.trim().length < 2) errors.name = "الاسم لازم يكون حرفين على الأقل.";
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errors.email = "أدخلي بريدًا إلكترونيًا صحيحًا.";
  if (password.length < 8) errors.password = "كلمة المرور لازم تكون 8 أحرف على الأقل.";
  return errors;
}

export default function RegisterPage() {
  const router = useRouter();
  const register = useRegister();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<Errors>({});

  function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    const found = validate(name, email, password);
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    register.mutate({ name, email, password }, { onSuccess: () => router.replace("/dashboard") });
  }

  return (
    <AuthCard
      title="إنشاء حساب"
      subtitle="حساب واحد، وكل وثائقك خاصة فيك."
      footer={{ text: "عندك حساب؟", linkLabel: "سجّلي الدخول", href: "/login" }}
    >
      <FormError message={register.isError ? errorMessage(register.error) : null} />
      <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
        <Field
          label="الاسم"
          autoComplete="name"
          value={name}
          error={errors.name}
          onChange={(e) => setName(e.target.value)}
        />
        <Field
          label="البريد الإلكتروني"
          type="email"
          dir="ltr"
          autoComplete="email"
          value={email}
          error={errors.email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <Field
          label="كلمة المرور"
          type="password"
          dir="ltr"
          autoComplete="new-password"
          value={password}
          error={errors.password}
          hint="8 أحرف على الأقل."
          onChange={(e) => setPassword(e.target.value)}
        />
        <Button type="submit" loading={register.isPending} className="mt-2 w-full">
          إنشاء الحساب
        </Button>
      </form>
    </AuthCard>
  );
}
