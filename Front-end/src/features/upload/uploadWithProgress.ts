export function uploadWithProgress(opts: {
  file: File;
  jobId?: string;
}): Promise<{ inputPath: string }> {
  const { file, jobId } = opts;

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    const url = `/api/jobs/upload?filename=${encodeURIComponent(file.name)}${jobId ? `&jobId=${encodeURIComponent(jobId)}` : ""}`;
    xhr.open("POST", url);

    const bc = typeof BroadcastChannel !== "undefined" && jobId ? new BroadcastChannel("job-progress") : null;

    // 업로드 진행률
    xhr.upload.onprogress = (e) => {
      if (!e.lengthComputable) return;
      const percent = Math.round((e.loaded / e.total) * 100);
      try { bc?.postMessage({ jobId, percent }); } catch {}
    };

    xhr.onload = () => {
      try {
        if (xhr.status < 200 || xhr.status >= 300) {
          bc?.close();
          reject(new Error(`Upload failed: ${xhr.status}`));
          return;
        }
        const data = JSON.parse(xhr.responseText) as { inputPath: string };
        try { bc?.postMessage({ jobId, percent: 100 }); } catch {}
        bc?.close();
        resolve(data);
      } catch (err) {
        bc?.close();
        reject(err);
      }
    };

    xhr.onerror = () => {
      bc?.close();
      reject(new Error("Network error during upload"));
    };

    // file 자체를 body로 보냄(지금 서버가 req.arrayBuffer()로 받는 구조와 동일)
    xhr.send(file);
  });
} 
