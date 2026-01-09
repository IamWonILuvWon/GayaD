"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, CheckCircle, XCircle } from "lucide-react";

type JobStatusType = "queued" | "processing" | "completed" | "failed" | "uploading";

type Job = {
  id: string;
  status: JobStatusType;
  inputPath: string;
  outputPath?: string | null;
  error?: string | null;
  createdAt: string;
  updatedAt: string;
};

export default function JobStatus({ id }: { id: string }) {
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  // PDF viewer state
  const [pdfNumPages, setPdfNumPages] = useState<number | null>(null);
  const [pdfCurrentPage, setPdfCurrentPage] = useState<number>(1);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // ✅ pdfjs 모듈을 state/ref로 들고 있음(브라우저에서만 로드)
  const pdfjsRef = useRef<typeof import("pdfjs-dist") | null>(null);

  const fetchJob = async () => {
    try {
      const res = await fetch(`/api/jobs/${id}`, { cache: "no-store" });
      if (!res.ok) {
        const e = await res.json().catch(() => ({}));
        setError(e?.error || `Failed to fetch job: ${res.status}`);
        return;
      }
      const data = (await res.json()) as Job;
      setJob(data);
      setError(null);
    } catch {
      setError("네트워크 오류가 발생했습니다.");
    }
  };

  // ✅ job polling (네 로직 유지)
  useEffect(() => {
    let canceled = false;
    let timeoutId: number | null = null;

    const tick = async () => {
      await fetchJob();
      if (canceled) return;

      const s = (job?.status ?? "queued") as JobStatusType;
      const running = s === "queued" || s === "processing" || s === "uploading";
      if (running) timeoutId = window.setTimeout(tick, 1500);
    };

    tick();
    return () => {
      canceled = true;
      if (timeoutId) window.clearTimeout(timeoutId);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, job?.status]);

  // ✅ pdfjs를 브라우저에서만 로드 + worker 설정
  useEffect(() => {
    let cancelled = false;

    (async () => {
      // window가 없으면(서버) 실행 X
      if (typeof window === "undefined") return;

      const pdfjsLib = await import("pdfjs-dist");
      if (cancelled) return;

      // worker 파일은 public에 있어야 함 (/public/pdf.worker.min.mjs)
      pdfjsLib.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";
      pdfjsRef.current = pdfjsLib;
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  // PDF 로드 및 렌더 (여기서 pdfjsRef 사용)
  useEffect(() => {
    let cancelled = false;

    async function loadPdfAndRender() {
      if (!job?.outputPath) return;
      if (!job.outputPath.toLowerCase().endsWith(".pdf")) return;

      const pdfjsLib = pdfjsRef.current;
      if (!pdfjsLib) return; // pdfjs 로딩 전이면 대기

      setPdfError(null);
      setPdfLoading(true);

      try {
        const url = job.outputPath.startsWith("http")
          ? job.outputPath
          : `/api/results?path=${encodeURIComponent(job.outputPath)}`;

        const res = await fetch(url);
        if (!res.ok) throw new Error(`Failed to fetch pdf: ${res.status}`);
        const buf = await res.arrayBuffer();

        const pdf = await pdfjsLib.getDocument({ data: buf }).promise;
        if (cancelled) return;

        setPdfNumPages(pdf.numPages);

        const current = Math.max(1, Math.min(pdf.numPages, pdfCurrentPage));
        if (current !== pdfCurrentPage) setPdfCurrentPage(current);

        const page = await pdf.getPage(current);
        if (cancelled) return;

        const viewport = page.getViewport({ scale: 1.5 });
        const canvas = canvasRef.current;
        if (!canvas) return;

        canvas.width = viewport.width;
        canvas.height = viewport.height;

        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        await page.render({ canvas, canvasContext: ctx, viewport }).promise;
      } catch (err) {
        setPdfError(err instanceof Error ? err.message : String(err));
      } finally {
        setPdfLoading(false);
      }
    }

    loadPdfAndRender();

    return () => {
      cancelled = true;
    };
  }, [job?.outputPath, pdfCurrentPage]);

  // outputPath 바뀌면 초기화
  useEffect(() => {
    setPdfNumPages(null);
    setPdfCurrentPage(1);
    setPdfError(null);
  }, [job?.outputPath]);

  // BroadcastChannel 업로드 진행률 수신
  useEffect(() => {
    if (typeof BroadcastChannel === "undefined") return;
    const bc = new BroadcastChannel("job-progress");
    const handler = (e: MessageEvent) => {
      const data = e.data as { jobId?: string; percent?: number } | undefined;
      if (!data) return;
      if (data.jobId !== id) return;
      setUploadProgress(typeof data.percent === "number" ? data.percent : null);
    };
    bc.addEventListener("message", handler);
    return () => {
      bc.removeEventListener("message", handler);
      bc.close();
    };
  }, [id]);

  // job 상태가 업로드가 아닐 때 진행률 초기화
  useEffect(() => {
    if (job?.status !== "uploading") setUploadProgress(null);
  }, [job?.status]);

  const statusIsRunning = (s?:string) => s === 'queued' || s === "processing" || s === "uploading";

  const downloadHref = job?.outputPath
    ? job.outputPath.startsWith("http")
      ? job.outputPath
      : `/api/results?path=${encodeURIComponent(job.outputPath)}`
    : null;

  return (
    <div className="w-full max-w-3xl mx-auto p-8 bg-white rounded-lg shadow">
      <h2 className="text-2xl font-semibold mb-4">작업 상태</h2>

      {error ? (
        <p className="text-red-600">{error}</p>
      ) : job ? (
        <div className="space-y-4">
          {/* 업로드 진행률 표시 */}
          {job.status === "uploading" && (
            <div className="w-full">
              <p className="text-sm text-gray-600">업로드 중… {uploadProgress ?? 0}%</p>
              <div className="w-full bg-gray-200 rounded h-2 mt-1 overflow-hidden">
                <div className="bg-blue-600 h-2" style={{ width: `${uploadProgress ?? 0}%` }} />
              </div>
            </div>
          )}

          {/* ... (여기부터는 네 UI 그대로 두면 됨) ... */}
          <div className="flex items-center gap-3">
            {statusIsRunning(job.status) ? (
              <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
            ) : job.status === "completed" ? (
              <CheckCircle className="w-8 h-8 text-green-600" />
            ) : (
              <XCircle className="w-8 h-8 text-red-600" />
            )}
            <div>
              <p className="font-medium">
                상태: <span className="font-semibold">{job.status}</span>
              </p>
              <p className="text-sm text-gray-500">
                업데이트: {new Date(job.updatedAt).toLocaleString()}
              </p>
            </div>
          </div>
          {downloadHref ? (
            <div>
              <p className="text-sm text-gray-700">출력 결과:</p>
              <a
                className="inline-block mt-2 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                href={downloadHref}
                target="_blank"
                rel="noreferrer"
              >
                악보 다운로드
              </a>

              {job.outputPath?.toLowerCase().endsWith(".pdf") ? (
                <div className="mt-4">
                  <p className="text-sm text-gray-700">PDF 미리보기:</p>

                  <div className="mt-2 rounded border p-3 bg-gray-50">
                    <div className="flex items-center gap-2 mb-2">
                      <button
                        className="px-3 py-1 rounded bg-gray-200 hover:bg-gray-300"
                        onClick={() => setPdfCurrentPage((p) => Math.max(1, p - 1))}
                        disabled={pdfCurrentPage <= 1}
                      >
                        이전
                      </button>
                      <button
                        className="px-3 py-1 rounded bg-gray-200 hover:bg-gray-300"
                        onClick={() =>
                          setPdfCurrentPage((p) => (pdfNumPages ? Math.min(pdfNumPages, p + 1) : p + 1))
                        }
                        disabled={pdfNumPages ? pdfCurrentPage >= pdfNumPages : false}
                      >
                        다음
                      </button>

                      <div className="ml-auto text-sm text-gray-500">
                        {pdfLoading ? "로딩 중…" : pdfNumPages ? `${pdfCurrentPage} / ${pdfNumPages}` : "-"}
                      </div>
                    </div>

                    {pdfError ? (
                      <div className="text-sm text-red-600">PDF 렌더링 오류: {pdfError}</div>
                    ) : (
                      <div className="w-full flex justify-center">
                        <canvas ref={canvasRef} className="max-w-full" />
                      </div>
                    )}
                  </div>
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : (
        <p className="text-gray-500">로딩 중...</p>
      )}
    </div>
  );
}
