import { useId, type InputHTMLAttributes } from "react";

type Props = InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string; hint?: string };

/** Labelled input with an accessible error message (linked via aria-describedby). */
export function Field({ label, error, hint, className = "", ...rest }: Props) {
  const id = useId();
  const messageId = `${id}-message`;
  const message = error ?? hint;
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-[15px] font-medium">
        {label}
      </label>
      <input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={message ? messageId : undefined}
        className={
          "h-11 rounded-xl border bg-surface px-3.5 text-[16px] text-ink outline-none transition-colors " +
          "placeholder:text-muted/70 focus:border-accent focus:ring-2 focus:ring-accent/25 " +
          (error ? "border-danger" : "border-line") +
          ` ${className}`
        }
        {...rest}
      />
      {message && (
        <p id={messageId} className={`text-[13px] ${error ? "text-danger" : "text-muted"}`}>
          {message}
        </p>
      )}
    </div>
  );
}
