"use client";

import { Link } from "lucide-react";

type YoutubeLinkUploaderProps = {
  youtubeLink: string;
  setYoutubeLink: React.Dispatch<React.SetStateAction<string>>;
};

export default function YoutubeLinkUploader({
  youtubeLink,
  setYoutubeLink,
}: YoutubeLinkUploaderProps) {
  return (
    <div className="mx-auto max-w-3xl border-2 border-gray-300 bg-gray-50 rounded-lg p-12">
      <div className="flex flex-col items-center justify-center gap-4">
        <Link className="w-12 h-12 text-gray-400" />
        <div className="text-center w-full">
          <p className="text-gray-900 mb-4">유튜브 영상 링크를 입력하세요</p>
          <input
            type="text"
            placeholder="https://www.youtube.com/watch?v=..."
            value={youtubeLink}
            onChange={e => setYoutubeLink(e.target.value)}
            className="w-full max-w-md px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-sm text-gray-500 mt-2">가야금 연주 영상의 URL을 붙여넣으세요</p>
        </div>
      </div>
    </div>
  );
}
