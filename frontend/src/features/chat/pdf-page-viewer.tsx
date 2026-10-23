"use client";

import { useEffect, useRef, useState } from "react";

type Props = {
  documentId: string;
  pageNumber: number;
  // Rectangles [x0, y0, x1, y1] in PDF points, origin at the page's top-left (from PyMuPDF).
  boxes: number[][];
};

type State = { status: "loading" } | { status: "error" } | { status: "ready"; scale: number; pageCount: number };

/**
 * Renders one page of the user's PDF with pdf.js and highlights the cited passage on top.
 * pdf.js is loaded only when a viewer opens, so it does not slow down the rest of the app.
 */
export function PdfPageViewer({ documentId, pageNumber, boxes }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const firstBoxRef = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    let cleanup = () => {};

    async function render() {
      setState({ status: "loading" });
      const pdfjs = await import("pdfjs-dist");
      pdfjs.GlobalWorkerOptions.workerSrc = new URL("pdfjs-dist/build/pdf.worker.min.mjs", import.meta.url).toString();

      // Same origin, so the session cookie is sent and only the owner can load the file.
      const task = pdfjs.getDocument({ url: `/api/v1/documents/${documentId}/file`, withCredentials: true });
      cleanup = () => void task.destroy();
      const pdf = await task.promise;
      const page = await pdf.getPage(Math.min(pageNumber, pdf.numPages));

      const canvas = canvasRef.current;
      const container = containerRef.current;
      if (cancelled || !canvas || !container) return;

      const base = page.getViewport({ scale: 1 });
      const scale = container.clientWidth / base.width;
      const viewport = page.getViewport({ scale });
      const ratio = window.devicePixelRatio || 1; // sharp text on high-density screens
      canvas.width = Math.floor(viewport.width * ratio);
      canvas.height = Math.floor(viewport.height * ratio);
      canvas.style.width = `${viewport.width}px`;
      canvas.style.height = `${viewport.height}px`;

      await page.render({
        canvas,
        viewport,
        transform: ratio !== 1 ? [ratio, 0, 0, ratio, 0, 0] : undefined,
      }).promise;
      if (!cancelled) setState({ status: "ready", scale, pageCount: pdf.numPages });
    }

    render().catch(() => !cancelled && setState({ status: "error" }));
    return () => {
      cancelled = true;
      cleanup();
    };
  }, [documentId, pageNumber]);

  useEffect(() => {
    if (state.status === "ready") firstBoxRef.current?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [state.status]);

  return (
    // dir="ltr" matters: a canvas inherits the page's CSS direction, and in an RTL page the
    // browser re-orders the glyphs pdf.js draws, scrambling Arabic text. Page coordinates are
    // also left-to-right, so the highlight boxes use `left`, not the logical `start`.
    <div ref={containerRef} dir="ltr" className="relative w-full overflow-hidden rounded-xl bg-white shadow-[var(--shadow)]">
      <canvas ref={canvasRef} className="block" aria-label={`الصفحة ${pageNumber} من الوثيقة`} role="img" />
      {state.status === "ready" &&
        boxes.map(([x0, y0, x1, y1], index) => (
          <div
            key={index}
            ref={index === 0 ? firstBoxRef : undefined}
            data-testid="highlight"
            className="pointer-events-none absolute rounded-[3px] bg-[#f5c542]/35 ring-2 ring-[#e0a800]/70 mix-blend-multiply"
            style={{
              left: x0 * state.scale - 2,
              top: y0 * state.scale - 2,
              width: (x1 - x0) * state.scale + 4,
              height: (y1 - y0) * state.scale + 4,
            }}
          />
        ))}
      {state.status === "loading" && (
        <div className="flex aspect-[1/1.414] w-full items-center justify-center bg-surface-2" aria-busy>
          <span className="size-6 animate-spin rounded-full border-2 border-accent border-t-transparent" />
        </div>
      )}
      {state.status === "error" && (
        <div className="flex aspect-[1/1.414] w-full items-center justify-center bg-surface-2 p-6 text-center text-[15px] text-muted">
          تعذّر عرض الصفحة. تقدرين تفتحين الملف كامل من الرابط تحت.
        </div>
      )}
    </div>
  );
}
