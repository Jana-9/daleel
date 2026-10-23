// Arabic text with Western digits, matching the rest of the interface.
const LOCALE = "ar-u-nu-latn";

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} بايت`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} كيلوبايت`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} ميجابايت`;
}

const dateFormatter = new Intl.DateTimeFormat(LOCALE, { day: "numeric", month: "long", year: "numeric" });

export function formatDate(iso: string): string {
  return dateFormatter.format(new Date(iso));
}

export function pagesLabel(count: number): string {
  if (count === 1) return "صفحة واحدة";
  if (count === 2) return "صفحتان";
  if (count >= 3 && count <= 10) return `${count} صفحات`;
  return `${count} صفحة`;
}
