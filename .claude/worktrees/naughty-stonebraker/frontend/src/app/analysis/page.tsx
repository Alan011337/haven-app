"use client";

import Link from "next/link";
import { ArrowLeft, BarChart2 } from "lucide-react";

export default function AnalysisPage() {
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="mx-auto max-w-3xl">
        <Link
          href="/"
          className="mb-8 inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-gray-500 transition-colors hover:bg-white hover:text-gray-800"
        >
          <ArrowLeft className="h-4 w-4" />
          回首頁
        </Link>

        <div className="rounded-2xl border border-gray-100 bg-white p-10 text-center shadow-sm">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-indigo-50">
            <BarChart2 className="h-6 w-6 text-indigo-500" />
          </div>
          <h1 className="text-2xl font-bold text-gray-800">情緒分析</h1>
          <p className="mt-3 text-gray-500">
            這個功能正在優化中，下一版會提供更完整的趨勢與洞察。
          </p>
        </div>
      </div>
    </div>
  );
}
