import Link from "next/link";

import { Logo } from "@/components/logo";
import { buttonClass } from "@/components/ui/button";

const steps = [
  { title: "ارفعي الوثيقة", body: "لائحة، دليل طالب، سياسة شركة. ملفات PDF بالعربي أو الإنجليزي." },
  { title: "اسألي بلغتك", body: "اكتبي سؤالك كما تقولينه، بدون كلمات مفتاحية أو بحث يدوي." },
  { title: "تحقّقي من المصدر", body: "كل إجابة معها رقم الصفحة والفقرة، وتفتحين الصفحة بضغطة." },
];

export default function LandingPage() {
  return (
    <div className="flex min-h-full flex-1 flex-col">
      <header className="mx-auto flex w-full max-w-6xl items-center justify-between px-5 py-5">
        <Logo />
        <nav className="flex items-center gap-2">
          <Link href="/login" className={buttonClass("ghost")}>
            تسجيل الدخول
          </Link>
          <Link href="/register" className={buttonClass("primary")}>
            أنشئي حسابًا
          </Link>
        </nav>
      </header>

      <main className="mx-auto grid w-full max-w-6xl flex-1 items-center gap-14 px-5 py-12 lg:grid-cols-[1.05fr_1fr] lg:py-20">
        <section className="animate-rise">
          <p className="mb-4 inline-flex rounded-full bg-accent-soft px-3 py-1 text-[13px] font-semibold text-accent">
            إجابات موثّقة من وثائقك
          </p>
          <h1 className="text-[40px] font-bold leading-[1.25] tracking-tight sm:text-[52px]">
            اسألي اللائحة،
            <br />
            واعرفي الجواب ومكانه بالضبط.
          </h1>
          <p className="mt-5 max-w-[34rem] text-[18px] text-muted">
            دليل يقرأ وثائقك الطويلة ويجاوب على أسئلتك منها فقط. إذا ما لقى الجواب في الوثيقة، يقولك ذلك بدل ما يخمّن.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/register" className={buttonClass("primary", "h-12 px-6 text-[16px]")}>
              ابدئي مجانًا
            </Link>
            <Link href="/login" className={buttonClass("ghost", "h-12 px-6 text-[16px]")}>
              عندي حساب
            </Link>
          </div>
        </section>

        <ProductPreview />
      </main>

      <section className="mx-auto w-full max-w-6xl px-5 pb-20">
        <h2 className="mb-6 text-[22px] font-bold">كيف يشتغل</h2>
        <ol className="grid gap-4 sm:grid-cols-3">
          {steps.map((step, index) => (
            <li key={step.title} className="rounded-2xl border border-line bg-surface p-6">
              <span className="text-[13px] font-semibold text-accent">الخطوة {index + 1}</span>
              <h3 className="mt-2 text-[18px] font-bold">{step.title}</h3>
              <p className="mt-1.5 text-[15px] text-muted">{step.body}</p>
            </li>
          ))}
        </ol>
      </section>

      <footer className="border-t border-line py-6 text-center text-[13px] text-muted">
        دليل · مشروع مفتوح المصدر
      </footer>
    </div>
  );
}

/** An illustration of the product, drawn in code (labelled as an example, not real data). */
function ProductPreview() {
  return (
    <figure
      className="animate-rise rounded-3xl border border-line bg-surface p-5 shadow-[var(--shadow)] [animation-delay:60ms]"
      aria-label="مثال توضيحي لسؤال وإجابة موثّقة"
    >
      <div className="mb-4 flex items-center justify-between text-[13px] text-muted">
        <span>دليل الطالب.pdf</span>
        <span>مثال توضيحي</span>
      </div>
      <div className="ms-auto mb-4 w-fit max-w-[85%] rounded-2xl rounded-se-md bg-accent px-4 py-2.5 text-[15px] text-accent-ink">
        وش شروط التدريب التعاوني؟
      </div>
      <div className="rounded-2xl rounded-ss-md bg-surface-2 p-4 text-[15px] leading-7">
        يشترط إتمام 100 ساعة معتمدة على الأقل، ومعدل تراكمي لا يقل عن 2.5 نقطة<Cite n={1} />.
        ومدة التدريب ثمانية أسابيع متصلة<Cite n={2} />.
        <div className="mt-4 space-y-2 border-t border-line pt-3 text-[13px]">
          <Source n={1} page={42} text="يُشترط لتسجيل مقرر التدريب التعاوني أن يكون الطالب قد أتم…" />
          <Source n={2} page={43} text="تكون مدة التدريب التعاوني ثمانية أسابيع متصلة…" />
        </div>
      </div>
    </figure>
  );
}

function Cite({ n }: { n: number }) {
  return (
    <sup className="ms-0.5 [unicode-bidi:isolate] rounded bg-accent-soft px-1 text-[11px] font-semibold text-accent">{n}</sup>
  );
}

function Source({ n, page, text }: { n: number; page: number; text: string }) {
  return (
    <div className="flex items-start gap-2">
      <span className="mt-0.5 grid size-5 shrink-0 place-items-center rounded bg-accent-soft text-[11px] font-semibold text-accent">
        {n}
      </span>
      <p className="text-muted">
        <span className="font-semibold text-ink">صفحة {page}</span> · {text}
      </p>
    </div>
  );
}
