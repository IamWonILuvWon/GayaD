"use client";

import { useState } from "react";
import { Upload, FileAudio } from "lucide-react";

type FileUploaderProps = {
  selectedFile: File | null;
  setSelectedFile: React.Dispatch<React.SetStateAction<File | null>>;
};

export default function FileUploader({ selectedFile, setSelectedFile }: FileUploaderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);
  const [stringCount, setStringCount] = useState<number>(12);

  const isAllowedFile = (file: File) => {
    const ext = file.name.split(".").pop()?.toLowerCase();
    const allowedExt = ["mp3", "wav", "m4a"];
    const allowedMime = ["audio/mpeg", "audio/wav", "audio/x-wav", "audio/mp4", "audio/x-m4a"];
    return (ext && allowedExt.includes(ext)) || allowedMime.includes(file.type);
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      const file = files[0];
      if (isAllowedFile(file)) {
        setSelectedFile(file);
        setFileError(null);
      } else {
        setFileError("MP3, WAV, M4A 파일만 업로드 가능합니다.");
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      const file = files[0];
      setSelectedFile(file);
      setFileError(null);
    }
  };

  return (
    <div
      className={`mx-auto max-w-3xl relative border-2 border-dashed rounded-lg p-12 transition-colors ${
        isDragging ? "border-blue-500 bg-blue-50" : "border-gray-300 bg-gray-50"
      }`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className="flex flex-col items-center justify-center  gap-4">
        <div className="inline-flex rounded-xl bg-neutral-100 p-1">
          <button
            className={`px-4 py-1 rounded-xl text-sm ${
              stringCount === 12 ? "bg-white font-medium" : ""
            }`}
            onClick={() => setStringCount(12)}
            aria-pressed={stringCount === 12}
          >
            12현
          </button>
          <button
            className={`px-4 py-1 rounded-xl text-sm ${
              stringCount === 18 ? "bg-white font-medium" : ""
            }`}
            onClick={() => setStringCount(18)}
            aria-pressed={stringCount === 18}
          >
            18현
          </button>
          <button
            className={`px-4 py-1 rounded-xl text-sm ${
              stringCount === 25 ? "bg-white font-medium" : ""
            }`}
            onClick={() => setStringCount(25)}
            aria-pressed={stringCount === 25}
          >
            25현
          </button>
        </div>
        {selectedFile ? (
          <>
            <FileAudio className="w-12 h-12 text-green-600" />
            <div className="text-center">
              <p className="text-gray-900">{selectedFile.name}</p>
              <p className="text-sm text-gray-500">
                {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
              </p>
            </div>
            <button
              onClick={() => setSelectedFile(null)}
              className="text-sm text-gray-600 hover:text-gray-900 underline"
            >
              다른 파일 선택
            </button>
          </>
        ) : (
          <>
            <Upload className="w-12 h-12 text-gray-400" />
            <div className="text-center">
              <p className="text-gray-900 mb-1">파일을 드래그하거나 클릭하여 업로드</p>
              <p className="text-sm text-gray-500">MP3, WAV, M4A 파일 지원</p>
            </div>
            <label className="cursor-pointer">
              <input type="file" className="hidden" accept="audio/*" onChange={handleFileChange} />
              <span className="inline-block px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                파일 선택
              </span>
            </label>
          </>
        )}
      </div>
      {fileError ? (
        <p className="absolute bottom-3 left-7 text-sm text-red-600" role="alert">
          {fileError}
        </p>
      ) : null}
    </div>
  );
}
