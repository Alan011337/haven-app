// frontend/src/app/settings/page.tsx
"use client";

import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import PartnerSettings from "@/components/features/PartnerSettings";

export default function SettingsPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-[#FDFBF9] p-6 flex flex-col">
      {/* 頂部導航 */}
      <div className="max-w-4xl mx-auto w-full mb-8">
        <button 
          onClick={() => router.push("/")} 
          className="group flex items-center text-slate-500 hover:text-slate-800 transition-colors font-medium px-4 py-2 rounded-xl hover:bg-white hover:shadow-sm"
        >
          <div className="bg-white p-1.5 rounded-lg shadow-sm border border-slate-100 mr-3 group-hover:border-slate-300 transition-colors">
             <ArrowLeft className="w-4 h-4"/>
          </div>
          回首頁
        </button>
      </div>

      {/* 主要內容區 */}
      <div className="flex-1 animate-in fade-in slide-in-from-bottom-8 duration-700">
        <PartnerSettings />
      </div>
    </div>
  );
}