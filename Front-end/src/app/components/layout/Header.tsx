import Link from "next/link";

export default function Header() {
  return (
    <header className="bg-white border-b border-gray-300">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="currentColor"
              className="h-8 w-8 text-indigo-600"
              aria-hidden="true"
            >
              <path d="M12 2a10 10 0 100 20 10 10 0 000-20z" opacity=".2" />
              <path d="M12 6a6 6 0 100 12 6 6 0 000-12z" />
            </svg>
            <span className="text-lg font-semibold text-black">가야금 디코더</span>
          </Link>

          <nav aria-label="Main navigation" className="hidden md:flex gap-6">
            <Link href="/" className="text-sm text-black hover:underline">
              사용방법
            </Link>
            <Link href="/about" className="text-sm text-black hover:underline">
              가격
            </Link>
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-black hover:underline"
            >
              문의
            </a>
          </nav>

          <div className="md:hidden">
            <button className="px-3 py-1 rounded-md text-sm hover:bg-gray-100 dark:hover:bg-gray-800">
              메뉴
            </button>
          </div>
        </div>
      </div>
    </header>
  );
} 