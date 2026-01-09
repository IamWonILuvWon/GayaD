import { useEffect, useState } from "react";

type Job = {
  id: string;
  status: "queued" | "processing" | "completed" | "failed";
  outputPath?: string | null;
  error?: string | null;
};

export function useJob(jobId: string | null) {
  const [job, setJob] = useState<Job | null>(null);

  useEffect(() => {
    if (!jobId) return;

    let alive = true;
    const tick = async () => {
      const res = await fetch(`/api/jobs/${jobId}`, { cache: "no-store" });
      if (!res.ok) return;
      const data = (await res.json()) as Job;
      if (!alive) return;
      setJob(data);

      // 완료/실패면 폴링 중단
      if (data.status === "completed" || data.status === "failed") return;

      setTimeout(tick, 1000);
    };

    tick();
    return () => {
      alive = false;
    };
  }, [jobId]);

  return job;
}
