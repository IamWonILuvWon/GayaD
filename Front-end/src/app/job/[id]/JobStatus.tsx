"use client";

import { useEffect, useState } from "react";
import { Loader2, CheckCircle, XCircle } from "lucide-react";

type Job = {
  id: string;
  status: string;
  inputPath: string;
  outputPath?: string | null;
  createdAt: string;
  updatedAt: string;
};

export default function JobStatus({ jobId }: { jobId: string }) {
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchJob = async () => {
    try {
      const res = await fetch(`/api/jobs/${jobId}`);
      if (!res.ok) {
        const e = await res.json().catch(() => ({}));
        setError(e?.error || `Failed to fetch job: ${res.status}`);
        return;
      }
      const data = await res.json();
      setJob(data);
      setError(null);
    } catch (err) {
      console.error(err);
      setError("네트워크 오류가 발생했습니다.");
    }
  };

  useEffect(() => {
    fetchJob();
    const iv = setInterval(fetchJob, 2000);
    return () => clearInterval(iv);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  const statusIsRunning = (s?: string) => s === "queued" || s === "processing";

  return (
    <div className="w-full max-w-3xl mx-auto p-8 bg-white rounded-lg shadow">
      <h2 className="text-2xl font-semibold mb-4">작업 상태</h2>

      {error ? (
        <p className="text-red-600">{error}</p>
      ) : job ? (
        <div className="space-y-4">
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

          <div>
            <p className="text-sm text-gray-700">
              입력: <code className="text-xs">{job.inputPath}</code>
            </p>
          </div>

          {job.outputPath ? (
            <div className="">
              <p className="text-sm text-gray-700">출력 결과:</p>
              <a
                className="inline-block mt-2 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                href={job.outputPath}
                target="_blank"
                rel="noreferrer"
              >
                악보 다운로드
              </a>
            </div>
          ) : null}

          {statusIsRunning(job.status) ? (
            <p className="text-sm text-gray-500">처리 중입니다. 잠시만 기다려주세요…</p>
          ) : null}
        </div>
      ) : (
        <p className="text-gray-500">로딩 중...</p>
      )}
    </div>
  );
}
