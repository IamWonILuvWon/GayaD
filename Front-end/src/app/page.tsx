"use client";

import { Upload, Youtube } from "lucide-react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { uploadWithProgress } from "@/src/features/upload/uploadWithProgress";
import FileUploader from "./components/ui/FileUploader";
import YoutubeLinkUploader from "./components/ui/YoutubeLinkUploader";

export default function Home() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [youtubeLink, setYoutubeLink] = useState("");
  const [select, setSelect] = useState(true);
  const [isConverting, setIsConverting] = useState(false);


  const canConvert = selectedFile || youtubeLink.trim() !== "";

  const router = useRouter();

  const handleConvert = async () => {
    if (!canConvert) return;
    setIsConverting(true);
    try {
      if (selectedFile) {
        // 먼저 job 생성 (파일 업로드는 뒤에서 비동기 처리)
        const createRes = await fetch("/api/jobs", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ filename: selectedFile.name }),
        });

        if (!createRes.ok) {
          const e2 = await createRes.json().catch(() => ({}));
          throw new Error(e2?.error || `작업 생성 실패: ${createRes.status}`);
        }

        const { jobId } = (await createRes.json()) as { jobId: string };

        // 업로드는 비동기로 시작 (실패 시 서버에 실패 상태를 보냄)
        uploadWithProgress({ file: selectedFile, jobId})
          .catch(async (err) => {
            try {
              await fetch(`/api/jobs/${jobId}/callback`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ status: "failed", error: err instanceof Error ? err.message : String(err) }),
              });
            } catch {}
            alert("업로드에 실패했습니다. 나중에 다시 시도해주세요.");
          });

        // 사용자는 즉시 job 페이지로 이동
        router.push(`/job/${jobId}`);
      } else if (youtubeLink.trim() !== "") {
      } else if (youtubeLink.trim() !== "") {
        // 유튜브 링크는 식별자 형식으로 전달
        const inputPath = `youtube:${youtubeLink.trim()}`;
        const jobRes = await fetch("/api/jobs", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ inputPath }),
        });
        if (!jobRes.ok) throw new Error("작업 생성 실패");
        const { jobId } = (await jobRes.json()) as { jobId: string };
        router.push(`/job/${jobId}`);
      }
    } catch (err) {
      alert(`오류가 발생했습니다: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setIsConverting(false);
    }
  };

  return (
    <main>
      <section>
        <div className="flex flex-col items-center pt-10 space-y-4">
          <p className="text-black text-3xl font-semibold">가야금 음원을 악보로 변환하세요</p>
          <p className="text-black">
            음성 파일 또는 유튜브 링크를 입력하면 자동으로 악보를 생성해드립니다
          </p>
        </div>
      </section>
      <section className="pt-10">
        <div className="mx-auto max-w-3xl flex rounded-xl bg-neutral-100 p-1">
          <button
            className={`flex flex-1 gap-2 justify-center items-center px-8 py-1 rounded-xl ${
              select ? "bg-white" : null
            }`}
            onClick={() => setSelect(true)}
          >
            <Upload size={20} />
            <p>파일 업로드</p>
          </button>
          <button
            className={`flex flex-1 gap-2 justify-center items-center px-8 py-1 rounded-xl ${
              select ? null : "bg-white"
            }`}
            onClick={() => setSelect(false)}
          >
            <Youtube size={20} />
            <p>유튜브 링크</p>
          </button>
        </div>
      </section>
      <section className="pt-3">
        {select ? (
          <FileUploader selectedFile={selectedFile} setSelectedFile={setSelectedFile} />
        ) : (
          <YoutubeLinkUploader youtubeLink={youtubeLink} setYoutubeLink={setYoutubeLink} />
        )}
        {canConvert && (
          <div className="mt-6 flex justify-center">
            <button
              onClick={handleConvert}
              disabled={isConverting}
              className={`px-8 py-3 rounded-lg transition-colors ${
                isConverting
                  ? "bg-gray-400 text-white cursor-not-allowed"
                  : "bg-blue-600 text-white hover:bg-blue-700"
              }`}
            >
              {isConverting ? "처리 중..." : "악보 변환하기"}
            </button>
          </div>
        )}
      </section>
    </main>
  );
}
