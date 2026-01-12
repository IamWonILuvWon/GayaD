"use client";

import { useEffect, useRef } from "react";

export default function PdfCanvas({ url }: { url: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    let canceled = false;

    async function render() {
      // ✅ 브라우저에서만 pdfjs 로드
      const pdfjsLib = await import("pdfjs-dist");

      pdfjsLib.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";

      const pdf = await pdfjsLib.getDocument(url).promise;
      const page = await pdf.getPage(1);

      if (canceled) return;

      const viewport = page.getViewport({ scale: 1.5 });
      const canvas = canvasRef.current!;
      const ctx = canvas.getContext("2d")!;

      canvas.width = viewport.width;
      canvas.height = viewport.height;

      await page.render({
        canvas,
        canvasContext: ctx,
        viewport,
      }).promise;
    }

    render();

    return () => {
      canceled = true;
    };
  }, [url]);

  return <canvas ref={canvasRef} />;
}
