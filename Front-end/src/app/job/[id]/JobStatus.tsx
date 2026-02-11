"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, CheckCircle, XCircle } from "lucide-react";
import dynamic from "next/dynamic";

const MusicXmlViewer = dynamic(() => import("../../components/ui/MusicXmlViewer.client"), { ssr: false });

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
  // Upload progress

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

  // musicxml viewer will be rendered client-side in a separate component

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

              {job.outputPath?.toLowerCase().endsWith(".musicxml") || job.outputPath?.toLowerCase().endsWith(".xml") ? (
                <div className="mt-4">
                  <p className="text-sm text-gray-700">악보 미리보기 (MusicXML):</p>
                  <div className="mt-2 rounded border p-3 bg-gray-50">
                    <MusicXmlViewer
                      url={
                        job.outputPath!.startsWith("http")
                          ? job.outputPath!
                          : `/api/results?path=${encodeURIComponent(job.outputPath!)}`
                      }
                    />
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
